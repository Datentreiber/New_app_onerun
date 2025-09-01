# app.py — Talk2Earth (Agents SDK + Streamlit) — FIXED IMPORT + STREAMLIT RUNNER MODE
import os
import re
import json
import pathlib
import subprocess
from typing import Optional, List

import streamlit as st

BASE_DIR = pathlib.Path(__file__).parent.resolve()

# ===== Agents SDK (korrekt) ===================================================
# pip install openai-agents openai
AGENTS_OK = True
try:
    from agents import Agent, Runner, function_tool
    from agents.models.openai_responses import OpenAIResponsesModel
    from openai import AsyncOpenAI
except Exception as e:
    AGENTS_OK = False
    AGENTS_IMPORT_ERROR = str(e)

# ===== Prompts laden (du lieferst die Dateien separat; hier Fallbacks) ========
def load_text_file(path: pathlib.Path, fallback: str = "") -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return fallback

PROMPTS_DIR = BASE_DIR / "knowledge" / "prompts"
MASTER_PROMPT = load_text_file(
    PROMPTS_DIR / "layer1_master.md",
    fallback="You are an EO analyst agent. Always output full Streamlit apps with interactive AOI/time/params widgets."
)
GATES_PROMPT = load_text_file(
    PROMPTS_DIR / "gates.md",
    fallback="Before answering, self-check Q1..Q5 and fix violations in the same turn."
)
ITERATION_PROMPT = load_text_file(
    PROMPTS_DIR / "iteration.md",
    fallback="When existing code is present, treat it as source of truth; apply only requested minimal changes; output full updated Streamlit code."
)

# ===== FS Layout ==============================================================
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

# ===== Tools (Function Tools) =================================================
@function_tool
def tool_list_packs(kind: str, domain: Optional[str] = None) -> str:
    """
    Listet verfügbare Pack-IDs.
    kind: "usecases" | "domains" | "negatives"
    domain: optionaler Filter (nur usecases)
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
    """Gibt den YAML-Inhalt eines Packs zurück."""
    for folder in (USECASES_DIR, DOMAINS_DIR, NEGATIVES_DIR):
        f = folder / f"{pack_id}.yml"
        if f.exists():
            return f.read_text(encoding="utf-8")
    return json.dumps({"error": f"pack '{pack_id}' not found"})

@function_tool
def tool_get_component(component_id: str) -> str:
    """Gibt den Python-Text (.py.txt) einer Komponente zurück."""
    f = COMPONENTS_DIR / f"{component_id}.py.txt"
    if f.exists():
        return f.read_text(encoding="utf-8")
    return json.dumps({"error": f"component '{component_id}' not found"})

@function_tool
def tool_get_util(util_id: str) -> str:
    """Gibt den Python-Text (.py.txt) eines Utils zurück."""
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
    Führt Code in der Sandbox aus.
    - mode="script":  python file.py (stdout/stderr zurück)
    - mode="streamlit": streamlit run file.py --server.headless true --server.port {port}
                        → gibt url & pid zurück (Logs gekürzt)
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

    elif mode == "streamlit":
        # Startet Streamlit headless auf festem Port; gibt URL & PID zurück
        try:
            proc = subprocess.Popen(
                ["streamlit", "run", str(target), "--server.headless", "true", "--server.port", str(port)],
                cwd=SANDBOX_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            # kleine Wartezeit, um erste Logs zu sammeln
            try:
                stdout = proc.stdout.readline().strip() if proc.stdout else ""
            except Exception:
                stdout = ""
            url = f"http://localhost:{port}"
            return json.dumps({
                "ok": True,
                "url": url,
                "pid": proc.pid,
                "path": str(target),
                "hint": "Öffne die URL im Browser. Beende den Prozess manuell bei Bedarf.",
                "mode": "streamlit",
                "bootstrap_log": stdout[-2000:]
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({
                "ok": False,
                "error": f"Failed to start streamlit: {e}",
                "path": str(target),
                "mode": "streamlit"
            }, ensure_ascii=False)

    else:
        return json.dumps({"error": f"unknown mode '{mode}'"})

# ===== Agent Setup ============================================================
if AGENTS_OK:
    openai_client = AsyncOpenAI()  # liest OPENAI_API_KEY aus Env/Secrets
    agent = Agent(
        name="EO-Agent",
        instructions="\n\n".join([MASTER_PROMPT, GATES_PROMPT, ITERATION_PROMPT]),
        tools=[tool_list_packs, tool_get_pack, tool_get_component, tool_get_util, tool_run_python],
        model=OpenAIResponsesModel(model=os.environ.get("OPENAI_MODEL", "gpt-4o"), openai_client=openai_client),
    )

# ===== Streamlit UI ===========================================================
st.set_page_config(page_title="talk2earth (Agents SDK)", layout="wide")
st.title("talk2earth — EO Agent (Agents SDK + Streamlit)")

with st.sidebar:
    st.subheader("Status")
    st.write("Agents SDK:", "✅ bereit" if AGENTS_OK else f"❌ {AGENTS_IMPORT_ERROR}")
    st.write("OPENAI_API_KEY gesetzt:", "✅" if os.environ.get("OPENAI_API_KEY") else "❌")
    st.divider()
    st.subheader("Knowledge Packs")
    try:
        uc_ids = json.loads(tool_list_packs("usecases"))
        st.write("Use-Cases:", ", ".join(uc_ids.get("ids", [])))
        dom_ids = json.loads(tool_list_packs("domains"))
        st.write("Domains:", ", ".join(dom_ids.get("ids", [])))
    except Exception as e:
        st.warning(f"Packs-Auflistung fehlgeschlagen: {e}")
    st.caption("AOI/Zeitraum/Parameter werden in den generierten Apps interaktiv bereitgestellt.")

if "history" not in st.session_state:
    st.session_state.history = []
if "last_code" not in st.session_state:
    st.session_state.last_code = ""

def extract_first_python_block(text: str) -> Optional[str]:
    m = re.search(r"```(?:python)?\s*(.+?)```", text, flags=re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else None

user_text = st.text_area("Deine Anfrage", placeholder="z.B. 'Cool Spots Sommer 2023 in München, Top 10%'", height=130)
c1, c2, c3 = st.columns([1,1,1])
fire = c1.button("Generieren (Code)", type="primary")
run_script = c2.button("Run (script)")
run_streamlit = c3.button("Run (streamlit)")

if fire and user_text.strip():
    if not AGENTS_OK:
        st.error("Agents SDK nicht verfügbar. Bitte `openai-agents` installieren.")
    else:
        iteration_context = ""
        if st.session_state.last_code:
            iteration_context = f"\n\n[EXISTING_CODE_BEGIN]\n{st.session_state.last_code}\n[EXISTING_CODE_END]\n"
        result = Runner.run_sync(agent, input=(user_text + iteration_context))
        answer = result.final_output or ""
        st.session_state.history.append(("assistant", answer))
        code_block = extract_first_python_block(answer)
        if code_block:
            st.session_state.last_code = code_block

st.subheader("Generierter Code")
st.code(st.session_state.last_code or "# Noch kein Code generiert.", language="python")

if run_script and st.session_state.last_code:
    with st.spinner("Runner (script)…"):
        res = json.loads(tool_run_python(st.session_state.last_code, mode="script"))  # type: ignore
    st.write(res)

if run_streamlit and st.session_state.last_code:
    with st.spinner("Runner (streamlit)…"):
        res = json.loads(tool_run_python(st.session_state.last_code, filename="app_streamlit.py", mode="streamlit", port=8502))  # type: ignore
    st.write(res)
    if res.get("ok") and res.get("url"):
        st.success(f"App läuft: {res['url']}  (PID: {res.get('pid')})")

st.divider()
st.subheader("Verlauf (letzte 6)")
for role, text in st.session_state.history[-6:]:
    if role == "assistant":
        st.markdown(text)
