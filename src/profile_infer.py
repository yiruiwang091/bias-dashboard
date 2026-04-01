import json
from typing import Dict, Any

from openai import OpenAI

ATTRIBUTE_SCHEMA = {
    "age": ["child", "adolescent", "adult", "older_adult"],
    "gender": ["female", "male"],
    "education": ["some_schooling", "college", "graduate"],
    "ses": ["low", "middle", "high"],
}

DISPLAY_NAMES = {
    "age": "Age",
    "gender": "Gender",
    "education": "Education",
    "ses": "Socioeconomic Status",
}


def _normalize_probs(raw_probs: Dict[str, float], labels: list[str]) -> Dict[str, float]:
    clean: Dict[str, float] = {}
    for label in labels:
        value = raw_probs.get(label, 0.0)
        try:
            value = float(value)
        except (TypeError, ValueError):
            value = 0.0
        clean[label] = max(value, 0.0)

    total = sum(clean.values())
    if total <= 0:
        uniform = 1.0 / len(labels)
        return {label: uniform for label in labels}

    return {label: value / total for label, value in clean.items()}


def _empty_profile() -> Dict[str, Any]:
    state: Dict[str, Any] = {}
    for attr, labels in ATTRIBUTE_SCHEMA.items():
        uniform = 1.0 / len(labels)
        state[attr] = {
            "top_label": "unknown",
            "confidence": 0.0,
            "probs": {label: uniform for label in labels},
            "pinned": None,
            "source": "empty",
        }
    return state


def _fallback_profile(chat_history: list[dict[str, str]]) -> Dict[str, Any]:
    if not chat_history:
        return _empty_profile()

    state = _empty_profile()
    for attr, labels in ATTRIBUTE_SCHEMA.items():
        probs = {label: 1.0 / len(labels) for label in labels}
        top_label = max(probs, key=probs.get)
        state[attr] = {
            "top_label": "unknown",
            "confidence": probs[top_label],
            "probs": probs,
            "pinned": None,
            "source": "fallback",
        }
    return state


def infer_profile(
    client: OpenAI,
    model_name: str,
    chat_history: list[dict[str, str]],
    threshold: float = 0.60,
) -> Dict[str, Any]:
    """
    Approximate the paper's 'reading probe' step with an LLM classifier.
    This is NOT the original probing method from the paper, but it preserves
    the dashboard logic for demo and teaching purposes.
    """
    if not chat_history:
        return _empty_profile()

    transcript = "\n".join(
        f"{msg['role'].upper()}: {msg['content']}" for msg in chat_history[-12:]
    )

    system_prompt = f"""
You are a strict classifier that infers an APPROXIMATE user profile from a conversation.
Return JSON only.

Rules:
- Infer from the user's wording, context, and cues when possible.
- If the evidence is weak, keep the distribution uncertain.
- Do not claim certainty when the conversation does not support it.
- The output must include probabilities for all labels under each attribute.
- Probabilities for each attribute must sum to 1.

Label schema:
- age: child, adolescent, adult, older_adult
- gender: female, male
- education: some_schooling, college, graduate
- ses: low, middle, high

Required JSON shape:
{{
  "age": {{"child": 0.0, "adolescent": 0.0, "adult": 0.0, "older_adult": 0.0}},
  "gender": {{"female": 0.0, "male": 0.0}},
  "education": {{"some_schooling": 0.0, "college": 0.0, "graduate": 0.0}},
  "ses": {{"low": 0.0, "middle": 0.0, "high": 0.0}}
}}
""".strip()

    user_prompt = f"Conversation transcript:\n\n{transcript}"

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content
        data = json.loads(raw)
    except Exception:
        return _fallback_profile(chat_history)

    state: Dict[str, Any] = {}
    for attr, labels in ATTRIBUTE_SCHEMA.items():
        probs = _normalize_probs(data.get(attr, {}), labels)
        top_label = max(probs, key=probs.get)
        confidence = probs[top_label]
        state[attr] = {
            "top_label": top_label if confidence >= threshold else "unknown",
            "confidence": confidence,
            "probs": probs,
            "pinned": None,
            "source": "llm_inference",
        }

    return state
