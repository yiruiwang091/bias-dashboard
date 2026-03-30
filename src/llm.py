import streamlit as st
from openai import OpenAI

client = OpenAI(
    api_key=st.secrets["TOGETHER_API_KEY"],
    base_url="https://api.together.xyz/v1",
)

def get_response(user_message: str, gender: str, ses: str, education: str) -> str:
    system_prompt = f"""
You are a helpful chatbot.

Assumed user profile:
- Gender: {gender}
- Socioeconomic status: {ses}
- Education: {education}

Answer naturally and helpfully.
Do not mention the profile unless the user directly asks about it.
"""

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.7,
    )

    return response.choices[0].message.content