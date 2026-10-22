// 진화 극장: 게임 속 진화 장면처럼 하얗게 빛나며 두 모습이 점점 빠르게 바뀌다가 번쩍! (AI 호출 없음)
// 진화 탭·도감 페이지·놀이터에서 playEvolution(id)로 연다. 동작 줄이기 설정이면 바뀌는 장면 없이 결과만.
import { api } from "./api.js";
import { el, errorText, josa } from "./ui.js";

const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
// 두 모습이 번갈아 보이는 간격(ms): 처음엔 느리게, 점점 빠르게
const SWAPS = [460, 420, 380, 330, 290, 250, 210, 180, 150, 125, 105, 90, 80, 70, 60, 60, 60, 60];

let dialog;
let run = 0;          // 장면 번호. 닫거나 "그만!"을 누르면 바뀌어 진행 중인 장면이 멈춘다
let onOpenNote = () => {};

const wait = (ms) => new Promise((r) => { setTimeout(r, ms); });

function sprite(p) {
  return el("img", { class: "pixel", src: p.sprite.static, alt: "", width: 96, height: 96 });
}

function parts() {
  return {
    stage: dialog.querySelector(".evo-stage"),
    line: dialog.querySelector(".evo-line"),
    actions: dialog.querySelector(".evo-actions"),
  };
}

function build() {
  dialog = el("dialog", { class: "evo-show", "aria-labelledby": "evoShowTitle" },
    el("h2", { class: "px22 underlined", id: "evoShowTitle" }, "진화 극장"),
    el("div", { class: "evo-stage" }),
    el("p", { class: "evo-line", "aria-live": "polite" }),
    el("div", { class: "evo-actions" }));
  dialog.addEventListener("close", () => { run += 1; });
  // 바깥(어두운 곳)을 누르면 닫힌다
  dialog.addEventListener("click", (e) => { if (e.target === dialog) dialog.close(); });
  document.body.append(dialog);
}

function buttons(...list) {
  parts().actions.replaceChildren(...list.map(([label, fn]) => el("button", { type: "button", onclick: fn }, label)));
}

const closeBtn = () => ["닫기", () => dialog.close()];

// 진화할 모습 고르기 (이브이처럼 갈래가 여럿일 때)
function choose(from, next) {
  const { stage, line, actions } = parts();
  stage.replaceChildren(el("div", { class: "evo-mons" }, sprite(from)));
  line.textContent = `${josa(from.name_ko, "은/는")} 어떤 모습으로 진화할까요?`;
  actions.replaceChildren(
    el("div", { class: "evo-choices" }, next.map((to) => el("button", { type: "button", onclick: () => scene(from, to) },
      sprite(to), el("span", {}, to.name_ko + (to.generation > 1 ? ` (${to.generation}세대)` : "")),
      el("small", { class: "pencil" }, to.condition || "조건 없음")))),
    el("button", { type: "button", onclick: () => dialog.close() }, "닫기"));
}

async function scene(from, to) {
  const my = ++run;
  const { stage, line } = parts();
  const a = sprite(from);
  const b = sprite(to);
  b.hidden = true;
  const flash = el("span", { class: "evo-flash", "aria-hidden": "true" });
  stage.replaceChildren(el("div", { class: "evo-mons" }, a, b), flash);
  line.textContent = `어라…? ${from.name_ko}의 모습이…!`;
  buttons(["그만! (진화 멈추기)", () => stop(from, to)]);

  const alive = () => my === run && dialog.open;
  await wait(1300);
  if (!alive()) return;
  if (!reduceMotion.matches) {
    stage.classList.add("glowing"); // 두 모습 모두 하얀 그림자로
    await wait(700);
    for (const ms of SWAPS) {
      if (!alive()) return;
      a.hidden = !a.hidden;
      b.hidden = !a.hidden;
      await wait(ms);
    }
    if (!alive()) return;
    a.hidden = true;
    b.hidden = false;
    flash.classList.add("on");
    await wait(450);
    stage.classList.remove("glowing");
    await wait(350);
  } else {
    a.hidden = true;
    b.hidden = false;
  }
  if (!alive()) return;
  flash.classList.remove("on");
  line.replaceChildren(...[
    el("strong", {}, `축하해요! ${josa(from.name_ko, "은/는")} ${josa(to.name_ko, "으로/로")} 진화했다!`),
    to.condition ? el("small", { class: "pencil" }, `진화 조건: ${to.condition}`) : null,
    to.generation > 1 ? el("small", { class: "pencil" }, `${josa(to.name_ko, "은/는")} ${to.generation}세대 게임에서 추가된 모습이에요`) : null,
  ].filter(Boolean));
  const list = [];
  // 1세대 밖 모습(크로뱃 등)은 이 노트가 다루지 않아 다음 진화를 묻지 않는다
  const after = to.id <= 151 ? await api.evolutionNext(to.id).catch(() => null) : null;
  if (!alive()) return;
  if (after?.next.length) list.push(["계속 진화하기", () => start(after)]);
  if (to.id <= 151) list.push([`${to.name_ko} 노트 열기`, () => { dialog.close(); onOpenNote(to.id); }]);
  buttons(...list, closeBtn());
}

// 게임에서 B 버튼을 누른 것처럼: 진화가 멈춘다
function stop(from, to) {
  run += 1;
  const { stage, line } = parts();
  stage.classList.remove("glowing");
  stage.replaceChildren(el("div", { class: "evo-mons" }, sprite(from)));
  line.textContent = `어라? ${from.name_ko}의 변화가 멈췄다!`;
  buttons(["다시 진화하기", () => scene(from, to)], closeBtn());
}

function start({ from, next }) {
  if (next.length > 1) choose(from, next);
  else scene(from, next[0]);
}

export function setOpenNote(fn) {
  onOpenNote = fn;
}

export async function playEvolution(id) {
  if (!dialog) build();
  run += 1;
  const { stage, line, actions } = parts();
  stage.classList.remove("glowing");
  stage.replaceChildren();
  line.textContent = "진화 자료를 펼치는 중…";
  actions.replaceChildren();
  if (!dialog.open) dialog.showModal();
  try {
    const data = await api.evolutionNext(id);
    if (!data.next.length) {
      stage.replaceChildren(el("div", { class: "evo-mons" }, sprite(data.from)));
      line.textContent = `${josa(data.from.name_ko, "은/는")} 더 이상 진화하지 않아요.`;
      buttons(closeBtn());
      return;
    }
    start(data);
  } catch (e) {
    line.textContent = errorText(e.code);
    buttons(closeBtn());
  }
}
