"""필수 기능 확인용 Streamlit 화면 (F2009~F2012). 실행: streamlit run streamlit_app.py

핵심 로직은 HTML 화면과 똑같이 rag/, features/ 함수를 그대로 부른다. 화면만 다르다.
"""
import streamlit as st

from data_prep.build_item_text import load_pokemon, pokemon_by_id
from data_prep.finder_terms import type_names
from data_prep.sprites import sprite_urls
from features import battle_coach, evolution_guide, finder
from rag.collector import collected_titles
from rag.graph import run
from services.config import settings
from services.errors import MESSAGES, ServiceError
from services.log import get_logger
from store.vector_store import DOCS, META, count

log = get_logger("streamlit")
st.set_page_config(page_title="이박사의 연구노트", layout="wide")

VERSION_NOTE = "게임 버전에 따라 내용이 다를 수 있어요."
NO_CITATION = "이번 답에는 인용된 근거가 없어요. 내용을 그대로 믿기 전에 확인해 주세요."
KIND_LABEL = {"chat": "기록", "battle": "배틀 상성", "evolution": "진화 안내"}

FREE = 0  # 선택 상자에서 "자유 질문(포켓몬 고르지 않음)"을 뜻하는 값
NEED_POKEMON = "이 기능은 포켓몬이 있어야 해요. 왼쪽에서 포켓몬을 먼저 골라 주세요."

ss = st.session_state
ss.setdefault("chats", {})       # F2009 — {포켓몬ID 또는 "free": [메시지들]} 따로 보관


def history(pid: int | None) -> list[dict]:
    return ss["chats"].setdefault("free" if pid is None else pid, [])


def select(pid: int) -> None:
    """도감 선택 상자와 탐색 카드가 함께 쓰는 선택 함수."""
    ss["pick"] = pid


def show_citations(msg: dict) -> None:
    """답변 아래 근거 목록 (실제로 인용된 것만)."""
    if msg.get("version_note"):
        st.caption(VERSION_NOTE)
    if msg.get("no_citation"):
        st.info(NO_CITATION)
        return
    with st.expander(f"답변에 사용한 근거 {len(msg['citations'])}건"):
        for c in msg["citations"]:
            st.markdown(f"**[근거 {c['no']}]** `{c['source_label']}` {c['title']} — [원문 보기 ↗]({c['url']})")
            st.caption(c["snippet"] + "…")


def show_message(msg: dict) -> None:
    with st.chat_message(msg["role"]):
        if msg["role"] == "user":
            st.markdown(f"**Q.** {msg['text']}")
            return
        if msg.get("kind", "chat") != "chat":
            st.caption(KIND_LABEL[msg["kind"]])
        if msg.get("verdict"):
            st.markdown(f"### 판정: {msg['verdict']}")
        if msg.get("chain"):
            cols = st.columns(len(msg["chain"]))
            for col, s in zip(cols, msg["chain"]):
                col.image(s["sprite"]["static"], width=72)
                col.caption(("▶ " if s["current"] else "") + s["name_ko"]
                            + (f"\n({s['condition']})" if s["condition"] else ""))
        st.markdown(msg["text"])
        if msg.get("error"):
            return
        if msg.get("matched"):
            names = ", ".join(f"「{m['name_ko']}」" for m in msg["matched"])
            st.caption(f"질문에서 {names}을 찾아 그 도감 자료로 답했어요")
        show_citations(msg)
        col = msg.get("collected")
        if col:
            skipped = [f"{s['title']}({s['reason']})" for s in col["skipped"][:5]]
            if len(col["skipped"]) > 5:  # 엉뚱한 검색 후보가 섞이므로 앞 5개만
                skipped.append(f"외 {len(col['skipped']) - 5}개")
            with st.expander("수집 기록"):
                st.markdown(f"- 찾아볼 단어: {', '.join(col['queries']) or '없음'}\n"
                            f"- 붙인 문서: {', '.join(col['indexed']) or '없음'}\n"
                            f"- 버린 문서: {', '.join(skipped) or '없음'}\n"
                            f"- 예전 자료(캐시): {', '.join(col['cached']) or '없음'}")


def call_with_status(label: str, func) -> dict | None:
    """진행 상태를 보여주며 실행한다 (F2012). 오류는 안내 문구만 보여준다 (NF2004)."""
    with st.status(label, expanded=True) as status:
        def progress(step, message, detail):
            st.write(message)
        try:
            result = func(progress)
        except ServiceError as e:
            status.update(label=e.message, state="error")
            return {"error": e.message}
        except Exception:  # noqa: BLE001 — 자세한 내용은 로그에만
            log.exception("Streamlit 처리 중 오류")
            status.update(label=MESSAGES["INTERNAL"], state="error")
            return {"error": MESSAGES["INTERNAL"]}
        n = len(result.get("collected", {}).get("indexed", []))
        status.update(label=f"문서 {n}개 새로 참고 · {result['elapsed_ms'] / 1000:.1f}초",
                      state="complete", expanded=False)
    return result


def to_message(result: dict, kind: str) -> dict:
    if "error" in result:
        return {"role": "assistant", "kind": kind, "text": result["error"], "error": True}
    return {"role": "assistant", "kind": kind, "text": result["answer"], "citations": result["citations"],
            "no_citation": result["no_citation"], "version_note": result["version_note"],
            "verdict": result.get("verdict"), "chain": result.get("chain"), "collected": result.get("collected"),
            "matched": result.get("matched")}


# ---------------- 사이드바 ----------------
pokemon = load_pokemon()
labels = {p["id"]: f"{p['dex_no']} {p['name_ko']}" for p in pokemon}
box_labels = {FREE: "자유 질문 (포켓몬 고르지 않음)", **labels}  # 맨 앞(기본값)이 자유 질문

with st.sidebar:
    st.title("이박사의 연구노트")
    meta_n, docs_n = count(META), count(DOCS)
    st.caption(f"도감 {meta_n} · 문서 {docs_n}")  # F2002 — 색인 건수 항상 표시
    if not settings.has_api_key():
        st.error(MESSAGES["API_KEY_MISSING"])
    if meta_n == 0:
        st.warning(MESSAGES["INDEX_EMPTY"])

    if "pick" in ss:  # 탐색 카드에서 고른 포켓몬을 선택 상자에 반영
        ss["pokemon_box"] = ss.pop("pick")
    st.selectbox("포켓몬 고르기", options=list(box_labels), format_func=box_labels.get, key="pokemon_box")
    pid = ss["pokemon_box"] or None  # 0(자유 질문) → None
    p = pokemon_by_id(pid) if pid else None
    if p:
        st.image(sprite_urls(pid)["animated"], width=96)
        st.markdown(f"**No.{p['dex_no']} {p['name_ko']}** · {p['genus_ko']}  \n타입: {', '.join(p['types'])}")
    else:
        st.caption("포켓몬을 고르지 않아도 물어볼 수 있어요. 질문에 포켓몬 이름이 있으면 그 도감 자료로 찾아봐요.")
    titles = collected_titles(pid)
    st.caption("모아 둔 문서: " + (", ".join(titles) if titles else "아직 없음"))

    with st.expander("이런 포켓몬 찾아줘"):  # F2011
        cond = st.text_input("조건", placeholder="물 타입인데 몸무게 100kg 넘는 포켓몬")
        if st.button("찾아보기") and cond.strip():
            try:
                ss["found"] = finder.find(cond.strip())
            except ServiceError as e:
                ss["found"] = {"cards": [], "filters": [], "message": e.message}
        found = ss.get("found")
        if found:
            if found["filters"]:
                st.caption("적용한 필터: " + ", ".join(found["filters"]))
            if found["message"]:
                st.info(found["message"])
            for c in found["cards"]:
                st.markdown(f"**No.{c['dex_no']} {c['name_ko']}** ({', '.join(c['types'])})  \n{c['reason']}"
                            f"  \n근거: [{c['citation']['title']}]({c['citation']['url']})")
                st.button(f"{c['name_ko']}에게 질문하기", key=f"go{c['id']}", on_click=select, args=(c["id"],))

# ---------------- 본문 ----------------
st.header(f"No.{p['dex_no']} {p['name_ko']}" if p else "자유 질문")
tab_chat, tab_battle, tab_evo = st.tabs(["기록", "배틀 상성", "진화 안내"])

with tab_chat:
    msgs = history(pid)
    if not msgs:
        st.caption("아직 이 포켓몬에 대한 기록이 없어요. 궁금한 걸 적어보세요." if p
                   else "예: 1세대에서 가장 무거운 포켓몬은? / 피카츄와 꼬부기 중 누가 더 빨라?")
    for m in msgs:
        show_message(m)

question = st.chat_input("질문을 적어 주세요 (1~500자)", max_chars=500)
if question:
    with tab_chat:
        user = {"role": "user", "kind": "chat", "text": question}
        msgs.append(user)
        show_message(user)
        result = call_with_status("찾아볼 단어를 고르고 있어요",
                                  lambda prog: run(pid, question, "chat", on_progress=prog))
        reply = to_message(result, "chat")
        msgs.append(reply)
        show_message(reply)

with tab_battle:  # F2010 ① 배틀 상성 코치
    if not p:
        st.info(NEED_POKEMON)
    how = st.radio("상대 고르기", ["포켓몬", "타입"], horizontal=True, disabled=not p)
    if how == "포켓몬":
        opp_id = st.selectbox("상대 포켓몬", options=list(labels), format_func=labels.get, key="opp")
        opp_type = None
    else:
        opp_type = st.selectbox("상대 타입", options=type_names(), key="opp_type")
        opp_id = None
    if st.button("상성 보기", disabled=not p):
        result = call_with_status("상성 자료를 펼치는 중이에요", lambda prog: battle_coach.coach(
            pid, opponent_id=opp_id, opponent_type=opp_type, on_progress=prog))
        vs = labels[opp_id] if opp_id else f"{opp_type} 타입"
        history(pid).append({"role": "user", "kind": "battle", "text": f"상대 {vs}와의 상성"})
        reply = to_message(result, "battle")
        history(pid).append(reply)
        show_message(reply)

with tab_evo:  # F2010 ② 진화 안내
    if not p:
        st.info(NEED_POKEMON)
    if st.button("진화 보기", disabled=not p):
        result = call_with_status("진화 기록을 찾는 중이에요",
                                  lambda prog: evolution_guide.guide(pid, on_progress=prog))
        history(pid).append({"role": "user", "kind": "evolution", "text": "진화 계통 안내"})
        reply = to_message(result, "evolution")
        history(pid).append(reply)
        show_message(reply)
