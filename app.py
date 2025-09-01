# app.py — talk2earth (Agents SDK + Streamlit) — Chat-UI, Function Tools, Streamlit-Runner
import os
import re
import json
import pathlib
import subprocess
from typing import Optional, List

import streamlit as st
import asyncio  # <— NEU: für Event-Loop-Fix

BASE_DIR = pathlib.Path(__file__).parent.resolve()

# ===== Agents SDK korrekt importieren =========================================
AGENTS_OK = True
try:
    from agents import Agent, Runner, function_tool
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
        "You are an EO analyst agent. Always output full Streamlit apps with interactive AOI/time/params widgets. "
        "Ask at most one semantic question only if a fixed, non-interactive output would otherwise be wrong."
    )
)
GATES_PROMPT = load_text_file(
    PROMPTS_DIR / "gates.md",
    fallback="Before answering, self-check Q1..Q5 and fix violations in the same turn."
)
ITERATION_PROMPT = load_text_file(
    PROMPTS_DIR / "iteration.md",
    fallback="When existing code is present, treat it as source of truth; apply only requested minimal changes; output full updated Streamlit code."
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
    """Return Python text (.py.txt) of a component."""
    f = COMPONENTS_DIR / f"{component_id}.py.txt"
    if f.exists():
        return f.read_text(encoding="utf-8")
    return json.dumps({"error": f"component '{component_id}' not found"})

@function_tool
def tool_get_util(util_id: str) -> str:
    """Return Python text (.py.txt) of a util helper."""
    f = UTILS_DIR / f"{util_id}.py.txt"
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
                "stdout": (e.stdout or "")[-15000:],
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
            # kleine Wartezeit: eine Zeile lesen (nicht blockieren)
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
                "hint": "Öffne die URL im Browser. Beende den Prozess bei Bedarf manuell.",
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

# ===== Agent Setup ============================================================
if AGENTS_OK:
    openai_client = AsyncOpenAI()  # liest OPENAI_API_KEY
    agent = Agent(
        name="EO-Agent",
        instructions="\n\n".join([MASTER_PROMPT, GATES_PROMPT, ITERATION_PROMPT]),
        tools=[tool_list_packs, tool_get_pack, tool_get_component, tool_get_util, tool_run_python],
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
        ucs = json.loads(tool_list_packs("usecases"))
        st.caption("Use-Cases: " + ", ".join(ucs.get("ids", [])))
        doms = json.loads(tool_list_packs("domains"))
        st.caption("Domains: " + ", ".join(doms.get("ids", [])))
    except Exception as e:
        st.warning(f"Packs-Auflistung fehlgeschlagen: {e}")
    st.divider()
    st.caption("Hinweis: AOI/Zeitraum/Parameter werden in den **generierten Apps** interaktiv bereitgestellt.")

# Chat-Speicher
if "messages" not in st.session_state:
    st.session_state.messages = []  # [{"role":"user"/"assistant","content":str}]
if "last_code" not in st.session_state:
    st.session_state.last_code = ""

# Verlauf rendern
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

def extract_first_python_block(text: str) -> Optional[str]:
    m = re.search(r"```(?:python)?\s*(.+?)```", text, flags=re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else None

# Chat-Eingabe (richtiger „Senden“-Flow)
prompt = st.chat_input("Nachricht an den Agenten eingeben und mit Enter senden…")
if prompt:
    # 1) User Nachricht anzeigen/speichern
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2) Agent call (mit optionaler Iterations-Injektion)
    if not AGENTS_OK:
        answer = "**Fehler:** Agents SDK nicht verfügbar. Bitte `pip install openai-agents openai` und den Server neu starten."
    else:
        iteration_context = ""
        if st.session_state.last_code:
            iteration_context = f"\n\n[EXISTING_CODE_BEGIN]\n{st.session_state.last_code}\n[EXISTING_CODE_END]\n"
        history_note = ""
        if st.session_state.messages[:-1]:
            history_note = "\n\n[HISTORY NOTE] Continue this session; respond naturally and follow iteration rules.\n"

        # >>>> FIX: Sicherstellen, dass ein Event-Loop existiert (Streamlit-Thread)
        ensure_event_loop()

        result = Runner.run_sync(agent, input=(prompt + history_note + iteration_context))
        answer = result.final_output or ""

    # 3) Assistant Nachricht rendern
    with st.chat_message("assistant"):
        st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})

    # 4) Falls Code dabei: extrahieren und separat anzeigen + Run-Buttons einblenden
    code_block = extract_first_python_block(answer)
    if code_block:
        st.session_state.last_code = code_block
        st.write("---")
        st.subheader("Erkannter Code aus der letzten Antwort")
        st.code(code_block, language="python")
        c1, c2 = st.columns(2)
        if c1.button("Run in Runner (script)"):
            with st.spinner("Runner (script)…"):
                res = json.loads(tool_run_python(code_block, mode="script"))  # type: ignore
            st.write(res)
        if c2.button("Run in Runner (streamlit)"):
            with st.spinner("Runner (streamlit)…"):
                res = json.loads(tool_run_python(code_block, filename="agent_streamlit.py", mode="streamlit", port=8502))  # type: ignore
            st.write(res)
            if res.get("ok") and res.get("url"):
                st.success(f"App läuft: {res['url']}  (PID: {res.get('pid')})")
