# 아프리카 디지털·AI 격차 DB — 작업 규칙

이 저장소에서 작업하는 사람과 AI(Claude 등)는 작업 전에 이 문서를 먼저 읽고 따른다.
AI를 저장소에 직접 연결하지 않고 쓰는 경우에도, 이 문서 전체를 대화에 붙여넣은 뒤 작업을 요청한다.

## 1. 프로젝트 개요

- 운영: 연세대학교 아프리카연구원 (Institute of African Studies, IAS)
- 목적: 아프리카 54개국의 디지털 전환과 AI 격차에 관한 자료(통계·문서·뉴스)를 자동으로 수집하고,
  국가·연도·주제·자료유형·출처·갱신시점 기준으로 연결된 데이터베이스로 축적·공개
- 근거: 연구계획서 「아프리카 디지털·AI 격차 DB 플랫폼」의 DB 스키마(그림 6-1)
- 사이트: GitHub Pages 정적 사이트 (서버 없음). 데이터는 JSON 파일로 저장하고, 수집은 GitHub Actions가 자동 실행

## 2. 파일 구조와 담당

| 경로 | 역할 | 담당 |
|---|---|---|
| `index.html` | 뉴스 페이지 (사이트 첫 화면) | **공유** — 아래 규칙 3 참고 |
| `fetch_news.py` | 뉴스 RSS 수집 → `articles.json` | 공유 |
| `articles.json` | 최근 2주 뉴스 (자동 생성, 직접 수정 금지) | 자동 |
| `data.html` | 지표 DB 페이지 | 지표 DB 담당 |
| `scripts/fetch_indicators.py` | World Bank 지표 수집 → `data/` | 지표 DB 담당 |
| `data/` | 지표 DB 데이터 (자동 생성, 직접 수정 금지) | 자동 |
| `data/manual/` | (예정) 직접 내려받은 지표 CSV (EGDI, AI 준비도 지수 등) | 지표 DB 담당 |
| `scripts/fetch_reports.py`, `reports.json`, `reports.html` | (예정) 싱크탱크 보고서 수집·게시 | 보고서 담당 |
| `.github/workflows/update.yml` | 매일 09:00 KST 뉴스 수집 | 공유 |
| `.github/workflows/indicators.yml` | 매월 1일 지표 수집 | 지표 DB 담당 |

새 기능은 **기존 파일을 크게 고치기보다 새 파일로 추가**하는 것을 원칙으로 한다.

## 3. 공동 작업 규칙

1. **항상 최신본을 기준으로 수정한다.** 웹에서 파일을 업로드하는 경우, 올리기 직전에 GitHub에서 최신 파일을 다시 받아 그 위에 수정한다. 예전 파일로 덮어쓰면 다른 사람의 수정이 사라진다.
2. **`index.html`은 필요한 부분만 최소로 수정한다.** 수정 전에 팀 단톡에 알리고, 한 번에 한 사람만 고친다. 다른 페이지로 연결하는 버튼은 상단 `<div class="hnav">` 안에 한 줄로 추가한다.
3. **자동 생성 파일(`articles.json`, `data/*.json`, `data/csv/*`)은 손으로 고치지 않는다.** 수집 스크립트를 고친다.
4. **새 워크플로(`.github/workflows/*.yml`)를 만들 때**는 push 직전에 `git pull --rebase`를 넣어, 다른 자동 작업과 동시에 실행돼도 충돌하지 않게 한다. 실행 시각은 기존 작업(매일 00:00 UTC, 매월 1일 01:17 UTC)과 겹치지 않게 정한다.
5. **수집 스크립트는 Python 표준 라이브러리만 사용한다** (`pip install` 없이 실행되도록). 외부 패키지가 꼭 필요하면 워크플로에 설치 단계를 추가하고 팀에 알린다.
6. **수집이 실패해도 기존 데이터를 지우지 않는다.** 실패 시 이전 데이터를 유지하도록 작성한다 (`scripts/fetch_indicators.py` 참고).
7. 커밋 메시지는 무엇을 바꿨는지 한 줄로 쓴다. 예: `보고서: ISS Africa RSS 추가`, `지표 DB: EGDI 추가`

## 4. DB 스키마 (연구계획서 그림 6-1 기준)

모든 자료는 아래 공통 키로 연결한다.

- `Country_ID`: ISO 3자리 국가 코드 (예: `KEN`, `NGA`). 여러 나라를 다루는 자료는 `AFR`(아프리카 대륙 전체) 또는 해당 국가 코드 목록을 사용
- `Year`: 자료 기준 연도 (정수)
- `Source_ID`: `source_table`의 출처 ID

### country_table — `data/country.json`
`Country_ID`, `Country_Name`(한글), `Country_Name_EN`, `Region`(AU 지역: North/West/Central/East/Southern), `Income_Group`

### digitalx_table (디지털 전환 지표) — `data/digitalx.json`
`Country_ID`, `Year`, `Indicator_Category`, `Indicator_Code`, `Indicator_Name`, `Value`, `Unit`, `Source_ID`

### aidivide_table (AI 격차 지표) — `data/aidivide.json`
`Country_ID`, `Year`, `AI_Dimension`, `Indicator_Code`, `Indicator_Name`, `Value`, `Unit`, `Source_ID`

### source_table (자료 출처) — `data/source.json`
`Source_ID`, `Source_Name`, `Source_Type`, `Collection_Date`, `Update_Date`, `Verification_Status`, `Reliability_Level`, `Source_URL`, `License`, `License_URL`

### text_table (비정형 자료: 뉴스·보고서·정책문서) — 보고서 담당이 우선 구현
| 필드 | 내용 |
|---|---|
| `Document_ID` | 고유 ID. 원문 URL을 기준으로 만들어 중복 수집을 막는다 |
| `Country_ID` | 관련 국가 코드 목록 (예: `["KEN"]`, `["AFR"]`) |
| `Year` | 발행 연도 |
| `Document_Type` | `news` / `report` / `policy` / `paper` 중 하나 |
| `Title` | 원문 제목 |
| `Institution` | 발행 기관 (예: Brookings, ISS Africa) |
| `Authors` | 저자 (없으면 빈 값) |
| `Published_Date` | 발행일 (YYYY-MM-DD) |
| `URL` | 원문 링크 |
| `Source_ID` | 출처 ID |
| `Keywords` | 매칭된 키워드 목록 |

### text_summary_table (AI 요약·태깅 결과) — AI API 도입 후 구현
`Document_ID`, `Keywords`, `Topics`, `Summary_Short`, `Summary_Long`, `LLM_Model`, `Prompt_Version`, `Extraction_Date`, `Validation_Status`(`auto` / `reviewed` / `rejected`)

### text_variable_table (문서에서 추출한 의미론적 변수) — 향후 구현
`Document_ID`, `Variable_Name`(예: `has_ai_strategy`, `regulation_level`, `priority_sectors`), `Value`, `Evidence`(근거 문장과 쪽수), `Validation_Status`

## 5. 수집 범위와 키워드

- 우선 주제: 아프리카의 **AI·디지털 전환**. 그 외에도 시사성 있는 아프리카 관련 자료는 폭넓게 수집한다.
- 공신력 있는 출처 위주: 국제기구, 정부·공공기관, 대학·싱크탱크, 주요 언론
- 디지털·AI 관련 기본 키워드 (제목·요약에서 대소문자 구분 없이 매칭):
  `AI`, `artificial intelligence`, `digital`, `digitalization`, `digital transformation`, `internet`, `broadband`,
  `connectivity`, `data`, `fintech`, `mobile money`, `e-government`, `cybersecurity`, `technology`, `ICT`, `startup`
  (`AI`는 단어 경계로 매칭해 `said`, `Kenya-Rwanda` 같은 오탐을 막는다)

## 6. 저작권·게시 원칙

- **원문 전체나 문단을 복제·번역해 게시하지 않는다.** 제목, 발행 기관, 날짜, 원문 링크, 그리고 짧은 요약만 게시한다.
- 요약은 RSS·초록 등 공개된 설명을 바탕으로 **새로 작성한 2~3문장**으로 하며, 원문 문장을 그대로 옮기지 않는다.
- 기사·보고서의 이미지는 게시하지 않는다.
- AI가 만든 요약에는 "AI 생성 요약" 표시를 붙이고 `Validation_Status`로 검수 여부를 관리한다.
- 대용량 원문 PDF는 저장소에 올리지 않고 연구원 Dropbox에 보관한 뒤 링크만 기록한다.
- **새 데이터 출처를 추가할 때는 이용 조건(라이선스)을 먼저 확인**하고 `source_table`의 `License`, `License_URL`에 기록한다.
  재배포가 허용되지 않거나 조건을 확인할 수 없는 자료는 수치를 게시하지 않고 링크만 건다.
  - World Bank: CC BY 4.0 (World Bank가 보증하는 것처럼 표현 금지)
  - Oxford Insights Government AI Readiness Index: CC BY-SA 4.0 (가공 데이터도 같은 조건으로 공개)

## 7. 사이트 디자인 규칙

- 기존 `index.html`, `data.html`의 색상 변수(`--bg`, `--accent` 등)와 글꼴(DM Sans / DM Serif Display)을 그대로 쓴다.
- 새 페이지는 상단 헤더 구조를 `data.html`과 똑같이 하고, 다른 페이지로 가는 버튼을 포함한다.
- 외부 라이브러리는 CDN으로만 불러온다 (현재 Chart.js 4.4.1 사용).
