# Pickthat — 수습 감정평가사 지원 정보 허브

**목적:** 13개 감정평가법인 비교, 공식 채용페이지/양식 접근, 자소서 작성 및 수습 감정평가사 채용 관련 신규 글 탐색.

## 파일 구성

- `index.html` — **CSS와 JavaScript까지 포함된 단일 HTML**. GitHub Pages 진입점.
- `scripts/collect_jobs.py` — GitHub Actions에서 실행되는 수집기(별도 상시 서버 불필요).
- `data/jobs.json` — 수집된 채용 *후보* 기록(깃허브에 누적 저장).
- `data/status.json` — 최근 수집 시도·오류 상태(배포 시 생성).
- `.github/workflows/update-and-deploy.yml` — 매일 4회 수집 후 GitHub Pages 배포.
- `tests/test_collector.py` — 수집기 로직 회귀 테스트.

## GitHub 배포 절차

연결된 사용자 이름은 `Regekels`, 요청된 저장소 이름은 `pickthat`입니다.

1. https://github.com/new?name=pickthat 로 이동하여 **Repository name: pickthat**을 설정하고 **Public**으로 생성합니다. `README` 자동 생성은 피하세요(충돌 방지).
2. 이 배포 ZIP을 압축 해제합니다. **ZIP 파일 하나를 업로드하지 말고 내부 파일과 `.github` 폴더를 그대로 업로드**해야 합니다. 일반적으로 `git` CLI가 가장 안정적입니다.
3. 압축 해제한 `pickthat` 폴더에서 Git Bash 또는 PowerShell을 열고 아래 명령을 실행합니다. (GitHub 인증이 선행되어야 합니다.)

   ```sh
   git init
   git branch -M main
   git add .
   git commit -m "Initial Pickthat site and scheduled recruitment collector"
   git remote add origin https://github.com/Regekels/pickthat.git
   git push -u origin main
   ```

4. GitHub의 `Settings` → `Pages` → `Build and deployment` → `Source`에서 **GitHub Actions**를 선택합니다.
5. `Actions` → `Update appraisal recruitment data and deploy Pages` → `Run workflow`를 한 번 실행합니다. `collect`, `deploy` 작업이 **success**인지 확인합니다.
6. 정상 배포 시 URL: `https://regekels.github.io/pickthat/` (정확한 주소는 Settings → Pages에서 확인).

**주의:** GitHub Actions가 처음 실행되었을 때 Pages 미활성화 오류가 뜨면 4단계를 먼저 수행해야 합니다. `configure-pages`의 `enablement` 옵션은 일반 `GITHUB_TOKEN`만으로 Pages를 자동 활성화할 수 없습니다.

## 자동 수집 방식과 정확성

- 13개 법인의 공개 공식 게시판을 주기적으로 방문해 수습 감정평가사 모집/채용 문구가 있는 링크를 후보로 추출합니다.
- Google 뉴스 RSS를 **보조 검색**으로 활용합니다. 일반 검색 2개와 법인별 검색 13개를 합쳐 총 15개 질의를 시도합니다. 제3자 링크와 공식 게시판 링크는 모두 **미검증 후보**로 표시하며, 모집중 여부/마감일/지원서 첨부파일을 **추측하지 않습니다**.
- 각 법인 사이트의 접근제한, 동적 렌더링, 자바스크립트, RSS 색인 누락 때문에 특정 채용공고가 탐지되지 않을 수 있습니다.
- 스케줄은 UTC 00:17, 06:17, 12:17, 18:17이며, 한국시간으로 **09:17, 15:17, 21:17, 03:17**입니다. 실제 실행은 GitHub 사정으로 지연되거나 건너뛸 수 있습니다.
- 각 수집 과정은 이전 기록을 지우지 않고 `data/jobs.json`에 누적합니다. 후보를 검토하고 공식 공고를 여는 것이 필요합니다.
- **공개 저장소에서는 코드와 후보 데이터가 모두 공개됩니다. 자기소개서 입력 내용은 브라우저 로컬 저장소에만 보관되며 서버에 저장되지 않습니다.**

## 로컬 테스트

```sh
python -m pip install -r scripts/requirements.txt
python -m unittest discover -s tests -v
python scripts/collect_jobs.py --dry-run
python -m http.server 8000
```

`http://localhost:8000/`에서 확인하세요. HTML을 직접 더블클릭하면 외부 로딩이 브라우저에서 차단되거나 로컬 JSON 불러오기가 실패할 수 있습니다.

## 유지보수

- 13개 대상 법인: 삼창, 경일, 미래새한, 대화, 하나, 제일, 태평양, 대일감정원, 나라, 중앙, 대한, 가온, 가람.
- 대화·경일·대일 등 일부 공식 주소는 웹 접근이나 검색 색인에 제약이 있어 확인된 공개자료의 주소를 사용했으며, 실제 채용 게시판을 확인한 것으로 간주하지 않습니다.
- 새로운 공식 채용 게시판을 확인했다면 `scripts/collect_jobs.py`의 `FIRMS` 내 공식 주소를 수정합니다.
- Github workflow의 최초 배포를 제외하고 추가 API 키는 필요하지 않습니다.
- 법인 공식 자기소개서 양식 다운로드는 `index.html`에 미리 확인된 링크만 제공합니다. 자동 수집기는 첨부파일을 임의로 추정하거나 내려받지 않습니다.
- 채용공고 공식 발표와 접수마감은 반드시 법인 원문을 우선합니다.
