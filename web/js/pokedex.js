// 왼쪽 위 도감 기계 (B안): 고른 포켓몬 화면, 상태 불 3개, 생각 중 렌즈, 십자키
import { current, selectPokemon, state } from "./state.js";
import { el, spriteImg, TEXT, typeBadges } from "./ui.js";

const LED_TEXT = {
  server: ["서버 연결됨", "서버 연결 없음"],
  index: ["도감 색인 있음", "도감 색인 비어 있음"],
  key: ["연구소 열쇠 있음", "연구소 열쇠 없음"],
};

// 움직이는 그림은 크기가 제각각이라, 화면 안에 들어오는 가장 큰 정수 배로 키운다 (픽셀이 뭉개지지 않게)
function fitSprite(img, box) {
  const nw = img.naturalWidth;
  const nh = img.naturalHeight;
  if (!nw || !nh) return;
  const scale = Math.max(1, Math.floor(Math.min(box.clientWidth / nw, box.clientHeight / nh)));
  img.style.width = `${nw * scale}px`;
  img.style.height = `${nh * scale}px`;
}

export const pokedex = {
  init() {
    for (const btn of document.querySelectorAll(".pd-dpad button")) {
      btn.addEventListener("click", () => this.step(Number(btn.dataset.step)));
    }
    // 십자키에 초점이 있을 때 키보드 화살표로도 넘긴다
    document.querySelector(".pd-dpad").addEventListener("keydown", (e) => {
      const step = { ArrowUp: -1, ArrowLeft: -1, ArrowDown: 1, ArrowRight: 1 }[e.key];
      if (!step) return;
      e.preventDefault();
      this.step(step);
    });
  },

  // 앞뒤 번호로 넘기기. 자유 질문에서는 아래 = 1번, 위 = 151번
  step(dir) {
    const list = state.pokemon;
    if (!list.length) return;
    const i = list.findIndex((p) => p.id === state.selectedId);
    const next = i < 0 ? (dir > 0 ? 0 : list.length - 1) : (i + dir + list.length) % list.length;
    selectPokemon(list[next].id);
  },

  show() {
    const p = current();
    const screen = document.getElementById("pdScreen");
    const lcd = document.getElementById("pdLcd");
    const sprite = el("div", { class: "pd-sprite" });
    if (p) {
      const img = spriteImg(p, { animated: true });
      img.removeAttribute("loading"); // 서랍 안에 숨어 있어도 바로 받아 둔다
      img.alt = p.name_ko;
      img.addEventListener("load", () => fitSprite(img, sprite));
      sprite.append(img);
      screen.replaceChildren(sprite, el("div", { class: "pd-types" }, typeBadges(p.types)));
      lcd.replaceChildren(el("small", {}, `No.${p.dex_no}`), p.name_ko); // 좁은 열에서도 안 잘리게 두 줄
    } else {
      sprite.append(el("span", { class: "pd-unknown", "aria-hidden": "true" }, "?"));
      screen.replaceChildren(sprite, el("div", { class: "pd-types" }));
      lcd.replaceChildren(el("small", {}, "No.???"), TEXT.freeLabel);
    }
    screen.classList.remove("swap");
    void screen.offsetWidth; // 같은 효과를 다시 틀기 위해
    screen.classList.add("swap");
  },

  // 불 3개: s가 null이면 서버 연결 없음
  status(s) {
    const ok = {
      server: Boolean(s),
      index: Boolean(s && s.meta_count > 0),
      key: Boolean(s && s.api_key),
    };
    for (const led of document.querySelectorAll(".led")) {
      const on = ok[led.dataset.led];
      led.classList.toggle("on", on);
      led.classList.toggle("warn", !on && (led.dataset.led === "server" || ok.server));
    }
    // 서버가 끊기면 나머지 두 불은 알 수 없으므로 서버 상태만 말한다
    const label = ok.server ? Object.keys(LED_TEXT).map((k) => LED_TEXT[k][ok[k] ? 0 : 1]).join(", ") : LED_TEXT.server[1];
    document.getElementById("pdLeds").setAttribute("aria-label", label);
  },

  // 답을 찾는 동안 렌즈가 깜빡이고, 답이 나오면 한 번 반짝인다
  think() {
    const lens = document.getElementById("pdLens");
    lens.classList.remove("flash");
    lens.classList.add("thinking");
  },
  done(ok) {
    const lens = document.getElementById("pdLens");
    lens.classList.remove("thinking");
    if (!ok) return;
    void lens.offsetWidth;
    lens.classList.add("flash");
  },
};
