document.addEventListener("DOMContentLoaded", () => {
    initWorkoutChecklists();
    initBmiCalculator();
    initHeartRateCalculator();
    initTdeeCalculator();
    initOneRepMaxCalculator();
    initWaistHipCalculator();
    initAgeSelector();
    initMotivationBanner();
    initChatWidget();
    initBackgroundRotator();
    initNavSelects();
    initConfirmForms();
});

// The CSP (see app.py's Talisman config) has no 'unsafe-inline' in
// script-src, which silently blocks inline event handler attributes
// (onchange=, onsubmit=, etc) — no JS error, the handler just never
// fires. Every interactive element needs its listener attached here via
// addEventListener instead.

function initNavSelects() {
    document.querySelectorAll("[data-nav-select]").forEach((select) => {
        select.addEventListener("change", () => {
            if (select.value) location.href = select.value;
        });
    });
}

function initConfirmForms() {
    document.querySelectorAll("form[data-confirm]").forEach((form) => {
        form.addEventListener("submit", (event) => {
            if (!window.confirm(form.dataset.confirm)) {
                event.preventDefault();
            }
        });
    });
}

// Translated strings for JS-generated text, rendered by base.html via
// Babel's `_()` so they follow the visitor's locale. `%(name)s` tokens are
// substituted client-side since JS has no gettext-style interpolation.
function readI18nStrings() {
    const el = document.getElementById("i18n-strings-data");
    if (!el) return {};
    try {
        return JSON.parse(el.textContent);
    } catch (e) {
        return {};
    }
}

const I18N = readI18nStrings();

function t(key, params) {
    let text = I18N[key] || key;
    if (params) {
        Object.keys(params).forEach((name) => {
            text = text.replace(`%(${name})s`, params[name]);
        });
    }
    return text;
}

// Checklist state lives in localStorage for everyone (works with no
// account, and offline). For a logged-in visitor it also syncs to the
// server (/api/workout-progress) — server state wins over local state on
// load, since it reflects every device, not just this one; local state is
// still updated as a fast/offline-friendly cache. `value` on each checkbox
// is the exercise's stable index (see workouts.html), not its translated
// label text — the label changes per locale, an index doesn't.
function initWorkoutChecklists() {
    const planCards = document.querySelectorAll("[data-plan]");
    if (!planCards.length) return;

    const isAuthenticated = document.body.dataset.authenticated === "true";

    function setup(serverProgress) {
        planCards.forEach((card) => {
            const planName = card.dataset.plan;
            const checkboxes = card.querySelectorAll("input[type=checkbox]");
            const progressBar = card.querySelector(`[data-progress-for="${planName}"]`);
            const storageKey = `fitafter40-progress-${planName}`;

            let saved = {};
            try {
                saved = JSON.parse(localStorage.getItem(storageKey) || "{}");
            } catch (e) {
                saved = {};
            }
            if (serverProgress && serverProgress[planName]) {
                saved = Object.assign({}, saved, serverProgress[planName]);
                try {
                    localStorage.setItem(storageKey, JSON.stringify(saved));
                } catch (e) {
                    /* localStorage unavailable, ignore */
                }
            }

            function updateProgress() {
                const total = checkboxes.length;
                const done = Array.from(checkboxes).filter((cb) => cb.checked).length;
                const pct = total ? Math.round((done / total) * 100) : 0;
                if (progressBar) {
                    progressBar.style.width = pct + "%";
                    progressBar.textContent = pct + "%";
                }
            }

            checkboxes.forEach((cb) => {
                if (saved[cb.value]) {
                    cb.checked = true;
                }
                cb.addEventListener("change", () => {
                    saved[cb.value] = cb.checked;
                    try {
                        localStorage.setItem(storageKey, JSON.stringify(saved));
                    } catch (e) {
                        /* localStorage unavailable, ignore */
                    }
                    if (isAuthenticated) {
                        syncWorkoutProgress(planName, Number(cb.value), cb.checked);
                    }
                    updateProgress();
                });
            });

            updateProgress();
        });
    }

    if (isAuthenticated) {
        fetchWorkoutProgress().then(setup).catch(() => setup(null));
    } else {
        setup(null);
    }
}

function fetchWorkoutProgress() {
    return fetch("/api/workout-progress", { headers: { Accept: "application/json" } }).then((r) =>
        r.ok ? r.json() : {}
    );
}

function syncWorkoutProgress(levelId, exerciseIndex, completed) {
    const csrfMeta = document.querySelector('meta[name="csrf-token"]');
    fetch("/api/workout-progress", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfMeta ? csrfMeta.content : "",
        },
        body: JSON.stringify({ level_id: levelId, exercise_index: exerciseIndex, completed: completed }),
    }).catch(() => {
        /* Offline or request failed — localStorage already has the local
           change, so the checklist itself still works; it just won't sync
           to other devices until the next successful save. */
    });
}

function initBmiCalculator() {
    const form = document.getElementById("bmi-form");
    if (!form) return;

    const result = document.getElementById("bmi-result");
    const isImperial = form.dataset.unitSystem === "imperial";

    form.addEventListener("submit", (event) => {
        event.preventDefault();

        let bmi;
        if (isImperial) {
            const heightFt = parseFloat(document.getElementById("bmi-height-ft").value) || 0;
            const heightIn = parseFloat(document.getElementById("bmi-height-in").value) || 0;
            const weightLb = parseFloat(document.getElementById("bmi-weight-lb").value);
            const totalInches = heightFt * 12 + heightIn;

            if (!totalInches || !weightLb || totalInches <= 0 || weightLb <= 0) {
                result.textContent = t("bmi_invalid");
                return;
            }
            // Standard imperial BMI formula — avoids a separate cm/kg
            // conversion step, since it's already unit-correct on its own.
            bmi = (703 * weightLb) / (totalInches * totalInches);
        } else {
            const heightCm = parseFloat(document.getElementById("bmi-height").value);
            const weightKg = parseFloat(document.getElementById("bmi-weight").value);

            if (!heightCm || !weightKg || heightCm <= 0 || weightKg <= 0) {
                result.textContent = t("bmi_invalid");
                return;
            }
            const heightM = heightCm / 100;
            bmi = weightKg / (heightM * heightM);
        }

        let category;
        if (bmi < 18.5) category = t("bmi_underweight");
        else if (bmi < 25) category = t("bmi_healthy");
        else if (bmi < 30) category = t("bmi_overweight");
        else category = t("bmi_obese");

        // BMI itself is unisex — same formula, same category cutoffs,
        // regardless of sex. Body fat % is the metric that actually
        // differs by sex (women carry more essential fat at the same
        // BMI), so that's the one sex feeds into here, not BMI itself.
        // Age and sex are both optional; without either, only BMI shows,
        // same as before this feature existed.
        const age = parseFloat(document.getElementById("bmi-age").value);
        const sex = document.getElementById("bmi-sex").value;

        if (age > 0 && (sex === "male" || sex === "female")) {
            const bodyFat = estimateBodyFatPercent(bmi, age, sex);
            result.textContent = t("bmi_result_with_bodyfat", {
                bmi: bmi.toFixed(1),
                category: category,
                bodyfat: bodyFat.toFixed(1),
            });
        } else {
            result.textContent = t("bmi_result", { bmi: bmi.toFixed(1), category: category });
        }
    });
}

// Deurenberg et al. (1991) formula — a widely-used estimate, not a
// measurement. Tends to overestimate body fat % for very muscular people,
// since it infers fat from BMI alone rather than actually measuring it.
function estimateBodyFatPercent(bmi, age, sex) {
    const sexFactor = sex === "male" ? 1 : 0;
    return 1.2 * bmi + 0.23 * age - 10.8 * sexFactor - 5.4;
}

function initHeartRateCalculator() {
    const form = document.getElementById("hr-form");
    if (!form) return;
    const result = document.getElementById("hr-result");

    form.addEventListener("submit", (event) => {
        event.preventDefault();

        const age = parseFloat(document.getElementById("hr-age").value);
        if (!age || age <= 0 || age > 120) {
            result.textContent = t("hr_invalid");
            return;
        }

        // "220 minus age" — the most commonly cited estimate for maximum
        // heart rate; not a measurement. Moderate/vigorous zones follow
        // the American Heart Association's standard 50–70% / 70–85%
        // bands of that estimated max.
        const maxHr = 220 - age;
        result.textContent = t("hr_result", {
            max: Math.round(maxHr),
            modLow: Math.round(maxHr * 0.5),
            modHigh: Math.round(maxHr * 0.7),
            vigLow: Math.round(maxHr * 0.7),
            vigHigh: Math.round(maxHr * 0.85),
        });
    });
}

function initTdeeCalculator() {
    const form = document.getElementById("tdee-form");
    if (!form) return;
    const result = document.getElementById("tdee-result");
    const isImperial = form.dataset.unitSystem === "imperial";

    form.addEventListener("submit", (event) => {
        event.preventDefault();

        let heightCm, weightKg;
        if (isImperial) {
            const heightFt = parseFloat(document.getElementById("tdee-height-ft").value) || 0;
            const heightIn = parseFloat(document.getElementById("tdee-height-in").value) || 0;
            const weightLb = parseFloat(document.getElementById("tdee-weight-lb").value);
            heightCm = (heightFt * 12 + heightIn) * 2.54;
            weightKg = weightLb * 0.45359237;
        } else {
            heightCm = parseFloat(document.getElementById("tdee-height").value);
            weightKg = parseFloat(document.getElementById("tdee-weight").value);
        }

        const age = parseFloat(document.getElementById("tdee-age").value);
        const sex = document.getElementById("tdee-sex").value;
        const activityMultiplier = parseFloat(document.getElementById("tdee-activity").value);

        if (!heightCm || !weightKg || !age || heightCm <= 0 || weightKg <= 0 || age <= 0) {
            result.textContent = t("tdee_invalid");
            return;
        }

        // Mifflin-St Jeor equation. Without a stated sex, use the
        // midpoint of the male (+5) and female (-161) constants rather
        // than forcing a choice — same "don't require disclosure"
        // approach as the BMI calculator's body-fat estimate.
        let sexConstant;
        if (sex === "male") sexConstant = 5;
        else if (sex === "female") sexConstant = -161;
        else sexConstant = -78;

        const bmr = 10 * weightKg + 6.25 * heightCm - 5 * age + sexConstant;
        const tdee = bmr * activityMultiplier;

        result.textContent = t("tdee_result", { tdee: Math.round(tdee), bmr: Math.round(bmr) });
    });
}

function initOneRepMaxCalculator() {
    const form = document.getElementById("orm-form");
    if (!form) return;
    const result = document.getElementById("orm-result");
    const tableEl = document.getElementById("orm-table");
    const isImperial = form.dataset.unitSystem === "imperial";

    form.addEventListener("submit", (event) => {
        event.preventDefault();

        const weight = parseFloat(document.getElementById("orm-weight").value);
        const reps = parseFloat(document.getElementById("orm-reps").value);

        if (!weight || weight <= 0 || !reps || reps < 1 || reps > 15) {
            result.textContent = t("orm_invalid");
            tableEl.innerHTML = "";
            return;
        }

        // Epley formula — most accurate under ~10-12 reps; accuracy
        // degrades for higher-rep sets, which is why the field caps at 15.
        const orm = weight * (1 + reps / 30);
        result.textContent = t(isImperial ? "orm_result_imperial" : "orm_result_metric", {
            orm: orm.toFixed(1),
        });

        const headerPercent = t("orm_table_percent");
        const headerWeight = t(isImperial ? "orm_table_weight_imperial" : "orm_table_weight_metric");
        const rows = [90, 80, 70, 60, 50]
            .map((pct) => `<tr><td>${pct}%</td><td>${((orm * pct) / 100).toFixed(1)}</td></tr>`)
            .join("");
        tableEl.innerHTML =
            `<table class="tool-result-table"><thead><tr><th>${headerPercent}</th>` +
            `<th>${headerWeight}</th></tr></thead><tbody>${rows}</tbody></table>`;
    });
}

function initWaistHipCalculator() {
    const form = document.getElementById("whr-form");
    if (!form) return;
    const result = document.getElementById("whr-result");

    form.addEventListener("submit", (event) => {
        event.preventDefault();

        const waist = parseFloat(document.getElementById("whr-waist").value);
        const hip = parseFloat(document.getElementById("whr-hip").value);
        const sex = document.getElementById("whr-sex").value;

        if (!waist || !hip || waist <= 0 || hip <= 0) {
            result.textContent = t("whr_invalid");
            return;
        }

        const ratio = waist / hip;

        if (sex === "male" || sex === "female") {
            // WHO risk bands — deliberately different per sex, unlike
            // BMI, since this is a metric where the sex difference is
            // actually standard clinical practice.
            let riskKey;
            if (sex === "male") {
                riskKey = ratio < 0.9 ? "whr_risk_low" : ratio < 1.0 ? "whr_risk_moderate" : "whr_risk_high";
            } else {
                riskKey = ratio < 0.8 ? "whr_risk_low" : ratio < 0.85 ? "whr_risk_moderate" : "whr_risk_high";
            }
            result.textContent = t("whr_result_with_risk", { ratio: ratio.toFixed(2), risk: t(riskKey) });
        } else {
            result.textContent = t("whr_result", { ratio: ratio.toFixed(2) });
        }
    });
}

const AGE_STORAGE_KEY = "fitafter40-age-group";

function getStoredAgeGroup() {
    try {
        return localStorage.getItem(AGE_STORAGE_KEY) || "";
    } catch (e) {
        return "";
    }
}

function setStoredAgeGroup(ageId) {
    try {
        if (ageId) {
            localStorage.setItem(AGE_STORAGE_KEY, ageId);
        } else {
            localStorage.removeItem(AGE_STORAGE_KEY);
        }
    } catch (e) {
        /* localStorage unavailable, ignore */
    }
}

function readAgeGuidanceData() {
    const el = document.getElementById("age-guidance-data");
    if (!el) return {};
    try {
        return JSON.parse(el.textContent);
    } catch (e) {
        return {};
    }
}

// {level_id: {age_id: [{label, video_url}, ...]}} — see content.py's
// WORKOUT_PLANS comment and app.py's exercises_for_age(). Only present on
// workouts.html.
function readWorkoutExercisesData() {
    const el = document.getElementById("workout-exercises-data");
    if (!el) return {};
    try {
        return JSON.parse(el.textContent);
    } catch (e) {
        return {};
    }
}

function initAgeSelector() {
    const pills = document.querySelectorAll(".age-pill");
    if (!pills.length) return;

    const guidance = readAgeGuidanceData();
    const exercisesByAge = readWorkoutExercisesData();

    // Capture the as-rendered (no-age-selected) exercise text/links once,
    // so clearing the age selection ("Any age") can restore them exactly
    // rather than needing a separate "default" entry in the JSON data.
    const exerciseItems = document.querySelectorAll("[data-exercise-index]");
    exerciseItems.forEach((li) => {
        const labelEl = li.querySelector("[data-exercise-label]");
        const videoEl = li.querySelector("[data-exercise-video]");
        if (labelEl) li.dataset.defaultLabel = labelEl.textContent;
        if (videoEl) li.dataset.defaultVideo = videoEl.getAttribute("href");
    });

    function applyAgeGroup(ageId) {
        pills.forEach((btn) => {
            btn.classList.toggle("active", btn.dataset.age === ageId);
        });

        const banner = document.querySelector("[data-age-recommendation]");
        if (banner) {
            const info = ageId ? guidance[ageId] : null;
            if (info) {
                banner.hidden = false;
                banner.textContent = t("age_recommendation", { age: ageId, headline: info.headline, blurb: info.blurb });
            } else {
                banner.hidden = true;
                banner.textContent = "";
            }
        }

        const recommendedLevel = ageId && guidance[ageId] ? guidance[ageId].recommended_level : null;
        document.querySelectorAll("[data-plan]").forEach((card) => {
            const isRecommended = Boolean(recommendedLevel) && card.dataset.plan === recommendedLevel;
            card.classList.toggle("recommended", isRecommended);
            const badge = card.querySelector("[data-recommended-badge]");
            if (badge) {
                badge.hidden = !isRecommended;
            }

            const levelExercises = exercisesByAge[card.dataset.plan];
            const ageExercises = ageId && levelExercises ? levelExercises[ageId] : null;
            card.querySelectorAll("[data-exercise-index]").forEach((li) => {
                const labelEl = li.querySelector("[data-exercise-label]");
                const videoEl = li.querySelector("[data-exercise-video]");
                const exercise = ageExercises ? ageExercises[Number(li.dataset.exerciseIndex)] : null;
                if (exercise) {
                    if (labelEl) labelEl.textContent = exercise.label;
                    if (videoEl) videoEl.setAttribute("href", exercise.video_url);
                } else {
                    if (labelEl) labelEl.textContent = li.dataset.defaultLabel;
                    if (videoEl) videoEl.setAttribute("href", li.dataset.defaultVideo);
                }
            });
        });

        document.querySelectorAll("[data-age-details]").forEach((details) => {
            details.open = details.dataset.ageDetails === ageId;
        });
    }

    pills.forEach((btn) => {
        btn.addEventListener("click", () => {
            const ageId = btn.dataset.age;
            setStoredAgeGroup(ageId);
            applyAgeGroup(ageId);
        });
    });

    applyAgeGroup(getStoredAgeGroup());
}

function initMotivationBanner() {
    const textEl = document.querySelector("[data-motivation-text]");
    const dataEl = document.getElementById("motivation-quotes-data");
    if (!textEl || !dataEl) return;

    let quotes = [];
    try {
        quotes = JSON.parse(dataEl.textContent);
    } catch (e) {
        return;
    }
    if (!Array.isArray(quotes) || quotes.length < 2) return;

    let index = quotes.indexOf(textEl.textContent.trim());
    if (index === -1) index = 0;

    setInterval(() => {
        index = (index + 1) % quotes.length;
        textEl.classList.add("fade-out");
        setTimeout(() => {
            textEl.textContent = quotes[index];
            textEl.classList.remove("fade-out");
        }, 300);
    }, 5000);
}

function initChatWidget() {
    const widget = document.querySelector("[data-chat-widget]");
    if (!widget) return;

    const toggleBtn = widget.querySelector("[data-chat-toggle]");
    const closeBtn = widget.querySelector("[data-chat-close]");
    const panel = widget.querySelector("[data-chat-panel]");
    const messagesEl = widget.querySelector("[data-chat-messages]");
    const form = widget.querySelector("[data-chat-form]");
    const input = widget.querySelector("[data-chat-input]");

    function addMessage(text, sender) {
        const el = document.createElement("div");
        el.className = `chat-message chat-message-${sender}`;
        el.textContent = text;
        messagesEl.appendChild(el);
        messagesEl.scrollTop = messagesEl.scrollHeight;
        return el;
    }

    function openPanel() {
        panel.hidden = false;
        input.focus();
    }

    function closePanel() {
        panel.hidden = true;
    }

    toggleBtn.addEventListener("click", () => {
        if (panel.hidden) {
            openPanel();
        } else {
            closePanel();
        }
    });
    closeBtn.addEventListener("click", closePanel);

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const message = input.value.trim();
        if (!message) return;

        addMessage(message, "user");
        input.value = "";
        input.disabled = true;

        const typingEl = addMessage("…", "bot");

        try {
            const csrfMeta = document.querySelector('meta[name="csrf-token"]');
            const response = await fetch("/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrfMeta ? csrfMeta.content : "",
                },
                body: JSON.stringify({ message: message }),
            });
            const data = await response.json();
            typingEl.textContent = data.reply || t("chat_fallback");
        } catch (e) {
            typingEl.textContent = t("chat_error");
        } finally {
            input.disabled = false;
            input.focus();
        }
    });
}

function initBackgroundRotator() {
    const el = document.querySelector("[data-bg-rotator]");
    const dataEl = document.getElementById("bg-images-data");
    if (!el || !dataEl) return;

    let images = [];
    try {
        images = JSON.parse(dataEl.textContent);
    } catch (e) {
        return;
    }
    if (!Array.isArray(images) || !images.length) return;

    let index = Math.floor(Math.random() * images.length);
    el.style.backgroundImage = `url(${images[index]})`;

    if (images.length < 2) return;

    const prefersReducedMotion = window.matchMedia
        && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReducedMotion) return;

    setInterval(() => {
        index = (index + 1) % images.length;
        el.classList.add("bg-fade");
        setTimeout(() => {
            el.style.backgroundImage = `url(${images[index]})`;
            el.classList.remove("bg-fade");
        }, 700);
    }, 6000);
}
