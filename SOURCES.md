# 데이터·문서 출처와 이용 조건 (NF2007)

이 프로젝트는 **SSAFY 교육용 비영리 프로젝트**입니다. 공개 배포나 상업적 사용을 하지 않습니다.
포켓몬은 Nintendo·Creatures·GAME FREAK의 상업 IP이며, 모든 권리는 원작사에 있습니다.

| 출처 | 쓰는 것 | 이용 조건 | 수집일 |
|---|---|---|---|
| [PokéAPI](https://pokeapi.co/) (`pokeapi.co/api/v2`) | 1세대 151마리 데이터(이름·분류·타입·특성·키·몸무게·능력치·도감 설명), 타입 상성, 진화 계통 | 무료 공개 API, 인증 키 없음. **공정 이용 규칙**: 받은 응답을 로컬에 저장해 다시 쓸 것 → `cache/pokeapi/`에 모두 저장, 두 번째 실행부터 외부 호출 0회 | 2026-10-21 |
| [PokéAPI sprites](https://github.com/PokeAPI/sprites) (GitHub) | 화면에 보이는 포켓몬 그림 (5세대 움직이는 GIF, 실패 시 정지 그림) | 주소로만 불러오고 저장소에 복사하지 않음. 그림 저작권은 Nintendo·Creatures·GAME FREAK. 교육용 비영리 사용 | (불러오기만 함) |
| [PokéAPI cries](https://github.com/PokeAPI/cries) (GitHub) | 실루엣 퀴즈의 울음소리 (옛 게임 8비트 소리, 없으면 요즘 소리) | 그림과 같이 주소로만 불러오고 저장소에 복사하지 않음. 소리 저작권은 Nintendo·Creatures·GAME FREAK. 교육용 비영리 사용 | (불러오기만 함) |
| [한국어 위키백과](https://ko.wikipedia.org/) (MediaWiki API) | 외부 문서 본문 | **CC BY-SA 4.0**. 근거마다 문서 제목과 원문 링크(`https://ko.wikipedia.org/?curid=<pageid>`)를 표시. 요청에 연락처가 든 User-Agent를 넣고, 호출 사이 1초 간격·최대 3회 재시도 규칙을 지킴 | 문서별 `collected_at` (청크 메타데이터와 `cache/wiki/<pageid>.json`에 기록) |
| [Galmuri11·Galmuri14](https://github.com/quiple/galmuri) | 제목·라벨·버튼 글꼴 (jsDelivr `galmuri@2.40.3`) | SIL Open Font License 1.1 | — |
| [Pretendard](https://github.com/orioncactus/pretendard) | 본문 글꼴 (jsDelivr `orioncactus/pretendard@v1.3.9`) | SIL Open Font License 1.1 | — |
| [Nanum Pen Script](https://fonts.google.com/specimen/Nanum+Pen+Script) | 손글씨 메모 (Google Fonts) | SIL Open Font License 1.1 | — |

## 외부 호출 예절 (NF2006) 지키는 방법

- 모든 외부 호출(PokéAPI, 위키백과, LLM)은 `services/http.py` 한 곳을 거칩니다.
- User-Agent: `PokemonRAGStudy/1.0 (SSAFY education project; youngjoon4u@gmail.com)`
  - 가이드에는 한글 "SSAFY 교육 프로젝트"로 되어 있었지만, HTTP 헤더에는 영문만 넣을 수 있어 영문으로 적었습니다.
- 호출 사이 `request_interval_sec`(1초) 간격, 실패하면 1초 → 2초 → 4초 기다리며 최대 3번 다시 시도합니다.
- 이미 수집한 `포켓몬ID|검색어`는 다시 수집하지 않습니다 (`cache/collected_queries.json`).

## 제출물에서 빠지는 것

`cache/`(원본 응답), `chroma_db/`(색인), `.env`(API 키), `.venv/`는 제출 zip에 넣지 않습니다.
색인은 `python -m scripts.build_index`로 다시 만들 수 있습니다.
