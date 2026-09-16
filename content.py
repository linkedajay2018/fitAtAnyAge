"""Static site content, kept separate from app.py's routing/business logic
so it can be edited without touching application code."""

from flask_babel import lazy_gettext as _l

# `level_id` is a stable, untranslated identifier used for matching
# (localStorage keys, the "Recommended for you" badge, AGE_GUIDANCE's
# recommended_level below) — never shown to users and never translated.
# `level` is the translated display label. Keep these two concepts
# separate: translating `level` must never change what `level_id` matches
# against, or age-based recommendations silently break in every language
# but the one they were written in.
#
# `exercises` is the base/default list shown before an age is picked (and
# is what `exercise_index` in models.py's WorkoutProgress always refers
# to — see the "Workout progress sync" note in CLAUDE.md). Real programming
# doesn't need to change per decade for every exercise — most bodyweight
# and light-load moves are fine across a wide age range — so instead of a
# fully separate 6-exercise list per age group (mostly duplicating the
# base list with cosmetic changes), `exercise_overrides_by_age` swaps in
# an age-appropriate variant only for the *specific* exercises where age
# genuinely changes what's appropriate (impact, load, balance demand).
# Keyed by AGE_GROUPS id -> {exercise index: replacement text}; an age
# with no entry here, or an index not overridden for that age, falls back
# to the plain `exercises` entry. app.py's workouts() route merges these
# into a per-age list for every AGE_GROUPS id (not just the ones with
# overrides) and embeds the result as JSON for script.js to swap in when
# an age is selected — the index itself never changes, only which text
# fills it, so WorkoutProgress rows stay valid across an age switch.
#
# `schedule` organizes that same flat `exercises` list into an actual
# day-by-day split — which exercises to do on Day 1 vs Day 2, etc. — one
# entry per training day, matching `days_per_week` in length (enforced by
# tests/test_workout_schedule.py). Each entry's `exercise_indices` refers
# back to the same global `exercises` list, NOT a day-local list: this is
# deliberate, so a single exercise (and its age overrides, and its
# WorkoutProgress row) is defined exactly once regardless of which day it
# appears under. The split itself (which exercises land on which day)
# does not vary by age — only the exercise text within a slot does — same
# "structure is stable, content within a slot varies" principle as the
# level/level_id and exercise-index-not-label decisions above.
WORKOUT_PLANS = [
    {
        "level_id": "beginner",
        "level": _l("Beginner"),
        "icon": "🌱",
        "focus": _l("Build a foundation safely"),
        "days_per_week": 3,
        "exercises": [
            _l("Bodyweight squats — 2 x 10"),
            _l("Wall or knee push-ups — 2 x 8"),
            _l("Seated rows (band) — 2 x 12"),
            _l("Glute bridges — 2 x 12"),
            _l("Standing balance hold — 2 x 20s per side"),
            _l("Gentle walk — 15 min"),
        ],
        "exercise_overrides_by_age": {
            "60s": {
                4: _l("Standing balance hold (hand on a chair for support) — 2 x 20s per side"),
            },
            "70s": {
                0: _l("Sit-to-stand from a chair — 2 x 8"),
                4: _l("Standing balance hold (hand on a chair for support) — 2 x 15s per side"),
                5: _l("Gentle walk — 10 min"),
            },
        },
        "schedule": [
            {"day_number": 1, "focus": _l("Squat & Push"), "exercise_indices": [0, 1]},
            {"day_number": 2, "focus": _l("Row & Hip Bridge"), "exercise_indices": [2, 3]},
            {"day_number": 3, "focus": _l("Balance & Walk"), "exercise_indices": [4, 5]},
        ],
    },
    {
        "level_id": "intermediate",
        "level": _l("Intermediate"),
        "icon": "🔥",
        "focus": _l("Strength and joint stability"),
        "days_per_week": 4,
        "exercises": [
            _l("Goblet squats — 3 x 10"),
            _l("Dumbbell bench press — 3 x 10"),
            _l("Bent-over dumbbell rows — 3 x 10"),
            _l("Romanian deadlifts (light) — 3 x 10"),
            _l("Plank — 3 x 30s"),
            _l("Brisk walk or cycling — 20 min"),
        ],
        "exercise_overrides_by_age": {
            "50s": {
                3: _l("Romanian deadlifts (light, focus on hip-hinge form) — 3 x 8"),
            },
            "60s": {
                3: _l("Romanian deadlifts (light, focus on hip-hinge form) — 3 x 8"),
                4: _l("Modified plank (on knees, or forearms on a bench) — 3 x 20s"),
            },
            "70s": {
                0: _l("Goblet squats (shallow depth, hold support if needed) — 3 x 8"),
                3: _l("Hip hinge with light dumbbells — 3 x 8"),
                4: _l("Modified plank (on knees, or forearms on a bench) — 3 x 15s"),
                5: _l("Brisk walk or stationary cycling — 15 min"),
            },
        },
        "schedule": [
            {"day_number": 1, "focus": _l("Legs"), "exercise_indices": [0, 3]},
            {"day_number": 2, "focus": _l("Upper Push"), "exercise_indices": [1]},
            {"day_number": 3, "focus": _l("Upper Pull & Core"), "exercise_indices": [2, 4]},
            {"day_number": 4, "focus": _l("Cardio"), "exercise_indices": [5]},
        ],
    },
    {
        "level_id": "active",
        "level": _l("Active"),
        "icon": "🚀",
        "focus": _l("Maintain strength, mobility, and cardio health"),
        "days_per_week": 5,
        "exercises": [
            _l("Barbell or dumbbell squats — 4 x 8"),
            _l("Overhead press — 3 x 8"),
            _l("Deadlifts (moderate) — 3 x 8"),
            _l("Pull-downs or assisted pull-ups — 3 x 10"),
            _l("Mobility flow (hips/shoulders) — 10 min"),
            _l("Low-impact cardio (swim/bike) — 25 min"),
        ],
        "exercise_overrides_by_age": {
            "20s": {
                5: _l("High-intensity interval training (sprints or rowing) — 20 min"),
            },
            "50s": {
                2: _l("Deadlifts (moderate, trap bar preferred for easier setup) — 3 x 8"),
            },
            "60s": {
                0: _l("Dumbbell or goblet squats (moderate load) — 4 x 8"),
                2: _l("Trap bar or kettlebell deadlifts (light-to-moderate) — 3 x 8"),
                3: _l("Assisted pull-downs — 3 x 10"),
            },
            "70s": {
                0: _l("Dumbbell squats (light-to-moderate load, comfortable range) — 3 x 8"),
                2: _l("Kettlebell deadlifts (light) — 3 x 8"),
                3: _l("Seated rows or assisted pull-downs — 3 x 10"),
                5: _l("Low-impact cardio (swim, bike, or brisk walk) — 20 min"),
            },
        },
        "schedule": [
            {"day_number": 1, "focus": _l("Legs"), "exercise_indices": [0]},
            {"day_number": 2, "focus": _l("Upper Push"), "exercise_indices": [1]},
            {"day_number": 3, "focus": _l("Upper Pull"), "exercise_indices": [3]},
            {"day_number": 4, "focus": _l("Posterior Chain"), "exercise_indices": [2]},
            {"day_number": 5, "focus": _l("Mobility & Cardio"), "exercise_indices": [4, 5]},
        ],
    },
]

# Shown in a rotating banner on every page (base.html). One is picked at
# random per request server-side, then script.js cycles through the rest.
# Keep these short — they're read at a glance in a thin banner strip.
MOTIVATIONAL_QUOTES = [
    _l("Strong today. Stronger tomorrow."),
    _l("Your best age to start is now."),
    _l("Every rep counts — begin today."),
    _l("Consistency beats intensity, every time."),
    _l("Small steps, real strength."),
    _l("Age is a number. Effort is a choice."),
    _l("The only bad workout is the one you skipped."),
    _l("You don't have to be great to start — you have to start to be great."),
    _l("Progress, not perfection."),
    _l("Show up. That's the hardest part, and you just did."),
    _l("Your future self is already proud of you."),
    _l("Discipline today, freedom tomorrow."),
    _l("Strength has no expiration date."),
    _l("Move today, thank yourself tomorrow."),
    _l("One workout won't transform you — but it starts the one that will."),
    _l("The best time to start was yesterday. The next best time is now."),
    _l("Every decade deserves its own strongest version of you."),
    _l("You're one workout away from a better mood."),
    _l("Fitness isn't a phase — it's a lifelong habit worth building."),
    _l("Nobody ever regretted a workout."),
]

# Tips that apply no matter your age — always shown on the Safety Tips page.
GENERAL_SAFETY_TIPS = [
    _l("Always warm up for 5-10 minutes before any workout."),
    _l("Stay hydrated and don't skip protein — it supports muscle maintenance."),
    _l("Check with a doctor before starting if you have any existing conditions."),
]

# Ordered youngest to oldest — this order drives the age-selector UI.
AGE_GROUPS = [
    {"id": "20s", "label": "20s", "range": "20–29", "icon": "🌱"},
    {"id": "30s", "label": "30s", "range": "30–39", "icon": "⚡"},
    {"id": "40s", "label": "40s", "range": "40–49", "icon": "🎯"},
    {"id": "50s", "label": "50s", "range": "50–59", "icon": "🦴"},
    {"id": "60s", "label": "60s", "range": "60–69", "icon": "🧭"},
    {"id": "70s", "label": "70s", "range": "70+", "icon": "💚"},
]

# Per-decade guidance. `recommended_level` is a starting-point suggestion
# only — it must match a "level_id" value in WORKOUT_PLANS above (a stable,
# untranslated id) — not a rule; actual fitness level matters more than
# age. Keep `safety_tips` to about 3 per group so the page stays scannable.
AGE_GUIDANCE = {
    "20s": {
        "recommended_level": "active",
        "headline": _l("Build strength and lifelong habits"),
        "blurb": _l("Recovery is fastest now — a great time to build a strength habit and learn good form that pays off for decades."),
        "safety_tips": [
            _l("Learn proper form early — it prevents injuries for decades to come."),
            _l("Don't skip warm-ups just because you recover fast; they still protect your joints long-term."),
            _l("Balance intense training with adequate sleep and real recovery days."),
        ],
    },
    "30s": {
        "recommended_level": "active",
        "headline": _l("Stay consistent as life gets busier"),
        "blurb": _l("Recovery starts slowing slightly. Prioritize consistency over intensity — three solid sessions a week beats sporadic hard ones."),
        "safety_tips": [
            _l("Fit in shorter, consistent sessions rather than skipping workouts when busy."),
            _l("Add mobility work now to offset more sitting and desk time."),
            _l("Progress weights gradually rather than jumping too fast, too soon."),
        ],
    },
    "40s": {
        "recommended_level": "intermediate",
        "headline": _l("Protect joints while maintaining strength"),
        "blurb": _l("Joints and tendons recover more slowly now. Prioritize form, mobility, and rest between strength sessions."),
        "safety_tips": [
            _l("Prioritize form over weight — joints and tendons recover slower now."),
            _l("Add mobility and stretching work to every session."),
            _l("Include 1-2 full rest days per week for recovery."),
        ],
    },
    "50s": {
        "recommended_level": "intermediate",
        "headline": _l("Build bone density and preserve muscle"),
        "blurb": _l("Strength training becomes important for bone density and metabolic health, and balance work starts to matter more."),
        "safety_tips": [
            _l("Include weight-bearing exercises to support bone density."),
            _l("Add balance exercises — they become more valuable each decade from here."),
            _l("Get a doctor's clearance first if you have any cardiovascular or joint conditions."),
        ],
    },
    "60s": {
        "recommended_level": "beginner",
        "headline": _l("Maintain strength, balance, and independence"),
        "blurb": _l("Functional strength and fall prevention take priority. Lower-impact options protect joints while keeping you strong."),
        "safety_tips": [
            _l("Prioritize balance and functional movements that mirror daily activities."),
            _l("Choose low-impact cardio (walking, swimming, cycling) over high-impact options."),
            _l("Warm up longer than you think you need — 10 minutes is a good starting point."),
        ],
    },
    "70s": {
        "recommended_level": "beginner",
        "headline": _l("Stay mobile, steady, and independent"),
        "blurb": _l("Consistency and safety matter more than intensity. Always get medical clearance before starting or changing a routine."),
        "safety_tips": [
            _l("Get medical clearance before starting or significantly changing your routine."),
            _l("Favor seated or supported variations of exercises where balance is a concern."),
            _l("Stop any exercise that causes pain — mild fatigue is fine, pain is not."),
        ],
    },
}

# Protein sources shown on the Diet Plan page — the same list applies at
# every age, grouped so both animal- and plant-based eaters have options.
# Values are approximate grams of protein per 100g, for orientation only.
PROTEIN_SOURCES = [
    {
        "category_id": "animal",
        "category": _l("Animal-based"),
        "icon": "🍗",
        "foods": [
            _l("Chicken breast — ~31g protein per 100g"),
            _l("Eggs — ~13g protein per 100g (about 6g per egg)"),
            _l("Greek yogurt — ~10g protein per 100g"),
            _l("Cottage cheese — ~11g protein per 100g"),
            _l("Salmon or tuna — ~22–25g protein per 100g"),
            _l("Lean beef or turkey — ~26g protein per 100g"),
        ],
    },
    {
        "category_id": "plant",
        "category": _l("Plant-based"),
        "icon": "🌿",
        "foods": [
            _l("Lentils, cooked — ~9g protein per 100g"),
            _l("Chickpeas, cooked — ~9g protein per 100g"),
            _l("Tofu or tempeh — ~12–19g protein per 100g"),
            _l("Edamame — ~11g protein per 100g"),
            _l("Quinoa, cooked — ~4.4g protein per 100g"),
            _l("Almonds or peanut butter — ~21–25g protein per 100g"),
        ],
    },
    {
        "category_id": "supplements",
        "category": _l("Protein Supplements"),
        "icon": "🥤",
        "foods": [
            _l("Whey protein powder — ~20–25g protein per scoop (fast-digesting, good post-workout)"),
            _l("Casein protein powder — ~20–25g protein per scoop (slow-digesting, good before bed)"),
            _l("Plant-based protein powder (pea, rice, or hemp blend) — ~15–25g protein per scoop"),
            _l("Ready-to-drink protein shakes — ~15–30g protein per bottle"),
            _l("Collagen peptides — ~9g protein per scoop (convenient, but an incomplete protein — doesn't replace the sources above)"),
            _l("Protein bars — ~15–20g protein per bar (check the label; sugar content varies a lot by brand)"),
        ],
    },
]

# Shown just below the Protein Supplements card on the Diet Plan page.
SUPPLEMENT_NOTE = _l(
    "Supplements are a convenient top-up, not a replacement for whole "
    "foods — use them to close a gap, not as your main protein source. "
    "Look for third-party tested products (e.g. NSF Certified for Sport, "
    "Informed-Sport) so you know what's actually in them, and check with "
    "a doctor first if you're on any medication, since some supplements "
    "can interact with it — this matters more the older you are."
)

# Per-decade diet guidance shown on the Diet Plan page. `protein_target` is
# a general range, not a prescription — protein needs actually trend UP
# with age (to fight anabolic resistance/sarcopenia), not down. This is
# general nutrition information, not medical advice — the page carries a
# disclaimer pointing people with kidney disease or other conditions to a
# doctor/dietitian before changing protein intake.
#
# `protein_target_kg`/`hydration_target_l` are raw metric numbers (not
# translatable strings) — units.py's format_protein_target()/
# format_hydration_target() turn them into a display string at render
# time, in the visitor's chosen unit system (config.UNIT_SYSTEMS) and
# locale. Keeping the numbers as plain floats here, instead of baking them
# into a pre-formatted "1.2–1.6 g per kg of bodyweight" string like before,
# is what makes an imperial (g/lb, fl oz) rendering possible at all —
# converting a number is easy, converting text embedded in a translated
# sentence is not. `hydration_note` is an optional short translatable
# clause units.py appends after the number (e.g. "— don't rely on thirst
# alone"); most decades have none.
DIET_GUIDANCE = {
    "20s": {
        "protein_target_kg": (1.2, 1.6),
        "hydration_target_l": (2.5, 3.5),
        "hydration_note": _l("(more on training days)"),
        "hydration_tip": _l("Your thirst cues are reliable at this age — drink when thirsty, and top up around workouts and in heat."),
        "focus": _l("Fuel growth and build good habits"),
        "tips": [
            _l("Spread protein across 3–4 meals rather than one big serving."),
            _l("Don't skip breakfast — it's easy to under-eat protein early in the day."),
            _l("Whole foods first; save supplements for when your diet genuinely falls short."),
        ],
    },
    "30s": {
        "protein_target_kg": (1.4, 1.8),
        "hydration_target_l": (2.5, 3.5),
        "hydration_note": None,
        "hydration_tip": _l("Busy schedules make it easy to under-drink — keep a bottle within sight as a visual reminder."),
        "focus": _l("Eat for consistency, not perfection"),
        "tips": [
            _l("Batch-cook protein sources on weekends to make busy weekdays easier."),
            _l("Keep quick options on hand — Greek yogurt, eggs, canned beans — for low-effort days."),
            _l("Watch liquid calories (alcohol, sugary drinks) creeping in as social life gets busier."),
        ],
    },
    "40s": {
        "protein_target_kg": (1.6, 2.0),
        "hydration_target_l": (2.3, 3.2),
        "hydration_note": None,
        "hydration_tip": _l("Joint stiffness is sometimes linked to mild dehydration — consistent water intake supports joint lubrication too."),
        "focus": _l("Protect muscle as metabolism shifts"),
        "tips": [
            _l("Prioritize protein at breakfast — it helps offset the muscle loss that tends to start around now."),
            _l("Add fiber-rich carbs (vegetables, whole grains) to support digestion and steady energy."),
            _l("Stay on top of hydration — thirst cues get less reliable with age."),
        ],
    },
    "50s": {
        "protein_target_kg": (1.6, 2.2),
        "hydration_target_l": (2.3, 3.0),
        "hydration_note": None,
        "hydration_tip": _l("Hormonal shifts (perimenopause/menopause) can affect fluid balance — pay extra attention in hot weather."),
        "focus": _l("Support bone density alongside muscle"),
        "tips": [
            _l("Pair protein with calcium-rich foods (dairy, leafy greens, fortified plant milk) for bone health."),
            _l("Get vitamin D through safe sun exposure, fortified foods, or a supplement — ask your doctor."),
            _l("Cut back on sodium where you can; blood pressure sensitivity often increases now."),
        ],
    },
    "60s": {
        "protein_target_kg": (1.8, 2.2),
        "hydration_target_l": (2.2, 3.0),
        "hydration_note": _l("— don't rely on thirst alone"),
        "hydration_tip": _l("Thirst sensation starts declining now — sip water on a schedule throughout the day rather than waiting to feel thirsty."),
        "focus": _l("Fight anabolic resistance with more, more often"),
        "tips": [
            _l("Your body needs more protein per meal now to build the same muscle it once did — aim for 25–30g per meal."),
            _l("Soft, easy-to-chew protein options (fish, eggs, yogurt, smoothies) help if dental issues make eating harder."),
            _l("Fiber and water together help prevent the constipation that becomes more common with age."),
        ],
    },
    "70s": {
        "protein_target_kg": (1.8, 2.4),
        "hydration_target_l": (2.0, 2.7),
        "hydration_note": _l("— ask your doctor if you take diuretics"),
        "hydration_tip": _l("Some medications affect fluid needs — get a personalized target from your doctor, and drink on a schedule, not just when thirsty."),
        "focus": _l("Eat to preserve strength and independence"),
        "tips": [
            _l("Appetite often decreases with age — smaller, more frequent, nutrient-dense meals can help you get enough."),
            _l("Protein at every meal, including breakfast, helps preserve the muscle you have."),
            _l("Talk to your doctor about your specific needs, especially with any chronic conditions or medications."),
        ],
    },
}

# Knowledge base for the FAQ chatbot (chatbot.py's get_faq_reply). This is
# the always-available fallback used when no AI backend is configured
# (config.CHATBOT_AI_CONFIGURED is False) — keep it self-contained and
# grounded only in what's actually on this site, since it can't reason
# beyond a keyword match. Order matters only as a tiebreaker; put more
# specific entries before more general ones that share keywords.
CHATBOT_FAQ = [
    {
        "keywords": ["how many days", "days a week", "days per week", "how often should i", "हफ्ते में कितने दिन", "कितने दिन"],
        "answer": _l("It depends on your level: Beginner is 3 days/week, Intermediate is 4, and Active is 5. Check the Workout Plans page — pick your decade in the age selector there and we'll suggest a starting level."),
    },
    {
        "keywords": ["beginner", "new to working out", "just starting", "where do i start", "never worked out", "शुरुआत", "नया हूं"],
        "answer": _l("Start with the Beginner plan on the Workout Plans page — 3 days/week, bodyweight-focused, built to be safe for a true starting point. It's fine to start slow and build up from there."),
    },
    {
        "keywords": ["which plan", "which level", "what level am i", "what plan should i", "कौन सा प्लान", "कौन सा लेवल"],
        "answer": _l("Pick your age decade in the selector on the Workout Plans page — it'll highlight a recommended starting level. That's just a suggestion though; your actual fitness level matters more than your age."),
    },
    {
        "keywords": ["how much protein", "protein need", "protein intake", "grams of protein", "कितना प्रोटीन", "प्रोटीन की जरूरत"],
        "answer": _l("Your protein target goes up with age, not down — roughly 1.2–1.6 g/kg of bodyweight in your 20s, up to 1.8–2.4 g/kg in your 70s (higher needs fight age-related muscle loss). See the Diet Plan page for your exact decade's target."),
    },
    {
        "keywords": ["protein source", "what should i eat", "protein food", "high protein food", "vegetarian protein", "vegan protein", "प्रोटीन स्रोत", "क्या खाऊं"],
        "answer": _l("The Diet Plan page has a full list — animal-based (chicken, eggs, Greek yogurt, fish), plant-based (lentils, chickpeas, tofu, edamame, quinoa), and protein supplements (whey, casein, plant protein powder) if whole food alone isn't hitting your target."),
    },
    {
        "keywords": ["protein powder", "whey", "casein", "supplement", "protein shake", "प्रोटीन पाउडर", "सप्लीमेंट"],
        "answer": _l("Whey, casein, and plant-based protein powders are all fine as a convenient top-up — not a replacement for whole foods. Look for third-party tested products and check with a doctor first if you're on medication. Full options on the Diet Plan page under Protein Sources."),
    },
    {
        "keywords": ["water", "hydration", "how much water", "drink", "dehydrat", "पानी", "हाइड्रेशन"],
        "answer": _l("Aim for roughly 2–3.5 L of water per day, trending down slightly with age — but older adults should drink on a schedule rather than waiting to feel thirsty, since thirst cues get less reliable. See the Diet Plan page for your decade's hydration target."),
    },
    {
        "keywords": ["bmi", "body mass index", "बीएमआई"],
        "answer": _l("Head to the Tools page — there's a free BMI calculator right there, just enter your height and weight."),
    },
    {
        "keywords": ["safe", "60s", "70s", "older", "elderly", "senior", "बुजुर्ग", "सुरक्षित"],
        "answer": _l("Yes, strength training is safe and valuable at any age with the right modifications — lower-impact options, more warm-up time, and a focus on balance and functional movement. Get medical clearance first if you have any conditions. See Safety Tips for decade-specific guidance."),
    },
    {
        "keywords": ["injury", "hurt", "pain", "prevent injury", "sore", "चोट", "दर्द"],
        "answer": _l("The big three: warm up properly (5-10 min, longer as you get older), prioritize form over weight, and take 1-2 rest days a week. If something causes sharp pain, stop — mild fatigue is fine, pain isn't. Full guidance on the Safety Tips page."),
    },
    {
        "keywords": ["warm up", "warmup", "वार्म अप"],
        "answer": _l("5-10 minutes before any workout, minimum — and give yourself more like 10+ minutes as you get into your 60s and 70s."),
    },
    {
        "keywords": ["build muscle after", "lose muscle", "muscle loss", "muscle after 50", "muscle after 60", "sarcopenia", "मांसपेशियां", "मसल्स"],
        "answer": _l("Yes, you can absolutely build and maintain muscle later in life — it just takes more deliberate effort: higher relative protein intake and consistent resistance training, since the body becomes more resistant to building muscle with age (\"anabolic resistance\"). See the Diet Plan and Workout Plans pages."),
    },
    {
        "keywords": ["doctor", "clearance", "medical condition", "health condition", "डॉक्टर", "बीमारी"],
        "answer": _l("If you have an existing health condition, are over 50, or are making a big change to your routine, it's worth getting a doctor's clearance first — especially before starting a new intensity level. This site gives general guidance, not medical advice."),
    },
    {
        "keywords": ["walk", "walking", "cardio", "पैदल", "टहलना"],
        "answer": _l("Walking is a great low-impact cardio option at any age, and it's built into every plan here. Swimming and cycling are good alternatives if you want to vary it up."),
    },
    {
        "keywords": ["rest day", "recovery", "how many rest days", "overtraining", "आराम का दिन", "रिकवरी"],
        "answer": _l("1-2 full rest days a week is the general guidance here, more if you're newer to training or in an older decade where recovery naturally takes longer."),
    },
    {
        "keywords": ["subscribe", "premium", "membership", "price", "cost", "upi", "stripe", "payment", "सदस्यता", "कीमत", "भुगतान"],
        "answer": _l("Check out the Membership page — you can subscribe via Stripe (card) or UPI. You'll need to be logged in first."),
    },
    {
        "keywords": ["hello", "hi there", "hey", "good morning", "good afternoon", "नमस्ते", "हैलो"],
        "answer": _l("Hey! Ask me anything about workouts, protein, hydration, or safety — I'm scoped to training and diet questions for this site."),
    },
    {
        "keywords": ["thank", "thanks", "धन्यवाद", "शुक्रिया"],
        "answer": _l("Anytime! Good luck with your training. 💪"),
    },
]

# Rotated as a fixed, site-wide background behind every page (base.html).
# Filenames under static/backgrounds/. Real photos from Pexels (free
# license — free for commercial use, no attribution required); each was
# reviewed for content before being added. See CLAUDE.md's static/ entry
# for the source photo of each and how to swap in different ones.
BACKGROUND_IMAGES = [
    "bg-sprint.jpg",
    "bg-squat.jpg",
    "bg-boxing.jpg",
    "bg-jump.jpg",
    "bg-kettlebell.jpg",
]
