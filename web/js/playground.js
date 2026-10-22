// 연구소 놀이터: 첫 화면(연구노트) 아래로 내리면 나오는 곳.
// 내 도감(풀숲에서 잡은 친구) · 실루엣 퀴즈 · 성격 테스트 · 포켓몬과 이야기하기 · 진화 극장
import { api } from "./api.js";
import { collection } from "./collection.js";
import { playEvolution } from "./evoshow.js";
import { meadow } from "./meadow.js";
import { state, storageGet, storageSet } from "./state.js";
import { el, errorText, formatTime, josa, spriteImg, typeBadges } from "./ui.js";

const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
const behavior = () => (reduceMotion.matches ? "auto" : "smooth");
const $ = (id) => document.getElementById(id);
const pickRandom = (list) => list[Math.floor(Math.random() * list.length)];
let onOpenNote = () => {};

function shuffle(list) {
  const a = [...list];
  for (let i = a.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

function pokemonOptions(list) {
  return list.map((p) => el("option", { value: p.id }, `${p.dex_no} ${p.name_ko}`));
}

// ---------- 내 도감 ----------
function renderMyDex() {
  const n = collection.size();
  $("myDexCount").textContent = `151마리 중 ${n}마리`;
  $("myDexBar").style.setProperty("--v", String(n / Math.max(state.pokemon.length, 1)));
  $("resetDex").disabled = n === 0; // 비울 게 없으면 잠금
  $("myDexGrid").replaceChildren(...state.pokemon.map((p) => {
    const got = collection.get(p.id);
    if (!got) return el("li", { class: "dex-cell" }, el("span", { class: "no", "aria-label": `No.${p.dex_no} 아직 못 만남` }, p.dex_no));
    return el("li", { class: "dex-cell caught" },
      el("button", {
        type: "button",
        title: `${p.name_ko} · 처음 잡은 날 ${formatTime(got.first).date} · ${got.count}번 잡음`,
        "aria-label": `No.${p.dex_no} ${p.name_ko} 노트 열기`,
        onclick: () => onOpenNote(p.id),
      }, spriteImg(p, { animated: false, size: 48 }), el("span", { class: "no" }, p.dex_no)));
  }));
}

function setupMyDex() {
  renderMyDex();
  collection.onChange(renderMyDex);
  $("goCatch").addEventListener("click", () => {
    window.scrollTo({ top: 0, behavior: behavior() });
    meadow.startCatching();
  });
  // 되돌릴 수 없으니 한 번 더 묻는다
  $("resetDex").addEventListener("click", () => {
    if (!collection.size()) return;
    if (window.confirm(`잡은 친구 ${collection.size()}마리를 모두 놓아주고 내 도감을 처음부터 시작할까요?`)) collection.reset();
  });
}

// ---------- 실루엣 퀴즈: 그림자와 울음소리로 맞히기 ----------
const QUIZ_BEST = "oak-quiz-best";
const quiz = { answer: null, streak: 0, best: Number(storageGet(QUIZ_BEST)) || 0, audio: null, fails: 0 };

function renderScore() {
  $("quizScore").textContent = `연속 정답 ${quiz.streak} · 최고 기록 ${quiz.best}`;
}

function playCry(p) {
  quiz.audio?.pause();
  const urls = [...p.cry];
  const tryNext = () => {
    if (!urls.length) { $("quizResult").textContent = "울음소리를 불러오지 못했어요."; return; }
    const audio = new Audio(urls.shift());
    audio.volume = 0.4;
    audio.addEventListener("error", tryNext, { once: true });
    quiz.audio = audio;
    audio.play().catch(() => { /* 오류는 error 이벤트에서 다음 주소로 */ });
  };
  tryNext();
}

function newQuestion() {
  const answer = pickRandom(state.pokemon);
  quiz.answer = answer;
  // 보기 4개: 정답 + 같은 타입 친구 1마리(너무 쉽지 않게) + 무작위
  const choices = new Map([[answer.id, answer]]);
  const sameType = state.pokemon.filter((p) => p.id !== answer.id && p.types.some((t) => answer.types.includes(t)));
  if (sameType.length) { const p = pickRandom(sameType); choices.set(p.id, p); }
  while (choices.size < 4) { const p = pickRandom(state.pokemon); choices.set(p.id, p); }

  const img = el("img", { class: "pixel silhouette", src: answer.sprite.static, alt: "그림자만 보이는 포켓몬", width: 96, height: 96 });
  img.addEventListener("load", () => { quiz.fails = 0; });
  img.addEventListener("error", () => { if (quiz.fails++ < 3) newQuestion(); }); // 그림이 없으면 다른 문제로
  $("quizStage").replaceChildren(img);
  $("quizChoices").replaceChildren(...shuffle([...choices.values()]).map((p) =>
    el("button", { type: "button", "data-id": p.id, onclick: (e) => answerQuiz(p, e.currentTarget) }, p.name_ko)));
  $("quizResult").textContent = "";
  $("quizNext").hidden = true;
}

function answerQuiz(picked, btn) {
  const { answer } = quiz;
  const right = picked.id === answer.id;
  for (const b of $("quizChoices").querySelectorAll("button")) {
    b.disabled = true;
    if (Number(b.dataset.id) === answer.id) b.classList.add("right");
  }
  if (!right) btn.classList.add("wrong");
  const img = $("quizStage").querySelector("img");
  img.classList.remove("silhouette");
  img.alt = answer.name_ko;
  quiz.streak = right ? quiz.streak + 1 : 0;
  if (quiz.streak > quiz.best) { quiz.best = quiz.streak; storageSet(QUIZ_BEST, String(quiz.best)); }
  renderScore();
  const name = josa(answer.name_ko, "이에요/예요");
  $("quizResult").textContent = (right ? `정답! ${name}!` : `아쉬워요! 정답은 ${name}.`)
    + (collection.has(answer.id) ? " 내 도감에 있는 친구예요." : "");
  $("quizNext").hidden = false;
  $("quizNext").focus({ preventScroll: true });
}

function setupQuiz() {
  renderScore();
  newQuestion();
  $("quizCry").addEventListener("click", () => playCry(quiz.answer));
  $("quizNext").addEventListener("click", newQuestion);
}

// ---------- 성격 테스트: 나는 어떤 포켓몬일까? ----------
const PERSONA_LAST = "oak-persona-last";
const QUESTIONS = [
  ["쉬는 날, 나는?", ["집에서 뒹굴뒹굴", "친구들과 밖으로", "혼자 낯선 곳 탐험", "뭔가 만들거나 공부"]],
  ["가장 끌리는 장소는?", ["파도 소리 나는 바닷가", "햇살 드는 숲속", "바람 부는 높은 산", "북적이는 도시"]],
  ["친구가 고민을 털어놓으면?", ["끝까지 들어 준다", "바로 해결책을 말한다", "맛있는 걸 사 준다", "웃긴 얘기로 기분을 풀어 준다"]],
  ["시험 전날 밤, 나는?", ["벼락치기로 불태운다", "미리 해 둬서 여유롭다", "일단 자고 본다", "친구와 같이 공부한다"]],
  ["나를 가장 화나게 하는 건?", ["약속을 어기는 것", "배고픔", "시끄러운 소리", "나는 거의 화를 안 낸다"]],
  ["딱 하나 가질 수 있다면?", ["하늘을 나는 날개", "불을 다루는 힘", "투명해지는 능력", "어디서든 잠드는 능력"]],
  ["팀 과제에서 나는?", ["앞장서는 리더", "기발한 아이디어 담당", "묵묵히 해내는 일꾼", "분위기 메이커"]],
  ["가장 좋아하는 시간은?", ["이른 아침", "나른한 오후", "노을 질 때", "모두 잠든 깊은 밤"]],
];
const persona = { i: 0, answers: [] };

function lastPersona() {
  try {
    const last = JSON.parse(storageGet(PERSONA_LAST));
    return last && state.byId.get(last.id) ? last : null;
  } catch (_) {
    return null;
  }
}

function personaStart() {
  const last = lastPersona();
  $("personaBox").replaceChildren(
    el("p", { class: "pane-lead" }, `질문 ${QUESTIONS.length}개에 답하면 이박사가 151마리 중에서 나와 닮은 포켓몬을 찾아 줘요.`),
    el("div", { class: "persona-start" },
      el("button", { type: "button", onclick: () => { persona.i = 0; persona.answers = []; personaQuestion(); } }, "테스트 시작"),
      last ? el("span", { class: "pencil small" }, `지난번 결과: ${state.byId.get(last.id).name_ko}`) : null));
}

function personaQuestion() {
  const [q, options] = QUESTIONS[persona.i];
  // replaceChildren은 null을 "null" 글자로 넣으므로 빈 칸은 걸러 낸다 (첫 질문에는 「이전 질문」이 없음)
  $("personaBox").replaceChildren(...[
    el("p", { class: "label px14 pencil" }, `${persona.i + 1} / ${QUESTIONS.length}`),
    el("span", { class: "progress", style: `--v: ${persona.i / QUESTIONS.length}`, "aria-hidden": "true" }),
    el("p", { class: "persona-q" }, q),
    el("div", { class: "persona-options" }, options.map((a) => el("button", { type: "button", onclick: () => {
      persona.answers[persona.i] = { q, a };
      persona.i += 1;
      if (persona.i < QUESTIONS.length) personaQuestion();
      else personaAsk();
    } }, a))),
    persona.i > 0 ? el("button", { type: "button", class: "persona-back", onclick: () => { persona.i -= 1; personaQuestion(); } }, "← 이전 질문") : null,
  ].filter(Boolean));
  $("personaBox").querySelector(".persona-options button").focus({ preventScroll: true });
}

async function personaAsk() {
  $("personaBox").replaceChildren(el("p", { class: "persona-wait" }, "이박사가 연구노트를 뒤적이는 중", el("span", { class: "dots" }, "…")));
  try {
    const r = await api.persona(persona.answers);
    storageSet(PERSONA_LAST, JSON.stringify({ id: r.id, reason: r.reason }));
    personaResult(r);
  } catch (e) {
    $("personaBox").replaceChildren(el("p", { class: "error-line" }, errorText(e.code)),
      el("div", { class: "persona-start" }, el("button", { type: "button", onclick: personaAsk }, "다시 시도"),
        el("button", { type: "button", onclick: personaStart }, "처음으로")));
  }
}

function personaResult(r) {
  const p = state.byId.get(r.id);
  $("personaBox").replaceChildren(
    el("div", { class: "persona-result" },
      spriteImg(p, { animated: false, size: 192 }),
      el("div", {},
        el("p", { class: "pencil small" }, "당신과 닮은 포켓몬은…"),
        el("p", { class: "persona-name" }, `No.${p.dex_no} ${p.name_ko}`),
        el("p", {}, typeBadges(p.types), el("span", { class: "small" }, r.genus_ko)),
        el("p", { class: "persona-reason" }, r.reason))),
    el("div", { class: "persona-start" },
      el("button", { type: "button", onclick: () => openTalk(p.id) }, `${josa(p.name_ko, "과/와")} 이야기하기`),
      el("button", { type: "button", onclick: () => onOpenNote(p.id) }, "도감 노트 열기"),
      el("button", { type: "button", onclick: personaStart }, "다시 하기")),
    el("p", { class: "pencil small" }, "재미로 보는 결과예요. 같은 답이어도 결과가 조금씩 달라질 수 있어요."));
}

// ---------- 포켓몬과 이야기하기 ----------
const HISTORY_MAX = 20; // 서버에 다시 보내는 최근 말 수 (서버는 그중 설정값만큼만 씀)
const talk = { id: 25, logs: new Map(), busyId: null };

function talkLog(id) {
  if (!talk.logs.has(id)) talk.logs.set(id, []);
  return talk.logs.get(id);
}

function renderTalk() {
  const p = state.byId.get(talk.id);
  const log = talkLog(talk.id);
  const box = $("talkLog");
  const say = (text) => { if (!talk.busyId) { $("talkInput").value = ""; sendTalk(text); } };
  if (!log.length) {
    box.replaceChildren(el("div", { class: "talk-intro" },
      spriteImg(p, { animated: true }),
      el("p", {}, `${josa(p.name_ko, "이/가")} 이쪽을 바라봐요. 말을 걸어 보세요!`),
      el("div", { class: "examples" }, ["안녕! 넌 누구야?", "너는 어떻게 진화해?", "네 자랑 좀 해 줘!"].map((q) =>
        el("button", { type: "button", onclick: () => say(q) }, q)))));
  } else {
    box.replaceChildren(...log.map((m) => el("div", { class: `talk-row ${m.role}` },
      m.role === "pokemon" ? spriteImg(p, { animated: false, size: 48 }) : null,
      el("p", { class: "talk-bubble" }, m.text))));
    if (talk.busyId === talk.id) {
      box.append(el("div", { class: "talk-row pokemon" }, spriteImg(p, { animated: false, size: 48 }),
        el("p", { class: "talk-bubble typing", "aria-label": `${josa(p.name_ko, "이/가")} 생각하는 중` },
          el("span", { class: "dot" }, "."), el("span", { class: "dot" }, "."), el("span", { class: "dot" }, "."))));
    }
  }
  box.scrollTop = box.scrollHeight;
  $("talkSend").disabled = Boolean(talk.busyId);
}

async function sendTalk(text) {
  if (talk.busyId) return;
  const id = talk.id;
  const log = talkLog(id);
  const history = log.filter((m) => m.role !== "error").slice(-HISTORY_MAX).map(({ role, text: t }) => ({ role, text: t.slice(0, 500) }));
  log.push({ role: "user", text });
  talk.busyId = id;
  renderTalk();
  try {
    const r = await api.talk(id, text, history);
    log.push({ role: "pokemon", text: r.reply });
  } catch (e) {
    log.push({ role: "error", text: errorText(e.code) });
  } finally {
    talk.busyId = null;
    renderTalk();
  }
}

function setTalkPokemon(id) {
  if (!state.byId.has(id)) return;
  talk.id = id;
  $("talkPick").value = String(id);
  renderTalk();
}

export function openTalk(id) {
  setTalkPokemon(id);
  $("playTalk").scrollIntoView({ behavior: behavior(), block: "start" });
  $("talkInput").focus({ preventScroll: true });
}

function setupTalk() {
  $("talkPick").replaceChildren(...pokemonOptions(state.pokemon));
  $("talkPick").addEventListener("change", (e) => setTalkPokemon(Number(e.target.value)));
  $("talkRandom").addEventListener("click", () => setTalkPokemon(pickRandom(state.pokemon).id));
  $("talkForm").addEventListener("submit", (e) => {
    e.preventDefault();
    const text = $("talkInput").value.trim();
    if (!text || talk.busyId) return;
    $("talkInput").value = "";
    sendTalk(text);
  });
  setTalkPokemon(talk.id);
}

// ---------- 진화 극장 (장면은 evoshow.js) ----------
function renderEvoPick() {
  const p = state.byId.get(Number($("evoPick").value));
  if (!p) return;
  $("evoPickFace").replaceChildren(spriteImg(p, { animated: false, size: 96 }),
    el("span", { class: "evo-pick-arrow", "aria-hidden": "true" }, "→"), el("span", { class: "evo-pick-q", "aria-hidden": "true" }, "?"));
}

function setupEvo() {
  const list = state.pokemon.filter((p) => p.evolves);
  $("evoPick").replaceChildren(...pokemonOptions(list));
  $("evoPick").value = String(list[0]?.id ?? "");
  $("evoPick").addEventListener("change", renderEvoPick);
  $("evoGo").addEventListener("click", () => playEvolution(Number($("evoPick").value)));
  renderEvoPick();
}

// ---------- 밖에서 부르는 함수들 ----------
export const playground = {
  init(openNote) {
    onOpenNote = openNote;
    setupMyDex();
    setupQuiz();
    personaStart();
    setupTalk();
    setupEvo();
    $("playJump").addEventListener("click", () => $("playground").scrollIntoView({ behavior: behavior() }));
    $("backToNote").addEventListener("click", () => window.scrollTo({ top: 0, behavior: behavior() }));
  },

  // 위쪽 노트에서 포켓몬을 고르면: 진화 극장과 (아직 말을 안 건) 이야기하기 상대를 그 포켓몬으로 맞춘다
  follow(id) {
    const p = id === null ? null : state.byId.get(id);
    if (!p) return;
    if (p.evolves) { $("evoPick").value = String(id); renderEvoPick(); }
    if (!talkLog(talk.id).length && !talk.busyId) setTalkPokemon(id);
  },
};
