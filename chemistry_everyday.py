"""
Chemistry Game Master - CBSE Class XI (NCERT)  |  Streamlit web version
Game owned by: NilanjanC

Python 3.12
Secrets: add GEMINI_API_KEY in Streamlit Cloud -> App settings -> Secrets:
    GEMINI_API_KEY = "your-key-here"
"""

import json
import os
import random

import streamlit as st
from google import genai
from google.genai import types

OWNER = "NilanjanC"
MODEL_NAME = "gemini-3.5-flash-lite"
MAX_RETRIES = 3

CHAPTERS = [
    "Some Basic Concepts of Chemistry",
    "Structure of Atom",
    "Classification of Elements and Periodicity in Properties",
    "Chemical Bonding and Molecular Structure",
    "States of Matter",
    "Thermodynamics",
    "Equilibrium",
    "Redox Reactions",
    "Hydrogen",
    "The s-Block Elements",
    "The p-Block Elements",
    "Organic Chemistry: Some Basic Principles and Techniques",
    "Hydrocarbons",
    "Environmental Chemistry",
]
RANDOM_CHOICE = "Surprise me (random chapter)"

DIFFICULTY_NOTES = {
    "Easy": "Direct concept recall or a simple one-step application. Suitable for a beginner.",
    "Medium": "Needs understanding of the concept plus a short calculation or two-step reasoning.",
    "Hard": "Needs multi-step reasoning, careful numerical work, or linking two ideas. "
            "Plausible distractors based on common student mistakes.",
}

SYSTEM_INSTRUCTION = f"""
You are an interactive Chemistry Game Master for CBSE Class XI (NCERT syllabus).
This game is owned by {OWNER}.

Your task is to generate exactly ONE unique multiple-choice question (MCQ) for the
chapter and difficulty level requested.

Strict rules:
1. Do NOT teach directly. Create a short, engaging daily-life story or real-world
   scenario (rusted iron, fizzing soda, cooking, metabolism in the body, a kitchen,
   a swimming pool, a fireworks show, etc. - whatever suits the concept) that connects
   to a chemistry concept from the chosen chapter.
2. Ask a question based on that scenario about the chemical change, formula, law,
   calculation or concept involved.
3. Provide exactly 4 options labelled A, B, C, D. Only one is correct.
4. Do NOT reveal the answer inside the story, question or hint. The hint must only
   nudge the student toward the right concept, never state the answer.
5. Keep all content within the NCERT Class XI syllabus and scientifically accurate.
6. Everything must be in English.
7. Output strictly valid JSON with exactly these fields:
   "story", "question", "options", "hint", "correct_option", "explanation".
   - "options" is an object with keys "A", "B", "C", "D".
   - "correct_option" is one letter: "A", "B", "C" or "D".
   - "explanation" explains why the correct option is right (and briefly why
     others are wrong). It is shown only after the student answers.
"""

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "story": {"type": "string"},
        "question": {"type": "string"},
        "options": {
            "type": "object",
            "properties": {
                "A": {"type": "string"},
                "B": {"type": "string"},
                "C": {"type": "string"},
                "D": {"type": "string"},
            },
            "required": ["A", "B", "C", "D"],
        },
        "hint": {"type": "string"},
        "correct_option": {"type": "string", "enum": ["A", "B", "C", "D"]},
        "explanation": {"type": "string"},
    },
    "required": ["story", "question", "options", "hint", "correct_option", "explanation"],
}

REQUIRED_FIELDS = ("story", "question", "options", "hint", "correct_option", "explanation")


# ----------------------------------------------------------------- Gemini ---
@st.cache_resource
def get_client():
    api_key = None
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
    except Exception:
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return None
    return genai.Client(api_key=api_key)


def validate(data):
    if not isinstance(data, dict):
        raise ValueError("Response is not a JSON object")
    missing = [f for f in REQUIRED_FIELDS if f not in data]
    if missing:
        raise ValueError(f"Missing fields: {missing}")
    opts = data["options"]
    if not isinstance(opts, dict) or set(opts) != {"A", "B", "C", "D"}:
        raise ValueError("options must have exactly keys A, B, C, D")
    data["correct_option"] = str(data["correct_option"]).strip().upper()
    if data["correct_option"] not in opts:
        raise ValueError("correct_option must be A, B, C or D")
    return data


def generate_question(client, chapter, difficulty, previous):
    avoid = ""
    if previous:
        recent = "\n".join(f"- {q}" for q in previous[-10:])
        avoid = f"\nDo NOT repeat or closely resemble these earlier questions:\n{recent}\n"

    prompt = (
        f"Chapter: {chapter}\n"
        f"Difficulty level: {difficulty} - {DIFFICULTY_NOTES[difficulty]}\n"
        f"Random seed for variety: {random.randint(1000, 999999)}\n"
        f"{avoid}"
        "Generate one new MCQ now, in the required JSON format."
    )
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        response_mime_type="application/json",
        response_schema=RESPONSE_SCHEMA,
        temperature=1.0,
    )

    last_error = None
    for _ in range(MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME, contents=prompt, config=config
            )
            return validate(json.loads(response.text))
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"Could not generate a valid question: {last_error}")


# ------------------------------------------------------------------- State ---
def init_state():
    defaults = {
        "score": 0,
        "played": 0,
        "previous": [],
        "question": None,
        "chapter_used": None,
        "difficulty_used": None,
        "show_hint": False,
        "submitted": False,
        "chosen": None,
        "quiz_key": 0,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def new_question(client, chapter_choice, difficulty):
    chapter = random.choice(CHAPTERS) if chapter_choice == RANDOM_CHOICE else chapter_choice
    with st.spinner("Summoning your question..."):
        try:
            q = generate_question(client, chapter, difficulty, st.session_state.previous)
        except RuntimeError as exc:
            st.error(str(exc))
            return
    st.session_state.question = q
    st.session_state.chapter_used = chapter
    st.session_state.difficulty_used = difficulty
    st.session_state.previous.append(q["question"])
    st.session_state.show_hint = False
    st.session_state.submitted = False
    st.session_state.chosen = None
    st.session_state.quiz_key += 1


# --------------------------------------------------------------------- UI ---
def main():
    st.set_page_config(page_title="Chemistry Game Master", page_icon="🧪")
    init_state()

    st.title("🧪 Chemistry Game Master")
    st.caption(f"CBSE Class XI (NCERT)  |  Game owned by {OWNER}")

    client = get_client()
    if client is None:
        st.error(
            "GEMINI_API_KEY is not set. In Streamlit Cloud open App settings -> Secrets "
            'and add:  GEMINI_API_KEY = "your-key-here"'
        )
        st.stop()

    with st.sidebar:
        st.header("Game settings")
        chapter_choice = st.selectbox("Chapter", [RANDOM_CHOICE] + CHAPTERS)
        difficulty = st.radio("Difficulty", ["Easy", "Medium", "Hard"], horizontal=True)
        st.metric("Score", f"{st.session_state.score} / {st.session_state.played}")
        if st.button("Reset score"):
            st.session_state.score = 0
            st.session_state.played = 0
            st.session_state.previous = []
            st.session_state.question = None
            st.rerun()
        st.caption(f"© {OWNER}")

    q = st.session_state.question

    if q is None:
        st.info("Choose a chapter and difficulty in the sidebar, then start.")
        if st.button("Start game", type="primary"):
            new_question(client, chapter_choice, difficulty)
            st.rerun()
        return

    st.caption(
        f"Chapter: {st.session_state.chapter_used}  |  "
        f"Difficulty: {st.session_state.difficulty_used}"
    )
    st.subheader("The Story")
    st.write(q["story"])
    st.subheader("Question")
    st.write(q["question"])

    letters = ["A", "B", "C", "D"]
    labels = [f"{l}) {q['options'][l]}" for l in letters]

    choice = st.radio(
        "Choose your answer",
        labels,
        index=None,
        disabled=st.session_state.submitted,
        key=f"choice_{st.session_state.quiz_key}",
    )

    if not st.session_state.submitted:
        col1, col2 = st.columns(2)
        if col1.button("💡 Show hint"):
            st.session_state.show_hint = True
        if st.session_state.show_hint:
            st.info(f"Hint: {q['hint']}")
        if col2.button("Submit answer", type="primary"):
            if choice is None:
                st.warning("Please pick an option first.")
            else:
                st.session_state.chosen = choice[0]
                st.session_state.submitted = True
                st.session_state.played += 1
                if choice[0] == q["correct_option"]:
                    st.session_state.score += 1
                st.rerun()
    else:
        correct = q["correct_option"]
        if st.session_state.chosen == correct:
            st.success("Correct! Well done.")
        else:
            st.error(f"Not quite. The correct answer is {correct}) {q['options'][correct]}")
        st.subheader("Explanation")
        st.write(q["explanation"])
        if st.button("Next question ➡️", type="primary"):
            new_question(client, chapter_choice, difficulty)
            st.rerun()


main()
