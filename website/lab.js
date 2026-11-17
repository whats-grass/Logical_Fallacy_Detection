/* Explore the Lab - page logic. Reuses the model engine and helpers of app.js (loaded first):
   el, fmt, pct, tokenize, prepModel, predict, contributions, groupOf, dumbbell, and the global M.
   Every number shown comes from data/results.json; nothing is typed in by hand. */
"use strict";

const LAB = { R: null, ex: [], data: null };

/* ---------- reading progress ---------- */
function initProgress() {
  const bar = $("#progress"); if (!bar) return;
  const upd = () => { const h = document.documentElement; bar.style.width = (100 * h.scrollTop / Math.max(1, h.scrollHeight - h.clientHeight)) + "%"; };
  document.addEventListener("scroll", upd, { passive: true }); upd();
}

/* ---------- chapter 1: label guide + spot the fallacy ---------- */
function renderGuide(guide) {
  const max = Math.max(...guide.map(g => g.share)), focus = ["Slippery Slope", "Ad Hominem", "False Dilemma"];
  $("#guide").replaceChildren(...guide.map(g => el("div", { class: "card" + (focus.includes(g.label) ? " focus" : "") },
    el("b", {}, g.label), el("p", {}, g.description),
    el("div", { class: "share", title: `${g.count.toLocaleString()} arguments` }, el("i", { style: `width:${100 * g.share / max}%` }), el("span", {}, pct(g.share, 1))))));
}
function renderQuiz(items) {
  let k = 0;
  const box = $("#quiz-box");
  const show = () => {
    const q = items[k], out = el("p", { class: "quiz-out", "aria-live": "polite" });
    const opts = el("div", { class: "quiz-opts" }, q.options.map(o => el("button", { onclick: e => {
      opts.querySelectorAll("button").forEach(b => { b.disabled = true; b.classList.toggle("picked", b === e.target); b.classList.toggle("label", b.textContent === q.label); });
      out.innerHTML = `Dataset label: <b>${q.label}</b>`;
      next.hidden = false;
    } }, o)));
    const next = el("button", { class: "next", hidden: "", onclick: () => { k = (k + 1) % items.length; show(); } }, k + 1 < items.length ? "Next argument →" : "Start again");
    box.replaceChildren(el("p", { class: "small" }, `Argument ${k + 1} of ${items.length}`), el("blockquote", {}, q.text), opts, out, next);
  };
  show();
}


/* ---------- chapter 2: see what the model sees ---------- */
const RD = { view: "words", bpe: [] };
function renderReader() {
  const text = $("#rd-text").value, toks = tokenize(text), out = $("#rd-out"), note = $("#rd-note");
  const chips = arr => el("div", { class: "chips" }, arr.map(t => el("span", { class: "chip" + (t.includes(" ") ? " pairchip" : "") }, t)));
  note.textContent = "";
  if (RD.view === "words") { out.replaceChildren(chips(toks)); note.textContent = `${toks.length} word tokens.`; }
  else if (RD.view === "pairs") {
    const pairs = toks.slice(1).map((t, i) => toks[i] + " " + t);
    out.replaceChildren(chips(toks.concat(pairs))); note.textContent = `${toks.length} words + ${pairs.length} word pairs (pairs shown with a dashed outline).`;
  } else if (RD.view === "bpe") {
    const hit = RD.bpe.find(b => b.text === text.trim());
    if (hit) { out.replaceChildren(chips(hit.tokens)); note.textContent = `${hit.tokens.length} BPE pieces (vocabulary of 5,000, learned from the training arguments). Rare words such as names break into familiar fragments.`; }
    else { out.replaceChildren(); note.textContent = "BPE pieces are shown for the seven example arguments in the list above; pick one of them to see its pieces."; }
  } else if (RD.view === "bow") {
    const c = new Map(); toks.forEach(t => c.set(t, (c.get(t) || 0) + 1));
    const rows = [...c].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
    out.replaceChildren(el("div", { class: "tablewrap" }, el("table", { class: "mini" }, el("thead", {}, el("tr", {}, el("th", {}, "word"), el("th", { class: "num" }, "count"))),
      el("tbody", {}, rows.map(([w, n]) => el("tr", {}, el("td", {}, w), el("td", { class: "num" }, n)))))));
    note.textContent = `${rows.length} different words. Order is gone: “the dog bit the man” and “the man bit the dog” get the same counts.`;
  } else {
    const x = featurize(toks), rows = [...x].map(([j, v]) => ({ t: M.vocab[j], v })).sort((a, b) => b.v - a.v);
    const max = rows.length ? rows[0].v : 1;
    out.replaceChildren(...rows.slice(0, 14).map(r => el("div", { class: "prow" }, el("span", { class: "pl" }, r.t),
      el("span", { class: "pbar" }, el("i", { class: "now", style: `width:${100 * r.v / max}%` })), el("span", { class: "pv" }, fmt(r.v, 2)), el("span", {}))));
    note.textContent = `${rows.length} words and word pairs get a score (only those seen in at least two training arguments). Top 14 shown; common words like “the” sink to the bottom.`;
  }
}
function initReader(bpe) {
  RD.bpe = bpe;
  const sel = $("#rd-example");
  sel.replaceChildren(...bpe.map((b, i) => el("option", { value: i }, b.text.slice(0, 70) + "…")));
  const load = i => { $("#rd-text").value = bpe[i].text; renderReader(); };
  sel.addEventListener("change", () => load(+sel.value));
  let t = null; $("#rd-text").addEventListener("input", () => { clearTimeout(t); t = setTimeout(renderReader, 120); });
  document.querySelectorAll("#reader .seg button").forEach(b => b.addEventListener("click", () => {
    document.querySelectorAll("#reader .seg button").forEach(x => x.setAttribute("aria-selected", x === b ? "true" : "false"));
    RD.view = b.dataset.v; renderReader();
  }));
  load(0);
}

/* ---------- chapter 3: contestants and their verdicts ---------- */
function renderContestants(R, data) {
  const T = R.test_table;
  document.querySelectorAll(".stat-line").forEach(p => {
    const r = T.find(x => x.model === p.dataset.model); if (!r) return;
    const nz = /Lasso/.test(r.model) ? ` · keeps ${pct(data.nonzero_share.Lasso, 1)} of its weights` : /ridge/.test(r.model) ? ` · uses ${pct(data.nonzero_share.Ridge, 0)} of its weights` : "";
    p.innerHTML = `Test macro-F1 <b>${fmt(r.macro_f1)}</b> <span class="small">${r.macro_f1_95ci}</span>${nz}`;
  });
  const M4 = data.models, names = ["BoW baseline", "Lasso", "Ridge", "Linear SVM"], nick = { "BoW baseline": "The counter", Lasso: "The minimalist", Ridge: "The diplomat", "Linear SVM": "The border guard" };
  $("#contest-intro").textContent = `Five test arguments, drawn at random (fixed seed) from the ${data.n_disagree} of ${data.n_test} test arguments on which the four contestants do not all agree. Each model says yes or no to every fallacy.`;
  const sel = $("#ct-select");
  sel.replaceChildren(...M4.map((m, i) => el("option", { value: i }, `Argument ${i + 1}: ${m.text.slice(0, 60)}…`)));
  const show = i => {
    const m = M4[i];
    $("#ct-text").textContent = m.text;
    $("#ct-table").replaceChildren(el("p", { class: "small" }, "Dataset label: ", el("b", {}, m.label.join(", "))),
      el("div", { class: "tablewrap" }, el("table", { class: "mini" }, el("thead", {}, el("tr", {}, el("th", {}, "contestant"), el("th", {}, "says"))),
        el("tbody", {}, names.map(n => el("tr", {}, el("td", {}, nick[n], el("span", { class: "small" }, ` (${n})`)),
          el("td", {}, m.pred[n].length ? m.pred[n].map(l => el("span", { class: "tagl" + (m.label.includes(l) ? " agree" : "") }, l)) : el("i", {}, "no fallacy"))))))));
  };
  sel.addEventListener("change", () => show(+sel.value)); show(0);
}

/* ---------- chapter 4: results ---------- */
function renderResultsCh(R) {
  const T = R.test_table, f = n => T.find(r => r.model === n);
  const C4 = [["The counter", "Unigram BoW + LR (baseline)"], ["The minimalist", "TF-IDF LR-L1 (Lasso)"], ["The diplomat", "TF-IDF LR-L2 (ridge)"], ["The border guard", "TF-IDF Linear SVM"]];
  const ci = s => (s || "").replace(/[\[\]]/g, "").split(",").map(Number);
  hbar($("#res-chart"), C4.map(([nk, m]) => { const r = f(m), [lo, hi] = ci(r.macro_f1_95ci); return { label: nk, value: r.macro_f1, lo, hi, note: m }; }), { valueLabel: "test macro-F1", highlight: r => r.label === "The border guard" });
  const s = f("TF-IDF Linear SVM"), ri = f("TF-IDF LR-L2 (ridge)"), la = f("TF-IDF LR-L1 (Lasso)"), b = f("Unigram BoW + LR (baseline)"), mf = f("Most-frequent label");
  $("#res-text").innerHTML = `The border guard (linear SVM) wins with <b>${fmt(s.macro_f1)}</b> ${s.macro_f1_95ci}, ahead of the diplomat (${fmt(ri.macro_f1)}), the minimalist (${fmt(la.macro_f1)}) and the counter (${fmt(b.macro_f1)}). The bars are 95% bootstrap intervals over test arguments.`;
  const groups = ["Always “Slippery Slope”"].concat(C4.map(c => c[0])), byG = { "Always “Slippery Slope”": mf };
  C4.forEach(([nk, m]) => { byG[nk] = f(m); });
  groupedBars($("#res-micro"), groups, ["macro-F1", "micro-F1"], (g, ser) => ser === "macro-F1" ? byG[g].macro_f1 : byG[g].micro_f1, { yLabel: "test score", width: 640, height: 240 });
  $("#res-micro-text").innerHTML = `Macro and micro tell different stories. A “model” that always answers Slippery Slope scores <b>${fmt(mf.micro_f1, 2)}</b> micro-F1, because Slippery Slope is so common, but only <b>${fmt(mf.macro_f1, 2)}</b> macro-F1, because it never finds any other fallacy. For the real models micro-F1 sits above macro-F1 too: the frequent fallacies are the easy ones.`;
}

/* ---------- chapter 5: three tests, revealed after a guess ---------- */
function renderClues(R) {
  const SVM = "TF-IDF Linear SVM", ov = b => R.overlap.find(r => r.bucket === b && r.model === SVM);
  const seen = ov("template-seen"), nov = ov("novel");
  const rs = R.val_shortcuts.val_restricted, rr = n => rs.find(r => r["trained & evaluated on"].startsWith(n)).macro_f1;
  const fl = t => R.stress.find(r => r.model === SVM && r.test === t)["flip rate"];
  $("#db-template").replaceChildren(dumbbell({ tag: "TEST", title: "Near-copies vs. new arguments", unit: "micro-F1 (higher is better)", href: "research.html#sc-a",
    a: { l: `near-copies (n=${R.bucket_counts["template-seen"]})`, v: seen.micro_f1, lo: seen.ci_lo, hi: seen.ci_hi },
    b: { l: `new arguments (n=${R.bucket_counts.novel})`, v: nov.micro_f1, lo: nov.ci_lo, hi: nov.ci_hi }, note: "Whiskers are 95% bootstrap intervals." }));
  $("#txt-template").innerHTML = `Clearly worse: from <b>${fmt(seen.micro_f1, 2)}</b> to <b>${fmt(nov.micro_f1, 2)}</b>, and the intervals do not overlap. Part of the headline score is recognition: the model has, in effect, seen these arguments before.`;
  $("#db-topic").replaceChildren(dumbbell({ tag: "VALIDATION", title: "Topic words vs. reasoning words", unit: "macro-F1 (higher is better)", href: "research.html#sc-c",
    a: { l: "topic words only", v: rr("topic words only") }, b: { l: "cue + function words only", v: rr("no topic words") }, note: "Each model was trained and scored on its own restricted vocabulary." }));
  $("#txt-topic").innerHTML = `About the same: <b>${fmt(rr("topic words only"), 2)}</b> against <b>${fmt(rr("no topic words"), 2)}</b>. Knowing only what an argument is <i>about</i> predicts its fallacy almost as well as knowing how it reasons. In this dataset, topic and fallacy travel together.`;
  $("#db-swap").replaceChildren(dumbbell({ tag: "TEST", title: "Swapping three topic words", unit: "share of correct detections that flip", href: "research.html#sc-b", max: 0.4, percent: true,
    a: { l: "most-weighted topic words", v: fl("topic swap (top-weighted)") }, b: { l: "random topic words", v: fl("topic swap (random control)") }, note: "Only arguments the model got right were edited." }));
  $("#txt-swap").innerHTML = `About 1 in 5: <b>${pct(fl("topic swap (top-weighted)"), 0)}</b> of correct detections flip, against <b>${pct(fl("topic swap (random control)"), 0)}</b> for random topic words. The model leans on a few specific subject words, and the reasoning does not hold it up once they are gone.`;
  document.querySelectorAll(".guess").forEach(g => g.querySelectorAll("button").forEach(b => b.addEventListener("click", () => {
    g.querySelectorAll("button").forEach(x => { x.disabled = true; x.classList.toggle("picked", x === b); });
    g.parentElement.querySelector(".reveal").hidden = false;
  })));
}

/* ---------- chapter 5: break the model ---------- */
const BRK = { base: "" };
function barsFor(probs, container, n = 5) {
  const top = M.labels.map((l, j) => ({ l, p: probs[j] })).sort((a, b) => b.p - a.p).slice(0, n);
  container.replaceChildren(...top.map(r => el("div", { class: "prow" }, el("span", { class: "pl" }, r.l),
    el("span", { class: "pbar" }, el("i", { class: "now", style: `width:${100 * r.p}%` }), el("b", { class: "half" })), el("span", { class: "pv" }, pct(r.p, 0)), el("span", {}))));
}
const verdict = probs => { const p = M.labels.filter((_, j) => probs[j] >= 0.5);
  return p.length ? `Model prediction: <b>${p.join(", ")}</b>` : `Model prediction: <b>no fallacy</b> (all ${M.labels.length} labels below 0.5)`; };
function renderBreak() {
  const text = $("#brk-text").value, toks = tokenize(text), { x, probs } = predict(toks);
  $("#brk-verdict").innerHTML = verdict(probs);
  $("#brk-chips").replaceChildren(...toks.map(t => el("span", { class: `chip g-${groupOf(t)}` }, t)));
  barsFor(probs, $("#brk-bars"));
  const k = probs.indexOf(Math.max(...probs));
  const tops = contributions(x, k).filter(c => c.c > 0 && c.term.split(" ").every(w => groupOf(w) === "topic" && w.length > 2 && !w.includes("'"))).slice(0, 3).map(c => c.term);
  $("#brk-hint").innerHTML = tops.length ? `Topic words pushing hardest towards <i>${M.labels[k]}</i>: ${tops.map(t => `<b>${t}</b>`).join(", ")}. Try replacing them with neutral words.` : "";
  BRK.tops = tops;
}
function initBreak(ex) {
  const seen = {}, pool = ex.filter(e => (e.source || "main") === "main" && e.labels.length === 1 && e.ins_status === "correct")
    .filter(e => (seen[e.labels[0]] = (seen[e.labels[0]] || 0) + 1) <= 2);      // up to two per fallacy
  const sel = $("#brk-example");
  sel.replaceChildren(...pool.map((e, i) => el("option", { value: i }, `[${e.labels[0]}] ${e.text.slice(0, 60)}…`)));
  const load = i => { BRK.base = pool[i].text; $("#brk-text").value = BRK.base; renderBreak(); };
  sel.addEventListener("change", () => load(+sel.value));
  let t = null; $("#brk-text").addEventListener("input", () => { clearTimeout(t); t = setTimeout(renderBreak, 120); });
  $("#brk-reset").addEventListener("click", () => { $("#brk-text").value = BRK.base; renderBreak(); });
  $("#brk-topic").addEventListener("click", () => {
    let s = $("#brk-text").value;
    for (const term of BRK.tops || []) for (const w of term.split(" ")) s = s.replace(new RegExp(`\\b${w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\b`, "gi"), "something");
    $("#brk-text").value = s; renderBreak();
  });
  const start = Math.max(0, pool.findIndex(e => e.labels[0] === "Slippery Slope"));
  sel.value = start; load(start);
}

/* ---------- chapter 5: contrastive pairs ---------- */
function initPairs(pairs) {
  const sel = $("#pair-select");
  sel.replaceChildren(...pairs.map((p, i) => el("option", { value: i }, `Pair ${i + 1}: ${p.valid.slice(0, 50)}…`)));
  const side = (title, text, cls) => {
    const { probs } = predict(tokenize(text)), box = el("div", { class: "bars" });
    barsFor(probs, box, 3);
    return el("div", { class: "side " + cls }, el("p", { class: "small" }, el("b", {}, title)), el("blockquote", {}, text), el("p", { class: "ins-verdict", html: verdict(probs) }), box);
  };
  const show = i => $("#pair-box").replaceChildren(side("Valid argument", pairs[i].valid, "ok"), side("Fallacious twin", pairs[i].fallacy, "bad"));
  sel.addEventListener("change", () => show(+sel.value)); show(0);
}

/* ---------- chapter 6: what the experiments show ---------- */
function renderDiscoveries(R) {
  const T = R.test_table, f = n => T.find(r => r.model === n), svm = f("TF-IDF Linear SVM"), base = f("Unigram BoW + LR (baseline)");
  const q6o = R.q6[0], q6g = R.q6.find(r => r.tau === 0.8) || R.q6[1];
  const ood = R.ood && R.ood.results.find(r => r.set === "edu" && r.model === "TF-IDF Linear SVM");
  const zs = R.binary && R.binary.zero_shot.find(r => r.source === "all");
  const cm = R.combined && R.combined.multi.find(r => r["test set"] === "main test" && r.model === "all datasets");
  const items = [
    `<b>The models are good at the task as set.</b> The best one, a linear SVM, reaches ${fmt(svm.macro_f1)} macro-F1 on held-out arguments from the main dataset, ahead of a simple word-count baseline (${fmt(base.macro_f1)}).`,
    `<b>Much of that is recognition.</b> When near-duplicate arguments must stay on one side of the split, the cross-validated score drops from ${fmt(q6o["macro_f1 mean"])} to ${fmt(q6g["macro_f1 mean"])}.`,
    `<b>Subject matter does a lot of the work.</b> Topic words alone predict the fallacy about as well as reasoning words, and swapping three topic words flips about one correct detection in five.`,
    ood ? `<b>The skill does not travel well.</b> On fallacy examples written by other people, the same model falls to ${fmt(ood.macro_f1)} macro-F1.` : "",
    zs ? `<b>Telling valid from fallacious is harder still.</b> A model trained only on fallacies flags ${pct(zs["valid flagged as fallacy (FPR)"], 0)} of valid arguments as fallacious.` : "",
    cm ? `<b>More data is not the fix.</b> Training one model on all the datasets keeps the main score at ${fmt(cm.macro_f1)} and helps mostly on text that looks like the new data.` : "",
    `<b>Sparsity and margins did not remove the shortcut.</b> The Lasso keeps only about 4% of the features, but they are mostly topic words; the SVM is the most accurate model and leans on topic words just as much.`];
  $("#discoveries").replaceChildren(...items.filter(Boolean).map(h => el("li", { html: h })));
  $("#answer").innerHTML = `Mostly the second. Our classical models do learn some genuine reasoning cues (words like “eventually”, “everyone”, “either”), but a large part of their accuracy comes from recognising templates and topics. A score of ${fmt(svm.macro_f1)} on a templated dataset says more about the dataset than about the model's grasp of reasoning.`;
}

/* ---------- boot ---------- */
async function labBoot() {
  initProgress();
  const get = f => fetch("data/" + f).then(r => { if (!r.ok) throw new Error(f); return r.json(); });
  try {
    const [R, model, ex, data] = await Promise.all([get("results.json"), get("lasso_model.json"), get("examples.json"), get("lab_data.json")]);
    M = prepModel(model); LAB.R = R; LAB.ex = ex; LAB.data = data;
    renderGuide(data.label_guide); renderQuiz(data.quiz);
    initReader(data.bpe); renderContestants(R, data); renderResultsCh(R);
    renderClues(R); initBreak(ex); initPairs(data.pairs); renderDiscoveries(R);
  } catch (err) {
    document.body.prepend(el("div", { class: "loaderr" }, "Could not load data files (" + err.message + "). Serve the folder instead of opening the file: python -m http.server -d website, then open http://localhost:8000/lab.html"));
  }
}
document.addEventListener("DOMContentLoaded", labBoot);
