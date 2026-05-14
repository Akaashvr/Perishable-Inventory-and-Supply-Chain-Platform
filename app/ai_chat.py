"""
ai_chat.py
==========

Right-panel query assistant powered by Gemini 2.5 Flash.

Capabilities (all via Gemini function calling):
    • query_database(sql)       — runs read-only SELECT/WITH on the live DB
    • navigate_to_tab(tab, …)   — switches the main tab + applies filters

Tab switching works by injecting JS that clicks the matching tab button.
Filter pre-fill works only if your sidebar multiselects in streamlit_app.py
have `key="filter_regions"`, `key="filter_categories"`, and
`key="filter_demand_levels"`. If they don't, the tab still switches and the
data the AI cites is still correct — just the sidebar widget won't auto-fill.
"""

from __future__ import annotations

import json
import re

import requests
import streamlit as st
import streamlit.components.v1 as components

from db import run_query
from theme import C

# ─── Gemini configuration ─────────────────────────────────────────────────────
# NOTE: This key is exposed in source. For production use, replace with
#   os.getenv("GEMINI_API_KEY", "")
API_KEY  = "AIzaSyAc1cCg6NdYlnowaDu0TyJ-4XR8tsFdLio"
MODEL    = "gemini-2.5-flash"
API_URL  = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}"

# Tabs available in streamlit_app.py (must match the labels exactly).
TAB_NAMES = ["Overview", "Products", "Suppliers", "Regions",
             "Waste", "Promotions", "Data Explorer"]

# ─── System prompt: full schema + page context ────────────────────────────────
SYSTEM_PROMPT = """
You are a concise data assistant embedded in a BI dashboard for a perishable
inventory & supply chain platform. The data lives in a Postgres star schema:

fact_inventory(transaction_id, product_id, store_id, supplier_id,
    transaction_date, expiration_date, quantity, unit_price,
    waste_amount, profit, demand_level, is_promotion)
  - demand_level in ('Low','Medium','High')
  - is_promotion is boolean

dim_product(product_id, product_code, product_name, category_name,
    shelf_life_days, storage_temp_celsius, spoilage_sensitivity)
  - spoilage_sensitivity in ('Low','Medium','High')

dim_store(store_id, store_code, region_name)

dim_supplier(supplier_id, supplier_code, supplier_score)
  - supplier_score is 0–100

Dashboard tabs and what each shows:
  Overview       — KPIs, daily revenue/profit/waste trend, 7-day moving avg
  Products       — top products by revenue/profit/units/waste, category mix
  Suppliers      — supplier ranking, score-vs-profit scatter (window funcs)
  Regions        — per-region bars, region × category revenue heatmap
  Waste          — spoilage by sensitivity, top wasted products
  Promotions     — promoted vs non-promoted side-by-side
  Data Explorer  — searchable transaction grid with CSV export

You have two tools:
  1. query_database(sql) — execute a read-only SELECT or WITH. Use this
     whenever a real number would help; never fabricate figures. Results
     are capped at 50 rows.
  2. navigate_to_tab(tab, regions?, categories?, demand_levels?) — open
     the right tab for the user and optionally set sidebar filters.

Workflow:
  • Data question → call query_database, then answer in ≤4 sentences citing
    the numbers.
  • "Show me / open / take me to …" → call navigate_to_tab with any
    relevant filters, then reply briefly confirming what you opened.
  • Ambiguous → ask one short clarifying question.
  • Never write more than ~120 words. Plain text only. No markdown headers.
""".strip()

# ─── Function declarations (Gemini tools) ─────────────────────────────────────
TOOLS = [{
    "functionDeclarations": [
        {
            "name": "query_database",
            "description": ("Execute a single read-only PostgreSQL SELECT or "
                            "WITH query against the star schema. Results "
                            "are limited to 50 rows."),
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": ("A single SELECT/WITH statement. "
                                        "No INSERT/UPDATE/DELETE/DDL.")
                    }
                },
                "required": ["sql"]
            }
        },
        {
            "name": "navigate_to_tab",
            "description": ("Open a specific dashboard tab. Optionally "
                            "pre-apply sidebar filters."),
            "parameters": {
                "type": "object",
                "properties": {
                    "tab": {
                        "type": "string",
                        "enum": TAB_NAMES,
                        "description": "Which tab to open."
                    },
                    "regions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional region names to filter."
                    },
                    "categories": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional product category names."
                    },
                    "demand_levels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional demand levels (Low/Medium/High)."
                    }
                },
                "required": ["tab"]
            }
        }
    ]
}]

# ─── SQL safety ───────────────────────────────────────────────────────────────
_SQL_FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|"
    r"REVOKE|COPY|EXECUTE|VACUUM|ANALYZE|LOCK|MERGE)\b",
    re.IGNORECASE,
)
_HAS_LIMIT = re.compile(r"\bLIMIT\s+\d+\b", re.IGNORECASE)


def _safe_sql(sql: str) -> tuple[bool, str, str]:
    sql = (sql or "").strip().rstrip(";").strip()
    if not sql:
        return False, "Empty SQL.", sql
    head = sql.lstrip().upper()
    if not (head.startswith("SELECT") or head.startswith("WITH")):
        return False, "Only SELECT or WITH statements are allowed.", sql
    if ";" in sql:
        return False, "Multiple statements not allowed.", sql
    if _SQL_FORBIDDEN.search(sql):
        return False, "Query contains a forbidden keyword.", sql
    if not _HAS_LIMIT.search(sql):
        sql = f"{sql}\nLIMIT 50"
    return True, "", sql


# ─── Tool executors ───────────────────────────────────────────────────────────
def _exec_query(sql: str) -> dict:
    ok, err, safe = _safe_sql(sql)
    if not ok:
        return {"error": err}
    try:
        df = run_query(safe)
        if df.empty:
            return {"row_count": 0, "result": "No rows returned."}
        df = df.head(50)
        # Truncate wide string cells so the response stays compact
        for col in df.select_dtypes(include="object").columns:
            df[col] = df[col].astype(str).str.slice(0, 80)
        return {
            "row_count": len(df),
            "columns": list(df.columns),
            "rows_csv": df.to_csv(index=False),
        }
    except Exception as e:                                       # noqa: BLE001
        return {"error": str(e)[:240]}


def _exec_navigate(args: dict) -> dict:
    tab = args.get("tab", "")
    if tab not in TAB_NAMES:
        return {"error": f"Unknown tab '{tab}'. Valid: {TAB_NAMES}"}

    st.session_state["pending_nav"] = tab

    applied: list[str] = []
    # These keys map to the multiselects in streamlit_app.py — IF those
    # multiselects have matching key= args. Harmless to set either way.
    for arg_key, state_key in [
        ("regions",       "filter_regions"),
        ("categories",    "filter_categories"),
        ("demand_levels", "filter_demand_levels"),
    ]:
        vals = args.get(arg_key)
        if vals:
            st.session_state[state_key] = list(vals)
            applied.append(f"{arg_key}={vals}")

    return {
        "navigated_to": tab,
        "filters_set": applied,
        "note": ("Tab will switch automatically. Filter pre-fill only "
                 "applies if sidebar widgets use matching key= args."),
    }


# ─── Gemini API plumbing ──────────────────────────────────────────────────────
def _gemini_call(history: list[dict]) -> dict:
    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": history,
        "tools": TOOLS,
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 1024,
        },
    }
    r = requests.post(
        API_URL,
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload),
        timeout=45,
    )
    r.raise_for_status()
    return r.json()


def _chat_turn(user_message: str) -> str:
    """Run a full turn: user msg → 0..N function calls → final text."""
    history: list = st.session_state.gemini_history
    history.append({"role": "user", "parts": [{"text": user_message}]})

    for _round in range(6):
        try:
            response = _gemini_call(history)
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "?"
            snippet = (e.response.text[:240] if e.response is not None else "")
            return f"API error {code}: {snippet}"
        except requests.exceptions.Timeout:
            return "Request timed out after 45s. Please try again."
        except Exception as e:                                   # noqa: BLE001
            return f"Network error: {e}"

        candidates = response.get("candidates", [])
        if not candidates:
            return "No response from Gemini. Try rephrasing."

        content = candidates[0].get("content", {}) or {}
        parts = content.get("parts", []) or []
        history.append(content)

        function_calls = [p["functionCall"] for p in parts if "functionCall" in p]
        text_parts     = [p.get("text", "") for p in parts if "text" in p]

        if function_calls:
            responses = []
            for fc in function_calls:
                name = fc.get("name", "")
                args = fc.get("args", {}) or {}
                if name == "query_database":
                    result = _exec_query(args.get("sql", ""))
                elif name == "navigate_to_tab":
                    result = _exec_navigate(args)
                else:
                    result = {"error": f"Unknown function: {name}"}
                responses.append({
                    "functionResponse": {
                        "name": name,
                        "response": result,
                    }
                })
            history.append({"role": "user", "parts": responses})
            continue  # send results back, get next response

        # Plain text response — we're done.
        text = "\n".join(t for t in text_parts if t).strip()
        return text or "(empty reply)"

    return "Conversation exceeded the function-call limit."


# ─── UI ───────────────────────────────────────────────────────────────────────
_SUGGESTIONS = [
    "Top 5 suppliers by profit",
    "Which region has highest waste?",
    "Open Waste tab for West region",
    "Show me promoted dairy products",
]


def render_ai_chat() -> None:
    # ─ Header ─────────────────────────────────────────────────────────────────
    st.markdown(
        """
        <div class="ai-panel-header">
          <div>
            <div class="ai-title">SupplyAIask</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ─ State init ─────────────────────────────────────────────────────────────
    st.session_state.setdefault("gemini_history", [])
    st.session_state.setdefault("chat_display", [])

    # ─ Handle a pending suggestion click (queued on previous run) ────────────
    pending = st.session_state.pop("ai_pending_msg", None)
    if pending:
        with st.spinner("Thinking…"):
            reply = _chat_turn(pending)
        st.session_state.chat_display.append({"role": "user",      "content": pending})
        st.session_state.chat_display.append({"role": "assistant", "content": reply})

    # ─ Empty state: show suggestions ──────────────────────────────────────────
    if not st.session_state.chat_display:
        st.markdown(
            f"""
            <div class="chat-empty">
            </div>
            """,
            unsafe_allow_html=True,
        )
        for s in _SUGGESTIONS:
            if st.button(s, key=f"sug_{hash(s)}"):
                st.session_state.ai_pending_msg = s
                st.rerun()

    # ─ History ────────────────────────────────────────────────────────────────
    for msg in st.session_state.chat_display:
        # escape HTML, preserve line breaks
        body = (msg["content"]
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("\n", "<br>"))
        cls = "chat-bubble-user" if msg["role"] == "user" else "chat-bubble-assistant"
        st.markdown(f'<div class="{cls}">{body}</div>', unsafe_allow_html=True)

    # ─ Input form ─────────────────────────────────────────────────────────────
    with st.form("ai_chat_form", clear_on_submit=True):
        user_input = st.text_input(
            "Message",
            placeholder="Ask anything…",
            label_visibility="collapsed",
        )
        c_send, c_clear = st.columns([2, 1])
        with c_send:
            sent = st.form_submit_button("Send", use_container_width=True)
        with c_clear:
            cleared = st.form_submit_button("Clear", use_container_width=True)

    if cleared:
        st.session_state.gemini_history = []
        st.session_state.chat_display = []
        st.rerun()

    if sent and user_input and user_input.strip():
        with st.spinner("Thinking…"):
            reply = _chat_turn(user_input.strip())
        st.session_state.chat_display.append(
            {"role": "user",      "content": user_input.strip()}
        )
        st.session_state.chat_display.append(
            {"role": "assistant", "content": reply}
        )
        st.rerun()

    # ─ Config notice when key missing ─────────────────────────────────────────
    if not API_KEY or not MODEL:
        st.markdown(
            """
            <div class="chat-bubble-system" style="margin-top:10px">
              <i class="ri-settings-3-line"></i>
              Set API_KEY and MODEL in app/ai_chat.py to enable.
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ─ Apply pending tab navigation via JS injection ──────────────────────────
    target = st.session_state.pop("pending_nav", None)
    if target:
        components.html(
            f"""
            <script>
              (function() {{
                const target = {json.dumps(target)};
                let tries = 0;
                const click = () => {{
                  tries++;
                  const doc = window.parent.document;
                  const tabs = doc.querySelectorAll('button[data-baseweb="tab"]');
                  for (const t of tabs) {{
                    if ((t.innerText || '').trim() === target) {{
                      t.click();
                      return;
                    }}
                  }}
                  if (tries < 12) setTimeout(click, 120);
                }};
                setTimeout(click, 60);
              }})();
            </script>
            """,
            height=0,
        )
