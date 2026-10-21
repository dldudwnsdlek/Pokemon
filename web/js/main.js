// 시작점: 서버 상태 확인 → 도감 색인 → 선택·기록·풀숲 연결
import { api } from "./api.js";
import { chainStrip, renderRecords, setAfterJob, setupPanes, showTab } from "./chat.js";
import { setupFinder } from "./finder.js";
import { meadow } from "./meadow.js";
import { current, hasRecords, onSelect, selectPokemon, state, storageGet, storageSet } from "./state.js";
import { el, hideNotice, showNotice, TEXT } from "./ui.js";

const LAST_KEY = "oak-last-pokemon";

// 상단 오른쪽 라벨: "도감 151 · 문서 12" (F2002)
async function refreshStatus() {
  const tag = document.getElementById("statusTag");
  try {
    const s = await api.status();
    tag.textContent = `도감 ${s.meta_count} · 문서 ${s.collected_docs}`;
    if (s.meta_count === 0) showNotice("도감이 비어 있어요", TEXT.INDEX_EMPTY);
    else if (!s.api_key) showNotice("열쇠가 없어요", TEXT.API_KEY_MISSING);
    else hideNotice();
    return s;
  } catch (_) {
    tag.textContent = "서버 연결 없음";
    showNotice("서버가 꺼져 있어요", TEXT.serverDown);
    return null;
  }
}

// 연필 표시 (기록이 있는 포켓몬)
const pencilSvg = () => {
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", "0 0 14 14");
  svg.setAttribute("class", "pencil-mark");
  svg.setAttribute("aria-label", "기록 있음");
  const path = document.createElementNS(ns, "path");
  path.setAttribute("d", "M2 12 L3 9 L10 2 L12 4 L5 11 Z M3 9 L5 11");
  path.setAttribute("fill", "none");
  path.setAttribute("stroke", "#5B6470");
  path.setAttribute("stroke-width", "1.3");
  svg.append(path);
  return svg;
};

function renderDex(filter = "") {
  const list = document.getElementById("dexList");
  const q = filter.trim();
  const items = state.pokemon
    .filter((p) => !q || p.name_ko.includes(q) || p.dex_no.includes(q) || String(p.id) === q)
    .map((p) => el("li", { class: `dex-item${p.id === state.selectedId ? " selected" : ""}`, "data-id": p.id },
      el("button", { type: "button", "aria-current": p.id === state.selectedId ? "true" : null, onclick: () => pick(p.id) },
        el("span", { class: "dex-no" }, p.dex_no),
        el("span", {}, p.name_ko),
        hasRecords(p.id) ? pencilSvg() : el("span", {}))));
  list.replaceChildren(...items);
}

function pick(id) {
  selectPokemon(id);
  showTab("chat");
  document.getElementById("dex").classList.remove("open");
  document.getElementById("drawerBtn").setAttribute("aria-expanded", "false");
}

function renderHeader() {
  const p = current();
  document.getElementById("currentLabel").textContent = `No.${p.dex_no} ${p.name_ko}`;
  document.title = `${p.name_ko} · 오박사의 연구노트`;
}

// 진화 탭에는 계통 그림부터 보여준다 (데이터로 그림, 설명 글은 "진화 보기"의 답변)
async function renderEvoPreview() {
  const box = document.getElementById("evoPreview");
  const id = state.selectedId;
  box.replaceChildren();
  try {
    const detail = await api.pokemon(id);
    if (state.selectedId === id) box.replaceChildren(chainStrip(detail.chain));
  } catch (_) { /* 그림이 없어도 기능은 동작 */ }
}

async function main() {
  await refreshStatus();
  let data;
  try {
    data = await api.pokemonList();
  } catch (_) {
    return;
  }
  state.pokemon = data.pokemon;
  state.types = data.types;
  state.byId = new Map(data.pokemon.map((p) => [p.id, p]));

  onSelect((id, changed) => {
    storageSet(LAST_KEY, String(id));
    renderHeader();
    renderDex(document.getElementById("dexSearch").value);
    renderRecords();
    renderEvoPreview();
    meadow.bringIn(id);
    if (changed) document.querySelector(`.dex-item[data-id="${id}"]`)?.scrollIntoView({ block: "nearest" });
  });

  setupPanes();
  setupFinder();
  setAfterJob(() => {
    refreshStatus();
    renderDex(document.getElementById("dexSearch").value);
  });
  document.getElementById("dexSearch").addEventListener("input", (e) => renderDex(e.target.value));
  document.getElementById("drawerBtn").addEventListener("click", (e) => {
    const dex = document.getElementById("dex");
    const open = dex.classList.toggle("open");
    e.currentTarget.setAttribute("aria-expanded", String(open));
  });

  meadow.init((id) => pick(id));
  const lastId = Number(storageGet(LAST_KEY)) || 25;
  selectPokemon(state.byId.has(lastId) ? lastId : 1);
  showTab("chat");
}

main();
