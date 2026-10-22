// 연구 기록(대화), 참고 카드, 배틀·진화 실행 (F2008~F2010, F2012, F2014)
import { api, ApiError } from "./api.js";
import { meadow } from "./meadow.js";
import { pokedex } from "./pokedex.js";
import { current, records, saveChats, selectPokemon, state } from "./state.js";
import { el, errorText, formatTime, progressLog, showNotice, spriteImg, TEXT, typeBadges } from "./ui.js";

const CITE = /\[근거\s*(\d+)\]/g;
const WELCOME_ID = 25; // 첫 화면 대표 포켓몬: 피카츄
let onDone = () => {};

// 포켓몬 상세(도감 페이지·진화 그림·모아 둔 자료)는 한 번 받으면 다시 쓰고, 기록이 생기면 새로 받는다
const details = new Map();
export function loadDetail(id) {
  if (!details.has(id)) details.set(id, api.pokemon(id).catch((e) => { details.delete(id); throw e; }));
  return details.get(id);
}

export function setAfterJob(fn) {
  onDone = fn;
}

// ---------- 탭 ----------
export function showTab(name) {
  for (const t of document.querySelectorAll(".tab")) t.setAttribute("aria-selected", String(t.dataset.tab === name));
  for (const p of document.querySelectorAll(".pane")) p.hidden = p.dataset.pane !== name;
  document.getElementById("askForm").hidden = name !== "chat";
  renderRefs();
}

// ---------- 답변 본문: [근거 n] → 작은 원 안의 숫자 ----------
function answerBody(record) {
  const body = el("div", { class: "a-body" });
  let last = 0;
  for (const m of record.answer.matchAll(CITE)) {
    body.append(record.answer.slice(last, m.index));
    const no = Number(m[1]);
    const mark = el("span", { class: "cite", role: "button", tabindex: "0", "aria-label": `근거 ${no} 보기` }, no);
    const highlight = (on) => markCard(record, no, on);
    mark.addEventListener("mouseenter", () => highlight(true));
    mark.addEventListener("mouseleave", () => highlight(false));
    mark.addEventListener("focus", () => highlight(true));
    mark.addEventListener("blur", () => highlight(false));
    const jump = () => {
      setActive(record);
      document.getElementById(`ref-${no}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
      markCard(record, no, true);
    };
    mark.addEventListener("click", jump);
    mark.addEventListener("keydown", (e) => { if (e.key === "Enter") jump(); });
    body.append(mark);
    last = m.index + m[0].length;
  }
  body.append(record.answer.slice(last));
  return body;
}

// ---------- 참고 카드 ----------
function refCard(c, idPrefix = "ref-") {
  return el("article", { class: "ref-card", id: idPrefix ? `${idPrefix}${c.no}` : null },
    el("div", { class: "ref-head" },
      el("span", { class: "ref-no" }, `[${c.no}]`),
      el("span", { class: "source-stamp", "data-source": c.source_type }, c.source_label)),
    el("p", { class: "ref-title" }, c.title),
    c.snippet ? el("p", { class: "ref-snippet" }, `${c.snippet}…`) : null,
    c.url ? el("a", { class: "ref-link", href: c.url, target: "_blank", rel: "noopener" }, "원문 보기 ↗") : null);
}

function emptyRefCard() {
  return el("div", { class: "ref-empty" }, el("p", { class: "hand" }, TEXT.noCitation));
}

function setActive(record) {
  if (state.activeRecord === record) return;
  state.activeRecord = record;
  renderRefs();
  for (const r of document.querySelectorAll(".record")) r.classList.toggle("active", r._record === record);
}

function markCard(record, no, on) {
  if (on) setActive(record);
  document.getElementById(`ref-${no}`)?.classList.toggle("marked", on);
}

export function renderRefs() {
  const box = document.getElementById("refCards");
  // 찾기 탭에서는 이전 답의 근거가 탐색 결과의 근거처럼 보이지 않게 안내만
  if (!document.querySelector('.pane[data-pane="find"]').hidden) {
    box.replaceChildren(el("p", { class: "pencil small" }, TEXT.findRefs));
    return;
  }
  const list = records().filter((r) => r.answer);
  const rec = state.activeRecord && list.includes(state.activeRecord) ? state.activeRecord : list.at(-1);
  state.activeRecord = rec || null;
  if (!rec) {
    box.replaceChildren(el("p", { class: "pencil small" }, TEXT.noRefsYet));
    const id = state.selectedId;
    if (id !== null) {
      loadDetail(id).then((d) => {
        if (state.selectedId === id && !state.activeRecord && document.querySelector('.pane[data-pane="find"]').hidden) {
          box.replaceChildren(...savedRefs(d).flat().filter(Boolean));
        }
      }).catch(() => { /* 안내 문구만 남김 */ });
    }
    return;
  }
  box.replaceChildren(...(rec.no_citation ? [emptyRefCard()] : rec.citations.map((c) => refCard(c))));
}

// 아직 답이 없을 때: 질문하면 근거로 쓰일 자료를 미리 보여준다 (도감 데이터 + 예전에 모은 위키 문서)
function savedRefs(d) {
  const card = (source, label, title) => el("div", { class: "ref-card saved" },
    el("div", { class: "ref-head" }, el("span", { class: "source-stamp", "data-source": source }, label)),
    el("p", { class: "ref-title" }, title));
  return [
    el("p", { class: "pencil small" }, TEXT.savedRefs),
    card("meta", "도감 데이터", `${d.name_ko} · PokéAPI 도감`),
    d.collected_titles.map((t) => card("wikipedia", "위키백과", t)),
    d.collected_titles.length ? null : el("p", { class: "pencil small" }, TEXT.noSavedDocs),
  ];
}

// ---------- 진화 계통 그림 (데이터로 그림, 설명 글은 답변) ----------
export function chainStrip(stages) {
  const strip = el("div", { class: "evo-strip", role: "img", "aria-label": "진화 계통 그림" });
  const depth = Math.max(...stages.map((s) => s.depth));
  for (let d = 0; d <= depth; d += 1) {
    if (d > 0) strip.append(el("span", { class: "evo-arrow", "aria-hidden": "true" }));
    const col = el("div", { class: "evo-branch" });
    for (const s of stages.filter((x) => x.depth === d)) {
      col.append(el("div", { class: `evo-mon${s.current ? " current" : ""}${s.generation > 1 ? " later" : ""}` },
        s.condition ? el("small", { class: "pencil" }, s.condition) : null,
        spriteImg({ id: s.id, sprite: s.sprite }, { animated: false, size: 48 }),
        el("span", {}, s.name_ko + (s.generation > 1 ? ` (${s.generation}세대)` : ""))));
    }
    strip.append(col);
  }
  return strip;
}

// ---------- 수집 기록: 찾아볼 단어, 붙인 문서, 버린 문서와 이유 (F2003, F2004) ----------
function collectedView(col) {
  const row = (label, items) => el("li", {}, el("span", { class: "label px14" }, label), " ",
    items.length ? items.join(", ") : "없음");
  const summary = col.cached.length && !col.indexed.length
    ? "예전에 모아 둔 자료를 다시 펼쳤어요"
    : `위키백과 문서 ${col.indexed.length}개를 붙였어요`;
  return el("div", { class: "collected" },
    el("h4", {}, "수집 기록"),
    el("p", {}, summary),
    el("ul", {},
      row("찾아볼 단어", col.queries || []),
      row("붙인 문서", col.indexed.map((t) => `「${t}」`)),
      // 위키 검색 후보에는 엉뚱한 제목도 섞이므로 앞 5개만 보이고 나머지는 개수로
      row("버린 문서", [...col.skipped.slice(0, 5).map((s) => `${s.title}(${s.reason})`),
        ...(col.skipped.length > 5 ? [`외 ${col.skipped.length - 5}개`] : [])]),
      row("예전 자료", col.cached),
      col.failed.length ? row("가져오지 못함", col.failed) : null));
}

// ---------- 기록 1건 ----------
function recordView(record) {
  const { date, time } = formatTime(record.at);
  const node = el("article", { class: `record${state.activeRecord === record ? " active" : ""}` },
    el("div", { class: "date-rule" }, `${date} ${TEXT.kind[record.kind]}`),
    el("div", { class: "q" },
      el("span", { class: "q-label" }, "Q."),
      el("div", { class: "q-text" },
        el("span", {}, record.kind !== "chat" ? el("span", { class: "kind" }, TEXT.kind[record.kind]) : null, record.q),
        el("span", { class: "q-time" }, time))));
  node._record = record;

  if (record.pending) return node;
  const a = el("div", { class: "a" }, el("span", { class: "a-label" }, "A."));
  const right = el("div", {});
  a.append(right);
  node.append(a);

  if (record.error) {
    right.append(el("p", { class: "error-line" }, errorText(record.error)));
    if (record.error === "UPSTREAM_ERROR" && record.retry) {
      right.append(el("div", { class: "record-tools" }, el("button", { onclick: () => retry(record) }, TEXT.retry)));
    }
    return node;
  }
  if (record.verdict) right.append(el("div", { class: "verdict", "data-v": record.verdict }, record.verdict));
  if (record.chain) right.append(chainStrip(record.chain));
  right.append(answerBody(record));
  if (record.version_note) right.append(el("p", { class: "version-note" }, TEXT.versionNote));
  // 자주 쓰는 행동(질문 속 포켓몬의 노트 열기)만 바로 보이게
  if (record.matched?.length) right.append(matchedButtons(record.matched));

  // 좁은 화면에서는 참고 카드를 답변 바로 아래에
  right.append(el("div", { class: "inline-refs" },
    record.no_citation ? emptyRefCard() : record.citations.map((c) => refCard(c, null))));

  // 나머지(이름 인식 설명, 수집 기록, 검색 방식 비교)는 "자세히 보기"에 접어 둔다
  const more = el("div", { class: "more-body" });
  if (record.matched?.length) more.append(el("p", {}, TEXT.matched(record.matched.map((m) => `「${m.name_ko}」`).join(", "))));
  if (record.collected) more.append(collectedView(record.collected));
  if (record.kind === "chat") {
    const tools = el("div", {}, el("h4", {}, "검색 방식 비교"),
      el("p", {}, "같은 질문을 두 가지 방법으로 찾았을 때 근거가 어떻게 달라지는지 봐요."));
    const btn = el("button", { type: "button", onclick: () => compare(record, tools, btn) }, "유사도 · MMR 비교하기");
    tools.append(el("div", { class: "record-tools" }, btn));
    more.append(tools);
  }
  if (more.childElementCount) right.append(el("details", { class: "more" }, el("summary", {}, "자세히 보기"), more));

  node.addEventListener("click", () => setActive(record));
  return node;
}

// 자유 질문에서 질문 속 포켓몬 이름을 찾았을 때: 그 포켓몬 노트로 가는 버튼
function matchedButtons(matched) {
  return el("div", { class: "record-tools" }, matched.map((m) =>
    el("button", { type: "button", onclick: () => { selectPokemon(m.id); showTab("chat"); } }, `${m.name_ko} 노트 열기`)));
}

function examples(p) {
  if (!p) return ["1세대에서 가장 무거운 포켓몬은?", "고스트 타입 기술은 에스퍼 타입에게 효과가 어때?", "피카츄와 꼬부기 중 누가 더 빨라?"];
  const name = p.name_ko;
  return [`${name}은(는) 어떻게 진화해?`, `${name}의 타입과 약점은?`, `${name}의 키와 몸무게는?`];
}

// 배틀·진화는 포켓몬이 있어야 하므로, 자유 질문일 때는 안내를 띄우고 버튼을 잠근다
export function updatePaneLocks() {
  const locked = state.selectedId === null;
  for (const pane of ["battle", "evolution"]) {
    const box = document.querySelector(`.pane[data-pane="${pane}"]`);
    let note = box.querySelector(".pane-lock");
    if (!note) {
      note = el("p", { class: "pane-lock error-line" }, TEXT.needPokemon);
      box.querySelector(".pane-lead").after(note);
    }
    note.hidden = !locked;
  }
  setBusy(state.busy);
}

const STAT_LABELS = [["hp", "HP"], ["attack", "공격"], ["defense", "방어"],
  ["sp_attack", "특수공격"], ["sp_defense", "특수방어"], ["speed", "스피드"]];
const STAT_MAX = 255; // 능력치가 가질 수 있는 최댓값

// 아직 기록이 없는 포켓몬: 빈 종이 대신 도감 데이터로 한 쪽을 채운다 (AI를 부르지 않음)
function dexPage(p) {
  const facts = el("div", { class: "dex-page-facts" });
  const fill = (q) => { const i = document.getElementById("askInput"); i.value = q; i.focus(); };
  loadDetail(p.id).then((d) => {
    if (state.selectedId === p.id && facts.isConnected) facts.replaceChildren(...dexFacts(d).filter(Boolean));
  }).catch(() => { /* 도감 페이지가 없어도 질문은 할 수 있다 */ });
  return el("div", { class: "dex-page" },
    el("h2", { class: "px22 underlined" }, `${p.name_ko} 연구 노트`),
    el("p", { class: "lead" }, TEXT.emptyRecord),
    el("p", { class: "examples-title px14" }, "이렇게 물어보세요"),
    el("div", { class: "examples" }, examples(p).map((q) =>
      el("button", { type: "button", onclick: () => fill(q) }, q))),
    facts);
}

function dexFacts(d) {
  const total = Object.values(d.stats).reduce((a, b) => a + b, 0);
  const evolves = d.chain.length > 1;
  return [
    el("div", { class: "dex-page-grid" },
      el("section", {},
        el("h3", { class: "px14" }, "기본 정보"),
        el("p", { class: "dex-genus" }, typeBadges(d.types), d.genus_ko),
        el("dl", { class: "dex-info" },
          el("dt", {}, "키"), el("dd", {}, `${d.height_m}m`),
          el("dt", {}, "몸무게"), el("dd", {}, `${d.weight_kg}kg`),
          el("dt", {}, "특성"), el("dd", {}, d.abilities.join(", "))),
        el("blockquote", { class: "dex-flavor" }, d.flavor_ko)),
      el("section", {},
        el("h3", { class: "px14" }, `능력치 (합계 ${total})`),
        // 막대 색은 첫 번째 타입 색 (타입 배지와 같은 색)
        el("dl", { class: "stat-bars", "data-type": d.types[0] }, STAT_LABELS.flatMap(([key, label]) => [
          el("dt", {}, label),
          el("dd", {},
            el("span", { class: "bar", style: `--v: ${Math.min(d.stats[key] / STAT_MAX, 1)}` }),
            el("span", { class: "num" }, d.stats[key]))])))),
    evolves ? el("section", {}, el("h3", { class: "px14" }, "진화"), chainStrip(d.chain)) : null,
    el("p", { class: "pencil small" }, TEXT.weakNote),
    el("p", { class: "pencil small dex-source" }, TEXT.dexSource),
  ];
}

// 첫 화면(자유 질문): 대표 포켓몬 한 마리 + 짧은 시작 안내 + 예시 질문.
// 포켓몬을 골랐으면 그 포켓몬의 도감 페이지 (그림은 왼쪽 도감 기계 화면에 있어서 여기서는 뺀다)
function welcomeView(p) {
  if (p) return dexPage(p);
  const mon = state.byId.get(WELCOME_ID);
  const fill = (q) => { const i = document.getElementById("askInput"); i.value = q; i.focus(); };
  return el("div", { class: `welcome${mon ? "" : " solo"}` },
    mon ? el("div", { class: "welcome-mon" },
      spriteImg(mon, { animated: false, size: 192 }),
      el("span", { class: "pencil" }, `No.${mon.dex_no} ${mon.name_ko}`)) : null,
    el("div", {},
      el("h2", { class: "px22 underlined" }, TEXT.welcomeTitle),
      el("p", { class: "lead" }, TEXT.freeEmpty),
      el("ol", { class: "steps" }, TEXT.welcomeSteps.map((t) => el("li", {}, t))),
      el("p", { class: "examples-title px14" }, "이렇게 물어보세요"),
      el("div", { class: "examples" }, examples(null).map((q) =>
        el("button", { type: "button", onclick: () => fill(q) }, q)))));
}

export function renderRecords() {
  const box = document.getElementById("records");
  const list = records();
  if (!list.length) {
    box.replaceChildren(welcomeView(current()));
  } else {
    box.replaceChildren(...list.map(recordView));
    // 최신 기록이 보이게 (오른쪽 참고 카드도 최신 답의 것)
    const sheet = box.closest(".sheet");
    requestAnimationFrame(() => { sheet.scrollTop = sheet.scrollHeight; });
  }
  renderRefs();
}

// ---------- 실행: 진행 기록 → 결과 ----------
async function runJob(kind, label, call, retryInfo) {
  if (state.busy) return;
  const pokemonId = state.selectedId;
  const record = { kind, q: label, at: new Date().toISOString(), pending: true };
  const list = records(pokemonId);
  list.push(record);
  state.busy = true;
  setBusy(true);
  showTab("chat");
  renderRecords();
  progressLog.start();
  meadow.think(pokemonId);
  pokedex.think();

  try {
    const result = await call((p) => progressLog.write(p.message));
    Object.assign(record, {
      answer: result.answer, citations: result.citations, no_citation: result.no_citation,
      version_note: result.version_note, verdict: result.verdict, chain: result.chain,
      collected: result.collected, elapsed_ms: result.elapsed_ms, matched: result.matched,
    });
    progressLog.fold(result.collected.indexed.length + result.collected.cached.length, result.elapsed_ms);
    meadow.greet(pokemonId);
    pokedex.done(true);
    state.activeRecord = record;
  } catch (e) {
    const code = e instanceof ApiError ? e.code : "INTERNAL";
    if (code === "INDEX_EMPTY") showNotice("도감이 비어 있어요", TEXT.INDEX_EMPTY);
    if (code === "API_KEY_MISSING") showNotice("열쇠가 없어요", TEXT.API_KEY_MISSING);
    if (code === "SERVER_DOWN") showNotice("서버가 꺼져 있어요", TEXT.serverDown);
    record.error = code;
    record.retry = retryInfo;
    progressLog.clear();
    meadow.droop(pokemonId);
    pokedex.done(false);
  } finally {
    if (pokemonId !== null) details.delete(pokemonId); // 새로 모은 문서가 "모아 둔 자료"에 보이게
    delete record.pending;
    state.busy = false;
    setBusy(false);
    saveChats();
    if (state.selectedId === pokemonId) renderRecords();
    onDone();
  }
}

function setBusy(on) {
  const locked = state.selectedId === null; // 배틀·진화는 포켓몬이 있어야 함
  document.getElementById("askBtn").disabled = on;
  for (const id of ["battleBtn", "evoBtn"]) document.getElementById(id).disabled = on || locked;
}

function retry(record) {
  const list = records();
  list.splice(list.indexOf(record), 1);
  const { kind, payload } = record.retry;
  if (kind === "chat") ask(payload);
  if (kind === "battle") battle(payload);
  if (kind === "evolution") evolution();
}

export function ask(question) {
  const id = state.selectedId;
  return runJob("chat", question, (prog) => api.ask(id, question, prog), { kind: "chat", payload: question });
}

export function battle(opponent) {
  const id = state.selectedId;
  if (id === null) return null; // 포켓몬이 있어야 하는 기능
  const vs = opponent.opponent_id ? state.byId.get(opponent.opponent_id).name_ko : `${opponent.opponent_type} 타입`;
  return runJob("battle", `상대 ${vs}와의 상성`, (prog) => api.battle(id, opponent, prog), { kind: "battle", payload: opponent });
}

export function evolution() {
  const id = state.selectedId;
  if (id === null) return null; // 포켓몬이 있어야 하는 기능
  return runJob("evolution", "진화 계통 안내", (prog) => api.evolution(id, prog), { kind: "evolution" });
}

// F2014 — 같은 질문의 유사도 / MMR 근거 목록을 나란히
async function compare(record, tools, btn) {
  btn.disabled = true;
  btn.textContent = "비교하는 중…";
  try {
    const r = await api.compareSearch(state.selectedId, record.q);
    const both = new Set(r.similarity.map((e) => e.id).filter((id) => r.mmr.some((m) => m.id === id)));
    const col = (title, list) => el("div", {},
      el("h4", {}, title),
      el("ol", {}, list.map((e) => el("li", { class: both.has(e.id) ? "both" : null },
        el("span", { class: "source-stamp", "data-source": e.source_type }, e.source_label), " ", e.title))));
    tools.replaceWith(el("div", {},
      el("h4", {}, "검색 방식 비교"),
      el("p", {},
        `겹치는 근거 ${r.shared}개 · 서로 다른 문서 수: 유사도 ${r.distinct_docs.similarity}개, MMR ${r.distinct_docs.mmr}개 (밑줄 = 양쪽 모두)`),
      el("div", { class: "compare" }, col("유사도 검색", r.similarity), col("MMR 검색", r.mmr))));
  } catch (e) {
    btn.disabled = false;
    btn.textContent = errorText(e.code);
  }
}

// ---------- 배틀·진화 화면 준비 ----------
export function setupPanes() {
  const kind = document.getElementById("oppKind");
  const oppPokemon = document.getElementById("oppPokemon");
  const oppType = document.getElementById("oppType");
  oppPokemon.replaceChildren(...state.pokemon.map((p) => el("option", { value: p.id }, `${p.dex_no} ${p.name_ko}`)));
  oppType.replaceChildren(...state.types.map((t) => el("option", { value: t }, t)));
  kind.addEventListener("change", () => {
    oppPokemon.hidden = kind.value !== "pokemon";
    oppType.hidden = kind.value !== "type";
  });
  document.getElementById("battleBtn").addEventListener("click", () => {
    battle(kind.value === "pokemon" ? { opponent_id: Number(oppPokemon.value) } : { opponent_type: oppType.value });
  });
  document.getElementById("evoBtn").addEventListener("click", () => evolution());

  document.getElementById("askForm").addEventListener("submit", (e) => {
    e.preventDefault();
    const input = document.getElementById("askInput");
    const q = input.value.trim();
    if (!q || q.length > 500) return;
    input.value = "";
    ask(q);
  });
  for (const t of document.querySelectorAll(".tab")) t.addEventListener("click", () => showTab(t.dataset.tab));
}
