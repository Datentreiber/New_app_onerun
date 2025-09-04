# app.py — talk2earth (Agents SDK + Streamlit) — Chat-UI, Function Tools, Streamlit-Runner
from __future__ import annotations

import os
import re
import json
import pathlib
import subprocess
import hashlib
from typing import Optional, List, Dict, Any

import streamlit as st
import asyncio  # für Event-Loop-Fix

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

# ===== Pfade / Repo-Layout (neu konsolidiert) =================================
KNOWLEDGE_DIR = BASE_DIR / "knowledge"
PROMPTS_DIR = KNOWLEDGE_DIR / "prompts"
META_INDEX_PATH = KNOWLEDGE_DIR / "meta" / "layer1_index.yml"   # L1.1 (Alltagssprache)
POLICY_PATH = KNOWLEDGE_DIR / "policy.json"                     # L2 (strict JSON)
USECASES_DIR = KNOWLEDGE_DIR / "usecases"                       # L1.2 (pro UC)

BLOCKS_DIR = BASE_DIR / "blocks"
COMPONENTS_DIR = BLOCKS_DIR / "components"
LEGACY_DIR = COMPONENTS_DIR / "legacy"                          # blockieren beim Bundling

RUNNER_DIR = BASE_DIR / "runner"
SANDBOX_DIR = RUNNER_DIR / "sandbox"
SANDBOX_DIR.mkdir(parents=True, exist_ok=True)

# ===== Prompt laden (NEU: nur mega_prompt.md) =================================
def load_text_file(path: pathlib.Path, fallback: str = "") -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return fallback

MEGA_PROMPT = load_text_file(
    PROMPTS_DIR / "mega_prompt.md",
    fallback=(
        "SYSTEM: Du bist ein einzelner Gesprächs-Agent, der Mini-Apps baut (GEE-first, UI optional). "
        "Arbeite L1.1→L1.2→L2→L3, nutze die Tools tool_get_meta, tool_get_policy, tool_get_uc_sections, "
        "tool_bundle_components, tool_run_python. AOI als strukturierte Spec, kein Textparser. "
        "Erzeuge vor Code eine PLAN_SPEC (JSON) und bundle dann exakt die benötigten Komponenten."
    )
)

# ===== Hilfsfunktionen ========================================================
def _sha1_text(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:10]

def _safe_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False)

def _is_legacy(p: pathlib.Path) -> bool:
    return (LEGACY_DIR in p.parents) or p.name.startswith("fs_")

def _repo_rel(path: pathlib.Path) -> str:
    try:
        return str(path.relative_to(BASE_DIR))
    except Exception:
        return str(path)

def _ls_usecase_ids() -> List[str]:
    if not USECASES_DIR.exists():
        return []
    return sorted([p.stem for p in USECASES_DIR.glob("*.yml")])

# ===== Neue Function Tools (prompt-first, keine alten Pack-Tools) =============

@function_tool
def tool_get_meta() -> str:
    """
    Load global Layer1.1 meta index (single YAML as text).
    Returns the full knowledge/meta/layer1_index.yml content (UTF-8).
    """
    if not META_INDEX_PATH.exists():
        return _safe_json({"error": f"meta index not found: {META_INDEX_PATH}"})
    return META_INDEX_PATH.read_text(encoding="utf-8")

@function_tool
def tool_get_policy() -> str:
    """
    Load global Layer2 policy (strict JSON as text).
    Returns the content of knowledge/policy.json (UTF-8).
    """
    if not POLICY_PATH.exists():
        return _safe_json({"error": f"policy not found: {POLICY_PATH}"})
    return POLICY_PATH.read_text(encoding="utf-8")

@function_tool
def tool_get_uc_sections(uc_id: str, sections: List[str]) -> str:
    """
    Load specific sections from a UC YAML.
    Allowed sections include:
      param_spec, invariants, visualize_presets, allowed_patterns,
      ui_contracts, render_pattern, capabilities_required,
      capabilities_provided, checks.
    Returns JSON with only the requested sections, or {"error": "..."}.
    """
    try:
        import yaml  # lazy import (verhindert Start-Crash, falls PyYAML fehlt)
    except Exception:
        return _safe_json({
            "error": "missing_dependency",
            "detail": "PyYAML is required. Add 'pyyaml' to requirements.txt."
        })

    uc_path = USECASES_DIR / f"{uc_id}.yml"
    if not uc_path.exists():
        return _safe_json({"error": f"unknown UC '{uc_id}'"})
    try:
        data = yaml.safe_load(uc_path.read_text(encoding="utf-8")) or {}
    except Exception as e:
        return _safe_json({"error": f"yaml parse error: {e}"})

    out: Dict[str, Any] = {}
    for sec in sections or []:
        if sec in data:
            out[sec] = data[sec]
    return _safe_json(out)

@function_tool
def tool_bundle_components(components: List[str]) -> str:
    """
    Load multiple component files and return a single concatenated string plus a manifest.
    Input: components -> relative repo paths, e.g. 'blocks/components/gee/aoi_from_spec.py'
    Rejects legacy/fs_*.
    Returns JSON:
      {
        "bundle": "<concatenated files with BEGIN/END headers>",
        "manifest": [{"id": path, "sha1": "...", "bytes": N}, ...]
      }
    """
    bundle_parts: List[str] = []
    manifest: List[Dict[str, Any]] = []

    for rel in components or []:
        p = (BASE_DIR / rel).resolve()
        # scope guard
        if not str(p).startswith(str(BASE_DIR)):
            return _safe_json({"error": f"component outside repo scope: {rel}"})
        if _is_legacy(p):
            return _safe_json({"error": f"legacy component not allowed: {rel}"})
        if not p.exists():
            return _safe_json({"error": f"component not found: {rel}"})

        txt = p.read_text(encoding="utf-8")
        h = _sha1_text(txt)
        header = f"\n# ==== BEGIN COMPONENT: {rel} (sha1:{h}) ====\n"
        footer = f"\n# ==== END COMPONENT: {rel} ====\n"
        bundle_parts.append(header + txt + footer)
        manifest.append({"id": rel, "sha1": h, "bytes": len(txt.encode("utf-8"))})

    return _safe_json({"bundle": "\n".join(bundle_parts), "manifest": manifest})

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
        instructions=MEGA_PROMPT,
        tools=[tool_get_meta, tool_get_policy, tool_get_uc_sections, tool_bundle_components, tool_run_python],
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
    st.subheader("Knowledge (debug)")
    try:
        ucs = _ls_usecase_ids()
        st.caption("Use-Cases: " + (", ".join(ucs) if ucs else "—"))
        st.caption("Meta-Index: " + (_repo_rel(META_INDEX_PATH) if META_INDEX_PATH.exists() else "not found"))
        st.caption("Policy: " + (_repo_rel(POLICY_PATH) if POLICY_PATH.exists() else "not found"))
    except Exception as e:
        st.warning(f"Debug-Auflistung fehlgeschlagen: {e}")
    st.divider()
    st.caption("Hinweis: AOI/Zeitraum/Parameter werden im Dialog geklärt; der Agent bündelt Komponenten vor dem Code.")

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
        answer = "**Fehler:** Agents SDK nicht verfügbar. Bitte SDK installieren/konfigurieren und Server neu starten."
    else:
        iteration_context = ""
        if st.session_state.last_code:
            iteration_context = f"\n\n[EXISTING_CODE_BEGIN]\n{st.session_state.last_code}\n[EXISTING_CODE_END]\n"
        history_note = ""
        if st.session_state.messages[:-1]:
            history_note = "\n\n[HISTORY NOTE] Continue this session; respond naturally and follow iteration rules.\n"

        # Sicherstellen, dass ein Event-Loop existiert (Streamlit-Thread)
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
