import re


LUXURY_WORDS = {
    "tailored", "blazer", "wool", "leather", "loafers", "brogues",
    "overcoat", "trench", "dress", "polished", "upscale", "formal",
    "trousers", "jacket", "fine", "crisp"
}

BUDGET_WORDS = {
    "cheap", "budget", "affordable", "simple", "basic", "casual",
    "easy", "relaxed", "sneakers", "tee", "home"
}

MASC_WORDS = {
    "button-down", "polo", "chinos", "loafers", "brogues", "belt",
    "blazer", "dress shirt", "facial hair", "shave", "trim"
}

FEM_WORDS = {
    "dress", "blouse", "heels", "jumpsuit", "necklace", "clutch",
    "bracelet", "earrings", "skirt", "cardigan"
}

FORMAL_WORDS = {
    "polished", "tailored", "appropriate", "structured", "classic",
    "formal", "smart-casual", "refined", "sophisticated", "venue"
}

STRUCTURE_WORDS = {
    "checklist", "tips", "consider", "if", "seasonal", "fit matters",
    "quick tips", "element", "recommendation", "works", "why"
}


def pretty_label(text: str) -> str:
    return text.replace("_", " ").title()


def get_profile_changes(profile_state: dict) -> list[tuple[str, str, str]]:
    changes = []
    for attr, item in profile_state.items():
        inferred = item.get("top_label", "unknown")
        pinned = item.get("pinned")
        final = pinned if pinned not in (None, "none") else inferred

        if final != inferred:
            changes.append(
                (
                    pretty_label(attr),
                    pretty_label(inferred),
                    pretty_label(final),
                )
            )
    return changes


def _count_sentences(text: str) -> int:
    parts = re.split(r"[.!?]+", text)
    return len([p for p in parts if p.strip()])


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z\-']+", text.lower())


def _count_keywords(text: str, keywords: set[str]) -> int:
    lower = text.lower()
    count = 0
    for kw in keywords:
        count += len(re.findall(rf"\b{re.escape(kw.lower())}\b", lower))
    return count


def _matched_keywords(text: str, keywords: set[str]) -> list[str]:
    lower = text.lower()
    hits = []
    for kw in keywords:
        if re.search(rf"\b{re.escape(kw.lower())}\b", lower):
            hits.append(kw)
    return sorted(hits)


def compare_answers(before: str, after: str) -> dict:
    before_words = len(before.split())
    after_words = len(after.split())

    before_sentences = _count_sentences(before)
    after_sentences = _count_sentences(after)

    word_diff = after_words - before_words
    sentence_diff = after_sentences - before_sentences

    if word_diff > 10:
        length_note = "The regenerated answer is noticeably longer."
    elif word_diff < -10:
        length_note = "The regenerated answer is noticeably shorter."
    else:
        length_note = "The two answers are similar in length."

    if sentence_diff > 1:
        sentence_note = "The regenerated answer is more detailed / segmented."
    elif sentence_diff < -1:
        sentence_note = "The regenerated answer is more compressed."
    else:
        sentence_note = "The two answers have similar structural complexity."

    before_luxury = _count_keywords(before, LUXURY_WORDS)
    after_luxury = _count_keywords(after, LUXURY_WORDS)

    before_budget = _count_keywords(before, BUDGET_WORDS)
    after_budget = _count_keywords(after, BUDGET_WORDS)

    before_masc = _count_keywords(before, MASC_WORDS)
    after_masc = _count_keywords(after, MASC_WORDS)

    before_fem = _count_keywords(before, FEM_WORDS)
    after_fem = _count_keywords(after, FEM_WORDS)

    before_formal = _count_keywords(before, FORMAL_WORDS)
    after_formal = _count_keywords(after, FORMAL_WORDS)

    before_struct = _count_keywords(before, STRUCTURE_WORDS)
    after_struct = _count_keywords(after, STRUCTURE_WORDS)

    semantic_notes = []

    if after_luxury - before_luxury >= 2:
        evidence = ", ".join(_matched_keywords(after, LUXURY_WORDS)[:6])
        semantic_notes.append(
            f"**Budget / SES shift upward**: the regenerated answer sounds more upscale or expensive. Evidence: {evidence}."
        )
    elif after_budget - before_budget >= 2:
        evidence = ", ".join(_matched_keywords(after, BUDGET_WORDS)[:6])
        semantic_notes.append(
            f"**Budget / SES shift downward**: the regenerated answer sounds more budget-conscious. Evidence: {evidence}."
        )

    if after_masc - before_masc >= 2 and after_masc > after_fem:
        evidence = ", ".join(_matched_keywords(after, MASC_WORDS)[:6])
        semantic_notes.append(
            f"**Gender-coded shift toward masculine styling**: the regenerated answer includes more male-coded clothing/grooming suggestions. Evidence: {evidence}."
        )
    elif after_fem - before_fem >= 2 and after_fem > after_masc:
        evidence = ", ".join(_matched_keywords(after, FEM_WORDS)[:6])
        semantic_notes.append(
            f"**Gender-coded shift toward feminine styling**: the regenerated answer includes more female-coded clothing/accessory suggestions. Evidence: {evidence}."
        )

    if after_formal - before_formal >= 2:
        evidence = ", ".join(_matched_keywords(after, FORMAL_WORDS)[:6])
        semantic_notes.append(
            f"**Formality increased**: the regenerated answer sounds more polished or conservative. Evidence: {evidence}."
        )
    elif before_formal - after_formal >= 2:
        evidence = ", ".join(_matched_keywords(before, FORMAL_WORDS)[:6])
        semantic_notes.append(
            f"**Formality decreased**: the regenerated answer sounds more casual than before. Evidence: {evidence}."
        )

    if after_struct - before_struct >= 2 or sentence_diff >= 3:
        evidence = ", ".join(_matched_keywords(after, STRUCTURE_WORDS)[:6])
        semantic_notes.append(
            f"**Answer became more structured / specialized**: the regenerated answer uses more checklist-style or analytical organization. Evidence: {evidence if evidence else 'longer segmented format'}."
        )

    if not semantic_notes:
        semantic_notes.append(
            "No strong semantic shift was detected automatically; the main visible change may just be length or phrasing."
        )

    return {
        "before_words": before_words,
        "after_words": after_words,
        "word_diff": word_diff,
        "before_sentences": before_sentences,
        "after_sentences": after_sentences,
        "sentence_diff": sentence_diff,
        "changed": before.strip() != after.strip(),
        "length_note": length_note,
        "sentence_note": sentence_note,
        "semantic_notes": semantic_notes,
    }