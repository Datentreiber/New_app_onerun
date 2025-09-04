# app.py
# -----------------------------------------------------------------------------
# Streamlit chat app using the existing Agents SDK shell — updated to the new
# 4-layer approach (L1.1 → L1.2 → L2 → L3) with:
#   • NEW tools: tool_get_meta, tool_get_policy, tool_get_uc_sections,
#                tool_bundle_components
#   • KEPT tool: tool_run_python (inline/script/streamlit runner)
#   • REMOVED (not exposed anymore): tool_list_packs, tool_get_pack
#   • DO NOT use per-component function calls from the LLM; instead the agent
#     prepares a Layer-2 PLAN_SPEC and then calls tool_bundle_components ONCE
#     to load all needed snippets as a single string into context.
#
# Notes:
# - This file assumes your existing "Agents SDK" decorator & Runner are available.
# - If import names differ in your SDK, adjust the three marked lines below.
# - The rest of the app structure (chat, session, inline runner) stays the same.
# -----------------------------------------------------------------------------

from __future__ import annotations

import io
import json
import os
import re
import sys
import time
import yaml
import shutil
import base64
import hashlib
import textwrap
import traceback
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Tuple

import streamlit as st

# ====== ADAPT THESE IMPORTS to your Agents SDK (3 lines) ======================
# Example: from openai_agents import agent, tool, Runner
try:
    from openai_agents import agent, tool, Runner  # <-- adjust if your SDK differs
except Exception:  # soft fallback for local editing; in prod your SDK is present
    def tool(*dargs, **dkwargs):
        def _decorator(f):
            return f
        return _decorator

    class Runner:  # minimal stub — your real Runner is used at runtime
        @staticmethod
        def run_sync(agent_obj, input: str, session: Dict[str, Any]):
            return {"final_output": "Runner stub: no SDK available", "new_items": []}

    class agent:  # minimal stub
        @staticmethod
        def create(instructions: str, tools: List[Any]):
            return {"instructions": instructions, "tools": tools}
# ==============================================================================


# -----------------------------------------------------------------------------
# Paths (repo layout)
# -----------------------------------------------------------------------------
ROOT = Path(__file__).parent.resolve()
KNOW = ROOT / "knowledge"
META_PATH = KNOW / "meta" / "layer1_index.yml"
POLICY_PATH = KNOW / "policy.json"
UCS_DIR = KNOW / "usecases"

COMP_DIR = ROOT / "blocks" / "components"
LEGACY_DIR = COMP_DIR / "legacy"

RUNNER_DIR = ROOT / "runner"
SANDBOX_DIR = RUNNER_DIR / "sandbox"
SANDBOX_DIR.mkdir(parents=True, exist_ok=True)

PROMPTS_DIR = KNOW / "prompts"
MEGA_PROMPT = PROMPTS_DIR / "mega_prompt.md"   # << put your new mega prompt here


# -----------------------------------------------------------------------------
# Streamlit page config (kept behavior)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Mini-Apps — One Run",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# -----------------------------------------------------------------------------
# Utilities
# -----------------------------------------------------------------------------
def _sha1_text(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:10]


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _safe_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False)


def _ensure_exists(path: Path, kind: str):
    if not path.exists():
        raise FileNotFoundError(f"{kind} not found: {path}")


def _is_legacy(p: Path) -> bool:
    return (LEGACY_DIR in p.parents) or p.name.startswith("fs_")


# -----------------------------------------------------------------------------
# NEW TOOLS — exactly as specified
# -----------------------------------------------------------------------------

@tool(name="tool_get_meta", description="Load global Layer1.1 meta index (single YAML).")
def tool_get_meta() -> str:
    """Return the complete layer1_index.yml as text (UTF-8)."""
    _ensure_exists(META_PATH, "meta index")
    return _read_text(META_PATH)


@tool(name="tool_get_policy", description="Load global Layer2 policy (strict JSON).")
def tool_get_policy() -> str:
    """Return policy.json as text (UTF-8 JSON)."""
    _ensure_exists(POLICY_PATH, "policy")
    return _read_text(POLICY_PATH)


@tool(
    name="tool_get_uc_sections",
    description=(
        "Load specific sections from a UC YAML. "
        "Allowed sections: param_spec, invariants, visualize_presets, allowed_patterns, "
        "ui_contracts, render_pattern, capabilities_required, capabilities_provided, checks."
    ),
)
def tool_get_uc_sections(uc_id: str, sections: list[str]) -> str:
    """
    Returns JSON with the requested sections from knowledge/usecases/<uc_id>.yml.
    Unknown sections are ignored. If UC missing: returns {'error': ...}.
    """
    uc_path = UCS_DIR / f"{uc_id}.yml"
    if not uc_path.exists():
        return _safe_json({"error": f"unknown UC '{uc_id}'"})
    try:
        data = yaml.safe_load(_read_text(uc_path)) or {}
        out = {}
        for sec in sections:
            if sec in data:
                out[sec] = data[sec]
        return _safe_json(out)
    except Exception as e:
        return _safe_json({"error": f"yaml parse error: {e}"})


@tool(
    name="tool_bundle_components",
    description=(
        "Load multiple component files and return a single concatenated string plus a manifest. "
        "Input: components:[relative_paths...] (e.g., 'blocks/components/gee/aoi_from_spec.py'). "
        "Rejects legacy/fs_*."
    ),
)
def tool_bundle_components(components: list[str]) -> str:
    """
    Reads all listed component files, disallows legacy/fs_* paths, and returns:
      {'bundle': '<all files concatenated with headers>', 'manifest': [{'id','sha1','bytes'}...]}
    """
    bundle_parts: List[str] = []
    manifest: List[Dict[str, Any]] = []

    try:
        for rel in components:
            p = (ROOT / rel).resolve()
            # guard: component must be within repo and not legacy
            if ROOT not in p.parents and p != ROOT:
                return _safe_json({"error": f"component outside repo scope: {rel}"})
            if _is_legacy(p):
                return _safe_json({"error": f"legacy component not allowed: {rel}"})
            if not p.exists():
                return _safe_json({"error": f"component not found: {rel}"})

            txt = _read_text(p)
            h = _sha1_text(txt)
            header = f"\n# ==== BEGIN COMPONENT: {rel} (sha1:{h}) ====\n"
            footer = f"\n# ==== END COMPONENT: {rel} ====\n"
            bundle_parts.append(header + txt + footer)
            manifest.append({"id": rel, "sha1": h, "bytes": len(txt.encode("utf-8"))})

        return _safe_json({"bundle": "\n".join(bundle_parts), "manifest": manifest})
    except Exception as e:
        return _safe_json({"error": f"bundle error: {str(e)}"})


# -----------------------------------------------------------------------------
# KEEP: Execution tool (inline/script/streamlit)
# -----------------------------------------------------------------------------
@tool(
    name="tool_run_python",
    description=(
        "Run Python code inline or as script/streamlit. "
        "Input: {code:str, mode:'inline'|'script'|'streamlit'}. "
        "Returns {'status':'ok'|'error','stdout','stderr','path?'}"
    ),
)
def tool_run_python(code: str, mode: str = "inline") -> str:
    """
    Executes generated Python code.
    - inline: exec in-process with basic stdout capture (fast; shares interpreter).
    - script: write /runner/sandbox/app_gen.py and run `python app_gen.py`.
    - streamlit: write /runner/sandbox/app_gen.py and run `streamlit run app_gen.py`.
    """
    try:
        SANDBOX_DIR.mkdir(parents=True, exist_ok=True)
        app_path = SANDBOX_DIR / "app_gen.py"

        if mode == "inline":
            # basic capture
            buf_out = io.StringIO()
            buf_err = io.StringIO()
            _globals = {}
            _locals = {}
            # Patch streamlit.set_page_config if needed to avoid duplication errors
            try:
                import streamlit as _st_internal
                if hasattr(_st_internal, "set_page_config"):
                    pass  # Streamlit guards repeated calls; keep as-is
            except Exception:
                pass

            # Redirect stdout/stderr temporarily
            _stdout, _stderr = sys.stdout, sys.stderr
            sys.stdout, sys.stderr = buf_out, buf_err
            try:
                exec(code, _globals, _locals)
            except SystemExit:
                # allow exit calls from streamlit scripts
                pass
            except Exception:
                traceback.print_exc()
            finally:
                sys.stdout, sys.stderr = _stdout, _stderr

            return _safe_json(
                {"status": "ok", "stdout": buf_out.getvalue(), "stderr": buf_err.getvalue()}
            )

        # Script or Streamlit: write file then subprocess
        app_path.write_text(code, encoding="utf-8")
        if mode == "script":
            proc = subprocess.Popen(
                [sys.executable, str(app_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(SANDBOX_DIR),
                text=True,
            )
        elif mode == "streamlit":
            proc = subprocess.Popen(
                ["streamlit", "run", str(app_path), "--server.headless=true"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(SANDBOX_DIR),
                text=True,
            )
        else:
            return _safe_json({"status": "error", "stderr": f"unknown mode: {mode}"})

        # Give the process a brief head start, then read non-blocking
        time.sleep(1.0)
        try:
            out, err = proc.communicate(timeout=3.0)
        except subprocess.TimeoutExpired:
            out, err = ("", f"Process started (pid {proc.pid}). Streaming not captured.")
        return _safe_json({"status": "ok", "stdout": out, "stderr": err, "path": str(app_path)})

    except Exception as e:
        return _safe_json({"status": "error", "stderr": f"runner error: {e}"})


# -----------------------------------------------------------------------------
# Agent construction — uses your new mega prompt (prompt-first)
# -----------------------------------------------------------------------------
def load_instructions() -> str:
    """Concatenate the new mega prompt (and optional add-ons if you keep them)."""
    parts: List[str] = []
    if MEGA_PROMPT.exists():
        parts.append(_read_text(MEGA_PROMPT))
    else:
        # Fallback minimal instructions if file missing (keeps app usable)
        parts.append(
            textwrap.dedent(
                """
                You are a single conversational agent that builds small geospatial mini-apps.
                Follow the 4-layer approach (L1.1→L1.2→L2→L3), use the provided tools:
                - tool_get_meta (once)
                - tool_get_policy
                - tool_get_uc_sections (portion: first param_spec, later invariants/presets)
                - tool_bundle_components (once, with Layer-2 plan.components)
                - tool_run_python
                Produce a PLAN_SPEC JSON before final code. AOI as structured spec. No legacy components.
                """
            ).strip()
        )
    return "\n\n".join(parts).strip()


def build_agent():
    instructions = load_instructions()
    tools = [
        tool_get_meta,
        tool_get_policy,
        tool_get_uc_sections,
        tool_bundle_components,
        tool_run_python,
    ]
    # ADAPT: if your SDK needs a factory, call it here; else return a tuple.
    try:
        agent_obj = agent.create(instructions=instructions, tools=tools)  # <-- adjust to your SDK
    except Exception:
        # fallback shape
        agent_obj = {"instructions": instructions, "tools": tools}
    return agent_obj


# -----------------------------------------------------------------------------
# Chat UI (kept simple)
# -----------------------------------------------------------------------------
def init_session():
    if "sdk_session" not in st.session_state:
        st.session_state.sdk_session = {}  # your SDK typically accepts a dict
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "last_code" not in st.session_state:
        st.session_state.last_code = ""


def render_history():
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])


def on_user_input(user_text: str, agent_obj):
    if not user_text:
        return
    st.session_state.messages.append({"role": "user", "content": user_text})

    # Build the input prompt for the Agent (you may add hidden context if needed)
    input_text = user_text

    # Run the agent with session (your SDK Runner handles tool calls)
    try:
        result = Runner.run_sync(agent_obj, input=input_text, session=st.session_state.sdk_session)
    except Exception as e:
        result = {"final_output": f"Agent error: {e}", "new_items": []}

    # Collect final output (Assistant message)
    final_output = result.get("final_output") or ""
    if final_output:
        st.session_state.messages.append({"role": "assistant", "content": final_output})

    # Display new items if your SDK returns them (optional)
    new_items = result.get("new_items") or []
    for it in new_items:
        if it.get("type") == "assistant_message":
            st.session_state.messages.append({"role": "assistant", "content": it.get("text", "")})


def main():
    init_session()
    st.title("🧭 Mini-Apps — One Run (L1.1→L1.2→L2→L3)")

    agent_obj = build_agent()

    with st.sidebar:
        st.markdown("### Session")
        st.write("SDK session keys:", list(st.session_state.sdk_session.keys()))
        st.markdown("---")
        st.markdown("**Tools enabled:**")
        st.code(
            "- tool_get_meta\n- tool_get_policy\n- tool_get_uc_sections\n- tool_bundle_components\n- tool_run_python",
            language="text",
        )

    render_history()
    user_text = st.chat_input("Schreib mir, was du sehen möchtest …")
    if user_text is not None:
        on_user_input(user_text, agent_obj)
        st.rerun()


if __name__ == "__main__":
    main()
