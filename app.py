"""Streamlit chat UI for AssistAI."""

from __future__ import annotations

import streamlit as st

from graph import support_graph

st.set_page_config(page_title="AssistAI IT Support", page_icon="🛠️", layout="centered")
st.title("AssistAI IT Support")
st.caption("Local agentic assistant: route → tool → response")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "employee_id" not in st.session_state:
    st.session_state.employee_id = ""

with st.sidebar:
    st.subheader("Session")
    employee_id = st.text_input("Employee ID", value=st.session_state.employee_id, placeholder="EMP1024")
    st.session_state.employee_id = employee_id.strip().upper()
    if st.button("Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    st.divider()
    st.caption("Available local tools")
    st.write("Knowledge search")
    st.write("Ticket lookup")
    st.write("Ticket creation")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant" and message.get("intent"):
            st.caption(f"Route: {message['intent']} | Tool: {message.get('tool', 'none')}")

if prompt := st.chat_input("Ask about an IT issue..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    state = {
        "messages": st.session_state.messages,
        "user_query": prompt,
        "employee_id": st.session_state.employee_id,
    }
    with st.chat_message("assistant"):
        try:
            result = support_graph.invoke(state)
            response = result.get("response", "I could not generate a response.")
            st.markdown(response)
            st.caption(f"Route: {result.get('intent', 'unknown')} | Tool result returned")
            st.session_state.messages.append({
                "role": "assistant",
                "content": response,
                "intent": result.get("intent"),
                "tool": result.get("intent"),
            })
        except Exception as exc:
            response = "The local support workflow failed gracefully. Please try again."
            st.error(response)
            st.caption(str(exc))
            st.session_state.messages.append({"role": "assistant", "content": response})
