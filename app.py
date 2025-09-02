# app.py — talk2earth (Agents SDK + Streamlit) — mit Inline-Mini-App Runner 
# Vollständige Chat-UI mit Function-Tools, echter Agents-Session, Code-Runner (script/streamlit) + INLINE-RUNNER
import os
import re
import json
import uuid
import pathlib
import subprocess
from typing import Optional, List

import streamlit as st
import asyncio  # Event-Loop-Fix für Streamlit-Thread

BASE_DIR = pathlib.Path(__file__).parent.resolve()

# ===== Agents SDK korrekt importieren =========================================
AGENTS_OK = True
try:
    from agents import Agent, Runner, function_tool, SQLiteSession
    from agents.models.openai_responses import OpenAIResponsesModel
    from openai import AsyncOpenAI
except Exception as e:
    AGENTS_OK = False
    AGENTS_IMPORT_ERROR = str(e)

# ===== Prompts laden (Fallbacks, falls Dateien fehlen) ========================
def load_text_file(path: pathlib.Path, fallback: str = "") -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return fallback

PROMPTS_DIR = BASE_DIR / "knowledge" / "prompts"
MASTER_PROMPT = load_text_file(
    PROMPTS_DIR / "layer1_master.md",
    fallback=(
        "You are the only Composer/Planner. Source allowed patterns and few-shot blocks; "
        "derive a strict phase plan (Scaffold→Map/UI→Acquire→(Process)→Reduce→Visualize→Render); "
        "then write the complete Streamlit app from scratch, 1:1 to the references, no inventions."
    )
)
GATES_PROMPT = load_text_file(
    PROMPTS_DIR / "gates.md",
    fallback="Enforce: single Scaffold first; one acquire chain; exact visuals; one render path; no alternative params."
)
ITERATION_PROMPT = load_text_file(
    PROMPTS_DIR / "iteration.md",
    fallback="Ask at most one focused question only if a required choice within one UC is missing. Otherwise single-pass."
)
CHEATSHEET_PROMPT = load_text_file(
    PROMPTS_DIR / "composer_cheatsheet.md",
    fallback=(
        "# Composer Cheatsheet\n"
        "1) tool_list_packs('usecases') → UC wählen\n"
        "2) tool_get_pack(UC) → invariants/allowed_patterns/few_shot_components\n"
        "3) Für jede ID in few_shot_components: tool_get_component(ID)\n"
        "4) Layer-2: Phasenplan (Scaffold→Map→Acquire→(Process)→Reduce→Visualize→Render)\n"
        "5) Layer-3: Vollständigen Streamlit-Code neu schreiben (keine Erfindungen)\n"
        "6) Fehler/Nullfälle wie in Vorlagen behandeln.\n"
    )
)

# ===== FS-Pfade ===============================================================
KNOWLEDGE_DIR = BASE_DIR / "knowledge"
USECASES_DIR = KNOWLEDGE_DIR / "usecases"
DOMAINS_DIR = KNOWLEDGE_DIR / "domains"
NEGATIVES_DIR = KNOWLEDGE_DIR / "negatives"

BLOCKS_DIR = BASE_DIR / "blocks"
COMPONENTS_DIR = BLOCKS_DIR / "components"
UTILS_DIR = BLOCKS_DIR / "utils"

RUNNER_DIR = BASE_DIR / "runner"
SANDBOX_DIR = RUNNER_DIR / "sandbox"
SANDBOX_DIR.mkdir(parents=True, exist_ok=True)

def _ls_ids(folder: pathlib.Path, suffix: str) -> List[str]:
    if not folder.exists():
        return []
    return [p.stem for p in sorted(folder.glob(f"*{suffix}"))]

# ===== Function Tools (Agents SDK) ============================================
@function_tool
def tool_list_packs(kind: str, domain: Optional[str] = None) -> str:
    """
    List available pack IDs.
    kind: "usecases" | "domains" | "negatives"
    domain: optional filter (usecases only)
    """
    res = {"ids": []}
    if kind == "usecases":
        ids = _ls_ids(USECASES_DIR, ".yml")
        if domain:
            filtered = []
            for uid in ids:
                data = (USECASES_DIR / f"{uid}.yml").read_text(encoding="utf-8")
                if f"domain: {domain}" in data or f"domain: '{domain}'" in data or f'domain: "{domain}"' in data:
                    filtered.append(uid)
            res["ids"] = ids
            res["filtered"] = filtered
        else:
            res["ids"] = ids
    elif kind == "domains":
        res["ids"] = _ls_ids(DOMAINS_DIR, ".yml")
    elif kind == "negatives":
        res["ids"] = _ls_ids(NEGATIVES_DIR, ".yml")
    else:
        return json.dumps({"error": f"unknown kind '{kind}'"})
    return json.dumps(res, ensure_ascii=False)

@function_tool
def tool_get_pack(pack_id: str) -> str:
    """Return YAML content of a pack (usecases/domains/negatives)."""
    for folder in (USECASES_DIR, DOMAINS_DIR, NEGATIVES_DIR):
        f = folder / f"{pack_id}.yml"
        if f.exists():
            return f.read_text(encoding="utf-8")
    return json.dumps({"error": f"pack '{pack_id}' not found"})

@function_tool
def tool_get_component(component_id: str) -> str:
    """Return Python text of a component (.py preferred, fallback .py.txt)."""
    for ext in (".py", ".py.txt"):
        f = COMPONENTS_DIR / f"{component_id}{ext}"
        if f.exists():
            return f.read_text(encoding="utf-8")
    return json.dumps({"error": f"component '{component_id}' not found"})

@function_tool
def tool_list_components(prefix: Optional[str] = None) -> str:
    """
    List available component IDs (fs_*). Accepts .py and .py.txt. Optional prefix filter.
    """
    ids = set()
    if COMPONENTS_DIR.exists():
        for p in COMPONENTS_DIR.glob("*.py"):
            ids.add(p.stem)
        for p in COMPONENTS_DIR.glob("*.py.txt"):
            ids.add(p.stem)
    out = sorted([i for i in ids if not prefix or i.startswith(prefix)])
    return json.dumps({"ids": out}, ensure_ascii=False)

@function_tool
def tool_get_util(util_id: str) -> str:
    """Return Python text of a util helper (.py preferred, fallback .py.txt)."""
    for ext in (".py", ".py.txt"):
        f = UTILS_DIR / f"{util_id}{ext}"
        if f.exists():
            return f.read_text(encoding="utf-8")
    return json.dumps({"error": f"util '{util_id}' not found"})

@function_tool
def tool_run_python(code: str,
                    filename: Optional[str] = None,
                    timeout_sec: int = 600,
                    mode: str = "script",
                    port: int = 8502) -> str:
    """
    Execute code inside runner/sandbox.
    - mode="script": python file.py (returns stdout/stderr)
    - mode="streamlit": streamlit run file.py --server.headless --server.port {port}
                        (returns url + pid + short bootstrap log)
    Hinweis: Auf Streamlit Cloud ist die zweite Streamlit-Instanz i. d. R. NICHT sichtbar.
    """
    if not filename:
        filename = "app_run.py"
    target = SANDBOX_DIR / filename
    target.write_text(code, encoding="utf-8")

    if mode == "script":
        try:
            proc = subprocess.run(
                ["python", str(target)],
                cwd=SANDBOX_DIR,
                capture_output=True,
                text=True,
                timeout=timeout_sec
            )
            return json.dumps({
                "ok": proc.returncode == 0,
                "stdout": proc.stdout[-15000:],
                "stderr": proc.stderr[-15000:],
                "path": str(target),
                "mode": "script"
            }, ensure_ascii=False)
        except subprocess.TimeoutExpired as e:
            return json.dumps({
                "ok": False,
                "stdout": (getattr(e, "stdout", "") or "")[-15000:],
                "stderr": f"TIMEOUT after {timeout_sec}s",
                "path": str(target),
                "mode": "script"
            }, ensure_ascii=False)

    if mode == "streamlit":
        try:
            proc = subprocess.Popen(
                ["streamlit", "run", str(target), "--server.headless", "true", "--server.port", str(port)],
                cwd=SANDBOX_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            try:
                bootstrap = proc.stdout.readline().strip() if proc.stdout else ""
            except Exception:
                bootstrap = ""
            url = f"http://localhost:{port}"
            return json.dumps({
                "ok": True,
                "url": url,
                "pid": proc.pid,
                "path": str(target),
                "hint": "Auf Streamlit Cloud meist nicht sichtbar (zweite Instanz). Inline-Runner nutzen.",
                "mode": "streamlit",
                "bootstrap_log": bootstrap[-2000:]
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({
                "ok": False,
                "error": f"Failed to start streamlit: {e}",
                "path": str(target),
                "mode": "streamlit"
            }, ensure_ascii=False)

    return json.dumps({"error": f"unknown mode '{mode}'"})

# ===== Async-Loop-Sicherung (Fix für Runner.run_sync in Streamlit-Thread) =====
def ensure_event_loop() -> None:
    """
    Stellt sicher, dass im aktuellen Thread ein asyncio-Event-Loop vorhanden ist.
    Notwendig, weil Streamlit Code in einem ScriptRunner-Thread ohne Default-Loop ausführt.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

# ===== INLINE RUNNER: führt Mini-App im aktuellen Streamlit aus ===============
def run_mini_app_inline(code: str, container: "st.delta_generator.DeltaGenerator") -> None:
    """
    Führt den übergebenen Streamlit-Code inline innerhalb des angegebenen Containers aus.
    - Unterdrückt st.set_page_config (No-Op), um Doppelaufrufe zu vermeiden.
    - Setzt __name__="__main__", damit 'if __name__ == "__main__":' in generiertem Code greift.
    - Führt den Code unter 'with container:' aus, damit alle st.*-Ausgaben im Mini-App-Bereich landen.
    """
    # Spätimport (damit die App ohne EE/Geemap auch startet)
    try:
        import ee
    except Exception:
        ee = None
    try:
        import geemap
        import geemap.foliumap as geemap_folium
        from geemap.foliumap import Map
    except Exception:
        geemap = None
        geemap_folium = None
        Map = None
    try:
        import folium
    except Exception:
        folium = None

    # st.set_page_config patchen → No-Op
    original_set_page_config = st.set_page_config
    try:
        st.set_page_config = lambda *a, **k: None  # No-Op im Mini-App-Kontext

        # Ausführung im Ziel-Container
        with container:
            # Separater Namespace mit __main__-Semantik
            exec_globals = {
                "__name__": "__main__",
                "st": st,
                "ee": ee,
                "geemap": geemap,
                "folium": folium,
            }
            # Optional bequeme Aliase, falls der Code sie direkt importfrei nutzt
            if geemap_folium:
                exec_globals["geemap_folium"] = geemap_folium
            if Map:
                exec_globals["Map"] = Map

            try:
                exec(code, exec_globals)
            except Exception as e:
                st.error(f"Mini-App exception: {e}")
                st.exception(e)
    finally:
        # Patch zurücksetzen
        st.set_page_config = original_set_page_config

# ===== Agent Setup + echte SDK-Session ========================================
if AGENTS_OK:
    openai_client = AsyncOpenAI()  # liest OPENAI_API_KEY

    agent = Agent(
        name="EO-Agent",
        instructions="\n\n".join([MASTER_PROMPT, GATES_PROMPT, ITERATION_PROMPT, CHEATSHEET_PROMPT]),
        tools=[tool_list_packs, tool_get_pack, tool_get_component, tool_list_components, tool_get_util, tool_run_python],
        model=OpenAIResponsesModel(model=os.environ.get("OPENAI_MODEL", "gpt-4o"), openai_client=openai_client),
    )

# ===== Streamlit: echtes Chat-Interface ======================================
st.set_page_config(page_title="talk2earth — EO Agent", layout="wide")
st.title("talk2earth — EO Agent (Agents SDK + Streamlit)")

with st.sidebar:
    st.subheader("Status")
    st.write("Agents SDK:", "✅ bereit" if AGENTS_OK else f"❌ {AGENTS_IMPORT_ERROR}")
    st.write("OPENAI_API_KEY gesetzt:", "✅" if os.environ.get("OPENAI_API_KEY") else "❌")
    st.divider()
    st.subheader("Knowledge Packs (debug)")
    try:
        # Debug-Listing OHNE Tool-Call (FunctionTool ist nicht direkt aufrufbar)
        ucs = {"ids": _ls_ids(USECASES_DIR, ".yml")}
        st.caption("Use-Cases: " + ", ".join(ucs["ids"]))
        doms = {"ids": _ls_ids(DOMAINS_DIR, ".yml")}
        st.caption("Domains: " + ", ".join(doms["ids"]))
    except Exception as e:
        st.warning(f"Packs-Auflistung fehlgeschlagen: {e}")
    st.divider()
    st.caption("Hinweis: AOI/Zeitraum/Parameter werden in den **generierten Apps** interaktiv bereitgestellt.")

# Chat-Speicher (UI) — unabhängig von der SDK-Session
if "messages" not in st.session_state:
    st.session_state.messages = []  # [{"role":"user"/"assistant","content":str}]
if "last_code" not in st.session_state:
    st.session_state.last_code = ""
if "agent_session_id" not in st.session_state:
    # per Browser-Session eine stabile ID
    st.session_state.agent_session_id = uuid.uuid4().hex

# SDK-Session herstellen (ohne externe DB)
# Option A: in-memory (flüchtig) — SQLiteSession(session_id)  → db_path=":memory:"
# Option B: Datei im Container — bleibt erhalten solange der App-Prozess/Container lebt
try:
    SESSIONS_DB = str((RUNNER_DIR / "sessions.db").resolve())
    sdk_session = SQLiteSession(st.session_state.agent_session_id, SESSIONS_DB)
    with st.sidebar:
        st.caption(f"Session: {st.session_state.agent_session_id[:8]}… (SQLite @ {SESSIONS_DB})")
except Exception as e:
    sdk_session = SQLiteSession(st.session_state.agent_session_id)  # in-memory fallback
    with st.sidebar:
        st.warning(f"SDK-Session init: Fallback in-memory ({e})")

# Verlauf (UI) rendern
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

def extract_first_python_block(text: str) -> Optional[str]:
    m = re.search(r"```(?:python)?\s*(.+?)```", text, flags=re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else None

# Chat-Eingabe
prompt = st.chat_input("Nachricht an den Agenten eingeben und mit Enter senden…")
if prompt:
    # 1) User Nachricht anzeigen/speichern
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2) Agent call mit Iterations-Injektion + echter SDK-Session
    if not AGENTS_OK:
        answer = "**Fehler:** Agents SDK nicht verfügbar. Bitte `pip install openai-agents openai` und den Server neu starten."
    else:
        iteration_context = ""
        if st.session_state.last_code:
            iteration_context = f"\n\n[EXISTING_CODE_BEGIN]\n{st.session_state.last_code}\n[EXISTING_CODE_END]\n"
        history_note = ""
        if st.session_state.messages[:-1]:
            history_note = "\n\n[HISTORY NOTE] Continue this session; respond naturally and follow iteration rules.\n"

        # Event-Loop sicherstellen
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            asyncio.set_event_loop(asyncio.new_event_loop())

        # >>> WICHTIG: echte SDK-Session übergeben
        result = Runner.run_sync(
            agent,
            input=(prompt + history_note + iteration_context),
            session=sdk_session
        )
        answer = result.final_output or ""

    # 3) Assistant-Antwort rendern — NUR Code, wenn vorhanden; sonst Markdown
    code_block = extract_first_python_block(answer)
    if code_block:
        st.session_state.last_code = code_block
        with st.chat_message("assistant"):
            st.code(code_block, language="python")
    else:
        with st.chat_message("assistant"):
            st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})

    # 4) Falls Code erkannt: Run-Buttons + Inline-Mini-App
    if code_block:
        st.write("---")
        st.subheader("Erkannter Code aus der letzten Antwort")

        c1, c2, c3 = st.columns(3)
        if c1.button("Run inline (empfohlen)"):
            mini_container = st.container()
            with st.spinner("Starte Mini-App inline…"):
                run_mini_app_inline(code_block, mini_container)

        if c2.button("Run in Runner (script)"):
            with st.spinner("Runner (script)…"):
                res = json.loads(tool_run_python(code_block, mode="script"))  # type: ignore
            st.write(res)

        if c3.button("Run in Runner (streamlit)"):
            with st.spinner("Runner (streamlit)…"):
                res = json.loads(tool_run_python(code_block, filename="agent_streamlit.py", mode="streamlit", port=8502))  # type: ignore
            st.write(res)
            if res.get("ok") and res.get("url"):
                st.info("Hinweis: Auf Streamlit Cloud ist die zweite Instanz in der Regel nicht erreichbar.")
                st.success(f"Lokale URL (falls lokal ausgeführt): {res['url']}  (PID: {res.get('pid')})")
