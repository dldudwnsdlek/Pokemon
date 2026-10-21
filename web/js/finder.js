// 조건 기반 탐색 — "이런 포켓몬 찾아줘" (F2011). 카드를 누르면 그 포켓몬의 기록으로 넘어간다.
import { api } from "./api.js";
import { showTab } from "./chat.js";
import { selectPokemon } from "./state.js";
import { el, errorText, spriteImg, TEXT, typeBadges } from "./ui.js";

function card(c) {
  return el("button", {
    class: "index-card",
    type: "button",
    "aria-label": `No.${c.dex_no} ${c.name_ko} 선택하기`,
    onclick: () => {
      selectPokemon(c.id);
      showTab("chat");
    },
  },
  spriteImg(c, { animated: false, size: 64 }),
  el("div", {},
    el("div", {}, el("span", { class: "dex-no" }, `No.${c.dex_no} `), el("span", { class: "name" }, c.name_ko)),
    el("div", {}, typeBadges(c.types)),
    el("p", { class: "reason" }, c.reason),
    c.unsure ? el("p", { class: "unsure" }, "확인 필요") : null,
    el("p", { class: "src" }, `근거: ${c.citation.title}`)));
}

export function setupFinder() {
  const form = document.getElementById("findForm");
  const input = document.getElementById("findInput");
  const results = document.getElementById("findResults");
  const filters = document.getElementById("findFilters");
  const btn = form.querySelector("button");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const condition = input.value.trim();
    if (!condition) return;
    btn.disabled = true;
    filters.textContent = "도감 색인 카드를 넘겨 보는 중…";
    results.replaceChildren();
    try {
      const r = await api.find(condition);
      filters.textContent = r.filters.length ? `먼저 걸러 낸 조건: ${r.filters.join(", ")}` : "";
      if (!r.cards.length) results.replaceChildren(el("p", {}, r.message || TEXT.findEmpty));
      else results.replaceChildren(...r.cards.map(card));
    } catch (err) {
      filters.textContent = "";
      results.replaceChildren(el("p", { class: "error-line" }, errorText(err.code)));
    } finally {
      btn.disabled = false;
    }
  });
}
