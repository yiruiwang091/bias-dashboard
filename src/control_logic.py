from copy import deepcopy
from typing import Dict, Any


def merge_profile_with_pins(profile_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Combine inferred profile with any user overrides (pins) to produce the
    effective profile used for answer generation.
    """
    effective = deepcopy(profile_state)
    for attr, item in effective.items():
        pinned = item.get("pinned")
        if pinned and pinned != "unknown":
            labels = list(item["probs"].keys())
            item["top_label"] = pinned
            item["confidence"] = 1.0
            item["probs"] = {label: 1.0 if label == pinned else 0.0 for label in labels}
            item["source"] = "pinned_override"
        elif pinned == "unknown":
            item["top_label"] = "unknown"
            item["confidence"] = 1.0
            labels = list(item["probs"].keys())
            uniform = 1.0 / len(labels)
            item["probs"] = {label: uniform for label in labels}
            item["source"] = "pinned_override"
    return effective


def effective_profile_summary(effective_profile: Dict[str, Any]) -> str:
    lines = []
    for attr, item in effective_profile.items():
        lines.append(
            f"- {attr}: {item['top_label']} (confidence={item['confidence']:.2f}, source={item.get('source', 'unknown')})"
        )
    return "\n".join(lines)
