// 화면 전체가 함께 쓰는 상태. 포켓몬 선택은 selectPokemon(id) 하나로만 한다 (도감 색인·탐색 카드·풀숲 공통).
// 대화 기록은 포켓몬마다 따로 { [pokemonId]: [기록들] } 로 보관하고 브라우저 저장소에 남긴다 (F2009).

const STORE_KEY = "oak-notes-v1";

function loadChats() {
  try {
    const raw = localStorage.getItem(STORE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch (_) {
    return {}; // 저장소를 못 써도 화면은 정상 동작
  }
}

export const state = {
  pokemon: [],          // 151마리 요약 목록
  byId: new Map(),
  types: [],
  selectedId: null,
  chats: loadChats(),
  activeRecord: null,   // 오른쪽 참고 카드에 보여줄 기록
  busy: false,
};

const listeners = new Set();

export function onSelect(fn) {
  listeners.add(fn);
}

export function selectPokemon(id) {
  if (!state.byId.has(id)) return;
  const changed = state.selectedId !== id;
  state.selectedId = id;
  if (changed) state.activeRecord = null;
  for (const fn of listeners) fn(id, changed);
}

export function current() {
  return state.byId.get(state.selectedId);
}

export function records(id = state.selectedId) {
  if (!state.chats[id]) state.chats[id] = [];
  return state.chats[id];
}

export function saveChats() {
  try {
    localStorage.setItem(STORE_KEY, JSON.stringify(state.chats));
  } catch (_) { /* 저장 실패해도 계속 */ }
}

export function hasRecords(id) {
  return (state.chats[id] || []).some((r) => r.answer);
}

export function storageGet(key) {
  try {
    return localStorage.getItem(key);
  } catch (_) {
    return null;
  }
}

export function storageSet(key, value) {
  try {
    localStorage.setItem(key, value);
  } catch (_) { /* 무시 */ }
}
