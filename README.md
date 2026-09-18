# 서울과기대 LMS e-Class 커넥터

서울과학기술대학교 e-Class에서 본인에게 허용된 데이터를 읽는 Python 3.12 커넥터다. 비밀번호를 코드에 받거나 저장하지 않는다. 최초 로그인만 사용자가 Playwright Chrome에서 직접 수행하고, 이후 과목·공지·과제 조회는 확인된 내부 HTML/AJAX 요청을 `httpx`로 재현한다.

> [!IMPORTANT]
> 서울과학기술대학교 또는 e-Class 운영사에서 제작·승인·지원하는 공식 프로그램이 아닌 독립적인 커뮤니티 프로젝트다. 중요한 일정과 제출 여부는 반드시 e-Class 원문에서 최종 확인해야 하며, 사용자는 자신의 계정과 허용된 데이터에 대해서만 본인 책임으로 사용해야 한다. 자세한 내용은 [DISCLAIMER.md](DISCLAIMER.md)를 확인한다.

## 왜 유용한가

e-Class의 정보는 과목별 공지와 과제 화면에 흩어져 있다. 이 커넥터는 그 정보를 공통 데이터 형태로 읽어 Codex, Claude 같은 AI가 한 번에 검색·정리할 수 있게 한다.

```text
이번 스페인어 테스트 날짜·시간·장소 찾아줘.
모든 과목 공지를 확인해서 중간고사 일정만 표로 만들어줘.
현재 미제출 과제를 마감이 가까운 순서로 정리해줘.
공지 본문까지 확인해서 이번 주 준비물과 변경사항만 알려줘.
```

공지 제목의 짧은 미리보기만 보는 것이 아니라 전체 본문을 조회하므로, 시험 시간·건물·강의실·범위처럼 본문 안에만 적힌 정보도 찾을 수 있다. LMS에 없는 값은 추측하지 않고 확인 불가로 처리하는 것이 기본 원칙이다.

### 다른 도구와 조합하면 가능한 활용

다음 기능은 이 저장소에 캘린더 쓰기 기능이 내장됐다는 뜻이 아니다. MCP를 지원하는 AI의 예약 실행 기능이나 Google Calendar·Outlook 같은 별도 도구를 사용자가 연결했을 때 구성할 수 있는 활용 예시다.

- 매일 아침 새 공지, 미제출 과제, 임박한 마감만 자동 브리핑
- 마감까지 남은 기간과 제출 상태를 기준으로 긴급·중요·여유 분류
- 확인된 시험과 과제 일정을 개인 캘린더에 등록
- 이전 조회 이후 새로 생기거나 변경된 공지 탐지
- 여러 과목의 시험 날짜·시간·장소·범위를 하나의 표로 통합
- 캘린더의 기존 일정과 시험·과제 마감 충돌 확인

AI 요약과 자동화는 편의 기능이다. 원문 변경, 파싱 오류 또는 AI 해석 오류가 생길 수 있으므로 시험과 제출처럼 중요한 정보는 e-Class 원문을 최종 기준으로 삼는다.

## 지원 기능

- `get_courses()` — 현재 정규 수강 과목
- `get_notices(course_id=None)` — 과목별 또는 전체 공지의 게시일과 전체 본문
- `search_notices(query, course_id=None)` — 공지 본문 검색 및 결과별 게시일 반환
- `get_assignments(course_id=None)` — 과목별 또는 전체 과제, 마감 시각, 제출 여부
- `get_pending_assignments()` — 현재 미제출 과제
- `start_login()` — 세션 만료 시 대화 중 로그인용 Chrome 창 열기
- 사람이 읽는 CLI, JSON 출력, 읽기 전용 MCP 서버
- Codex와 Claude에서 사용하는 로컬 MCP 연동

2026-09-17 실제 로그인 세션에서 과목 6개, 공지 8개, 과제 5개 조회를 확인했다. 계정별 실제 데이터는 저장소나 문서에 기록하지 않는다.

## 한 줄 설치

필수 조건은 Python 3.12다. Codex 또는 Claude가 설치돼 있으면 설치 스크립트가 감지해서 자동 등록한다.

다운로드한 `seoultech_lms_connector` 폴더를 파일 탐색기에서 우클릭하고 **터미널에서 열기**를 누른 뒤 다음 한 줄만 실행한다.

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

이 명령은 다음 작업을 한 번에 처리한다.

1. Python 패키지와 의존성 설치
2. 현재 PC의 Python 경로를 사용해 Codex 플러그인 등록
3. 서울과기대 로고가 포함된 Claude Desktop `.mcpb` 확장 생성
4. Claude Code가 설치돼 있으면 사용자 범위 MCP 등록
5. 로그인 세션이 없으면 브라우저를 열어 최초 LMS 로그인 진행

비밀번호를 스크립트나 터미널에 입력하지 않는다. 설치 중 열린 브라우저에서 사용자가 직접 로그인한 뒤 LMS 메인 화면이 나타나면 터미널로 돌아와 Enter를 누른다.

Claude Desktop은 보안상 확장 파일을 운영체제에서 바로 실행하는 방식을 지원하지 않는다. 설치 스크립트가 표시한 `.mcpb` 파일을 Claude의 `설정 > 확장 프로그램 > 고급 설정 > 확장 프로그램 설치`에서 직접 선택하고 설치를 승인하면, 커넥터 목록에 서울과기대 로고가 적용된다. 설치 스크립트는 배포 폴더와 Codex 플러그인에도 같은 아이콘을 적용한다. 파일 탐색기에서 폴더 아이콘이 바로 갱신되지 않으면 `F5`를 누르거나 해당 폴더를 다시 열면 된다. 설치가 끝나면 Codex와 Claude를 완전히 종료한 뒤 다시 실행한다.

특정 연동이나 최초 로그인을 생략해야 할 때만 다음 옵션을 사용한다.

```powershell
.\install.ps1 -SkipCodex
.\install.ps1 -SkipClaude
.\install.ps1 -SkipLogin
```

개발용 설치는 `py -3.12 -m pip install -e .`로 할 수 있다.

기본값은 PC에 설치된 Chrome을 Playwright가 별도 프로필로 실행하는 방식이다. Chrome이 없다면 다음을 한 번 실행한다.

```powershell
python -m playwright install chromium
```

## 로그인 세션 갱신

Codex 또는 Claude에서 조회 중 세션 만료가 감지되면 AI가 `start_login` 도구를 호출해 로그인용 Chrome 창을 열 수 있다. 사용자가 그 창에서 직접 로그인하면 LMS 메인 화면을 감지해 세션을 저장하고 창이 자동으로 닫힌다. 그 뒤 같은 대화에서 원래 요청을 다시 실행하면 된다. 비밀번호는 AI에 전달되지 않는다.

터미널에서 직접 갱신하려면 다음 명령을 사용한다.

```powershell
seoultech-lms login
```

설치 때 최초 로그인을 마쳤다면 평소에는 다시 실행할 필요가 없다. 세션이 만료됐을 때만 다음 절차로 갱신한다.

1. 열린 Chrome에서 직접 로그인한다.
2. LMS 메인 화면이 완전히 나타나면 터미널로 돌아와 Enter를 누른다.
3. 세션은 `%LOCALAPPDATA%\seoultech-lms-connector\auth_state.json`에 저장된다. 프로젝트와 플러그인에는 복사되지 않는다.

세션이 만료되면 같은 명령으로 갱신한다. 비밀번호는 storage state에 저장하지 않고, 코드나 `.env`에서도 취급하지 않는다.

## CLI

```powershell
seoultech-lms doctor
seoultech-lms courses
seoultech-lms notices
seoultech-lms assignments
seoultech-lms pending
```

한 과목만 조회하려면 `courses` 출력의 ID를 사용한다.

```powershell
seoultech-lms notices --course-id A...
seoultech-lms assignments --course-id A...
```

AI 에이전트나 다른 프로그램에서는 JSON 출력을 사용한다.

```powershell
seoultech-lms courses --json
seoultech-lms notices --json
seoultech-lms assignments --json
seoultech-lms pending --json
```

## Codex에서 사용

설치 후 Codex를 새로 열어 플러그인을 로드하고 다음처럼 요청한다.

```text
@seoultech_c4t 현재 제출해야 하는 과제 정리해줘.
@seoultech_c4t 7일 안에 마감되는 미제출 과제 알려줘.
@seoultech_c4t 과목별 최근 공지를 요약해줘.
```

MCP 서버는 과목·공지·과제·미제출·마감일 조회 도구와 로그인 창을 여는 `start_login`을 공개한다. LMS 데이터 작업은 모두 조회 전용이며, 로그인 도구는 공식 로그인 페이지를 열고 인증 상태를 로컬에 저장하는 기능만 수행한다.

## Claude에서 사용

Claude Desktop 또는 Claude Code를 재시작한 뒤 자연어로 요청한다.

```text
서울과기대 LMS에서 현재 미제출 과제를 정리해줘.
전체 공지를 확인해서 중간고사 일정을 찾아줘.
7일 안에 마감되는 과제를 알려줘.
```

Claude Desktop에는 기본 MCP 연결이 먼저 등록되어 바로 사용할 수 있다. 로고와 설명이 표시되는 `.mcpb` 확장은 Claude의 확장 프로그램 설정에서 사용자가 직접 파일을 선택하고 승인하는 선택 기능이다. 확장을 아직 설치하지 않았더라도 기본 MCP 연결은 유지된다. Claude Code가 설치돼 있으면 같은 서버가 사용자 범위로 등록된다.

## 제거

Codex 플러그인, Claude MCP 설정과 Python 패키지를 제거하려면:

```powershell
.\uninstall.ps1
```

로컬 로그인 세션까지 함께 없애려면 명시적으로 옵션을 준다.

```powershell
.\uninstall.ps1 -RemoveAuth
```

평소 세션만 지우고 싶다면 `seoultech-lms logout`을 실행한다.

Claude Desktop 확장은 Claude의 `설정 > 확장 프로그램`에서 `seoultech_c4t`를 선택해 제거한다.

## 읽기 전용 보장

클라이언트는 조사로 확인된 조회용 endpoint만 allowlist로 허용한다. 과제 제출, 게시물/댓글 작성, 수정, 삭제, 파일 업로드 endpoint는 호출하지 않으며, allowlist 밖 요청은 네트워크 전송 전에 차단한다.

공지 상세 열람으로 읽음 상태 또는 조회수가 변경될 수 있으며, 이는 사용자가 허용한 조회 부작용이다. 공지 본문만 파싱하고 댓글 영역은 제외한다. 댓글·게시물 작성, 과제 제출, 파일 업로드, 수정 및 삭제 endpoint는 계속 허용하지 않는다.

## 비공식 프로젝트 및 책임 고지

- 이 프로젝트는 LMS 읽기 기능을 구현한 비공식 소프트웨어이며 학교의 보증이나 지원을 받지 않는다.
- LMS 구조 변경, 세션 만료, 네트워크 오류, 파싱 오류, AI의 잘못된 요약으로 일부 정보가 누락되거나 부정확할 수 있다.
- 사용자는 학교 규정, e-Class 이용 조건과 관련 법령을 확인하고 자신에게 접근 권한이 있는 데이터만 사용해야 한다.
- 과제 제출, 시험 응시, 마감 확인 등 최종 학사 책임은 사용자 본인에게 있다.
- `auth_state.json`은 로그인 세션을 포함하는 민감한 파일이다. 타인에게 전달하거나 GitHub에 업로드하면 안 된다.

전체 고지는 [DISCLAIMER.md](DISCLAIMER.md)에 정리돼 있다.

취약점이나 버그를 제보할 때 지켜야 할 민감정보 처리 방법은 [SECURITY.md](SECURITY.md)를 확인한다.

## 조사 도구

```powershell
python scripts/inspect_network.py
python scripts/inspect_network.py --json-only
```

Fetch/XHR의 method, URL, status, content type과 JSON 구조만 기록한다. Cookie, Authorization, CSRF, 세션, 토큰, 개인정보성 query/header는 마스킹되며 요청 본문은 저장하지 않는다.

## 테스트

```powershell
python -m unittest discover -s tests -v
python scripts/test_connector.py
```
