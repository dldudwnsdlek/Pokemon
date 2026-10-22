# 검증 결과 (명세서 4장 · 가이드 13장)

상태: ✅ 통과 · ❌ 실패 · ⬜ 미확인.
실행 기록 원본은 `docs/evidence/`에 있습니다 (`checks.md`는 `python -m scripts.run_checks`로 다시 만들 수 있음).
화면 캡처는 `docs/screenshots/`에 있습니다 (2026-10-22, 실제 키로 켠 서버를 크롬으로 조작해 찍음. 터미널 그림은 명령 출력을 그대로 옮김. V06·V07은 다시 실행하면 색인이 바뀌어 기록 파일을 그림으로 옮김).
추가 캡처: `F2009_first_screen.png`(첫 화면), `F2012_progress.png`(답을 찾는 중 진행 상태), `F2013_mobile_390.png`(좁은 화면).

검증 환경: 2026-10-21 · gpt-4.1-mini / text-embedding-3-small · 청크 800/150 · Top-k 5 · similarity

## 1. 검증 항목 (V01 ~ V20)

V19·V20은 "자유 질문" 추가 뒤 새로 넣은 항목입니다. V06·V07·V16은 순위 문서 9개를 넣기 전(공용 문서 96개)에 측정했습니다.

| 번호 | 확인 내용 | 요구사항 | 결과 | 근거 기록 | 캡처 |
|---|---|---|---|---|---|
| V01 | 로드 151건 = 색인 151청크, 두 번 실행해도 151 | F2001, F2002 | ✅ 1회차 0 → 151, 2회차 151 → 151 | `build_index` 출력 | `screenshots/V01_terminal.png` |
| V02 | 리자몽 항목 텍스트에 모든 속성 포함 | F2001 | ✅ 이름·번호·분류·타입·특성·키·몸무게·능력치·진화·구분·도감 설명 | `build_item_text --id 6` | `screenshots/V02_terminal.png` |
| V03 | 검색어 목록, 색인된 문서 / 버려진 문서 | F2003, F2004 | ✅ 예: Q2 검색어 [리자몽, 포켓몬의 타입] → 색인 「리자몽」, 버림: 목록 문서 2개(표로 된 목록), 파이리·꼬부기 등(관련 적음) | `evidence/checks.md` | `screenshots/V03_V18_answer_new_collect.png` · `screenshots/V03_V05_collect_log.png` |
| V04 | 같은 질문 재질문 시 "예전에 모아 둔 자료" | F2004, NF2002 | ✅ Q1~Q6 모두 재질문 때 검색어 전부 캐시, 새 색인 0개 | `evidence/checks.md` | `screenshots/V04_cached_requestion.png` |
| V05 | 포켓몬 자체 위키 문서가 항상 포함 | F2004 | ✅ 이브이 → 「이브이」, 팬텀 → 「팬텀 (포켓몬)」(동음이의어 「팬텀」은 제외), 잠만보 → 「잠만보」. 단독 문서가 없는 119마리는 이유를 기록 | `evidence/checks.md`, `wiki_coverage.md` | `screenshots/V03_V05_collect_log.png` (라프라스 → 「라프라스」) |
| V06 | 청크 크기 800 → 400 변경 시 청크 수 변화 | F2005 | ✅ 위키 청크 181 → 377 (pokemon_docs 277 → 473), 원복 시 277 | `evidence/V06_*.txt` | `screenshots/V06_terminal.png` (기록 파일) |
| V07 | Top-k 3 → 8 변경 시 근거 목록 변화 | F2006 | ✅ 근거 4개 → 9개 (늘어난 근거 대부분 같은 「이브이」 문서의 다른 조각) | `evidence/V07_V16_compare_search.txt` | `screenshots/V07_terminal.png` (기록 파일) |
| V08 | LangGraph 노드 두 개 | F2007 | ✅ `__start__ → retrieve → generate → __end__` | `rag.graph --draw` | `screenshots/V08_terminal.png` |
| V09 | 답변 근거 번호 = 참고 카드, 출처 종류 구분 | F2007, F2008, F2016 | ✅ 답변에 쓴 번호만 목록에 남음(없는 번호 무시). 예: Q4 → [1] 도감 데이터 · [2] 위키백과 · [3] PokéAPI 자료 | `evidence/checks.md` | `screenshots/V09_citations_source_types.png` |
| V10 | 문서에 없는 질문 → "확인되지 않습니다" | F2007 | ✅ "피카츄의 꼬리 길이는 몇 cm야?" → "제공된 자료에서는 확인되지 않습니다" (3회 반복 모두 같음) | `evidence/checks.md` | `screenshots/V10_V11_not_found_no_citation.png` |
| V11 | 인용 근거 0개 안내 | F2008 | ✅ 위 질문에서 `no_citation: true` → 참고 카드 자리에 점선 빈 카드 "이번 답에는 인용된 근거가 없어요" | `evidence/checks.md` | `screenshots/V10_V11_not_found_no_citation.png` |
| V12 | 포켓몬 바꾸면 대화가 섞이지 않음 | F2009 | ✅ 기록은 `{포켓몬ID 또는 "free": [기록]}`로 따로 저장되고 선택한 것만 그림. Streamlit 자동 시험: 자유 질문 기록 2개를 만든 뒤 리자몽으로 바꾸면 리자몽 기록 0개 | `web/js/state.js`, Streamlit AppTest | `screenshots/V12_switch_to_charizard.png` · `screenshots/V12_switch_to_pikachu.png` |
| V13 | 조건 탐색 결과에 조건 밖 포켓몬 없음 | F2011 | ✅ "물 타입인데 몸무게 100kg 넘는 포켓몬" → 라프라스·쥬레곤·파르셀·갸라도스 = 데이터 기준 정답 4마리와 정확히 일치 | `evidence/checks.md` | `screenshots/V13_find.png` |
| V14 | 특화 기능 결과에 근거 표시 | F2010 | ✅ 피카츄 vs 꼬부기 → 판정 "유리", 근거 4건(양쪽 도감 데이터 + 전기·물 타입 상성). 이브이 진화 → 근거 3건 | `evidence/checks.md` | `screenshots/V14_battle_coach.png` · `screenshots/V14_evolution_guide.png` |
| V15 | 색인 없음 / 키 없음 안내 | F2012 | ✅ 키 없음: `/api/ask` → 503 `API_KEY_MISSING` + 화면 안내 카드. 색인 없음: "도감이 비어 있어요" 안내 카드 | 1280·390px 스크린샷 확인 | `screenshots/V15_index_empty.png` · `screenshots/V15_api_key_missing.png` |
| V16 | 유사도 vs MMR 근거 비교 | F2014 | ✅ Top-k 8: 서로 다른 문서 유사도 4개 → MMR 8개 (무관한 공용 문서도 섞임 — 설계문서 7장) | `evidence/V07_V16_compare_search.txt` | `screenshots/V16_similarity_vs_mmr.png` |
| V17 | RAG 전후 비교 문서 | F2015 | ✅ 7문항. RAG 없이 완전히 맞은 것 2개(Q2·Q6) / RAG 7개 모두 맞음. Q7은 근거 없이 "약 10cm"로 지어냄 | `rag_comparison.md` | — |
| V18 | 대표 질문 처리 시간 | NF2001 | ✅ 첫 질문 3.2~7.4초(위키 수집 포함), 재질문 1.8~4.3초 | `evidence/checks.md` | `screenshots/V03_V18_answer_new_collect.png` · `screenshots/V04_cached_requestion.png` (2026-10-22 다시 잼: 새 수집 26.6초, 재질문 8.3초) |
| V19 | 자유 질문 (포켓몬을 고르지 않고 묻기) | F2009-1 | ✅ "1세대에서 가장 무거운 포켓몬은?" → 잠만보 460kg [1세대 몸무게 순위]. "고스트→에스퍼" → 1세대 0배·현재 2배 [타입 상성 2건]. "피카츄와 꼬부기 중 누가 빨라?" → 두 이름을 찾아 90 vs 43 [두 도감 데이터] | `evidence/checks.md` | `screenshots/V19_free_question.png` |
| V20 | 자유 질문 문서가 포켓몬별 검색에 섞이지 않음 | F2009-1, F2006 | ✅ 자유 질문 문서 제목으로 포켓몬 7마리 × 유사도·MMR 검색 → 섞인 문서 0건 | `evidence/checks.md` | — |

## 2. 명세서 4장 항목별 대조

### 4.1 데이터와 색인 (F2001 ~ F2002)
- [x] 로드한 항목 수(151)와 색인된 청크 수(151)가 일치 — V01
- [x] 색인을 두 번 실행해도 청크 수가 늘지 않음 — V01
- [x] 항목 1건의 색인 텍스트에 의도한 속성이 모두 들어감 — V02

### 4.2 문서 수집과 색인 (F2003 ~ F2005)
- [x] 프롬프트 1이 뽑은 검색어 목록 확인 — V03
- [x] 프롬프트 2로 색인된 문서와 버려진 문서 구분 — V03
- [x] 같은 질문 재질문 시 수집이 다시 일어나지 않음 — V04
- [x] 선택한 항목 자체를 다룬 문서가 빠지지 않음 — V05
- [x] 청크 크기·중복 길이 변경 시 청크 수가 달라짐 — V06

### 4.3 답변과 근거 (F2006 ~ F2008)
- [x] Top-k 변경 시 근거 목록 변화 — V07
- [x] LangGraph가 retrieve·generate 두 노드 — V08
- [x] 답변 근거 번호 = 화면 근거 목록 — V09
- [x] 메타데이터와 외부 문서가 구분되어 표시 — V09
- [x] 문서에 없는 것을 물으면 확인되지 않는다고 답함 — V10
- [x] 인용 근거가 하나도 없을 때 안내 — V11

### 4.4 서비스 기능과 화면 (F2009 ~ F2012)
- [x] 항목을 바꿨을 때 이전 대화가 섞이지 않음 — V12 (캡처는 사람이)
- [x] 조건 탐색 결과에 조건과 맞지 않는 항목이 없음 — V13
- [x] 도메인 특화 기능 결과에도 근거 제시 — V14
- [x] 문서 수집·답변 생성 중 진행 상태 표시 — SSE `progress` 6~7줄 확인
- [x] 색인이 없는 상태와 API 키가 없는 상태의 안내 — V15
- [x] 위험 도메인 면책 — 해당 없음 (게임·애니메이션). 대신 "게임 버전에 따라 내용이 다를 수 있어요"

### 4.5 심화 기능 (F2013 ~ F2016)
- [x] F2013 — 실제 키로 모든 API 주소 동작 확인 (ask·battle·evolution SSE, find, compare-search). 화면 동작은 가짜 데이터 스크린샷으로 확인
- [x] F2014 — 같은 질문에 유사도·MMR 근거 목록 비교 — V16
- [x] F2015 — 대표 질문 RAG 전후 답변 — V17
- [x] F2016 — 근거 목록에 출처 종류(도감 데이터/위키백과/PokéAPI 자료) 구분 — V09

### 4.7 비기능 요구사항
- [x] NF2001 대표 질문 처리 시간 — V18
- [x] NF2002 이미 수집한 데이터는 다시 수집하지 않음 — PokéAPI 두 번째 실행 외부 호출 0회, 위키는 V04
- [x] NF2003 소스·제출물에 API 키 없음 — `.env`는 Git 제외, `git log -p`에 키 값 0건
- [x] NF2004 화면·API에 키·프롬프트·traceback 비노출 — 오류 응답은 코드+문구만
- [x] NF2005 수집·색인·검색·생성·UI 모듈 분리 — `data_prep / store / rag / features / api·web`
- [x] NF2006 재시도·호출 간격·User-Agent — `services/http.py` 한 곳. GMS 시간 초과 1회를 재시도로 자동 복구한 기록 있음(`logs/app.log`)
- [x] NF2007 출처·이용 조건 기록 — `SOURCES.md`

## 3. 디자인 금지 목록 점검 (가이드 9-8)

| 항목 | 결과 | 확인 방법 |
|---|---|---|
| 보라·파랑 그라데이션 배경, 그라데이션 글자 | ✅ 없음 | `linear-gradient`는 모눈 선·카드 가로줄 무늬에만 사용 |
| 반투명 유리 효과 (`backdrop-filter`) | ✅ 없음 | 코드 검색 0건 |
| 흐릿하고 큰 그림자 | ✅ 없음 | 그림자는 `3px 3px 0 var(--ink)` 하나 |
| 큰 둥근 모서리 (12px 이상) | ✅ 없음 | 기본 2px, 카드 4px. 원 모양은 근거 번호 동그라미·판정 도장·펀칭 구멍·그림자 타원(가이드가 정한 부품)만 |
| 이모지·반짝이·로봇 아이콘 | ✅ 없음 | 연필 표시는 직접 그린 SVG |
| "AI 어시스턴트" 같은 문구 | ✅ 없음 | `web/`에서 "AI·어시스턴트·챗봇·생성형" 검색 0건 |
| 가운데 큰 제목 + 부제 + 버튼 2개 첫 화면 | ✅ 없음 | 첫 화면이 바로 노트 |
| 같은 크기 카드 3개 기능 소개 | ✅ 없음 | |
| Inter·Roboto·시스템 글꼴만 사용 | ✅ 아님 | Galmuri11 + Pretendard + Nanum Pen Script |
| Tailwind 기본 색 | ✅ 아님 | Tailwind 미사용, 색은 `tokens.css` 변수만 |
| 의미 없이 움직이는 장식 | ✅ 없음 | 움직임은 풀숲 포켓몬(선택 수단)과 "…" 말풍선(기다리는 중)뿐 |

## 4. 제출 전 점검 (가이드 13-6)

- [x] 필수 F2001~F2012 동작 (기능 검증 완료, 화면 캡처는 사람이)
- [x] 심화 F2013~F2016 결과가 있고 필수 구현과 비교되어 있음 (`rag_comparison.md`, 설계문서 7장)
- [x] V01~V19 화면 캡처 — `docs/screenshots/` (V17·V20은 문서·기록으로 확인)
- [x] 요구사항 정의서(`docs/requirements.md`), RAG 파이프라인 설계문서(`docs/rag_design.md`), README.md, SOURCES.md
- [ ] 셀프·상호 체크리스트 (3일차 오후 제공 양식)
- [x] README에 실행 순서: ① 가상환경·설치 ② .env ③ build_index ④ uvicorn 또는 streamlit
- [ ] zip에 `.env`, `.venv/`, `chroma_db/`, `cache/`가 들어 있지 않음 (zip 만들 때 확인)
- [ ] 파일명: `AI 코어프로젝트 2_[포켓몬 연구노트]_지역_반_성명.zip`
