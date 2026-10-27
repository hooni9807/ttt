# TTT — 탁구 스윙 3D 분석

폰으로 찍은 스윙 영상 하나를 받아 3D 자세를 복원하고, 스윙 수치를 계산합니다.

- **3D 스윙**: MediaPipe Pose로 프레임마다 관절 33개의 3D 좌표를 추정합니다.
- **궤적·임팩트**: 손목 궤적을 속도별 색으로 표시하고, 가장 빠른 순간을 임팩트로 잡습니다.
- **힘 전달**: 골반 → 어깨 → 팔꿈치 → 손목 순서로 최고 속도에 도달하는지 확인합니다.
- **프로 비교**: 백스윙, 임팩트, 피니시마다 팔꿈치·무릎·몸통 꼬임 각도를 프로 범위와 비교합니다.
- **스윙 면 기울기**: 백스윙~피니시 손목 궤적에 맞춘 평면이 바닥과 이루는 각도(0° 수평, 90° 수직). 프로 범위가 있으면 "9° 더 눕힘"처럼 차이를 알려 줍니다.
- **스윙 점수(항목마다 10점 만점, 참고용)**: 힘 전달(골반→어깨→팔꿈치→손목 3구간 중 순서가 맞는 비율), 프로 범위(범위 안에 든 항목 비율), 손목 속도(프로 기준 대비, 넘으면 만점)를 각각 10점 만점으로 매기고, 종합 점수는 기준이 있는 항목들의 평균입니다.

## 웹에서 쓰기

https://hooni9807.github.io/ttt/ 에서 스윙 영상을 올리면 3D 자세, 프로 기준 비교, 피드백을 바로 보여 줍니다. 영상은 서버로 가지 않고 브라우저 안에서 MediaPipe로 분석됩니다(`index.html` + `analyze.js`). "이미지로 저장"은 결과 화면 전체를 한 장의 PNG로, "영상으로 저장"은 스윙 구간을 스켈레톤·궤적을 입혀 지금 고른 재생 속도(기본 0.25배 슬로모션)로 녹화해 저장합니다. 아이폰은 공유 창에서 "이미지/비디오 저장"을 누르면 사진 앱에, 안드로이드는 다운로드 폴더(갤러리의 다운로드 앨범)에 저장됩니다. "결과 저장"으로 받은 프로 스윙 분석은 `make_ranges.py`로 기준 범위를 만들 때 쓸 수 있습니다.

## 명령줄로 실행

[uv](https://docs.astral.sh/uv/)가 필요합니다. 처음 실행할 때 포즈 모델(약 30MB)을 내려받습니다.

```bash
uv run swing.py 내스윙.mp4            # 오른손잡이
uv run swing.py 내스윙.mp4 --left     # 왼손잡이
uv run swing.py 내스윙.mp4 --ref my_pro.json      # 직접 만든 프로 범위와 비교
```

실행하면 리포트와 피드백을 출력하고 `내스윙.json`을 저장합니다. 웹 페이지 첫 화면 아래의 "저장한 결과 열기"로 이 파일을 열면 3D로 돌려 볼 수 있습니다.

테스트: `uv run test_swing.py` (node 가 있으면 웹용 `analyze.js` 결과도 Python 과 대조합니다)

피드백 문구는 `tips.json`에서 고칠 수 있습니다.

## 프로 기준값

`pro_ranges.json` 은 공개 데이터셋 **Table Tennis Forehand Stroke Mediapipe Datasets** (Lyu et al. 2025, [figshare 28881086](https://figshare.com/articles/dataset/Table_Tennis_Forehand_Stroke_Mediapipe_Datasets/28881086), CC BY 4.0)의 도 대표 여자 선수 34명 포핸드 340개를 TTT 와 같은 코드로 분석한 평균 ± 표준편차입니다. 원 논문: Lyu, Duan, Yang & Ye (2025), *Development of a MediaPipe-based framework for biomechanical quantification of table tennis forehand strokes*, Frontiers in Sports and Active Living.

- 이 데이터에서 TTT 의 임팩트 판정은 데이터에 표시된 실제 임팩트와 중앙값 2프레임(20ms) 차이였습니다(96%가 3프레임 이내).
- 데이터는 오른쪽 앞 45°에서 100fps 로 찍었습니다. 사용자 영상의 각도가 다르면 차이가 날 수 있어 참고용입니다.
- 다시 만들기: figshare 에서 파일을 `data/figshare/` 에 받은 뒤 `uv run --with pandas --with openpyxl build_standard.py data/figshare`
- 같은 스크립트가 자세 → 공 속도를 맞히는 모델(`ballspeed_model.json`)도 학습하지만, 선수 단위 검증 오차가 3.1 km/h 로 평균만 찍는 것(3.3 km/h)과 큰 차이가 없어 사이트에는 쓰지 않습니다. 가장 큰 관련 요인은 손목 속도였습니다.
- 직접 찍은 프로 영상으로 기준을 만들려면 `make_ranges.py` 를 씁니다.

## 촬영 팁

- 폰을 세워 고정하고, **몸 전체**가 화면에 나오게 찍어 주세요.
- 스윙이 빨라서 **60fps 이상**, 가능하면 슬로모션(120~240fps)으로 찍는 게 좋습니다.
- 영상 하나에 스윙 **한 번**만 담아 주세요. 영상은 **최대 15초**까지만 분석하고, 2~5초면 충분합니다.

## 한계와 다음 단계

- 카메라 한 대로 추정한 깊이(z)는 오차가 큽니다. 더 정확한 모델로는 WHAM, 4D-Humans 등이 있습니다.
- 라켓과 공은 추적하지 않습니다. 추적하려면 객체 검출 모델(YOLO 등)을 따로 학습시켜야 합니다.
- AI 코치는 아직 없습니다. 리포트를 LLM(Claude API)에 넣어 교정 문구를 생성하는 방식으로 붙일 수 있습니다.

## 데이터 보태기 (Firebase)

결과 화면의 "분석 개선에 데이터 보태기"는 사용자가 동의하고 직접 보낼 때만 **스윙 구간의 관절 좌표와 분석 수치**를 Firebase Cloud Firestore 에 저장합니다. 영상·사진·식별 정보는 보내지 않습니다. 안내문은 `privacy.html` 입니다.

`firebase-config.js` 가 `null` 이면 이 기능은 화면에 나오지 않습니다. 켜는 방법:

1. [Firebase 콘솔](https://console.firebase.google.com)에서 프로젝트를 만들고, **웹 앱**을 추가합니다.
2. **Firestore Database** 를 만듭니다. 위치는 `asia-northeast3 (서울)`, 모드는 **프로덕션 모드**로 고릅니다. (`privacy.html` 에 서울 리전이라고 적혀 있습니다. 다른 곳을 고르면 안내문도 고쳐야 합니다.)
3. Firestore → **규칙** 탭에 `firestore.rules` 내용을 붙여 넣고 게시합니다. 브라우저는 새 문서 쓰기만 할 수 있고 읽기·수정·삭제는 막힙니다.
4. 프로젝트 설정 → 내 앱(웹)의 `firebaseConfig` 값을 `firebase-config.js` 의 `null` 자리에 붙여 넣고 push 합니다.

저장 형식(컬렉션 `swings`, 문서 1개 = 스윙 1개): `fps`, `hand`, `window`(원본 프레임 중 저장한 구간), `metrics`(분석 결과), `frames`(3D 좌표 JSON 문자열), `frames2d`(영상 위 2D 좌표 JSON 문자열), `createdAt`, `consent`, `app`.
모인 데이터는 Firebase 콘솔이나 서버용 관리자 SDK 로 내려받습니다.

## 데이터셋 점수 매기기와 평가 AI 학습

1. **관리자 등록**: 사이트에서 Google 로그인을 한 번 한 뒤, Firebase 콘솔 → Firestore 에 `admins` 컬렉션을 만들고 문서 ID 를 내 계정 UID(Authentication → 사용자 목록에 있음)로 추가합니다. 필드는 아무거나(예: `name`) 하나 있으면 됩니다.
2. **점수 매기기**: https://hooni9807.github.io/ttt/label.html 에서 데이터셋 스윙을 하나씩 재생해 보고 0~10점(0.5 단위)과 메모를 저장합니다. 다시 열면 고칠 수 있습니다. 단축키 ←/→ 점수, Enter 저장하고 다음, Space 재생. 관리자만 데이터셋을 보고 점수를 쓸 수 있습니다(`firestore.rules`).
3. **내려받기**: "점수 매긴 데이터 내려받기"로 `ttt-labels-날짜.json` 을 받습니다.
4. **학습**: `uv run train_scorer.py ttt-labels-날짜.json -o scorer.json`
   - 구간별 각도 9개, 손목 속도, 스윙 면, 힘 전달 순서·타이밍으로 사람 점수를 맞히는 릿지 회귀를 학습합니다.
   - 하나씩 빼고 맞혀 본 평균 오차를 "모두 평균으로 찍었을 때"와 비교해 출력합니다. 최소 10개, 믿을 만하려면 50개 이상 필요합니다.

## AI 코치 (Cloudflare Workers AI)

결과 화면 "AI 코치에게 물어보기"는 로그인한 사용자의 분석 수치(각도·속도·스윙 면·힘 전달 순서·점수)만 `worker/` 의 Cloudflare Worker 로 보내고, Workers AI(`@cf/qwen/qwen3-30b-a3b-fp8`, 생각 과정 없이 바로 답하도록 `/no_think`)가 오늘의 과제·이유·연습 방법·잘하는 점을 한국어로 답합니다. 영상·좌표는 보내지 않습니다.

- Worker 는 Firebase(Google 로그인) 토큰을 직접 검증하고, KV 로 1인당 하루 20번까지만 허용하며, 숫자·정해진 값만 받아 프롬프트를 서버에서 만듭니다.
- 배포: `cd worker && npx wrangler deploy` (주소 https://ttt-coach.dchkimppi.workers.dev)
