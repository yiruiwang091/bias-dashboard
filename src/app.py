import streamlit as st

from control_logic import merge_profile_with_pins
from llm import build_client, get_response, MODEL_NAME
from profile_infer import infer_profile, ATTRIBUTE_SCHEMA, DISPLAY_NAMES
from compare import get_profile_changes, compare_answers

st.set_page_config(page_title="TalkTuner-style Dashboard Demo", layout="wide")

st.title("TalkTuner-style Bias Dashboard Demo")
st.caption(
    "Approximate inferred profile, not ground truth. This demo reproduces the dashboard/control logic of the paper, not the original activation-probe method."
)


# ---------- session state ----------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "profile_state" not in st.session_state:
    st.session_state.profile_state = infer_profile(client=None, model_name=MODEL_NAME, chat_history=[])

if "last_user_message" not in st.session_state:
    st.session_state.last_user_message = None

if "baseline_reply" not in st.session_state:
    st.session_state.baseline_reply = None

if "controlled_reply" not in st.session_state:
    st.session_state.controlled_reply = None

if "show_controlled_reply" not in st.session_state:
    st.session_state.show_controlled_reply = False


# ---------- helpers ----------
def label_display(label: str) -> str:
    return label.replace("_", " ").title()


def render_probability_table(probs: dict[str, float]):
    for label, prob in probs.items():
        st.write(f"{label_display(label)} — {prob:.2f}")
        st.progress(min(max(float(prob), 0.0), 1.0))


def sync_pinned_value(attr: str):
    widget_key = f"pin_widget_{attr}"
    st.session_state.profile_state[attr]["pinned"] = st.session_state[widget_key]


# ---------- api client ----------
api_key = st.secrets.get("TOGETHER_API_KEY")
if not api_key:
    st.error("Missing TOGETHER_API_KEY in Streamlit secrets.")
    st.stop()

client = build_client(api_key)


# ---------- layout ----------
left_col, right_col = st.columns([1.15, 1.85], gap="large")

with left_col:
    st.subheader("Chatbot's Model of You")
    st.info(
        "The dashboard first shows the model's inferred profile from the conversation. You can then pin any attribute and regenerate the answer to observe the change."
    )

    for attr, labels in ATTRIBUTE_SCHEMA.items():
        item = st.session_state.profile_state.get(attr, {})

        with st.container(border=True):
            top_label = item.get("top_label", "unknown")
            confidence = float(item.get("confidence", 0.0))
            pinned = item.get("pinned")
            source = item.get("source", "unknown")

            st.markdown(f"**{DISPLAY_NAMES[attr]}**")
            st.write(f"Top prediction: **{label_display(top_label)}**")
            st.write(f"Confidence: {confidence:.2f}")
            st.progress(min(max(confidence, 0.0), 1.0))
            st.caption(f"Source: {source}")

            with st.expander("Show class probabilities"):
                render_probability_table(item.get("probs", {}))

            pin_options = ["none", "unknown", *labels]
            current = pinned if pinned is not None else "none"
            safe_index = pin_options.index(current) if current in pin_options else 0
            st.selectbox(
                f"Pin / override {DISPLAY_NAMES[attr]}",
                pin_options,
                index=safe_index,
                key=f"pin_widget_{attr}",
                format_func=lambda x: "None" if x == "none" else label_display(x),
                on_change=sync_pinned_value,
                args=(attr,),
            )

    if st.button("Clear all pins"):
        for attr in ATTRIBUTE_SCHEMA:
            st.session_state.profile_state[attr]["pinned"] = None
            st.session_state[f"pin_widget_{attr}"] = "none"
        st.session_state.controlled_reply = None
        st.session_state.show_controlled_reply = False
        st.rerun()

    st.markdown("---")
    st.markdown("**Suggested demo prompts**")
    st.caption(
        "Try asking for career advice, product recommendations, financial planning tips, or study guidance. Those prompts make profile-conditioned differences easier to observe."
    )

with right_col:
    st.subheader("Chat")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    user_input = st.chat_input("Ask a question")

    if user_input:
        st.session_state.last_user_message = user_input
        st.session_state.controlled_reply = None
        st.session_state.show_controlled_reply = False

        st.session_state.messages.append({"role": "user", "content": user_input})

        # Step 1: infer profile from conversation so far (including latest user msg)
        inferred = infer_profile(
            client=client,
            model_name=MODEL_NAME,
            chat_history=st.session_state.messages,
        )

        # preserve pinned values across re-inference
        for attr in ATTRIBUTE_SCHEMA:
            inferred[attr]["pinned"] = st.session_state.profile_state.get(attr, {}).get("pinned")

        st.session_state.profile_state = inferred
        effective_profile = merge_profile_with_pins(st.session_state.profile_state)

        baseline_reply = get_response(
            client=client,
            user_message=user_input,
            effective_profile=effective_profile,
            full_chat_history=st.session_state.messages,
        )
        st.session_state.baseline_reply = baseline_reply
        st.session_state.messages.append({"role": "assistant", "content": baseline_reply})
        st.rerun()

    st.markdown("---")
    st.subheader("Regeneration")
    st.caption("Pin one or more attributes on the left, then regenerate the answer to the same last user message.")

    can_regenerate = st.session_state.last_user_message is not None
    if st.button("Regenerate with pinned profile", disabled=not can_regenerate):
        effective_profile = merge_profile_with_pins(st.session_state.profile_state)
        controlled_reply = get_response(
            client=client,
            user_message=st.session_state.last_user_message,
            effective_profile=effective_profile,
            full_chat_history=st.session_state.messages,
        )
        st.session_state.controlled_reply = controlled_reply
        st.session_state.show_controlled_reply = True
        st.rerun()

    if st.session_state.baseline_reply:
        st.markdown("---")
        st.subheader("Comparison")

        if st.session_state.show_controlled_reply and st.session_state.controlled_reply:
            changes = get_profile_changes(st.session_state.profile_state)
            stats = compare_answers(
                st.session_state.baseline_reply,
                st.session_state.controlled_reply,
            )

            st.markdown("**Profile changes applied**")
            if changes:
                for attr, before_label, after_label in changes:
                    st.write(f"- {attr}: {before_label} → {after_label}")
            else:
                st.write("- No pinned change was applied.")

            metric_col1, metric_col2, metric_col3 = st.columns(3)
            with metric_col1:
                st.metric(
                    "Word count",
                    stats["after_words"],
                    delta=stats["word_diff"],
                )
            with metric_col2:
                st.metric(
                    "Sentence count",
                    stats["after_sentences"],
                    delta=stats["sentence_diff"],
                )
            with metric_col3:
                st.metric(
                    "Changed?",
                    "Yes" if stats["changed"] else "No",
                )

            before_col, after_col = st.columns(2)

            with before_col:
                st.markdown("**Before control**")
                st.write(st.session_state.baseline_reply)

            with after_col:
                st.markdown("**After control**")
                st.write(st.session_state.controlled_reply)

            st.markdown("**Quick summary**")
            st.write(f"- {stats['length_note']}")
            st.write(f"- {stats['sentence_note']}")

            st.markdown("**Meaningful changes detected**")
            for note in stats["semantic_notes"]:
                st.write(f"- {note}")

            if stats["changed"]:
                st.success("Answer changed after profile control.")
            else:
                st.warning("The answer did not visibly change this time. Try a different question or stronger pin.")

        else:
            st.markdown("**Original answer**")
            st.write(st.session_state.baseline_reply)
            st.info("Pin one or more attributes and click 'Regenerate with pinned profile' to see the comparison view.")