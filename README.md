# 이박사의 연구노트 — 포켓몬 RAG 서비스

SSAFY AI 코어 프로젝트 2회차(RAG 기반 도메인 지식 서비스) 결과물입니다.

관동지방 1세대 포켓몬 151마리에 대해 질문하면, **도감 데이터와 위키백과를 찾아 읽고 근거 번호를 붙여** 답하는 포켓몬 연구 도우미입니다.
화면 아래 풀숲에서는 포켓몬들이 돌아다니고, 누르면 그 포켓몬에 대해 바로 물어볼 수 있습니다.

> **RAG**(검색 증강 생성): 답하기 전에 자료를 먼저 찾아 읽고, 찾은 자료만 근거로 답하게 하는 방법.
> 기억에만 의존하면 틀리기 쉬운 사실(진화 조건, 세대별 타입 상성, 정확한 몸무게)을 자료로 확인해서 답합니다.

---

## 1. 실행 방법

```bash
# ① 가상환경 만들고 설치 (Python 3.10 이상)
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

# ② .env 작성: .env.example을 복사해서 GMS_API_KEY에 SSAFY GMS 키를 넣는다
copy .env.example .env          # macOS/Linux: cp .env.example .env

# ③ 데이터 준비와 색인 (처음 한 번)
python -m data_prep.fetch_pokeapi   # PokéAPI → data/*.json (data/ 폴더가 이미 있으면 생략 가능)
python -m scripts.build_index       # 두 컬렉션 색인

# ④ 화면 켜기 — 둘 중 하나
uvicorn api.server:app --reload     # 직접 만든 화면 → http://localhost:8000
streamlit run streamlit_app.py      # 필수 기능 확인용 간단 화면
```

`.env`에 키가 없거나 색인이 비어 있으면, 화면이 무엇을 해야 하는지 안내합니다.
키가 있는데 도감 색인이 비어 있으면 서버가 켜질 때 스스로 색인을 만듭니다(약 10초~1분, 화면에 "도감을 펼치는 중" 안내).

### 무료 배포 (Render)

| 칸 | 값 |
|---|---|
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn api.server:app --host 0.0.0.0 --port $PORT` |
| Environment | `GMS_API_KEY`, `GMS_BASE_URL`, `PYTHON_VERSION=3.12.9` |

무료 서버는 잠들었다 깨면 파일이 처음 상태로 돌아갈 수 있어서, 색인은 서버가 켜질 때 비어 있으면 자동으로 만듭니다. 질문하며 모은 위키 문서도 이때 사라지고 다음 질문 때 다시 모읍니다.

## 2. 기능

### 필수 기능 (F2001 ~ F2012)

| 번호 | 기능 | 어디서 |
|---|---|---|
| F2001 | 151마리 데이터 로드, 1마리 = 검색용 글 1개 | `data_prep/fetch_pokeapi.py`, `data_prep/build_item_text.py` |
| F2002 | 메타데이터 색인 (`pokemon_meta`, 151청크 고정, 다시 돌려도 안 늘어남) | `store/indexer.py`, `scripts/build_index.py` |
| F2003 | 검색어 추출 (프롬프트 1, 포켓몬 연구가 역할, JSON 배열) | `rag/collector.py`, `rag/prompts.py` |
| F2004 | 위키백과 후보 수집 → 선별 (프롬프트 2) → 본문·원문 주소 수집 | `rag/collector.py`, `data_prep/wiki_source.py` |
| F2005 | 위키 본문 청킹 → `pokemon_docs` 색인 (크기·중복은 `config.yaml`) | `store/indexer.py` |
| F2006 | 두 컬렉션 검색·병합·중복 제거 (Top-k는 `config.yaml`) | `rag/retriever.py` |
| F2007 | LangGraph `retrieve → generate` 두 노드, 근거만으로 답 (프롬프트 3) | `rag/graph.py` |
| F2008 | 답변 속 `[근거 n]`을 찾아 실제 인용된 근거만 표시, 없으면 안내 | `rag/citations.py` |
| F2009 | 포켓몬 선택 + 포켓몬별로 따로 저장되는 대화 기록 | `web/js/state.js`, `streamlit_app.py` |
| F2009-1 | **자유 질문**: 포켓몬을 고르지 않고도 질문. 질문에 포켓몬 이름이 있으면 그 포켓몬의 자료로 답함 (화면을 열면 자유 질문으로 시작) | `rag/graph.py`, `data_prep/name_match.py` |
| F2010 | 특화 기능 2개: **배틀 상성 코치**, **진화 안내** | `features/battle_coach.py`, `features/evolution_guide.py` |
| F2011 | 조건 기반 탐색 ("물 타입인데 100kg 넘는 포켓몬") | `features/finder.py`, `data_prep/finder_terms.py` |
| F2012 | 진행 상태 표시, 색인 없음·키 없음·결과 없음 안내 | `web/js/ui.js`, `services/errors.py` |

### 심화 기능 (F2013 ~ F2016)

| 번호 | 기능 | 요약 |
|---|---|---|
| F2013 | 직접 만든 화면 | 순수 HTML·CSS·JavaScript(`web/`) + FastAPI 서버(`api/server.py`). 요청·응답 형식은 `docs/rag_design.md` 8장 |
| F2014 | MMR 검색 | `config.yaml`의 `retrieval.search_type: mmr`로 전환. 화면의 "근거 비교: 유사도 · MMR" 버튼, `scripts/compare_search.py` |
| F2015 | RAG 전후 비교 | `python -m scripts.compare_rag` → `docs/rag_comparison.md` |
| F2016 | 여러 종류 출처 결합 | 위키백과(서술형) + PokéAPI 구조화 문서(타입 상성 18개·진화 계통 78개·1세대 순위 9개). 근거마다 출처 종류 도장 표시 |

## 3. 데이터 준비와 색인 절차

1. **PokéAPI 수집** — `python -m data_prep.fetch_pokeapi`
   포켓몬마다 `/pokemon`, `/pokemon-species`, 진화 계통, 타입·특성 한국어 이름을 받아 `data/pokemon.json`을 만듭니다.
   받은 응답은 `cache/pokeapi/`에 저장해서, 두 번째 실행부터는 바깥 호출이 0회입니다(PokéAPI 공정 이용 규칙).
   키는 ÷10 해서 m, 몸무게는 ÷10 해서 kg로 바꿉니다.
2. **구조화 문서 만들기** — 같은 스크립트가 타입 상성 18개(`data/type_docs.json`), 진화 계통 78개(`data/evolution_docs.json`)를 문장으로 바꿔 저장합니다. 1세대 때 상성(예: 고스트 → 에스퍼 "효과 없음")도 함께 적습니다.
3. **색인** — `python -m scripts.build_index`
   `pokemon_meta`에 151청크(포켓몬 1마리 = 1청크, ID `pkm:6`), `pokemon_docs`에 구조화 문서 105청크(타입 18 + 진화 78 + 순위 9, ID `shared:type-ghost:0`)를 넣습니다.
4. **위키백과는 질문할 때 모읍니다.** 질문마다 검색어를 뽑고, 필요한 문서만 골라 `pokemon_docs`에 더합니다(ID `133:2514891:0`).
5. 청크 크기를 바꿔 다시 색인: `config.yaml` 수정 → `python -m scripts.build_index --reset-docs` (바꾸기 전·후 청크 수 출력)

확인용 명령:

```bash
python -m data_prep.build_item_text --id 6   # 리자몽 1마리의 색인 글
python -m rag.graph --draw                   # LangGraph 구조 (retrieve → generate)
python -m scripts.compare_search --pokemon 133 --question "이브이는 무엇으로 진화해?" --top-k 3 8
python -m scripts.run_checks                 # 대표 질문·탐색·특화 기능 검증 → docs/evidence/checks.md
python -m scripts.compare_rag                # RAG 전후 비교 → docs/rag_comparison.md
```

검증 결과는 [docs/verification.md](docs/verification.md)에 정리되어 있습니다.
대표 질문 7개 중 RAG 없이는 2개만 완전히 맞았고, RAG로는 7개 모두 맞았습니다([docs/rag_comparison.md](docs/rag_comparison.md)).

## 4. 사용한 데이터·문서의 출처와 이용 조건

자세한 표는 [SOURCES.md](SOURCES.md)에 있습니다.

- **PokéAPI** — 무료 공개 API, 공정 이용 규칙(로컬 캐시) 준수
- **한국어 위키백과** — CC BY-SA 4.0, 근거에 문서 제목과 원문 링크 표시
- **포켓몬 그림** — PokéAPI sprites 저장소 주소로 불러옴(복사하지 않음). 저작권은 Nintendo·Creatures·GAME FREAK
- **글꼴** — Galmuri11·Galmuri14, Pretendard, Nanum Pen Script (모두 SIL Open Font License)

> 포켓몬은 상업 IP입니다. 이 프로젝트는 **교육용으로만** 쓰고, 공개 배포·상업적 사용을 하지 않습니다.
> 위험 도메인(건강·금융)이 아니어서 면책 문구 대신, 세대별 차이가 있는 답에는 "게임 버전에 따라 내용이 다를 수 있어요"를 붙입니다.

## 5. 화면 디자인 메모

- 컨셉은 **"관동지방 포켓몬 연구소 책상 위에 펼쳐진 연구노트"**입니다. 대화는 연구 기록, 근거는 테이프로 붙인 참고 카드, 조건 탐색 결과는 도감 색인 카드입니다.
- **다크 모드는 만들지 않았습니다.** 종이 노트라는 세계관을 지키기 위한 선택입니다.
- 풀숲 포켓몬은 열 때마다 무작위로 나오고, 20~40초마다 1마리씩 화면 끝으로 나가면 새 친구가 반대쪽이나 같은 쪽 끝에서 들어옵니다. 같은 줄에서 마주치면 가끔 멈춰 "!" 하고 지나갑니다. 전설·환상의 포켓몬은 직접 골랐을 때만 나옵니다.
- 왼쪽 위 **도감 기계**는 고른 포켓몬의 움직이는 그림과 타입을 보여줍니다. 불 3개는 서버·도감 색인·연구소 열쇠(API 키) 상태(꺼진 불이 깜빡이면 문제)이고, 파란 렌즈는 답을 찾는 동안 깜빡입니다. 십자키(또는 십자키에 초점을 두고 화살표 키)로 앞뒤 번호의 포켓몬으로 넘어갑니다. 실물 도감 사진은 쓰지 않고 CSS로 다시 그렸습니다.
- 풀숲은 숲 가장자리를 옆에서 본 모습입니다: 먼 숲 → 땅(먼 곳일수록 밝은 세 띠, 풀포기·꽃·조약돌) → 나뭇잎 사이 햇빛 → 포켓몬 → 키 큰 풀 → 앞쪽 풀. 포켓몬과 같은 픽셀 그림체이고, 그림은 `python -m scripts.make_meadow_art` 로 직접 만들었습니다(`web/assets/`). 포켓몬이 걸으면 발밑에서 풀잎 조각이 튀고, 키 큰 풀은 가끔 바람에 흔들립니다.
- 운영체제의 "동작 줄이기"를 켜면 풀숲 포켓몬이 걷지 않고 제자리에 서 있고, 교대도 하지 않습니다. 햇빛·바람·풀잎 조각도 멈춥니다. "풀숲 멈추기" 버튼으로도 모두 멈출 수 있습니다.

## 6. 폴더 구조

```
data_prep/   도메인(포켓몬)에 묶인 코드: PokéAPI·위키백과 수집, 항목 텍스트, 단어 사전
services/    설정, 외부 호출 공용 함수(재시도·간격·User-Agent), LLM, 오류 문구, 로그
store/       Vector DB 컬렉션, 청킹·색인
rag/         프롬프트, 수집기, 검색·병합, LangGraph, 근거 정리
features/    조건 탐색, 배틀 상성 코치, 진화 안내
scripts/     색인, RAG 전후 비교, 검색 설정 비교, 위키 문서 조사
api/         FastAPI 서버
web/         직접 만든 화면 (HTML·CSS·JS)
docs/        요구사항 정의서, RAG 파이프라인 설계문서, 검증 결과, 비교 문서
```

## 7. 보안

- API 키는 `.env`에만 두고, 코드·화면·API 응답 어디에도 나오지 않습니다(NF2003, NF2004).
- 화면에는 오류 안내 문구만 보이고, 자세한 오류는 서버 로그(`logs/app.log`)에만 남습니다.
