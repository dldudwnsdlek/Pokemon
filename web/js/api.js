// 서버와 이야기하는 함수들 (가이드 8장). 화면은 이 주소들로만 서버와 대화한다.

export class ApiError extends Error {
  constructor(code, message) {
    super(message);
    this.code = code;
  }
}

async function readError(res) {
  try {
    const body = await res.json();
    if (body.error) return new ApiError(body.error.code, body.error.message);
  } catch (_) { /* 본문이 JSON이 아님 */ }
  return new ApiError("INTERNAL", "");
}

async function getJson(path) {
  let res;
  try {
    res = await fetch(path);
  } catch (_) {
    throw new ApiError("SERVER_DOWN", "");
  }
  if (!res.ok) throw await readError(res);
  return res.json();
}

async function postJson(path, body) {
  let res;
  try {
    res = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  } catch (_) {
    throw new ApiError("SERVER_DOWN", "");
  }
  if (!res.ok) throw await readError(res);
  return res.json();
}

// 진행 상태를 한 줄씩 받는 요청 (Server-Sent Events). onProgress로 단계마다 알려 주고, 결과를 돌려준다.
async function postStream(path, body, onProgress) {
  let res;
  try {
    res = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  } catch (_) {
    throw new ApiError("SERVER_DOWN", "");
  }
  if (!res.ok) throw await readError(res);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let cut;
    while ((cut = buffer.indexOf("\n\n")) !== -1) {
      const block = buffer.slice(0, cut);
      buffer = buffer.slice(cut + 2);
      const event = /^event: (.*)$/m.exec(block)?.[1];
      const dataLine = /^data: (.*)$/m.exec(block)?.[1];
      if (!event || !dataLine) continue;
      const data = JSON.parse(dataLine);
      if (event === "progress") onProgress?.(data);
      else if (event === "result") return data;
      else if (event === "error") throw new ApiError(data.error.code, data.error.message);
    }
  }
  throw new ApiError("UPSTREAM_ERROR", "");
}

export const api = {
  status: () => getJson("/api/status"),
  pokemonList: () => getJson("/api/pokemon"),
  pokemon: (id) => getJson(`/api/pokemon/${id}`),
  ask: (pokemonId, question, onProgress) => postStream("/api/ask", { pokemon_id: pokemonId, question }, onProgress),
  battle: (pokemonId, opponent, onProgress) => postStream("/api/battle", { pokemon_id: pokemonId, ...opponent }, onProgress),
  evolution: (pokemonId, onProgress) => postStream("/api/evolution", { pokemon_id: pokemonId }, onProgress),
  find: (condition) => postJson("/api/find", { condition }),
  compareSearch: (pokemonId, question) => postJson("/api/compare-search", { pokemon_id: pokemonId, question }),
  // 연구소 놀이터
  talk: (pokemonId, message, history) => postJson("/api/talk", { pokemon_id: pokemonId, message, history }),
  persona: (answers) => postJson("/api/persona", { answers }),
  evolutionNext: (id) => getJson(`/api/evolution/${id}/next`),
};
