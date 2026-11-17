/* Logical Fallacy Detection - client-side logic. No build step, no server.
   Data files are produced by `python -m src.export_web` into docs/data/. */
"use strict";
const $ = (s, r = document) => r.querySelector(s);
const el = (tag, attrs = {}, ...kids) => {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") n.className = v; else if (k === "html") n.innerHTML = v;
    else if (k.startsWith("on")) n.addEventListener(k.slice(2), v); else n.setAttribute(k, v);
  }
  for (const k of kids.flat()) if (k != null) n.append(k.nodeType ? k : document.createTextNode(k));
  return n;
};
const fmt = (x, d = 3) => (x == null || Number.isNaN(x) ? "–" : Number(x).toFixed(d));
const pct = (x, d = 1) => (x == null ? "–" : (100 * x).toFixed(d) + "%");
const SVGNS = "http://www.w3.org/2000/svg";
const sv = (tag, attrs = {}) => { const n = document.createElementNS(SVGNS, tag); for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v); return n; };
const GROUP_COLOR = { topic: "var(--c-topic)", cue: "var(--c-cue)", function: "var(--c-func)" };

/* ---------- tooltip ---------- */
const tip = el("div", { class: "tip", role: "status" });
document.body.append(tip);
function showTip(e, html) { tip.innerHTML = html; tip.style.opacity = 1; moveTip(e); }
function moveTip(e) { tip.style.left = Math.min(e.clientX + 14, innerWidth - tip.offsetWidth - 8) + "px"; tip.style.top = (e.clientY + 14) + "px"; }
function hideTip() { tip.style.opacity = 0; }
function hover(node, html) { node.addEventListener("mousemove", e => showTip(e, typeof html === "function" ? html() : html)); node.addEventListener("mouseleave", hideTip); }

/* ---------- generic horizontal bar chart (one series, optional CI) ---------- */
function hbar(container, rows, { max = 1, valueLabel = "macro-F1", color = "var(--c-1)", highlight = () => false, width = 640 } = {}) {
  const rowH = 26, left = 320, right = 70, h = rows.length * rowH + 30;
  const svg = sv("svg", { viewBox: `0 0 ${width} ${h}`, class: "chart", role: "img", "aria-label": valueLabel + " bar chart" });
  const x = v => left + (width - left - right) * (v / max);
  for (let t = 0; t <= 1.0001; t += 0.25) {
    svg.append(sv("line", { x1: x(t * max), x2: x(t * max), y1: 0, y2: h - 22, class: "grid" }));
    const tx = sv("text", { x: x(t * max), y: h - 6, class: "tick", "text-anchor": "middle" }); tx.textContent = (t * max).toFixed(2); svg.append(tx);
  }
  rows.forEach((r, i) => {
    const y = i * rowH + 4;
    const lab = sv("text", { x: left - 8, y: y + 15, class: "lab" + (highlight(r) ? " strong" : ""), "text-anchor": "end" }); lab.textContent = r.label; svg.append(lab);
    const bar = sv("rect", { x: left, y: y + 3, width: Math.max(0, x(r.value) - left), height: rowH - 10, rx: 3, fill: r.color || color, opacity: highlight(r) ? 1 : 0.8 });
    svg.append(bar);
    if (r.lo != null) {
      svg.append(sv("line", { x1: x(r.lo), x2: x(r.hi), y1: y + rowH / 2 - 2, y2: y + rowH / 2 - 2, class: "ci" }));
      for (const v of [r.lo, r.hi]) svg.append(sv("line", { x1: x(v), x2: x(v), y1: y + 7, y2: y + rowH - 11, class: "ci" }));
    }
    const vt = sv("text", { x: Math.max(x(r.value), x(r.hi ?? 0)) + 6, y: y + 15, class: "val" }); vt.textContent = fmt(r.value); svg.append(vt);
    const hit = sv("rect", { x: 0, y, width, height: rowH, fill: "transparent" }); svg.append(hit);
    hover(hit, `<b>${r.label}</b><br>${valueLabel}: ${fmt(r.value, 4)}` + (r.lo != null ? `<br>95% CI: [${fmt(r.lo)}, ${fmt(r.hi)}]` : "") + (r.note ? `<br>${r.note}` : ""));
  });
  container.replaceChildren(svg);
}

/* ---------- grouped bars (few series, few groups) ---------- */
function groupedBars(container, groups, series, get, { max = 1, yLabel = "", width = 640, height = 260, err = null } = {}) {
  const m = { l: 46, r: 10, t: 10, b: 46 }, W = width - m.l - m.r, H = height - m.t - m.b;
  const svg = sv("svg", { viewBox: `0 0 ${width} ${height}`, class: "chart", role: "img", "aria-label": yLabel });
  const y = v => m.t + H * (1 - v / max);
  for (let t = 0; t <= 1.0001; t += 0.25) {
    svg.append(sv("line", { x1: m.l, x2: width - m.r, y1: y(t * max), y2: y(t * max), class: "grid" }));
    const tx = sv("text", { x: m.l - 6, y: y(t * max) + 4, class: "tick", "text-anchor": "end" }); tx.textContent = (t * max).toFixed(2); svg.append(tx);
  }
  const gw = W / groups.length, bw = Math.min(28, (gw - 16) / series.length - 2);
  groups.forEach((g, gi) => {
    const gx = m.l + gi * gw + (gw - series.length * (bw + 2)) / 2;
    series.forEach((s, si) => {
      const v = get(g, s); if (v == null) return;
      const bx = gx + si * (bw + 2);
      const r = sv("rect", { x: bx, y: y(v), width: bw, height: Math.max(0, y(0) - y(v)), rx: 3, fill: `var(--c-${si + 1})` }); svg.append(r);
      if (err) { const e = err(g, s); if (e) { svg.append(sv("line", { x1: bx + bw / 2, x2: bx + bw / 2, y1: y(e[0]), y2: y(e[1]), class: "ci" })); } }
      const hit = sv("rect", { x: bx - 1, y: m.t, width: bw + 2, height: H, fill: "transparent" }); svg.append(hit);
      hover(hit, `<b>${s}</b><br>${g}: ${fmt(v, 4)}` + (err && err(g, s) ? `<br>95% CI [${fmt(err(g, s)[0])}, ${fmt(err(g, s)[1])}]` : ""));
    });
    const tx = sv("text", { x: m.l + gi * gw + gw / 2, y: height - m.b + 16, class: "lab", "text-anchor": "middle" }); tx.textContent = g; svg.append(tx);
  });
  const lg = el("div", { class: "legend" }, series.map((s, i) => el("span", {}, el("i", { style: `background:var(--c-${i + 1})` }), s)));
  container.replaceChildren(lg, svg);
}

/* ---------- simple table ---------- */
function table(container, cols, rows) {
  const t = el("table", {}, el("thead", {}, el("tr", {}, cols.map(c => el("th", { class: c.num ? "num" : "" }, c.h)))),
    el("tbody", {}, rows.map(r => el("tr", { class: r._class || "" }, cols.map(c => el("td", { class: c.num ? "num" : "" }, c.f ? c.f(r) : r[c.k]))))));
  container.replaceChildren(el("div", { class: "tablewrap" }, t));
}

/* =====================================================================
   TF-IDF + Lasso logistic regression, re-implemented in JS.
   Matches sklearn: tokens -> uni+bigrams -> (1 + ln tf) * idf -> L2 norm -> w.x + b -> sigmoid
   ===================================================================== */
const TOKEN_RE = /(?<![\p{L}\p{N}_])(?:[a-z][a-z']*[a-z]|[a-z])(?![\p{L}\p{N}_])/gu;
const tokenize = s => s.toLowerCase().match(TOKEN_RE) || [];
let M = null; // model
function prepModel(m) {
  m.index = new Map(m.vocab.map((t, i) => [t, i]));
  m.W = m.labels.map(l => { const mp = new Map(); m.coef[l].idx.forEach((j, q) => mp.set(j, m.coef[l].w[q])); return mp; });
  m.cueSet = new Set(m.cues); m.funcSet = new Set(m.function_words);
  return m;
}
const groupOf = w => (M.cueSet.has(w) ? "cue" : M.funcSet.has(w) ? "function" : "topic");
function featurize(tokens) {
  const counts = new Map();
  const add = t => { const j = M.index.get(t); if (j !== undefined) counts.set(j, (counts.get(j) || 0) + 1); };
  tokens.forEach(add);
  for (let i = 0; i + 1 < tokens.length; i++) add(tokens[i] + " " + tokens[i + 1]);
  let norm = 0; const x = new Map();
  for (const [j, c] of counts) { const v = (1 + Math.log(c)) * M.idf[j]; x.set(j, v); norm += v * v; }
  norm = Math.sqrt(norm) || 1;
  for (const [j, v] of x) x.set(j, v / norm);
  return x;
}
function predict(tokens) {
  const x = featurize(tokens);
  const probs = M.labels.map((_, k) => { let z = M.intercept[k]; for (const [j, v] of x) { const w = M.W[k].get(j); if (w) z += w * v; } return 1 / (1 + Math.exp(-z)); });
  return { x, probs };
}
function contributions(x, k) {
  const out = [];
  for (const [j, v] of x) { const w = M.W[k].get(j); if (w) out.push({ term: M.vocab[j], w, c: w * v }); }
  return out.sort((a, b) => Math.abs(b.c) - Math.abs(a.c));
}

/* ---------- Perturbation inspector ---------- */
const INS = { ex: null, tokens: [], off: new Set(), base: null, label: 0, custom: false };
function initInspector(examples) {
  const sel = $("#ins-example");
  const byStatus = { correct: "Correct", "missed label(s)": "Missed a label", "extra label(s)": "Extra label", swapped: "Swapped label" };
  for (const [st, name] of Object.entries(byStatus)) {
    const og = el("optgroup", { label: name });
    examples.filter(e => e.status === st).forEach(e => og.append(el("option", { value: e.i }, `[${e.labels.join(" + ")}] ${e.text.slice(0, 70)}…`)));
    if (og.children.length) sel.append(og);
  }
  sel.addEventListener("change", () => loadExample(examples.find(e => e.i == sel.value)));
  $("#ins-label").replaceChildren(...M.labels.map((l, k) => el("option", { value: k }, l)));
  $("#ins-label").addEventListener("change", e => { INS.label = +e.target.value; renderInspector(); });
  $("#ins-reset").addEventListener("click", () => { INS.off.clear(); renderInspector(); });
  for (const g of ["topic", "cue", "function"]) $(`#ins-drop-${g}`).addEventListener("click", () => { INS.tokens.forEach((t, i) => { if (groupOf(t) === g) INS.off.add(i); }); renderInspector(); });
  $("#ins-own").addEventListener("click", () => {
    const txt = $("#ins-text").value.trim(); if (!txt) return;
    INS.ex = { text: txt, labels: [], bucket: "your text", status: "custom" }; INS.tokens = tokenize(txt); INS.off.clear();
    INS.base = predict(INS.tokens).probs; INS.custom = true; renderInspector();
  });
  // start on a well-known template case if present
  const start = examples.find(e => /calculator/i.test(e.text)) || examples[0];
  sel.value = start.i; loadExample(start);
}
function loadExample(e) {
  INS.ex = e; INS.custom = false; INS.tokens = tokenize(e.text); INS.off.clear();
  INS.base = predict(INS.tokens).probs;
  const k = M.labels.indexOf(e.labels[0]); INS.label = k >= 0 ? k : 0; $("#ins-label").value = INS.label;
  renderInspector();
}
function renderInspector() {
  const kept = INS.tokens.filter((_, i) => !INS.off.has(i));
  const { x, probs } = predict(kept);
  const k = INS.label, contrib = contributions(x, k);
  const termW = new Map(); // per-unigram weight for the chosen label (unigram coef only) for chip shading
  INS.tokens.forEach(t => { const j = M.index.get(t); termW.set(t, j !== undefined ? (M.W[k].get(j) || 0) : 0); });
  // chips
  const chips = INS.tokens.map((t, i) => {
    const g = groupOf(t), w = termW.get(t);
    const c = el("button", { class: `chip g-${g}` + (INS.off.has(i) ? " off" : "") + (w > 0 ? " pos" : w < 0 ? " neg" : ""), "aria-pressed": INS.off.has(i) ? "true" : "false", title: "" }, t);
    c.addEventListener("click", () => { INS.off.has(i) ? INS.off.delete(i) : INS.off.add(i); renderInspector(); });
    hover(c, `<b>${t}</b> · ${g} word<br>unigram Lasso weight for <i>${M.labels[k]}</i>: ${w ? fmt(w, 3) : "0 (zeroed / unseen)"}<br>click to ${INS.off.has(i) ? "restore" : "remove"}`);
    return c;
  });
  $("#ins-chips").replaceChildren(...chips);
  const ex = INS.ex;
  $("#ins-meta").innerHTML = INS.custom ? "Your own text (no ground truth)." :
    `True label(s): <b>${ex.labels.join(", ")}</b> · overlap with training data: <b>${ex.bucket}</b> (max cosine ${fmt(ex.max_sim, 2)}) · ${INS.off.size} token(s) removed`;
  // probability bars
  const rows = M.labels.map((l, j) => ({ l, p: probs[j], b: INS.base[j], truth: !INS.custom && ex.labels.includes(l) })).sort((a, b) => b.b - a.b);
  const list = rows.map(r => {
    const d = r.p - r.b;
    const row = el("div", { class: "prow" + (r.truth ? " truth" : "") + (M.labels[k] === r.l ? " sel" : "") },
      el("span", { class: "pl" }, r.l + (r.truth ? " ✓" : "")),
      el("span", { class: "pbar" }, el("i", { class: "now", style: `width:${100 * r.p}%` }), el("b", { class: "was", style: `left:${100 * r.b}%` }), el("b", { class: "half" })),
      el("span", { class: "pv" }, pct(r.p, 0)), el("span", { class: "pd " + (d > 0.005 ? "up" : d < -0.005 ? "down" : "") }, Math.abs(d) < 0.005 ? "" : (d > 0 ? "+" : "−") + pct(Math.abs(d), 0)));
    row.addEventListener("click", () => { INS.label = M.labels.indexOf(r.l); $("#ins-label").value = INS.label; renderInspector(); });
    return row;
  });
  $("#ins-probs").replaceChildren(...list);
  // active coefficients
  const top = contrib.slice(0, 14);
  $("#ins-coefs").replaceChildren(
    el("p", { class: "small" }, `${contrib.length} non-zero Lasso coefficient(s) for “${M.labels[k]}” are active in this text (of ${M.coef[M.labels[k]].idx.length} non-zero in the model, ${M.vocab.length.toLocaleString()} features in total).`),
    el("div", { class: "tablewrap" }, el("table", {}, el("thead", {}, el("tr", {}, el("th", {}, "feature"), el("th", {}, "group"), el("th", { class: "num" }, "weight w"), el("th", { class: "num" }, "w · x"))),
      el("tbody", {}, top.map(c => { const g = c.term.split(" ").some(w => groupOf(w) === "topic") ? "topic" : c.term.split(" ").some(w => groupOf(w) === "cue") ? "cue" : "function";
        return el("tr", {}, el("td", {}, c.term), el("td", {}, el("span", { class: `dot g-${g}` }), g), el("td", { class: "num" }, fmt(c.w, 2)), el("td", { class: "num " + (c.c > 0 ? "up" : "down") }, fmt(c.c, 3))); })))));
}

/* ---------- Cost-optimal threshold tool ---------- */
const TH = { k: 0, logr: 0 };
let TD = null;
function initThreshold(td) {
  TD = td;
  const s = $("#th-label"); s.replaceChildren(...td.labels.map((l, k) => el("option", { value: k }, `${l} (n=${td.y[k].reduce((a, b) => a + b, 0)})`)));
  s.addEventListener("change", e => { TH.k = +e.target.value; renderThreshold(); });
  $("#th-ratio").addEventListener("input", e => { TH.logr = +e.target.value; renderThreshold(); });
  $("#th-f1").addEventListener("click", () => { const t = td.f1_threshold_val[TH.k]; TH.logr = Math.log10((1 - t) / t); $("#th-ratio").value = TH.logr; renderThreshold(); });
  $("#th-half").addEventListener("click", () => { TH.logr = 0; $("#th-ratio").value = 0; renderThreshold(); });
  renderThreshold();
}
function confusion(p, y, t) { let tp = 0, fp = 0, fn = 0, tn = 0; for (let i = 0; i < p.length; i++) { const h = p[i] >= t; if (h && y[i]) tp++; else if (h) fp++; else if (y[i]) fn++; else tn++; } return { tp, fp, fn, tn }; }
function renderThreshold() {
  const p = TD.prob[TH.k], y = TD.y[TH.k], n = p.length, r = 10 ** TH.logr, t = 1 / (1 + r);
  const c = confusion(p, y, t);
  const prec = c.tp / (c.tp + c.fp || 1), rec = c.tp / (c.tp + c.fn || 1), f1 = 2 * prec * rec / (prec + rec || 1);
  const cost = (c.fp + r * c.fn) / n;
  $("#th-readout").innerHTML = `C<sub>FN</sub> / C<sub>FP</sub> = <b>${r < 1 ? r.toFixed(2) : r.toFixed(1)}</b> → threshold p* = 1 / (1 + r) = <b>${t.toFixed(3)}</b>`;
  $("#th-cm").innerHTML = `<table class="cm"><tr><th></th><th>predicted yes</th><th>predicted no</th></tr>
    <tr><th>truly ${TD.labels[TH.k]}</th><td class="good">TP ${c.tp}</td><td class="bad">FN ${c.fn}</td></tr>
    <tr><th>truly not</th><td class="bad">FP ${c.fp}</td><td class="good">TN ${c.tn}</td></tr></table>
    <div class="kpis"><div><span>precision</span><b>${fmt(prec)}</b></div><div><span>recall</span><b>${fmt(rec)}</b></div><div><span>F1</span><b>${fmt(f1)}</b></div><div><span>expected cost / argument</span><b>${fmt(cost, 4)}</b></div></div>`;
  // PR curve + operating point, and cost curve
  const order = p.map((v, i) => [v, y[i]]).sort((a, b) => b[0] - a[0]);
  const P = y.reduce((a, b) => a + b, 0); let tp = 0, fp = 0; const pts = [];
  for (const [v, yy] of order) { yy ? tp++ : fp++; pts.push([tp / P, tp / (tp + fp)]); }
  drawXY($("#th-pr"), [{ pts, color: "var(--c-1)" }], { x: rec, y: prec }, "recall", "precision", [0, 1], [0, 1]);
  const cp = []; for (let lr = -2; lr <= 2.0001; lr += 0.05) { const rr = 10 ** lr, cc = confusion(p, y, 1 / (1 + rr)); cp.push([lr, (cc.fp + rr * cc.fn) / n]); }
  const ymax = Math.max(...cp.map(q => q[1])) * 1.1;
  drawXY($("#th-cost"), [{ pts: cp, color: "var(--c-2)" }], { x: TH.logr, y: cost }, "log₁₀ cost ratio r", "expected cost / argument", [-2, 2], [0, ymax]);
}
function drawXY(container, series, point, xl, yl, xr, yr) {
  const w = 320, h = 230, m = { l: 48, r: 10, t: 10, b: 38 };
  const X = v => m.l + (w - m.l - m.r) * (v - xr[0]) / (xr[1] - xr[0]), Y = v => m.t + (h - m.t - m.b) * (1 - (v - yr[0]) / (yr[1] - yr[0]));
  const svg = sv("svg", { viewBox: `0 0 ${w} ${h}`, class: "chart" });
  for (let i = 0; i <= 4; i++) {
    const gy = yr[0] + (yr[1] - yr[0]) * i / 4, gx = xr[0] + (xr[1] - xr[0]) * i / 4;
    svg.append(sv("line", { x1: m.l, x2: w - m.r, y1: Y(gy), y2: Y(gy), class: "grid" }));
    const a = sv("text", { x: m.l - 5, y: Y(gy) + 4, class: "tick", "text-anchor": "end" }); a.textContent = gy.toFixed(gy < 0.1 && gy > 0 ? 3 : 2); svg.append(a);
    const b = sv("text", { x: X(gx), y: h - m.b + 14, class: "tick", "text-anchor": "middle" }); b.textContent = +gx.toFixed(2); svg.append(b);
  }
  for (const s of series) svg.append(sv("path", { d: s.pts.map((q, i) => (i ? "L" : "M") + X(q[0]).toFixed(1) + "," + Y(q[1]).toFixed(1)).join(""), fill: "none", stroke: s.color, "stroke-width": 2 }));
  svg.append(sv("circle", { cx: X(point.x), cy: Y(point.y), r: 6, class: "op" }));
  const a = sv("text", { x: (m.l + w - m.r) / 2, y: h - 4, class: "axis", "text-anchor": "middle" }); a.textContent = xl; svg.append(a);
  const b = sv("text", { x: 12, y: (m.t + h - m.b) / 2, class: "axis", "text-anchor": "middle", transform: `rotate(-90 12 ${(m.t + h - m.b) / 2})` }); b.textContent = yl; svg.append(b);
  container.replaceChildren(svg);
}

/* ---------- boot ---------- */
async function boot() {
  const get = f => fetch("data/" + f).then(r => { if (!r.ok) throw new Error(f); return r.json(); });
  try {
    const [res, model, ex, td] = await Promise.all([get("results.json"), get("lasso_model.json"), get("examples.json"), get("threshold_data.json")]);
    M = prepModel(model);
    window.RESULTS = res;
    if (typeof renderResults === "function") renderResults(res);
    initInspector(ex); initThreshold(td);
    // self-check: JS reimplementation vs Python probabilities
    let maxd = 0; for (const e of ex) { const p = predict(tokenize(e.text)).probs; p.forEach((v, j) => { maxd = Math.max(maxd, Math.abs(v - e.py_prob[j])); }); }
    $("#selfcheck").textContent = `Self-check: the in-browser model reproduces the Python probabilities for all ${ex.length} example arguments to within ${maxd.toExponential(1)}.`;
  } catch (err) {
    document.body.prepend(el("div", { class: "loaderr" }, "Could not load data files (" + err.message + "). If you opened index.html from disk, serve the folder instead: python -m http.server -d website (from the repo root), then open http://localhost:8000"));
  }
}
document.addEventListener("DOMContentLoaded", boot);
