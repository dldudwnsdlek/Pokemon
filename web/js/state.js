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
  selectedId: null,     // null = 포켓몬을 고르지 않은 자유 질문
  chats: loadChats(),
  activeRecord: null,   // 오른쪽 참고 카드에 보여줄 기록
  busy: false,
};

const listeners = new Set();

export function onSelect(fn) {
  listeners.add(fn);
}

// id가 null이면 자유 질문으로 돌아간다
export function selectPokemon(id) {
  if (id !== null && !state.byId.has(id)) return;
  const changed = state.selectedId !== id;
  state.selectedId = id;
  if (changed) state.activeRecord = null;
  for (const fn of listeners) fn(id, changed);
}

export function current() {
  return state.selectedId === null ? null : state.byId.get(state.selectedId);
}

// 기록 칸 이름: 포켓몬 번호, 자유 질문은 "free" (포켓몬별 기록과 섞이지 않게)
const chatKey = (id) => (id === null ? "free" : id);

export function records(id = state.selectedId) {
  const key = chatKey(id);
  if (!state.chats[key]) state.chats[key] = [];
  return state.chats[key];
}

export function saveChats() {
  try {
    localStorage.setItem(STORE_KEY, JSON.stringify(state.chats));
  } catch (_) { /* 저장 실패해도 계속 */ }
}

export function hasRecords(id) {
  return (state.chats[chatKey(id)] || []).some((r) => r.answer);
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
