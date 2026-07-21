# Sonol Higgsfield

[한국어](README.ko.md) | [English](README.md)

영상 아이디어를 서로 단절된 생성 결과 모음이 아니라, 검토하고 통제할 수
있는 하나의 Higgsfield 영상 제작 프로젝트로 완성합니다.

Sonol Higgsfield는 Codex CLI, Claude Code 및 Agent Skills 호환 에이전트를
위한 제작 스킬입니다. 요구사항, 스토리보드, 촬영 문법, 레퍼런스, 예산
승인, 영상 생성, 연속성 검사, 오디오 분기, 선택적 보정, 후반 작업과
납품까지 멀티숏 영화·광고·스토리·캠페인·내레이션 영상의 전체 흐름을
관리합니다.

> 이 저장소는 Higgsfield 공식 CLI를 기반으로 만든 커뮤니티 제작
> 스킬입니다. Higgsfield의 공식 제품은 아닙니다.

## 자동 설치

Codex CLI와 Claude Code 사용자 전역에 동시에 설치합니다.

<!-- markdownlint-disable MD013 -->

```bash
npx --yes skills@latest add volition79/sonol-higgsfield --skill sonol-higgsfield --global --agent codex --agent claude-code --copy --yes
```

한 에이전트에만 설치하려면 다음 명령을 사용합니다.

```bash
# Codex CLI
npx --yes skills@latest add volition79/sonol-higgsfield --skill sonol-higgsfield --global --agent codex --copy --yes

# Claude Code
npx --yes skills@latest add volition79/sonol-higgsfield --skill sonol-higgsfield --global --agent claude-code --copy --yes
```

<!-- markdownlint-enable MD013 -->

이 저장소는 Skills CLI에서 `sonol-higgsfield`라는 유효한 스킬 한 개로
인식됩니다. 두 에이전트 동시 설치 명령도 격리된 새 사용자 환경에서 실제
검증했습니다. 설치 후에는 Codex 또는 Claude Code를 새 세션으로
시작해야 스킬을 안정적으로 인식합니다.

자동 설치에 필요한 항목:

- Node.js 18 이상과 `npx`
- Git
- Codex CLI 또는 Claude Code

## 전체 실행 환경 준비

스킬 설치는 에이전트에게 제작 절차를 제공하는 단계입니다. Higgsfield 공식
CLI 설치와 계정 인증은 별도로 필요합니다.

```bash
# Windows, macOS, Linux 공통 Higgsfield CLI 설치
npm install -g @higgsfield/cli

# 브라우저 또는 기기 인증
higgsfield auth login

# 필요한 경우 결제 워크스페이스 선택
higgsfield workspace list
higgsfield workspace set <workspace_id>

# 현재 계정과 워크스페이스 확인
higgsfield account status
higgsfield workspace status
```

전체 제작 기능을 사용하려면 다음 환경도 준비하는 것이 좋습니다.

- Python 3.10 이상. 개발 및 검증 환경은 Python 3.12
- 영상 검사·트리밍·오디오·전환·조립용 FFmpeg와 FFprobe
- 한글 OCR이 필요한 경우 한국어(`kor`) 데이터가 포함된 Tesseract
- 활성화된 Higgsfield 계정, 선택된 워크스페이스, 승인할 생성 작업에
  충분한 크레딧
- 화면상 대사 또는 외부 내레이션이 필요할 때 ElevenLabs API 키와 승인된
  음성 ID
- Higgsfield MCP는 선택 사항. 이 스킬은 라이브 CLI 스키마를 최종 실행
  계약으로 사용하므로 MCP 없이도 작동

공식 설치 자료:

- [Higgsfield CLI](https://higgsfield.ai/cli)
- [Higgsfield CLI 소스와 운영체제별 설치 방법](https://github.com/higgsfield-ai/cli)
- [Skills CLI](https://github.com/vercel-labs/skills)

## 이 스킬이 필요한 이유

### 클립이 아니라 한 편의 영상을 만듭니다

스토리 상태, 인물, 장소, 소품, 카메라 방향, 오디오와 편집 연결 지점을
숏과 숏 사이에서 유지합니다. 화면 감독이 이전 승인 영상의 마지막 프레임
연결, 시작·끝 브리지, 편집 컷, 장면 재설정 중 하나를 선택하므로 앵글이
바뀌는 컷까지 억지로 모핑하지 않습니다.

### 일반인의 표현을 전문 촬영 문법으로 바꿉니다

“정체가 드러나는 순간을 불안하게 보여줘”, “공간 방향을 잃지 않고
인물을 따라가 줘”처럼 평범한 말로 요청할 수 있습니다. 스킬은 148개 영상
기법 카탈로그를 검색해 설명 가능한 카메라·연출 대안을 제시하고, 선택한
문법을 현재 라이브 생성 모델에 맞게 컴파일합니다.

### 빠르게 크레딧을 통제합니다

유료 요청 전에 모델의 라이브 계약, 계정 크레딧, 워크스페이스, 레퍼런스
제한과 사용자가 승인한 프로젝트 총상한을 확인합니다. 느린 라이브 비용
조회와 3단계 견적은 만들지 않습니다. 동일 조건의 실제 사용 기록이 있을
때만 초당 실사용 크레딧으로 참고 산술값을 보여주고, 근거가 없으면 추정
불가라고 표시합니다. 사용자의 침묵은 승인으로 처리하지 않습니다.

### Seedance 2.0을 무리하게 사용하지 않습니다

짧은 프로토타입에서 하나의 주 행동과 하나의 주 카메라 움직임을 기본으로
합니다. 타임코드 멀티숏 생성은 전체 클립을 다시 생성해야 할 위험을
사용자가 받아들였을 때만 실험적으로 사용합니다.

각 유료 영상에는 시작 이미지 하나만 전달합니다. 첫 영상의 시작 이미지만
미리 만들고, 이후 영상은 승인된 경계 프레임을 이어받거나 감독이 선택한
컷에서 새 시작 이미지를 즉시 합성합니다. 컴파일러는 경쟁하는 이미지
레퍼런스를 차단하고 핵심 불변조건을 최대 3개로 제한합니다. FFmpeg는 마지막
0.5초의 후보 8장을 비교해 블러 점수가 가장 낮은 프레임을 선택합니다.
스키마 v6는 첫 프레임 QC, 경계 분석 기록, 잠긴 스토리 고정점과 이전 영상의
사용자 승인이 있어야 다음 영상을 생성하도록 강제합니다.

### 긴 프로젝트를 중단했다가 다시 시작할 수 있습니다

로컬 제작 폴더와 대시보드에 요구사항, 버전, 승인, 생성 작업, 비용, QC
상태와 이력을 보존합니다. 다음 세션은 채팅 기억을 재구성하지 않고 기록된
제작 상태에서 바로 이어갑니다.

### 실패한 부분만 선택적으로 고칩니다

비용이 큰 재생성 전에 편집점, J/L 컷, 공통 앰비언스, 색보정, 속도 조정,
컷어웨이, 브리지 숏과 전환 영상을 먼저 검토합니다. 재생성이 필요해도
전체 영상을 다시 만드는 대신 문제가 있는 숏을 대상으로 합니다.

### 한글과 오디오를 후반 작업의 일부로 관리합니다

중요한 한글 텍스트는 OCR 증거와 사람의 시각 검수를 함께 사용합니다.
화면상 대사는 깨끗한 ElevenLabs V3 음성을 생성 조건용 참조로 먼저
확정합니다. 생성 전에 음성 연기, 전체 앰비언스, 화면 동기 효과음, 음악
여부와 금지 소리를 하나의 압축된 Seedance 음향 지시로 기록합니다.
Seedance가 영상과 전체 프로덕션 사운드를 함께 생성하고, QC를 통과한
네이티브 트랙은 창작적 후반 덧입힘 없이 보존합니다. 화면 밖 내레이션과
무대사 후반 제작 숏은 기존의 분리된 피니싱 경로를 사용합니다.

## 전체 제작 흐름

1. 인터뷰를 진행하고 요구사항을 확정합니다.
2. 지속 가능한 제작 상태와 대시보드를 만듭니다.
3. 타임코드 대본, 장면, 에셋과 숏 계획을 작성합니다.
4. 각 숏의 촬영 문법을 선택하고 검증합니다.
5. Higgsfield 라이브 스키마와 크레딧을 확인하고 프로젝트 총상한을 승인합니다.
6. 애니매틱과 레퍼런스를 승인합니다.
7. 범위가 명확한 숏을 한 번에 하나씩 생성합니다.
8. 연속성, 오디오, 텍스트와 기술 품질을 즉시 검토합니다.
9. 문제가 있는 부분만 보정하거나 선택적으로 재생성합니다.
10. 승인된 버전을 조립하고 후반 작업·감사·납품을 완료합니다.

## 사용 시작하기

설치 후 새 에이전트 세션에서 자연스럽게 요청하면 됩니다.

> sonol-higgsfield를 사용해서 60초짜리 시네마틱 브랜드 영상을 기획해 줘.
> 먼저 나를 인터뷰하고, 스토리보드와 프로젝트 크레딧 총상한을 보여준 뒤
> 내가 승인하기 전에는 유료 생성을 실행하지 마.

또는 기존 제작을 이어갈 수 있습니다.

> 기존 Sonol Higgsfield 제작 프로젝트를 다시 열고 대시보드를 보여줘.
> 다음 숏 진행을 막고 있는 승인 또는 QC 단계를 알려줘.

에이전트는 `sonol-higgsfield`를 불러오고 라이브 CLI 계약을 확인한 뒤,
유료 생성이 아니라 요구사항 인터뷰 또는 저장된 제작 상태부터 시작해야
합니다.

## 설치 확인

```bash
npx --yes skills@latest list --global --agent codex --agent claude-code
higgsfield --version
higgsfield account status
higgsfield workspace status
```

다음 파일 중 해당 에이전트 경로가 존재하는지 확인할 수도 있습니다.

- Codex: `~/.agents/skills/sonol-higgsfield/SKILL.md`
- Claude Code: `~/.claude/skills/sonol-higgsfield/SKILL.md`

Skills CLI는 공통 원본과 에이전트별 링크 또는 복사본을 함께 관리할 수
있습니다. 위 명령은 심볼릭 링크 권한이 환경마다 다른 Windows에서도
예측 가능하게 설치되도록 `--copy`를 사용합니다.

## 업데이트

동일한 자동 설치 명령을 다시 실행한 뒤 에이전트를 새 세션으로
시작합니다.

<!-- markdownlint-disable MD013 -->

```bash
npx --yes skills@latest add volition79/sonol-higgsfield --skill sonol-higgsfield --global --agent codex --agent claude-code --copy --yes
```

<!-- markdownlint-enable MD013 -->

## 수동 설치

Node.js를 사용할 수 없다면 해당 에이전트의 사용자 스킬 폴더에 저장소를
복제합니다.

```bash
# Codex CLI
git clone https://github.com/volition79/sonol-higgsfield.git ~/.agents/skills/sonol-higgsfield

# Claude Code
git clone https://github.com/volition79/sonol-higgsfield.git ~/.claude/skills/sonol-higgsfield
```

Windows PowerShell에서도 `$HOME/.agents/skills/...`와
`$HOME/.claude/skills/...`는 현재 Windows 사용자 프로필 아래의 경로로
해석됩니다.

## 저장소 구조

```text
SKILL.md       에이전트 제작 절차와 반드시 지켜야 하는 승인 게이트
scripts/       제작 상태, 대시보드, 비용, 촬영 문법, QC 및 실행 도구
references/    촬영 문법, Seedance, 연속성, 오디오, 모델 분기 및 정책
assets/        로컬 제작 대시보드 템플릿
tests/         결정론적 워크플로 및 실행 계약 테스트
```

## 반드시 알아야 할 한계

- 생성 모델이 모든 카메라 또는 연기 지시를 그대로 지킨다고 보장할 수는
  없습니다.
- 검증된 프롬프트와 촬영 문법은 통제력을 높이지만 결과를 보증하지
  않습니다.
- MCP는 현재 세션에서 실제 도구 스키마가 확인될 때만 사용합니다.
- Higgsfield 유료 작업은 크레딧을 사용합니다. 이 스킬은 프로젝트 총상한을
  승인받지만 정확한 라이브 견적을 의도적으로 생략하므로, 한 작업이 남은
  상한을 초과할 수 있고 이미 제출된 작업은 되돌릴 수 없습니다.
- OCR, 음성 전사와 자동 검사는 증거이며 사람의 시각·편집·연속성 검수를
  대신하지 않습니다.
