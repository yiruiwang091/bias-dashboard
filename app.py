import streamlit as st
from src.llm import get_response

st.set_page_config(page_title="Bias Dashboard Demo", layout="wide")

st.title("TalkTuner-inspired Bias Demo")

with st.sidebar:
    st.header("Assumed User Profile")
    gender = st.selectbox("Gender", ["unknown", "female", "male"])
    ses = st.selectbox("SES", ["low", "middle", "high"])
    education = st.selectbox("Education", ["some schooling", "college", "graduate"])

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

user_input = st.chat_input("Ask a question")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("user"):
        st.write(user_input)

    reply = get_response(user_input, gender, ses, education)

    st.session_state.messages.append({"role": "assistant", "content": reply})

    with st.chat_message("assistant"):
        st.write(reply)