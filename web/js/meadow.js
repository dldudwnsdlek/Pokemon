// 돌아다니는 포켓몬 (가이드 10장). 장식이 아니라 포켓몬을 고르는 또 하나의 방법이다.
// 포켓몬 1마리 = <button class="critter"> 안에 <img> 1개. 위치는 transform으로만 바꾼다.
import { state, storageGet, storageSet } from "./state.js";
import { el } from "./ui.js";

const PAUSE_KEY = "oak-meadow-paused";
const EDGE = 24;          // 무대 양끝 여백
const SPRITE_W = 96;      // 버튼 폭
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
const narrow = window.matchMedia("(max-width: 900px)");

const critters = [];      // {id, el, body, shadow, bubble, x, lane, dir, state, t, dur, target, ...}
let stage;
let last = performance.now();
let rafId = 0;
let visible = !document.hidden;
let onScreen = true;
let paused = storageGet(PAUSE_KEY) === "1";
let onPick = () => {};

// ---------- 고정 난수 (같은 씨앗이면 같은 결과) ----------
function mulberry32(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const between = (r, lo, hi) => lo + r() * (hi - lo);
const rand = Math.random;

// "오늘의 풀숲": 날짜를 씨앗으로 고른다. 전설·환상은 무작위로 나오지 않는다.
function todaysFriends(count) {
  const d = new Date();
  const seed = d.getFullYear() * 10000 + (d.getMonth() + 1) * 100 + d.getDate();
  const r = mulberry32(seed);
  const pool = state.pokemon.filter((p) => !p.is_legendary && !p.is_mythical).map((p) => p.id);
  const picked = [];
  while (picked.length < count && pool.length) picked.push(pool.splice(Math.floor(r() * pool.length), 1)[0]);
  return picked;
}

function capacity() {
  return narrow.matches ? 3 : 6;
}

// 깊이 줄 3개 (뒤·가운데·앞). 뒤 줄일수록 위쪽, 0.85배, 살짝 흐린 색.
function laneY(lane) {
  const h = stage.clientHeight;
  return [-(h * 0.3), -(h * 0.15), -(h * 0.02)][lane];
}
const LANE_SCALE = [0.85, 1, 1];

function width() {
  return stage.clientWidth;
}

function randomTarget(c) {
  const lo = EDGE;
  const hi = Math.max(lo + 1, width() - EDGE - SPRITE_W);
  for (let i = 0; i < 6; i += 1) {
    const dist = between(rand, 80, 260) * (rand() < 0.5 ? -1 : 1);
    const t = c.x + dist;
    if (t >= lo && t <= hi) return t;
  }
  return Math.min(hi, Math.max(lo, c.x + (c.x < width() / 2 ? 120 : -120)));
}

// ---------- 상태 바꾸기 ----------
function setState(c, next, opts = {}) {
  c.state = next;
  c.t = 0;
  c.dur = opts.dur ?? 0;
  c.bubble.hidden = true;
  if (next === "idle") c.dur = between(rand, 1.5, 4);
  if (next === "walk") {
    c.target = opts.target ?? randomTarget(c);
    c.dir = c.target > c.x ? 1 : -1;
    c.walkStarted = performance.now();
  }
  if (next === "hop") {
    c.hops = rand() < 0.5 ? 1 : 2;
    c.dur = c.hops * 0.35 + between(rand, 0.05, 0.1);
  }
  if (next === "turn") { c.dir *= -1; c.dur = 0.3; }
  if (next === "greet") { c.dur = 0.8; showBubble(c, "!"); }
  if (next === "think") showBubble(c, "think");
  if (next === "enter" || next === "leave") {
    c.target = opts.target;
    c.dir = c.target > c.x ? 1 : -1;
    c.walkStarted = performance.now();
  }
}

function showBubble(c, kind) {
  c.bubble.replaceChildren(...(kind === "think"
    ? [el("span", { class: "dot" }, "."), el("span", { class: "dot" }, "."), el("span", { class: "dot" }, ".")]
    : ["!"]));
  c.bubble.hidden = false;
}

function nextAfterIdle(c) {
  const r = rand();
  const hop = c.hopChance;
  if (r < hop) return "hop";
  if (r < hop + 0.25) return "idle";
  return "walk";
}

// 두 포켓몬이 같은 줄에서 40px 안으로 다가오면 늦게 출발한 쪽이 돌아선다
function checkBump(c) {
  for (const o of critters) {
    if (o === c || o.lane !== c.lane || o.state === "leave" || o.state === "enter") continue;
    const dx = o.x - c.x;
    if (Math.abs(dx) < 40 && Math.sign(dx) === c.dir) {
      if (o.state !== "walk" || (c.walkStarted || 0) >= (o.walkStarted || 0)) {
        setState(c, "turn");
        return true;
      }
    }
  }
  return false;
}

// ---------- 매 프레임 갱신 (상태 기계, 가이드 10-4) ----------
function updateCritter(c, dt) {
  if (c.hovered) return; // 마우스를 올리면 잠시 멈춤
  c.t += dt;
  c.lift = 0;
  const still = reduceMotion.matches;

  switch (c.state) {
    case "idle":
      c.lift = still ? 0 : Math.round(Math.sin((c.t / c.breath) * Math.PI * 2) * 0.5 + 0.5); // 1px 숨쉬기
      if (c.t >= c.dur && !still) setState(c, nextAfterIdle(c));
      break;
    case "walk":
    case "enter":
    case "leave": {
      if (still && c.state === "walk") { setState(c, "idle"); break; }
      if (c.state === "walk" && checkBump(c)) break;
      const step = c.speed * dt * (c.state === "walk" ? 1 : 1.3);
      const remain = c.target - c.x;
      c.x += Math.sign(remain) * Math.min(Math.abs(remain), step);
      c.stride += step;
      c.lift = Math.abs(Math.sin((c.stride / 14) * Math.PI)) * 2; // 걸음마다 2px 흔들림
      if (Math.abs(c.target - c.x) < 0.5) {
        if (c.state === "leave") return remove(c);
        setState(c, "idle");
      }
      break;
    }
    case "hop": {
      const phase = Math.min(c.t / 0.35, c.hops);
      c.lift = phase < c.hops ? Math.sin((phase % 1) * Math.PI) * 10 : 0;
      if (c.t >= c.dur) setState(c, "idle");
      break;
    }
    case "turn":
      if (c.t >= c.dur) setState(c, "walk", { target: c.x + c.dir * between(rand, 80, 200) });
      break;
    case "greet":
      c.lift = still ? 0 : Math.sin(Math.min(c.t / 0.5, 1) * Math.PI) * 24; // 높게 깡충
      if (c.t >= c.dur) setState(c, "idle");
      break;
    case "think":
      break; // 답이 올 때까지 멈춰서 "…"
    default:
      break;
  }
  if (c.droop > 0) c.droop = Math.max(0, c.droop - dt);
  // 목표가 무대 밖으로 밀렸을 때(창 크기 변경) 안쪽으로
  if (c.state === "walk") c.target = Math.min(Math.max(c.target, EDGE), Math.max(EDGE, width() - EDGE - SPRITE_W));
}

function renderCritter(c) {
  const sink = c.droop > 0 ? 2 : 0; // 오류: 고개를 떨군 듯 2px 내려앉음
  c.el.style.transform = `translate3d(${c.x.toFixed(1)}px, ${laneY(c.lane).toFixed(1)}px, 0) scale(${LANE_SCALE[c.lane]})`;
  // 5세대 그림은 왼쪽을 본다 → 오른쪽으로 갈 때 뒤집기
  c.body.style.transform = `translateY(${(-c.lift + sink).toFixed(1)}px) scaleX(${c.dir > 0 ? -1 : 1})`;
  // 그림자는 같이 뜨지 않고 작아지기만
  c.shadow.style.transform = `scale(${(1 - Math.min(c.lift, 24) / 48).toFixed(2)})`;
}

function tick(now) {
  const dt = Math.min((now - last) / 1000, 0.05); // 탭 복귀 시 순간이동 방지
  last = now;
  for (const c of [...critters]) {
    updateCritter(c, dt);
    if (critters.includes(c)) renderCritter(c);
  }
  rafId = running() ? requestAnimationFrame(tick) : 0;
}

function running() {
  return visible && onScreen && !paused;
}

function startLoop() {
  if (rafId || !running()) return;
  last = performance.now();
  rafId = requestAnimationFrame(tick);
}

// ---------- 포켓몬 만들기·없애기 ----------
function personality(id) {
  // 번호가 가까워도 개성이 비슷해지지 않도록 씨앗을 잘 섞는다
  const r = mulberry32(Math.imul(id, 2654435761) ^ 0x5bd1e995);
  r();
  return {
    speed: between(r, 28, 55),
    breath: 2.4 * between(r, 0.8, 1.2),
    hopChance: 0.15 * between(r, 0.8, 1.2),
    lane: Math.floor(r() * 3),
  };
}

function loadSprite(p) {
  // 그림을 미리 불러오고, 다 불러온 포켓몬부터 등장시킨다
  return new Promise((resolve) => {
    const tryUrl = (urls) => {
      if (!urls.length) return resolve(null);
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = () => tryUrl(urls.slice(1));
      img.src = urls[0];
    };
    tryUrl([p.sprite.animated, p.sprite.static]);
  });
}

async function spawn(id, { entering = false } = {}) {
  const p = state.byId.get(id);
  if (!p || critters.some((c) => c.id === id)) return null;
  const img = await loadSprite(p);
  if (critters.some((c) => c.id === id)) return null;
  const persona = personality(id);
  const body = el("span", { class: "body" },
    img ? Object.assign(img, { alt: "", className: "pixel" }) : el("span", { class: "placeholder" }, p.dex_no));
  const shadow = el("span", { class: "shadow" });
  const bubble = el("span", { class: "bubble", hidden: true });
  const node = el("button", {
    class: `critter${persona.lane === 0 ? " back" : ""}`,
    type: "button",
    "aria-label": `No.${p.dex_no} ${p.name_ko} 선택하기`,
  }, shadow, body, el("span", { class: "tag" }, `No.${p.dex_no} ${p.name_ko}`), bubble);
  node.style.zIndex = String(persona.lane + 1); // 앞 줄일수록 위에

  const c = {
    id, el: node, body, shadow, bubble, ...persona,
    x: entering ? width() + 10 : between(rand, EDGE, Math.max(EDGE + 1, width() - EDGE - SPRITE_W)),
    dir: -1, state: "idle", t: 0, dur: 0, stride: 0, lift: 0, droop: 0, bornAt: performance.now(),
  };
  node.addEventListener("mouseenter", () => { c.hovered = true; });
  node.addEventListener("mouseleave", () => { c.hovered = false; });
  node.addEventListener("click", () => {
    if (c.state !== "think") setState(c, "greet");
    renderCritter(c);
    onPick(id);
  });
  critters.push(c);
  stage.append(node);
  if (entering && !reduceMotion.matches && !paused) {
    setState(c, "enter", { target: between(rand, width() * 0.55, width() - EDGE - SPRITE_W) });
  } else {
    if (entering) c.x = between(rand, width() * 0.55, Math.max(width() * 0.55 + 1, width() - EDGE - SPRITE_W));
    setState(c, "idle");
  }
  renderCritter(c);
  startLoop();
  return c;
}

function remove(c) {
  c.el.remove();
  critters.splice(critters.indexOf(c), 1);
}

function find(id) {
  return critters.find((c) => c.id === id && c.state !== "leave");
}

// 가장 오래 머문 1마리가 반대쪽(왼쪽) 끝으로 걸어 나가 수를 유지한다
function keepCount(exceptId) {
  const staying = critters.filter((c) => c.state !== "leave");
  if (staying.length <= capacity()) return;
  const oldest = staying.filter((c) => c.id !== exceptId && c.id !== state.selectedId)
    .sort((a, b) => a.bornAt - b.bornAt)[0];
  if (!oldest) return;
  if (reduceMotion.matches || paused) remove(oldest);
  else setState(oldest, "leave", { target: -SPRITE_W - 20 });
}

// ---------- 밖에서 부르는 함수들 ----------
export const meadow = {
  init(pickHandler) {
    stage = document.getElementById("stage");
    onPick = pickHandler;
    const toggle = document.getElementById("meadowPause");
    toggle.checked = paused;
    toggle.addEventListener("change", () => {
      paused = toggle.checked;
      storageSet(PAUSE_KEY, paused ? "1" : "0");
      startLoop();
    });
    document.addEventListener("visibilitychange", () => { visible = !document.hidden; startLoop(); });
    new IntersectionObserver(([entry]) => { onScreen = entry.isIntersecting; startLoop(); })
      .observe(document.getElementById("meadow"));
    for (const id of todaysFriends(capacity())) spawn(id);
  },

  // 도감 색인이나 탐색 카드에서 고르면: 오른쪽 끝에서 걸어 들어온다 (이미 있으면 그 자리에서 깡충)
  async bringIn(id) {
    for (const c of critters) c.el.classList.toggle("selected", c.id === id);
    const here = find(id);
    if (here) {
      if (here.state !== "think" && !reduceMotion.matches) setState(here, "hop");
      startLoop();
      return;
    }
    const c = await spawn(id, { entering: true });
    if (c) c.el.classList.add("selected");
    keepCount(id);
  },

  think(id) {
    const c = find(id);
    if (c) { setState(c, "think"); renderCritter(c); }
  },

  greet(id) {
    const c = find(id);
    if (c) { setState(c, "greet"); startLoop(); }
  },

  droop(id) {
    const c = find(id);
    if (c) { setState(c, "idle"); c.droop = 0.5; renderCritter(c); startLoop(); }
  },
};
