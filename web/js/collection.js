// 내 도감: 풀숲에서 잡은 포켓몬. 서버는 잠들면 파일이 지워지므로 브라우저 저장소에만 남긴다.
// { [포켓몬 번호]: { first: 처음 잡은 시각, count: 잡은 횟수 } }
import { storageGet, storageSet } from "./state.js";

const STORE_KEY = "oak-caught-v1";
const listeners = new Set();

function load() {
  try {
    return JSON.parse(storageGet(STORE_KEY)) || {};
  } catch (_) {
    return {};
  }
}

const caught = load();

export const collection = {
  has: (id) => Boolean(caught[id]),
  get: (id) => caught[id] || null,
  size: () => Object.keys(caught).length,

  // 잡았으면 기록하고, 처음 잡은 친구인지 알려 준다
  add(id) {
    const first = !caught[id];
    caught[id] = { first: caught[id]?.first || new Date().toISOString(), count: (caught[id]?.count || 0) + 1 };
    storageSet(STORE_KEY, JSON.stringify(caught));
    for (const fn of listeners) fn(id, first);
    return first;
  },

  // 내 도감 비우기 (놀이터의 「도감 비우기」)
  reset() {
    for (const id of Object.keys(caught)) delete caught[id];
    storageSet(STORE_KEY, JSON.stringify(caught));
    for (const fn of listeners) fn(null, false);
  },

  onChange(fn) {
    listeners.add(fn);
  },
};

// 잡기 확률: 도감의 잡기 쉬움(3~255)을 10%~90%로 바꾼다. 캐터피(255)는 90%, 뮤츠(3)는 약 11%
export function catchChance(p) {
  return 0.1 + 0.8 * ((p.capture_rate ?? 45) / 255);
}
