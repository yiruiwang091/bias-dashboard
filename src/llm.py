from typing import Dict, Any

from openai import OpenAI

from control_logic import effective_profile_summary

MODEL_NAME = "openai/gpt-oss-20b"


def build_client(api_key: str, base_url: str = "https://api.together.xyz/v1") -> OpenAI:
    return OpenAI(api_key=api_key, base_url=base_url)


def get_response(
    client: OpenAI,
    user_message: str,
    effective_profile: Dict[str, Any],
    full_chat_history: list[dict[str, str]] | None = None,
) -> str:
    """
    Use the effective profile (inferred + pinned overrides) when generating
    the assistant's answer.
    """
    history_text = ""
    if full_chat_history:
        history_text = "\n".join(
            f"{msg['role'].upper()}: {msg['content']}" for msg in full_chat_history[-10:]
        )

    system_prompt = f"""
You are a helpful chatbot in a teaching demo about inferred user models.

Use the following EFFECTIVE USER PROFILE as a soft conditioning signal:
{effective_profile_summary(effective_profile)}

Instructions:
- Answer naturally and helpfully.
- Do not explicitly mention the inferred profile unless the user asks.
- Keep the answer plausible as a normal chatbot reply.
- The profile may be approximate and can contain errors.
- If the user asks for something sensitive or high stakes, avoid making assumptions based on profile alone.
""".strip()

    messages = [{"role": "system", "content": system_prompt}]
    if history_text:
        messages.append({"role": "system", "content": f"Recent chat history:\n{history_text}"})
    messages.append({"role": "user", "content": user_message})

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=0.7,
    )

    return response.choices[0].message.content