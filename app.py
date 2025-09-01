import os
import re
import json
import pathlib
import subprocess
from typing import Optional, List, Dict, Any

import streamlit as st

# === Agents SDK (korrekt) ===
# Installation: pip install openai-agents openai
# Doku: function tools + Runner.run_sync + Responses model
from openai-agents import Agent, Runner, function_tool  # :contentReference[oaicite:1]{index=1}
from openai-agents import WebSearchTool, FileSearchTool  # optional; wir registrieren sie nicht standardmäßig
from openai-agents.ref.models.openai_responses import OpenAIResponsesModel  # Responses Model (optional) :contentReference[oaicite:2]{index=2}
from openai import AsyncOpenAI

BASE_DIR = pathlib.Path(__file__).parent.resolve()

# -------------------------------
# Helper: Prompts laden (mit Fallbacks, weil du sie "außerhalb" lieferst)
# -------------------------------
def load_text_file(path: pathlib.Path, fallback: str = "") -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return fallback

PROMPTS_DIR = BASE_DIR / "knowledge" / "prompts"  # existiert bei dir; Inhalte lieferst du selbst
MASTER_PROMPT = load_text_file(
    PROMPTS_DIR / "layer1_master.md",
    fallback="You are an EO analyst agent. Always provide Streamlit code with interactive AOI/time/params widgets."
)
GATES_PROMPT = load_text_file(
    PROMPTS_DIR / "gates.md",
    fallback="Before answering, self-check Q1..Q5 and fix violations in the same turn."
)
ITERATION_PROMPT = load_text_file(
    PROMPTS_DIR / "iteration.md",
    fallback="When existing code is present, treat it as source of truth and apply minimal, requested changes only."
)

# -------------------------------
# Tooling: Packs/Blocks aus dem Dateisystem laden
# -------------------------------

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

@function_tool
def tool_list_packs(kind: str, domain: Optional[str] = None) -> str:
    """
    Listet verfügbare Pack-IDs.
    Args:
        kind: "usecases" | "domains" | "negatives"
        domain: optionaler Filter für Use-Cases (Domain im YAML-Feld "domain")
    Returns:
        JSON-String mit {"ids": [...]} oder {"ids":[...], "filtered":[...]}.
    """
    result = {"ids": []}
    if kind == "usecases":
        ids = _ls_ids(USECASES_DIR, ".yml")
        if domain:
            filtered = []
            for uid in ids:
                data = (USECASES_DIR / f"{uid}.yml").read_text(encoding="utf-8")
                # einfacher Filter
                if f"domain: {domain}" in data or f"domain: '{domain}'" in data or f'domain: "{domain}"' in data:
                    filtered.append(uid)
            result["ids"] = ids
            result["filtered"] = filtered
        else:
            result["ids"] = ids
    elif kind == "domains":
        result["ids"] = _ls_ids(DOMAINS_DIR, ".yml")
    elif kind == "negatives":
        result["ids"] = _ls_ids(NEGATIVES_DIR, ".yml")
    else:
        result["ids"] = []
    return json.dumps(result, ensure_ascii=False)

@function_tool
def tool_get_pack(pack_id: str) -> str:
    """
    Liefert den Pack-Inhalt (YAML) als String.
    Args:
        pack_id: Dateistamm unter knowledge/usecases|domains|negatives
    Returns:
        YAML-Text als String (oder Fehlermeldung).
    """
    for folder in (USECASES_DIR, DOMAINS_DIR, NEGATIVES_DIR):
        f = folder / f"{pack_id}.yml"
        if f.exists():
            return f.read_text(encoding="utf-8")
    return f"# ERROR: pack '{pack_id}' not found"

@function_tool
def tool_get_component(component_id: str) -> str:
    """
    Liefert den Inhalt eines Komponenten-Blocks (.py.txt) als String.
    Args:
        component_id: Dateistamm unter blocks/components ohne .py.txt
    Returns:
        Python-Text (String) oder Fehlermeldung.
    """
    f = COMPONENTS_DIR / f"{component_id}.py.txt"
    if f.exists():
        return f.read_text(encoding="utf-8")
    return f"# ERROR: component '{component_id}' not found"

@function_tool
def tool_get_util(util_id: str) -> str:
    """
    Liefert Utils (.py.txt) als String.
    Args:
        util_id: Dateistamm unter blocks/utils ohne .py.txt
    """
    f = UTILS_DIR / f"{util_id}.py.txt"
    if f.exists():
        return f.read_text(encoding="utf-8")
    return f"# ERROR: util '{util_id}' not found"

@function_tool
def tool_run_python(code: str, filename: Optional[str] = None, timeout_sec: int = 600) -> str:
    """
    Führt Python-Code im Runner/Sandbox aus. Schreibt 'code' in Datei und startet Subprozess.
    Args:
        code: Vollständiger Python-Skripttext (z. B. generierte Streamlit-freie Logik oder eigenes CLI).
        filename: Optionaler Dateiname (ohne Pfad); default 'app_run.py'
        timeout_sec: Timeout
    Returns:
        JSON-String mit {"ok": bool, "stdout": str, "stderr": str, "path": str}
    """
    if not filename:
        filename = "app_run.py"
    target = SANDBOX_DIR / filename
    target.write_text(code, encoding="utf-8")
    # Subprozess ausführen
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
            "stdout": proc.stdout[-15000:],  # tail zur Sicherheit
            "stderr": proc.stderr[-15000:],
            "path": str(target)
        }, ensure_ascii=False)
    except subprocess.TimeoutExpired as e:
        return json.dumps({
            "ok": False,
            "stdout": e.stdout or "",
            "stderr": f"TIMEOUT after {timeout_sec}s",
            "path": str(target)
        }, ensure_ascii=False)

# -------------------------------
# Agent Setup (Responses-Model + Tools)
# -------------------------------
# Offiziell: Runner.run_sync | Function Tools | Responses Model (korrekt) :contentReference[oaicite:3]{index=3}
openai_client = AsyncOpenAI()  # nutzt OPENAI_API_KEY aus Env

agent = Agent(
    name="EO-Agent",
    instructions="\n\n".join([MASTER_PROMPT, GATES_PROMPT, ITERATION_PROMPT]),
    tools=[tool_list_packs, tool_get_pack, tool_get_component, tool_get_util, tool_run_python],
    model=OpenAIResponsesModel(model="gpt-4o", openai_client=openai_client),
)

# -------------------------------
# Streamlit UI
# -------------------------------
st.set_page_config(page_title="talk2earth (Agents SDK)", layout="wide")
st.title("talk2earth — EO Agent (Agents SDK + Streamlit)")

with st.sidebar:
    st.markdown("### Packs")
    uc_ids = json.loads(tool_list_packs("usecases"))  # type: ignore
    st.write("Use-Cases:", ", ".join(uc_ids.get("ids", [])))
    dom_ids = json.loads(tool_list_packs("domains"))  # type: ignore
    st.write("Domains:", ", ".join(dom_ids.get("ids", [])))
    st.divider()
    st.caption("Hinweis: AOI/Zeitraum/Parameter werden später in der **generierten** App interaktiv bereitgestellt.")

if "history" not in st.session_state:
    st.session_state.history = []  # [(role, text)]
if "last_code" not in st.session_state:
    st.session_state.last_code = ""

def extract_first_python_block(text: str) -> Optional[str]:
    # ```python ... ```  oder ``` ... ```
    m = re.search(r"```(?:python)?\s*(.+?)```", text, flags=re.DOTALL|re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None

with st.container():
    user_text = st.text_area("Deine Anfrage", placeholder="z.B. 'Kühlste 10% Flächen im Sommer in München anzeigen (Landsat LST)'", height=120)
    col1, col2, col3 = st.columns([1,1,1])
    fire = col1.button("Generieren (Code)")
    runn = col2.button("Im Runner ausführen")
    clear = col3.button("Reset Gespräch")

    if clear:
        st.session_state.history = []
        st.session_state.last_code = ""
        st.experimental_rerun()

    if fire and user_text.strip():
        # Wenn es schon existierenden Code gibt, injizieren wir ihn als Kontext (Iteration-Regel)
        iteration_context = ""
        if st.session_state.last_code:
            iteration_context = (
                "\n\n[EXISTING_CODE_BEGIN]\n" +
                st.session_state.last_code +
                "\n[EXISTING_CODE_END]\n"
            )
        # Ein Turn mit dem Agent (die Agent-Loop handled Tools selbst) :contentReference[oaicite:4]{index=4}
        result = Runner.run_sync(agent, input=(user_text + iteration_context))
        answer = result.final_output or ""
        st.session_state.history.append(("assistant", answer))
        code_block = extract_first_python_block(answer)
        if code_block:
            st.session_state.last_code = code_block

    if runn and st.session_state.last_code:
        with st.spinner("Runner wird ausgeführt..."):
            run_res_json = tool_run_python(st.session_state.last_code)  # type: ignore
            run_res = json.loads(run_res_json)
            st.subheader("Runner Ergebnis")
            st.write("OK:", run_res.get("ok"))
            st.text_area("stdout", run_res.get("stdout", ""), height=200)
            st.text_area("stderr", run_res.get("stderr", ""), height=200)
            st.code(st.session_state.last_code, language="python")

st.divider()
st.subheader("Verlauf")
for role, text in st.session_state.history[-6:]:
    if role == "assistant":
        st.markdown(text)

