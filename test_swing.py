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
text = report({**m, "impact_speed": 6.0, "angles": {"임팩트": {"팔꿈치": 130}}}, FPS, pro)
assert "프로 5~7 ✓" in text and "팔꿈치 130° (프로 100~120 ⚠)" in text and "- 테스트" in text, text

assert "피드백:" in text and "팔이 너무 펴져 있어요" in text, text

# 점수: 힘 전달 순서 정상(4/4), 범위 2개 중 1개 안(2/4), 손목 속도 기준의 절반(1/2) → 7/10
from swing import score

sm = {"chain_peaks": {"골반": 1, "어깨": 2, "팔꿈치": 3, "손목": 4}, "impact_speed": 2.75,
      "angles": {"백스윙": {"무릎": 140}, "피니시": {"무릎": 170}}}
sref = {"impact_speed": {"value": 5.5, "source": "t"},
        "angles": {"백스윙": {"무릎": {"min": 130, "max": 148, "source": "t"}}, "피니시": {"무릎": {"min": 115, "max": 160, "source": "t"}}}}
assert score(sm, sref) == (7.0, [("힘 전달", 4.0, 4), ("프로 범위", 2.0, 4), ("손목 속도", 1.0, 2)]), score(sm, sref)
# 순서가 하나 어긋나면 힘 전달 2.7/4, 기준이 없으면 그 항목은 빼고 10점 환산
sm["chain_peaks"]["팔꿈치"] = 5
assert score(sm, {}) == (6.8, [("힘 전달", 2.7, 4)]), score(sm, {})

# 웹(analyze.js)이 Python 과 같은 결과를 내는지 대조 (node 가 있을 때)
import json, shutil, subprocess, tempfile
from pathlib import Path

if shutil.which("node"):
    cases = []
    for fps in (60, 240):
        r = analyze(smooth(holes, fps), fps)
        r.pop("speed")
        cases.append({"fps": fps, "expected": r, "report": report(r, fps, json.loads(Path("pro_ranges.json").read_text())),
                      "pts": [None if np.isnan(f).all() else f.tolist() for f in holes]})
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump({"cases": cases, "ref": json.loads(Path("pro_ranges.json").read_text())}, f, ensure_ascii=False)
    subprocess.run(["node", "test_analyze.mjs", f.name], check=True)
else:
    print("node 없음: 웹 분석 대조 생략")

print("ok")
