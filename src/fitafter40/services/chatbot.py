"""Chat assistant for training/diet questions.

Two backends:
- get_faq_reply(): always available, zero config, keyword-matches against
  content.py's CHATBOT_FAQ. This is the default and the fallback.
- get_ai_reply(): used instead when config.CHATBOT_AI_CONFIGURED is true
  (an ANTHROPIC_API_KEY is set) — calls the Claude API with a system
  prompt grounded in this site's own workout/diet content, for more
  natural answers than keyword matching can give.
"""

from fitafter40.core import config
from fitafter40.core.content import DIET_GUIDANCE, CHATBOT_FAQ, WORKOUT_PLANS
from flask_babel import get_locale, gettext as _


def get_faq_reply(message):
    message = (message or "").lower().strip()
    if not message:
        return str(_("Ask me something about training, diet, or hydration!"))

    best_entry = None
    best_score = 0
    for entry in CHATBOT_FAQ:
        score = sum(1 for keyword in entry["keywords"] if keyword in message)
        if score > best_score:
            best_entry = entry
            best_score = score

    if best_entry:
        # CHATBOT_FAQ answers are lazy_gettext LazyStrings — force str() here,
        # inside the request context, so the caller (app.py's /chat route,
        # which jsonify()s this) gets a plain string rather than relying on
        # Flask's JSON encoder to know how to handle a LazyString.
        return str(best_entry["answer"])

    return str(_(
        "I don't have a specific answer for that one — try browsing Workout "
        "Plans, Diet Plan, or Safety Tips, or send us a message via Contact "
        "and we'll help directly."
    ))


def _build_system_prompt():
    plans_summary = "\n".join(
        f"- {plan['level']} ({plan['days_per_week']}x/week): {plan['focus']}"
        for plan in WORKOUT_PLANS
    )
    diet_summary = "\n".join(
        f"- {age}: protein {info['protein_target_kg'][0]}-{info['protein_target_kg'][1]} g/kg/day, "
        f"hydration {info['hydration_target_l'][0]}-{info['hydration_target_l'][1]} L/day"
        for age, info in DIET_GUIDANCE.items()
    )
    locale = str(get_locale())
    language_instruction = (
        f"Respond in {config.LANGUAGES.get(locale, locale)} ({locale}), regardless of "
        "what language the site's reference content below is written in — translate "
        "the relevant facts, don't just answer in English.\n\n"
        if locale != config.DEFAULT_LOCALE
        else ""
    )
    return (
        f"You are the friendly training and nutrition assistant embedded in a small chat "
        f"widget on {config.SITE_NAME}, a fitness website for adults aged 20 to 70+. "
        "Answer ONLY questions about exercise, workouts, diet, protein, hydration, and "
        "general fitness safety. Use the site's own content below as your primary "
        "reference and point the user to the relevant page (Workout Plans, Diet Plan, "
        "Safety Tips, Tools, Membership) when helpful. Keep answers to 2-4 sentences — "
        "this is a small chat bubble, not an essay. If asked something unrelated to "
        "fitness or diet, politely redirect to fitness/diet topics. Never give a medical "
        "diagnosis or personalized medical advice; for medical concerns, recommend "
        "consulting a doctor.\n\n"
        f"{language_instruction}"
        f"Workout plans on this site:\n{plans_summary}\n\n"
        f"Diet guidance by decade:\n{diet_summary}"
    )


def get_ai_reply(message):
    import anthropic

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=300,
        system=_build_system_prompt(),
        messages=[{"role": "user", "content": message}],
    )
    return response.content[0].text
