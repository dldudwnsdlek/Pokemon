// 화면 문구와 공용 화면 도우미 (가이드 11-2). 문구는 모두 여기 모아 둔다.

export const TEXT = {
  opening: "연구노트를 펼치는 중…",
  building: "연구소 서버가 막 깨어나서 151마리 도감 색인을 만들고 있어요. 1분쯤 걸려요. 끝나면 이 안내가 저절로 닫혀요.",
  INDEX_EMPTY: "아직 도감이 비어 있어요. 터미널에서 <code>python -m scripts.build_index</code> 를 실행한 뒤 새로고침해 주세요.",
  API_KEY_MISSING: "연구소 열쇠(API 키)가 설정되지 않았어요. <code>.env</code> 파일에 <code>GMS_API_KEY</code> 를 넣고 서버를 다시 켜 주세요.",
  serverDown: "연구소 서버와 연결되지 않아요. 터미널에서 서버가 켜져 있는지 확인해 주세요.",
  NO_RESULTS: "관련 자료를 찾지 못했어요. 질문을 조금 바꿔 보시겠어요?",
  noCitation: "이번 답에는 인용된 근거가 없어요. 내용을 그대로 믿기 전에 확인해 주세요.",
  UPSTREAM_ERROR: "자료실 연결이 잠시 불안정해요. 잠시 후 다시 시도해 주세요.",
  OUT_OF_SCOPE: "이 노트는 관동지방 1세대(1~151번) 포켓몬만 다뤄요.",
  INTERNAL: "노트를 넘기다 문제가 생겼어요. 잠시 후 다시 시도해 주세요.",
  BAD_REQUEST: "질문은 1~500자로 적어 주세요.",
  versionNote: "게임 버전에 따라 내용이 다를 수 있어요",
  emptyRecord: "아직 이 포켓몬에 대한 기록이 없어요. 궁금한 걸 적어보세요.",
  findEmpty: "조건에 맞는 포켓몬을 찾지 못했어요. 조건을 하나 줄여보세요.",
  noRefsYet: "답을 기록하면 여기에 참고한 자료가 붙어요.",
  findRefs: "찾은 포켓몬의 근거는 각 카드 아래에 적혀 있어요.",
  savedRefs: "질문하면 아래 자료 중에서 근거를 골라 붙여요.",
  noSavedDocs: "아직 모아 둔 위키백과 문서는 없어요. 질문하면 필요한 문서를 찾아 모아요.",
  weakNote: "타입 약점은 세대마다 달라요. 「배틀」 탭에서 근거와 함께 확인해 보세요.",
  dexSource: "자료: PokéAPI 도감 데이터",
  retry: "다시 시도",
  freeLabel: "자유 질문",
  freeEmpty: "포켓몬을 고르지 않아도 물어볼 수 있어요. 질문에 포켓몬 이름이 있으면 그 포켓몬의 도감 자료로 찾아봐요.",
  welcomeTitle: "관동 포켓몬 151마리 연구노트",
  welcomeSteps: [
    "아래 칸에 궁금한 걸 적고 「기록하기」를 눌러요.",
    "답 속 동그란 숫자를 누르면 근거가 된 자료 카드로 이어져요.",
    "왼쪽 도감 색인이나 풀숲에서 포켓몬을 고르면 그 포켓몬의 노트가 열려요.",
  ],
  needPokemon: "이 기능은 포켓몬이 있어야 해요. 왼쪽 도감 색인이나 아래 풀숲에서 포켓몬을 먼저 골라 주세요.",
  matched: (names) => `질문에서 ${names}을 찾아 그 도감 자료로 답했어요`,
  kind: { chat: "기록", battle: "배틀", evolution: "진화" },
};

// 받침에 맞는 조사 붙이기: josa("피카츄", "을/를") → "피카츄를", josa("이상해풀", "으로/로") → "이상해풀로"
export function josa(word, pair) {
  const [withFinal, without] = pair.split("/");
  const code = word.charCodeAt(word.length - 1) - 0xac00;
  if (code < 0 || code > 11171) return `${word}${without}`; // 한글이 아니면 받침 없는 쪽
  const final = code % 28;
  // "으로/로"는 ㄹ 받침(8)도 "로"
  const useFinal = final !== 0 && !(withFinal === "으로" && final === 8);
  return `${word}${useFinal ? withFinal : without}`;
}

// 오류 코드 → 문구. 모르는 코드는 일반 안내로.
export function errorText(code) {
  return TEXT[code] || TEXT.INTERNAL;
}

// 작은 요소 만들기 도우미: el("div", {class: "x"}, "글자", 자식…)
export function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === undefined || v === null || v === false) continue;
    if (k === "class") node.className = v;
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v === true ? "" : v);
  }
  for (const c of children.flat()) {
    if (c === null || c === undefined || c === false) continue;
    node.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return node;
}

export function typeBadges(types) {
  return types.map((t) => el("span", { class: "type-badge", "data-type": t }, t));
}

// 그림: 움직이는 GIF → 실패하면 정지 그림 → 그것도 실패하면 점선 원 자리표시
export function spriteImg(p, { animated = true, size } = {}) {
  const img = el("img", { alt: "", class: "pixel", loading: "lazy", width: size, height: size });
  const sources = animated ? [p.sprite.animated, p.sprite.static] : [p.sprite.static];
  let i = 0;
  img.src = sources[0];
  img.addEventListener("error", () => {
    i += 1;
    if (i < sources.length) img.src = sources[i];
    else img.replaceWith(el("span", { class: "placeholder" }, p.dex_no || String(p.id).padStart(3, "0")));
  });
  return img;
}

// 노트 전체를 덮는 안내 카드
export function showNotice(title, html) {
  document.getElementById("noticeTitle").textContent = title;
  document.getElementById("noticeText").innerHTML = html; // 문구는 위 TEXT 상수에서만 온다
  document.getElementById("notice").hidden = false;
}
export function hideNotice() {
  document.getElementById("notice").hidden = true;
}

// 진행 기록: 노트 맨 아래에 연필로 쓰듯 한 줄씩, 끝나면 한 줄로 접힘
export const progressLog = {
  box: () => document.getElementById("progressLog"),
  start() {
    this.box().replaceChildren();
    this.started = performance.now();
  },
  write(message) {
    const box = this.box();
    const last = box.lastElementChild;
    if (last && last.textContent === message) return;
    box.append(el("div", { class: "line" }, message));
    box.scrollIntoView({ block: "end", behavior: "smooth" });
  },
  fold(docCount, elapsedMs) {
    const secs = ((elapsedMs ?? performance.now() - this.started) / 1000).toFixed(1);
    this.box().replaceChildren(el("div", { class: "folded" }, `문서 ${docCount}개 참고 · ${secs}초`));
  },
  clear() {
    this.box().replaceChildren();
  },
};

export function formatTime(iso) {
  const d = new Date(iso);
  const pad = (n) => String(n).padStart(2, "0");
  return {
    date: `${d.getFullYear()}.${pad(d.getMonth() + 1)}.${pad(d.getDate())}`,
    time: `${pad(d.getHours())}:${pad(d.getMinutes())}`,
  };
}
