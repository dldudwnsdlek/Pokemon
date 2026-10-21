# CLAUDE.md — 이박사의 연구노트 (포켓몬 RAG)

어느 컴퓨터에서 작업하든 Claude가 같은 기준으로 일하도록 적어 둔 안내입니다.
SSAFY AI 코어 프로젝트 2회차 결과물: 관동 1세대 포켓몬 151마리에 대해 도감 데이터와 위키백과를 찾아 근거 번호를 붙여 답하는 RAG 서비스.

## 사용자와 말하는 법

- 사용자는 개발을 막 배우기 시작한 SSAFY 교육생입니다. **보고·커밋 설명·README는 전문용어 없이 쉬운 한국어**로 쓰고, 꼭 필요한 용어는 괄호로 한 줄 풀이합니다.
- 큰 작업이 끝나면 "무엇을 만들었는지 / 어떻게 확인하는지 / 다음 할 일" 순서로 짧게 보고합니다.

## 기준 문서와 정하는 법

- 원래 기준은 명세서 PDF 두 개(요구사항 정의서, 사용자가 쓴 구현 가이드라인)이며 **저장소에는 없습니다**. 저장소 안에서는 `docs/requirements.md`가 그 내용을 정리한 문서입니다.
- **가이드와 다르게 판단할 때는 구현 전에 사용자에게 묻습니다.** 결정한 내용은 `docs/requirements.md` 4장 "가이드와 다르게 정한 점" 표에 한 줄씩 남깁니다.
- **새 라이브러리를 추가하기 전에는 사용자에게 묻습니다.** (`requirements.txt`는 버전을 고정해 둠)
- 이미 정해진 것: 서비스 이름 「이박사의 연구노트」, 모델 `gpt-4.1-mini` / `text-embedding-3-small` (SSAFY GMS), 화면을 열면 포켓몬을 고르지 않은 "자유 질문"으로 시작.

## 실행과 확인

```bash
pip install -r requirements.txt
# .env 파일을 만들고 GMS_API_KEY, GMS_BASE_URL 을 넣는다 (.env.example 참고)
uvicorn api.server:app --reload     # http://localhost:8000 (직접 만든 화면)
streamlit run streamlit_app.py      # 필수 기능 확인용 간단 화면
python -m scripts.build_index       # 색인 (서버가 빈 도감으로 켜지면 자동으로도 함)
python -m scripts.run_checks        # 검증 항목 실행 → docs/evidence/checks.md (실제 API 호출, 비용 듦)
```

- 폴더 구조와 기능 번호(F2001~F2016)는 `README.md` 2장·6장, RAG 설계는 `docs/rag_design.md`.
- 실제 API를 부르는 확인(질문·색인·검증)은 사용자의 GMS 사용량을 쓰므로 필요한 만큼만 합니다.

## 비밀 값

- API 키는 `.env`와 배포 서비스의 환경변수에만 있습니다. **`.env`를 커밋하거나 키 값을 화면·로그·문서에 적지 않습니다.** (`.gitignore`에 `.env`, `chroma_db/`, `cache/`, `logs/`, `.venv/`)

## 배포 (Render 무료)

- GitHub `main` 브랜치에 push하면 Render가 자동으로 다시 배포합니다. 다른 브랜치는 배포되지 않습니다.
- 설정: Build `pip install -r requirements.txt`, Start `uvicorn api.server:app --host 0.0.0.0 --port $PORT`, 환경변수 `GMS_API_KEY`, `GMS_BASE_URL`, `PYTHON_VERSION=3.12.9`.
- 무료 서버는 메모리 512MB(지금 서버는 약 225MB 사용), 15분 쉬면 잠들고, 다시 켜질 때 파일이 처음 상태로 돌아갈 수 있습니다. 그래서 `api/server.py`가 켜질 때 도감이 비어 있으면 스스로 색인합니다(`/api/status`의 `building`). 질문하며 모은 위키 문서도 이때 사라집니다.
- 배포가 실패하면 Render는 이전 버전을 계속 보여줍니다. 무거운 라이브러리를 더하면 512MB를 넘지 않는지 확인합니다.

## 화면 (`web/`) 규칙

- 콘셉트: 모눈종이 연구노트 + 왼쪽 위 빨간 도감 기계 + 아래 픽셀 풀숲. 다크 모드는 만들지 않습니다.
- **색은 `web/css/tokens.css`의 값만** 씁니다. 새 색이 필요하면 토큰을 먼저 추가합니다.
- 픽셀 글꼴 크기: Galmuri11은 11·22·33px, Galmuri14는 14px만 (픽셀이 뭉개지지 않게).
- 빨간 주요 버튼(`button.primary`)은 한 화면에 하나. 테이프·기울기·그림자 장식은 첫 참고 카드에만.
- 풀숲 그림(`web/assets/forest.svg`, `grass-*.svg`, `ground-*.svg`, `sunlight.svg`)은 **손으로 고치지 말고** `scripts/make_meadow_art.py`를 고친 뒤 `python -m scripts.make_meadow_art`로 다시 만듭니다. 그림 크기는 칸 수의 정수 배로만 늘립니다.
- 움직임은 "동작 줄이기" 설정과 "풀숲 멈추기"에서 모두 멈춰야 합니다.
- 실물 도감 사진 같은 공식 그림은 넣지 않고 CSS로 다시 그립니다 (저작권).
- 화면 폭 기준: 1200px 이하 참고 카드가 답변 아래로, 900px 이하 도감 색인이 서랍으로, 높이 480px 이하 가로 화면에서는 풀숲을 숨김.

## 코드와 커밋

- 주석은 한국어, 주변 코드와 같은 밀도·말투로. 파일 줄바꿈은 LF.
- 커밋 메시지: `[태그] 한 줄 요약` + 빈 줄 + `-` 목록, 쉬운 한국어. 태그 예: `[디자인]`, `[배포]`, `[변경N]`, `[Mn]`(마일스톤).
- 작업을 시작하기 전에 `git pull`로 최신 코드를 받습니다 (여러 컴퓨터에서 작업함).

## 확인할 때 알아 둘 것

- 헤드리스 크롬 스크린샷에서는 풀숲 포켓몬이 걷지 않습니다(애니메이션 루프가 돌지 않음). 걷는 모습은 실제 브라우저에서 확인을 부탁합니다.
- 휴대폰 크기는 크롬 창이 일정 폭 아래로 줄지 않으므로, 같은 주소의 임시 페이지에 `<iframe width="390">`으로 넣어 찍습니다. 임시 파일은 확인 후 지웁니다.
