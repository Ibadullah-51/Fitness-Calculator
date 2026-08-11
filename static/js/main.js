/* =========================================================================
   MacroLab — frontend logic
   Responsibilities:
     1. Tab + unit switching
     2. Read each form, POST JSON to the Flask API, render the readout
     3. Share state across tabs so results chain (BMR -> goals -> protein -> macros)
     4. Drive the live macro donut + fat/carb slider
   Everything talks to the same-origin Flask API under /api/.
   ========================================================================= */

"use strict";

/* ---- Tiny DOM helpers ------------------------------------------------- */
const $  = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

// Does the user prefer reduced motion? Used to skip count-up animations.
const REDUCED_MOTION = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/* ---- Shared app state ------------------------------------------------- */
// One object holds everything the tabs share. When Body stats is computed,
// weight/goals/etc. land here and later tabs read from it to prefill.
const state = {
  units: "metric",       // "metric" | "imperial"
  weight: null,          // raw weight value the user typed (in current units)
  bmr: null,
  tdee: null,
  goals: null,           // dict of calorie goals from /api/tdee
  chosenCalories: null,  // which calorie target to feed into Macros
  proteinG: null,        // recommended protein grams from /api/protein
};

/* ---- API helper ------------------------------------------------------- */
// POST a JS object as JSON and return the parsed response.
// If the server responds with ok:false, we throw an Error carrying its
// message so the caller can show it inline.
async function postJSON(endpoint, payload) {
  const res = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!res.ok || !data.ok) {
    throw new Error(data.error || "Something went wrong.");
  }
  return data;
}

/* ---- Small UI utilities ---------------------------------------------- */

// Show / clear an inline error message inside a form.
function showError(form, message) {
  const el = $("[data-error]", form);
  if (!el) return;
  if (message) {
    el.textContent = message;
    el.hidden = false;
  } else {
    el.hidden = true;
  }
}

// Swap a readout panel from its empty state to its populated body.
function revealReadout(readout) {
  $("[data-empty]", readout).hidden = true;
  $("[data-body]", readout).hidden = false;
}

// Animate a number counting up to `target` inside `el`.
function countTo(el, target) {
  target = Math.round(target);
  if (REDUCED_MOTION) { el.textContent = target.toLocaleString(); return; }

  const start = 0;
  const duration = 550;
  const t0 = performance.now();

  function frame(now) {
    const p = Math.min((now - t0) / duration, 1);
    // easeOutCubic for a natural deceleration
    const eased = 1 - Math.pow(1 - p, 3);
    el.textContent = Math.round(start + (target - start) * eased).toLocaleString();
    if (p < 1) requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
}

/* ---- Unit label maps -------------------------------------------------- */
const UNIT_LABELS = {
  metric:   { length: "cm", weight: "kg" },
  imperial: { length: "in", weight: "lb" },
};

// Update every unit chip (cm/kg vs in/lb) when the toggle changes.
function applyUnitLabels() {
  const labels = UNIT_LABELS[state.units];
  $$("[data-unit='length']").forEach(el => (el.textContent = labels.length));
  $$("[data-unit='weight']").forEach(el => (el.textContent = labels.weight));
}

/* =========================================================================
   1. Unit toggle
   ========================================================================= */
// Conversion factors used when the user flips units.
const LB_PER_KG = 2.20462;
const CM_PER_IN = 2.54;

// Convert every measurement input in place so the number matches the new unit
// (e.g. 80 kg becomes 176.4 lb) rather than being silently relabelled.
function convertInputs(from, to) {
  if (from === to) return;
  $$(".input-wrap").forEach(wrap => {
    const unitChip = $("[data-unit]", wrap);
    const input = $("input", wrap);
    if (!unitChip || !input || input.value === "") return;

    const kind = unitChip.dataset.unit;   // "length" | "weight"
    let v = parseFloat(input.value);
    if (Number.isNaN(v)) return;

    if (kind === "weight") {
      v = to === "imperial" ? v * LB_PER_KG : v / LB_PER_KG;
    } else if (kind === "length") {
      v = to === "imperial" ? v / CM_PER_IN : v * CM_PER_IN;
    }
    input.value = Math.round(v * 10) / 10;   // 1 decimal place
  });
}

$$(".unit-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    if (btn.classList.contains("is-active")) return;
    $$(".unit-btn").forEach(b => b.classList.remove("is-active"));
    btn.classList.add("is-active");

    const from = state.units;
    const to = btn.dataset.units;
    convertInputs(from, to);   // keep the numbers meaningful
    state.units = to;
    applyUnitLabels();
    // Prior results were computed in the old units, so clear them.
    resetAllReadouts();
  });
});

// Return every readout to its empty state (used on unit change).
function resetAllReadouts() {
  $$(".readout").forEach(r => {
    $("[data-empty]", r).hidden = false;
    $("[data-body]", r).hidden = true;
  });
  state.weight = state.bmr = state.tdee = state.goals = state.chosenCalories = state.proteinG = null;
  // Hide any "filled from earlier tabs" hints since state was cleared.
  $$("[data-prefill-hint]").forEach(h => (h.hidden = true));
}

/* =========================================================================
   2. Tabs
   ========================================================================= */
$$(".tab").forEach(tab => {
  tab.addEventListener("click", () => {
    const name = tab.dataset.tab;

    $$(".tab").forEach(t => {
      const active = t === tab;
      t.classList.toggle("is-active", active);
      t.setAttribute("aria-selected", active ? "true" : "false");
    });
    $$(".panel").forEach(p =>
      p.classList.toggle("is-active", p.dataset.panel === name)
    );

    // When arriving on a tab, prefill it from shared state.
    if (name === "protein") prefillProtein();
    if (name === "macros")  prefillMacros();
  });
});

/* =========================================================================
   3. Segmented controls (sex + goal)
   ========================================================================= */
// Sex toggles. There's one on Body stats and one on Body fat; each tracks its
// own value. On Body fat, switching to "female" reveals the hip field.
const genderValue = { stats: "male", bodyfat: "male" };

$$("[data-gender-group]").forEach(group => {
  const which = group.dataset.genderGroup;
  $$(".seg", group).forEach(seg => {
    seg.addEventListener("click", () => {
      $$(".seg", group).forEach(s => s.classList.remove("is-active"));
      seg.classList.add("is-active");
      genderValue[which] = seg.dataset.gender;

      // Body fat: women need a hip measurement.
      if (which === "bodyfat") {
        const hipField = $("[data-hip-field]");
        hipField.hidden = genderValue.bodyfat !== "female";
      }
    });
  });
});

// Goal toggle on the Protein tab.
let proteinGoal = "maintenance";
$$("[data-goal-group] .seg").forEach(seg => {
  seg.addEventListener("click", () => {
    $$("[data-goal-group] .seg").forEach(s => s.classList.remove("is-active"));
    seg.classList.add("is-active");
    proteinGoal = seg.dataset.goal;
  });
});

/* =========================================================================
   4. Body stats form  ->  /api/bmr then /api/tdee
   ========================================================================= */
const GOAL_LABELS = {
  fat_loss_aggressive: "Fat loss · aggressive",
  fat_loss_moderate:   "Fat loss · moderate",
  fat_loss_mild:       "Fat loss · mild",
  maintenance:         "Maintenance",
  muscle_gain_mild:    "Muscle gain · mild",
  muscle_gain_moderate:"Muscle gain · moderate",
};
// Order goals from biggest deficit to biggest surplus for a natural ladder.
const GOAL_ORDER = [
  "fat_loss_aggressive", "fat_loss_moderate", "fat_loss_mild",
  "maintenance", "muscle_gain_mild", "muscle_gain_moderate",
];

$("#stats-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  showError(e.target, null);

  // Collect inputs.
  const payload = {
    units:  state.units,
    gender: genderValue.stats,
    age:    $("#age").value,
    height: $("#height").value,
    weight: $("#weight").value,
  };

  try {
    // Step 1: BMR.
    const bmrRes = await postJSON("/api/bmr", payload);

    // Step 2: TDEE (+ goals), using the BMR we just got and the activity level.
    const tdeeRes = await postJSON("/api/tdee", {
      bmr: bmrRes.bmr,
      activity_level: $("#activity").value,
    });

    // Save to shared state.
    state.weight = payload.weight;
    state.bmr = bmrRes.bmr;
    state.tdee = tdeeRes.tdee;
    state.goals = tdeeRes.goals;
    state.chosenCalories = tdeeRes.tdee; // default macro target = maintenance

    renderStats();
  } catch (err) {
    showError(e.target, err.message);
  }
});

function renderStats() {
  const r = $("#stats-readout");
  revealReadout(r);

  countTo($("[data-bmr]", r), state.bmr);
  countTo($("[data-tdee]", r), state.tdee);

  // Build the tappable goals ladder.
  const list = $("[data-goals]", r);
  list.innerHTML = "";
  GOAL_ORDER.forEach(key => {
    const g = state.goals[key];
    if (!g) return;

    const li = document.createElement("li");
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "goal-row";

    const delta = g.delta;
    const deltaClass = delta > 0 ? "pos" : delta < 0 ? "neg" : "";
    const deltaText = delta === 0 ? "±0" : (delta > 0 ? "+" : "") + delta;

    btn.innerHTML =
      `<span class="goal-name">${GOAL_LABELS[key]}</span>` +
      `<span class="goal-cal">${g.calories.toLocaleString()}</span>` +
      `<span class="goal-delta ${deltaClass}">${deltaText}</span>` +
      `<span class="goal-arrow">→</span>`;

    // Clicking a goal sends its calorie target to the Macros tab.
    btn.addEventListener("click", () => {
      state.chosenCalories = g.calories;
      goToTab("macros");
    });

    li.appendChild(btn);
    list.appendChild(li);
  });
}

// Programmatically switch tabs (reused by the "send to macros" buttons).
function goToTab(name) {
  $(`.tab[data-tab='${name}']`).click();
}

/* =========================================================================
   5. Protein form  ->  /api/protein
   ========================================================================= */
// Prefill weight from Body stats when landing on the Protein tab.
function prefillProtein() {
  if (state.weight && !$("#p-weight").value) {
    $("#p-weight").value = state.weight;
    $("#protein-form [data-prefill-hint]").hidden = false;
  }
}

$("#protein-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  showError(e.target, null);

  try {
    const res = await postJSON("/api/protein", {
      units: state.units,
      weight: $("#p-weight").value,
      goal: proteinGoal,
    });
    renderProtein(res.protein);
  } catch (err) {
    showError(e.target, err.message);
  }
});

function renderProtein(p) {
  const r = $("#protein-readout");
  revealReadout(r);

  countTo($("[data-protein-g]", r), p.recommended_g);
  countTo($("[data-protein-kcal]", r), p.calories);
  $("[data-protein-low]", r).textContent = p.range_g.low;
  $("[data-protein-high]", r).textContent = p.range_g.high;

  // Position the marker along the low..high band.
  const { low, high } = p.range_g;
  const pct = high > low ? ((p.recommended_g - low) / (high - low)) * 100 : 50;
  $("[data-range-fill]", r).style.width = pct + "%";
  $("[data-range-dot]", r).style.left = pct + "%";

  // Remember the recommendation so Macros can use it.
  state.proteinG = p.recommended_g;
}

// "Use in Macros" button on the protein readout.
$("[data-send-protein]").addEventListener("click", () => {
  if (state.proteinG) goToTab("macros");
});

/* =========================================================================
   6. Macros  ->  /api/macros  (+ live client-side recompute on slider)
   ========================================================================= */
const DONUT_CIRCUMFERENCE = 2 * Math.PI * 52; // r = 52 in the SVG

// Prefill calories + protein from earlier tabs when arriving on Macros.
function prefillMacros() {
  let filled = false;
  if (state.chosenCalories && !$("#m-calories").value) {
    $("#m-calories").value = state.chosenCalories;
    filled = true;
  }
  if (state.proteinG && !$("#m-protein").value) {
    $("#m-protein").value = state.proteinG;
    filled = true;
  }
  $("#macros-form [data-prefill-hint]").hidden = !filled;

  // If we have both numbers, compute immediately so the donut is ready.
  if ($("#m-calories").value && $("#m-protein").value) {
    computeMacrosFromServer();
  }
}

// Mirror of the server's macro math, used for the instant slider response so we
// don't hit the network on every pixel of drag. Kept identical to macros.py.
function computeMacrosClient(calories, proteinG, fatFraction) {
  fatFraction = Math.max(0.15, Math.min(0.60, fatFraction));
  const proteinKcal = proteinG * 4;
  let remaining = calories - proteinKcal;
  if (remaining < 0) remaining = 0;

  const fatKcal = remaining * fatFraction;
  const carbKcal = remaining * (1 - fatFraction);
  const fatG = Math.round(fatKcal / 9);
  const carbG = Math.round(carbKcal / 4);

  const pct = (kcal) => (calories ? Math.round((kcal / calories) * 100) : 0);

  return {
    calories,
    protein: { grams: proteinG, calories: proteinKcal, percent: pct(proteinKcal) },
    fat:     { grams: fatG,     calories: fatKcal,     percent: pct(fatKcal) },
    carbs:   { grams: carbG,    calories: carbKcal,    percent: pct(carbKcal) },
    // Exact fractions (not rounded %) for gap-free donut arcs:
    _frac: {
      protein: calories ? proteinKcal / calories : 0,
      fat:     calories ? fatKcal / calories : 0,
      carbs:   calories ? carbKcal / calories : 0,
    },
  };
}

// Authoritative compute via the API (used on load / when the numbers change).
// The server validates the inputs; the slider drag then uses the client mirror.
async function computeMacrosFromServer() {
  const calories = $("#m-calories").value;
  const protein  = $("#m-protein").value;
  const fatPct   = Number($("#fat-slider").value);

  if (!calories || !protein) return;

  try {
    showError($("#macros-form"), null);
    await postJSON("/api/macros", {
      goal_calories: calories,
      protein_g: protein,
      fat_pct: fatPct,           // server accepts 0-100 and normalizes
    });
    // Render from the client mirror so the arc fractions are exact.
    renderMacros(computeMacrosClient(Number(calories), Number(protein), fatPct / 100));
  } catch (err) {
    showError($("#macros-form"), err.message);
  }
}

function renderMacros(m) {
  const r = $("#macros-readout");
  revealReadout(r);

  $("[data-total]", r).textContent = m.calories.toLocaleString();

  $("[data-mg-protein]", r).textContent = m.protein.grams;
  $("[data-mg-carbs]", r).textContent   = m.carbs.grams;
  $("[data-mg-fat]", r).textContent     = m.fat.grams;
  $("[data-mp-protein]", r).textContent = m.protein.percent + "%";
  $("[data-mp-carbs]", r).textContent   = m.carbs.percent + "%";
  $("[data-mp-fat]", r).textContent     = m.fat.percent + "%";

  // Draw the donut. Each arc's length is its fraction of the circumference;
  // we offset each segment so they sit end-to-end around the ring.
  const order = [
    { seg: "protein", frac: m._frac.protein },
    { seg: "carbs",   frac: m._frac.carbs },
    { seg: "fat",     frac: m._frac.fat },
  ];
  let offset = 0;
  order.forEach(({ seg, frac }) => {
    const len = frac * DONUT_CIRCUMFERENCE;
    const el = $(`[data-seg='${seg}']`, r);
    el.style.strokeDasharray = `${len} ${DONUT_CIRCUMFERENCE - len}`;
    el.style.strokeDashoffset = `${-offset}`;
    offset += len;
  });
}

// Live slider: update the % label and recompute instantly (client-side).
$("#fat-slider").addEventListener("input", () => {
  const fatPct = Number($("#fat-slider").value);
  $("[data-fat-pct]").textContent = fatPct;

  const calories = Number($("#m-calories").value);
  const protein  = Number($("#m-protein").value);
  if (calories && protein) {
    renderMacros(computeMacrosClient(calories, protein, fatPct / 100));
  }
});

// If the user edits calories or protein directly, re-validate via the server.
["#m-calories", "#m-protein"].forEach(sel => {
  $(sel).addEventListener("change", computeMacrosFromServer);
});

/* =========================================================================
   7. Body fat form  ->  /api/bodyfat
   ========================================================================= */
$("#bodyfat-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  showError(e.target, null);

  const payload = {
    units: state.units,
    gender: genderValue.bodyfat,
    height: $("#bf-height").value,
    neck:   $("#bf-neck").value,
    waist:  $("#bf-waist").value,
  };
  if (genderValue.bodyfat === "female") payload.hip = $("#bf-hip").value;

  try {
    const res = await postJSON("/api/bodyfat", payload);
    renderBodyFat(res.bodyfat);
  } catch (err) {
    showError(e.target, err.message);
  }
});

function renderBodyFat(bf) {
  const r = $("#bodyfat-readout");
  revealReadout(r);

  $("[data-bf-pct]", r).textContent = bf.body_fat_percent;
  $("[data-bf-category]", r).textContent = bf.category;
  $("[data-bf-note]", r).textContent = bf.note;

  // Place the marker on a rough 5%..45% visual scale.
  const clamped = Math.max(5, Math.min(45, bf.body_fat_percent));
  const pos = ((clamped - 5) / 40) * 100;
  $("[data-bf-dot]", r).style.left = pos + "%";
}

/* =========================================================================
   Init
   ========================================================================= */
applyUnitLabels();
