"""가짜 스윙 데이터로 analyze/smooth 확인. 실행: uv run test_swing.py"""
import numpy as np

from swing import L, analyze, smooth

FPS, N = 60, 120
pose = np.zeros((33, 3))
for name, xyz in {"LEFT_HIP": (-0.1, 0, 0), "RIGHT_HIP": (0.1, 0, 0),
                  "LEFT_SHOULDER": (-0.2, -0.5, 0), "RIGHT_SHOULDER": (0.2, -0.5, 0),
                  "RIGHT_ELBOW": (0.3, -0.25, 0.1), "RIGHT_WRIST": (0.4, -0.2, 0.3),
                  "RIGHT_KNEE": (0.1, 0.45, 0.05), "RIGHT_ANKLE": (0.1, 0.9, 0)}.items():
    pose[L[name]] = xyz
pts = np.repeat(pose[None], N, axis=0)
t = np.arange(N)


def rotate(idx, peak):  # 골반/어깨를 y축으로 비틀기, 회전 속도는 peak 프레임에서 최고
    a = np.radians(40) * np.tanh((t - peak) / 4)
    for i in idx:
        x, z = pose[i, 0], pose[i, 2]
        pts[:, i, 0] = x * np.cos(a) - z * np.sin(a)
        pts[:, i, 2] = x * np.sin(a) + z * np.cos(a)


rotate([L.LEFT_HIP, L.RIGHT_HIP], 65)
rotate([L.LEFT_SHOULDER, L.RIGHT_SHOULDER], 72)
pts[:, L.RIGHT_WRIST, 0] += 0.6 * np.tanh((t - 80) / 4)  # 손목 최고속도 = 프레임 80

m = analyze(pts, FPS)
# 백스윙·피니시는 임팩트 앞 0.8초(48프레임), 뒤 0.6초(36프레임) 안에서만 찾는다
assert m["phases"] == {"백스윙": 32, "임팩트": 80, "피니시": 116}, m["phases"]
assert abs(m["chain_peaks"]["골반"] - 65) <= 1 and abs(m["chain_peaks"]["어깨"] - 72) <= 1, m["chain_peaks"]
assert m["chain_peaks"]["골반"] < m["chain_peaks"]["어깨"] < m["chain_peaks"]["손목"]

# 사람이 안 잡힌 프레임은 보간되어 임팩트가 그대로 나와야 함
holes = pts.copy()
holes[[10, 11, 50, 81]] = np.nan
assert analyze(smooth(holes, FPS), FPS)["phases"]["임팩트"] in (79, 80, 81)

# 사람이 아예 없으면 친절한 에러
try:
    smooth(np.full((N, 33, 3), np.nan), FPS)
    raise AssertionError("ValueError 가 나야 함")
except ValueError:
    pass

# 프로 범위: 영상 3개로 평균 ± 표준편차, 범위 밖이면 ⚠
from make_ranges import ranges
from swing import report

pro = ranges([{"impact_speed": s, "angles": {ph: {"팔꿈치": e} for ph in ("백스윙", "임팩트", "피니시")}}
              for s, e in ((5, 100), (6, 110), (7, 120))], "테스트")
assert pro["angles"]["임팩트"]["팔꿈치"] == {"min": 100.0, "max": 120.0, "source": "테스트"}
assert "swing_plane" not in pro  # 스윙 면 값이 없으면 범위도 만들지 않는다
assert ranges([{"impact_speed": 1, "swing_plane": v, "angles": {ph: {} for ph in ("백스윙", "임팩트", "피니시")}} for v in (40, 50, 60)], "t")["swing_plane"] == {"min": 40.0, "max": 60.0, "source": "t"}
text = report({**m, "impact_speed": 6.0, "angles": {"임팩트": {"팔꿈치": 130}}}, FPS, pro)
assert "프로 5~7 ✓" in text and "팔꿈치 130° (프로 100~120 ⚠)" in text and "- 테스트" in text, text

assert "피드백:" in text and "팔이 너무 펴져 있어요" in text, text

# 스윙 면: 바닥에서 30° 기운 평면 위의 호 → 30°, 직선 궤적 → None
from swing import swing_plane

phi = np.linspace(0, np.pi, 40)[:, None]
u, w = np.array([1, 0, 0]), np.array([0, -np.sin(np.radians(30)), np.cos(np.radians(30))])
arc = 0.5 * (np.cos(phi) * u + np.sin(phi) * w)
assert swing_plane(arc) == 30, swing_plane(arc)
assert swing_plane(np.linspace(0, 1, 20)[:, None] * u) is None

# 점수: 항목마다 10점. 힘 전달 순서 정상(10), 범위 2개 중 1개 안(5), 손목 속도 기준의 절반(5) → 평균 6.7
from swing import score

sm = {"chain_peaks": {"골반": 1, "어깨": 2, "팔꿈치": 3, "손목": 4}, "impact_speed": 2.75,
      "angles": {"백스윙": {"무릎": 140}, "피니시": {"무릎": 170}}}
sref = {"impact_speed": {"value": 5.5, "source": "t"},
        "angles": {"백스윙": {"무릎": {"min": 130, "max": 148, "source": "t"}}, "피니시": {"무릎": {"min": 115, "max": 160, "source": "t"}}}}
assert score(sm, sref) == (6.7, [("힘 전달", 10.0, 10), ("프로 범위", 5.0, 10), ("손목 속도", 5.0, 10)]), score(sm, sref)
# 순서가 하나 어긋나면 힘 전달 6.7, 기준이 없는 항목은 빼고 평균
sm["chain_peaks"]["팔꿈치"] = 5
assert score(sm, {}) == (6.7, [("힘 전달", 6.7, 10)]), score(sm, {})

# 웹(analyze.js)이 Python 과 같은 결과를 내는지 대조 (node 가 있을 때)
import json, shutil, subprocess, tempfile
from pathlib import Path

if shutil.which("node"):
    cases = []
    # 논문 기준 + 스윙 면 범위(20~25°)를 붙여서, 30° 스윙이 범위 밖 판정·피드백·점수까지 같게 나오는지 본다
    ref_t = {**json.loads(Path("pro_ranges.json").read_text()), "swing_plane": {"min": 20, "max": 25, "source": "테스트 스윙 면"}}
    # 손목이 30° 기운 평면 위에서 움직이는 경우도 대조 (스윙 면이 정해지는 경우)
    tilted = pts.copy()
    ang = np.pi * (0.5 + 0.5 * np.tanh((t - 80.3) / 6))[:, None]  # 80.3: 두 프레임 속도가 똑같이 최대가 되지 않게
    tilted[:, L.RIGHT_WRIST] = pose[L.RIGHT_SHOULDER] + 0.5 * (np.cos(ang) * u + np.sin(ang) * w)
    for fps, data in ((60, holes), (240, holes), (60, tilted)):
        r = analyze(smooth(data, fps), fps)
        r.pop("speed")
        cases.append({"fps": fps, "expected": r, "report": report(r, fps, ref_t),
                      "pts": [None if np.isnan(f).all() else f.tolist() for f in data]})
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump({"cases": cases, "ref": ref_t}, f, ensure_ascii=False)
    subprocess.run(["node", "test_analyze.mjs", f.name], check=True)
else:
    print("node 없음: 웹 분석 대조 생략")

print("ok")

# 평가 AI 학습: 점수가 특징의 선형 함수면 거의 그대로 맞혀야 한다
from train_scorer import features, fit, loo_error, predict

rng = np.random.default_rng(0)
fake_rows = []
for _ in range(40):
    mm = {"angles": {ph: {k: float(rng.uniform(60, 170)) for k in ("팔꿈치", "무릎", "몸통 꼬임")} for ph in ("백스윙", "임팩트", "피니시")},
          "impact_speed": float(rng.uniform(2, 8)), "swing_plane": float(rng.uniform(10, 60)), "chain_ok": bool(rng.random() > .5),
          "phases": {"임팩트": 50}, "chain_peaks": {"골반": int(rng.integers(30, 50)), "어깨": int(rng.integers(30, 50)), "팔꿈치": int(rng.integers(30, 50))}}
    fake_rows.append(mm)
FX = np.array([features(r, 60)[1] for r in fake_rows])
fy = np.clip(1.0 * FX[:, 9] + 2 * FX[:, 11] - 1, 0, 10)  # 손목 속도와 힘 전달 순서로 정한 점수
assert loo_error(FX, fy, 0.1) < 0.5, loo_error(FX, fy, 0.1)
FX[0, 10] = np.nan  # 스윙 면 측정 불가여도 예측은 된다
assert np.isfinite(predict(fit(FX, fy), FX)).all()
print("scorer ok")
