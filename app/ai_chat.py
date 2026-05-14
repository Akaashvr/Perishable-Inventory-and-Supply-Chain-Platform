from __future__ import annotations
import json
import requests
import streamlit as st

from theme import C

API_KEY  = ""   # ← paste your API key here
MODEL    = ""   # ← paste your model name here  e.g. claude-sonnet-4-20250514
API_URL  = "https://api.anthropic.com/v1/messages"


_SYSTEM_PROMPT = """
You are a concise data assistant for a Perishable Inventory & Supply Chain
BI Dashboard. The database is a Postgres Star Schema with these tables:

- fact_inventory: transaction_id, product_id, store_id, supplier_id,
    transaction_date, expiration_date, quantity, unit_price, waste_amount,
    profit, demand_level (Low/Medium/High), is_promotion
- dim_product: product_id, product_code, product_name, category_name,
    shelf_life_days, storage_temp_celsius, spoilage_sensitivity (Low/Med/High)
- dim_store: store_id, store_code, region_name
- dim_supplier: supplier_id, supplier_code, supplier_score (0-100)

Dashboard pages: Overview, Products, Suppliers, Regions, Waste, Promotions,
Data Explorer.

Answer questions about the data briefly (3-5 sentences max). If the user
asks "where can I see X", tell them which page. If they ask for a query,
give clean SQL. Never invent data — say you don't know if uncertain.
Respond in plain text, no markdown headers.
""".strip()


def _call_api(messages: list[dict]) -> str:
    """Make a single API call and return the assistant reply text."""
    if not API_KEY or not MODEL:
        return (
            "API not configured yet. "
            "Open app/ai_chat.py and fill in API_KEY and MODEL."
        )
    try:
        resp = requests.post(
            API_URL,
            headers={
                "x-api-key": API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": MODEL,
                "max_tokens": 400,
                "system": _SYSTEM_PROMPT,
                "messages": messages,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"]
    except requests.exceptions.Timeout:
        return "Request timed out. Please try again."
    except requests.exceptions.HTTPError as e:
        code = e.response.status_code if e.response else "?"
        if code == 401:
            return "Invalid API key. Check API_KEY in app/ai_chat.py."
        if code == 404:
            return "Model not found. Check MODEL in app/ai_chat.py."
        return f"API error {code}. Check your configuration."
    except Exception as e:        # noqa: BLE001
        return f"Error: {e}"


def render_ai_chat() -> None:
    """Render the right-panel AI assistant."""
    # Header
    st.markdown(
        """
        <div class="ai-panel-header">
          <div>
            <div class="ai-title">Ask a question about your supply chain data.</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Session state
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Suggested prompts
    if not st.session_state.chat_history:
        suggestions = [
            "Which region has highest waste?",
            "Show SQL for supplier ranking",
            "Where can I see promotion impact?",
            "What does demand_level mean?",
        ]
        for s in suggestions:
            if st.button(s, key=f"sug_{s}"):
                st.session_state.chat_history.append({"role": "user", "content": s})
                reply = _call_api(st.session_state.chat_history)
                st.session_state.chat_history.append({"role": "assistant", "content": reply})
                st.rerun()

    # Chat history 
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                st.markdown(
                    f'<div class="chat-bubble-user">{msg["content"]}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div class="chat-bubble-assistant">{msg["content"]}</div>',
                    unsafe_allow_html=True,
                )

    # Input
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    user_input = st.text_input(
        "Message",
        key="ai_input",
        placeholder="Ask anything…",
        label_visibility="collapsed",
    )

    col_send, col_clear = st.columns([2, 1])
    with col_send:
        if st.button("Send", key="ai_send"):
            if user_input and user_input.strip():
                st.session_state.chat_history.append(
                    {"role": "user", "content": user_input.strip()}
                )
                reply = _call_api(st.session_state.chat_history)
                st.session_state.chat_history.append(
                    {"role": "assistant", "content": reply}
                )
                st.rerun()

    with col_clear:
        if st.button("Clear", key="ai_clear"):
            st.session_state.chat_history = []
            st.rerun()
