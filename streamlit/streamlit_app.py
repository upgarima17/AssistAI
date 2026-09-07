"""Streamlit frontend for AssistIQ."""

from __future__ import annotations

import streamlit as st

from client import send_message

st.set_page_config(page_title="AssistIQ IT Support", page_icon="🛠️", layout="centered")
st.title("AssistIQ IT Support")
st.caption("Local agentic assistant: route → tool → response")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "employee_id" not in st.session_state:
    st.session_state.employee_id = ""
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None

with st.sidebar:
    st.subheader("Session")
    employee_id = st.text_input("Employee ID", value=st.session_state.employee_id, placeholder="EMP1024")
    st.session_state.employee_id = employee_id.strip().upper()
    if st.button("Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.thread_id = None
        st.rerun()
    st.divider()
    st.caption("Available local tools")
    st.write("Knowledge search (RAG)")
    st.write("Ticket lookup")
    st.write("Ticket creation")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant" and message.get("intent"):
            st.caption(f"Route: {message['intent']}")
            if message.get("sources"):
                st.caption("Sources: " + ", ".join(message["sources"]))

if prompt := st.chat_input("Ask about an IT issue..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        response_placeholder.markdown("...")
        try:
            result = send_message(prompt, st.session_state.thread_id, st.session_state.employee_id)
            st.session_state.thread_id = result["thread_id"]
            response = result["response"]
            response_placeholder.markdown(response)
            st.caption(f"Route: {result['intent']}")
            if result.get("sources"):
                st.caption("Sources: " + ", ".join(result["sources"]))
            st.session_state.messages.append({
                "role": "assistant",
                "content": response,
                "intent": result["intent"],
                "sources": result.get("sources", []),
            })
        except Exception as exc:
            response = "The support service is unavailable. Please start the FastAPI server and try again."
            st.error(response)
            st.caption(str(exc))
            st.session_state.messages.append({"role": "assistant", "content": response})
