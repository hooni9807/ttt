# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users
생활체육 탁구 동호회 아마추어. 탁구장에서 폰을 세워 두고 자기 스윙을 찍은 뒤, 그 자리에서 폰 브라우저로 영상을 올려 자세를 점검한다. 레슨에서 고친 자세가 혼자 칠 때 유지되는지, 무엇을 고쳐야 하는지 알고 싶어 한다.

## Product Purpose
스윙 영상 하나로 3D 자세를 복원해 임팩트 속도, 백스윙·임팩트·피니시 관절 각도, 힘 전달 순서를 숫자로 보여 주고, 프로 기준을 벗어난 항목에 짧은 교정 피드백을 준다. 성공은 사용자가 다음 연습에서 고칠 한 가지를 알고 떠나는 것.

## Positioning
영상이 서버로 가지 않고 사용자의 브라우저 안에서만 분석된다. 설치·가입·센서 없이 링크 하나로 쓴다. 무료 정적 호스팅(GitHub Pages)이라 운영 서버가 없다.

## Operating Context
- 탁구장 현장: 폰 한 대, 한 손, 밝은 실내 조명, 짧은 휴식 시간 사이에 사용.
- 영상: 폰 카메라 60fps 이상 권장, 15초 이내, 스윙 1회.
- 결과 확인: 원본 영상과 3D 스켈레톤을 나란히 재생, 0.25배속, 구간 점프.

## Capabilities and Constraints
- 정적 페이지: `index.html` + `analyze.js`(분석), `pro_ranges.json`(프로 기준), `tips.json`(피드백 문구). 빌드 단계 없음.
- 외부 의존: MediaPipe Tasks Vision 1.1.0(jsDelivr), 포즈 모델 full(약 9MB, Google Storage), three.js r128 + OrbitControls.
- 기능: 영상 업로드, fps 자동 추정, 3D 자세 복원 진행률, 오른손/왼손 전환, 3D 회전 뷰어, 리포트·피드백, 결과 JSON 저장, 분석 JSON 열기.
- 명령줄 도구(`swing.py`, `make_ranges.py`)가 같은 분석을 하며 `test_swing.py`가 웹과 결과를 대조한다.

## Brand Commitments
- 이름: TTT (유지).
- 언어: 한국어, 존댓말.

## Evidence on Hand
- 프로 기준은 논문 3편에서 가져온 값 3개뿐이다(손 속도 참고값, 백스윙·피니시 무릎 각도). 팔꿈치·몸통 꼬임 기준은 없다. 측정 장비가 달라 참고용임을 밝혀야 한다.
- 사용자 후기, 사용자 수, 정확도 수치는 없다. 지어내지 않는다.

## Product Principles
- 영상은 기기 밖으로 나가지 않는다는 점을 숨기지 않고 보여 준다.
- 숫자보다 "다음에 고칠 한 가지"가 먼저 보인다.
- 프로 기준의 한계(출처, 측정 방식 차이)를 정직하게 표시한다.
- 폰 한 손 사용이 기본이다.

## Accessibility & Inclusion
폰 한 손 조작(큰 터치 영역), 밝은 탁구장 조명에서도 읽히는 대비.
