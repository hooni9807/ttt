"""탁구 스윙 영상 → 3D 자세 → 스윙 수치.

사용법: uv run swing.py 영상.mp4 [--left] [--ref 프로기준.json]
결과: 콘솔 리포트 + 영상.json (웹 페이지의 "저장한 결과 열기"로 3D 보기)
"""
import argparse
import json
import sys
import urllib.request
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import BaseOptions, vision

MODEL = Path(__file__).with_name("pose_landmarker_heavy.task")
MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
             "pose_landmarker_heavy/float16/latest/pose_landmarker_heavy.task")
PRO_RANGES = Path(__file__).with_name("pro_ranges.json")
TIPS = json.loads(Path(__file__).with_name("tips.json").read_text())
L = vision.PoseLandmark
CONNECTIONS = [(c.start, c.end) for c in vision.PoseLandmarksConnections.POSE_LANDMARKS]
PHASES = ("백스윙", "임팩트", "피니시")
BACK_SEC, FOLLOW_SEC = 0.8, 0.6  # 백스윙·피니시를 찾는 범위(임팩트 기준 초)
CHAIN = ("골반", "어깨", "팔꿈치", "손목")


def extract(video):
    """영상 프레임마다 33개 관절의 3D 좌표(미터, 골반 중심). 사람이 없는 프레임은 NaN."""
    if not MODEL.exists():
        print("포즈 모델 다운로드 중...", file=sys.stderr)
        urllib.request.urlretrieve(MODEL_URL, MODEL)
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        sys.exit(f"영상을 열 수 없습니다: {video}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    opts = vision.PoseLandmarkerOptions(base_options=BaseOptions(model_asset_path=str(MODEL)),
                                        running_mode=vision.RunningMode.VIDEO)
    pts = []
    with vision.PoseLandmarker.create_from_options(opts) as lm:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            img = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            r = lm.detect_for_video(img, int(len(pts) * 1000 / fps))
            pts.append([[p.x, p.y, p.z] for p in r.pose_world_landmarks[0]]
                       if r.pose_world_landmarks else np.full((33, 3), np.nan))
    return np.array(pts, dtype=float).reshape(-1, 33, 3), fps


def smooth(pts, fps):
    """빈 프레임은 보간하고 이동평균으로 떨림을 줄인다."""
    # ponytail: 이동평균은 최고속도를 살짝 깎음, 부족하면 Savitzky-Golay(scipy)로 교체
    win = max(3, int(fps // 20) | 1)
    t = np.arange(len(pts))
    out = np.empty_like(pts)
    for j in range(pts.shape[1]):
        for d in range(3):
            v = pts[:, j, d]
            ok = ~np.isnan(v)
            if ok.sum() < 2:
                raise ValueError("영상에서 사람을 거의 찾지 못했습니다. 몸 전체가 화면에 나오게 찍어 주세요.")
            v = np.interp(t, t[ok], v[ok])
            out[:, j, d] = np.convolve(np.pad(v, win // 2, mode="edge"), np.ones(win) / win, mode="valid")
    return out


def angle(a, b, c):
    """b 관절에서 a-b-c 가 이루는 각도(도)."""
    v1, v2 = a - b, c - b
    cos = (v1 * v2).sum(-1) / (np.linalg.norm(v1, axis=-1) * np.linalg.norm(v2, axis=-1))
    return np.degrees(np.arccos(np.clip(cos, -1, 1)))


def yaw(left, right):
    """위에서 내려다본 좌우 선(골반, 어깨)의 회전각(도)."""
    d = right - left
    return np.degrees(np.unwrap(np.arctan2(d[:, 2], d[:, 0])))


def analyze(pts, fps, hand="R"):
    side = "RIGHT" if hand == "R" else "LEFT"
    J = lambda name: pts[:, L[f"{side}_{name}"]]
    wrist = J("WRIST")
    speed = np.r_[0, np.linalg.norm(np.diff(wrist, axis=0), axis=1) * fps]

    # 임팩트 = 손목이 가장 빠른 순간, 백스윙/피니시 = 그 앞뒤로 손목이 가장 멀리 간 순간
    # ponytail: 스윙 하나만 있다고 가정, 여러 번 치는 영상은 스윙 구간 분할 필요
    impact = int(np.argmax(speed))
    dist = np.linalg.norm(wrist - wrist[impact], axis=1)
    # 영상 속 다른 움직임(걷기, 공 줍기)을 빼려고 임팩트 앞 0.8초, 뒤 0.6초 안에서만 찾는다
    # ponytail: 포핸드 기준 고정 창, 느린 스윙(커트·로브)이 잘리면 늘릴 것
    b0, f1 = max(0, impact - int(BACK_SEC * fps)), min(len(wrist), impact + int(FOLLOW_SEC * fps) + 1)
    phases = dict(zip(PHASES, (b0 + int(np.argmax(dist[b0:impact + 1])), impact, impact + int(np.argmax(dist[impact:f1])))))

    hips = yaw(pts[:, L.LEFT_HIP], pts[:, L.RIGHT_HIP])
    shoulders = yaw(pts[:, L.LEFT_SHOULDER], pts[:, L.RIGHT_SHOULDER])
    elbow = angle(J("SHOULDER"), J("ELBOW"), J("WRIST"))
    knee = angle(J("HIP"), J("KNEE"), J("ANKLE"))
    twist = np.abs((shoulders - hips + 180) % 360 - 180)

    # 힘 전달: 백스윙~임팩트 사이에서 골반 → 어깨 → 팔꿈치 → 손목 순으로 최고 속도에 도달해야 함
    rate = lambda x: np.abs(np.gradient(x)) * fps
    w = slice(phases["백스윙"], impact + 1)
    peaks = {k: phases["백스윙"] + int(np.argmax(v[w]))
             for k, v in zip(CHAIN, (rate(hips), rate(shoulders), rate(elbow), speed))}

    return {
        "impact_speed": round(float(speed[impact]), 2),
        "phases": phases,
        "angles": {ph: {"팔꿈치": round(float(elbow[f])), "무릎": round(float(knee[f])),
                        "몸통 꼬임": round(float(twist[f]))} for ph, f in phases.items()},
        "chain_peaks": peaks,
        "chain_ok": sorted(CHAIN, key=lambda k: (peaks[k], CHAIN.index(k))) == list(CHAIN),
        "swing_plane": swing_plane(wrist[phases["백스윙"]:phases["피니시"] + 1]),
        "speed": speed,
    }


def swing_plane(seg):
    """백스윙~피니시 손목 궤적에 맞는 평면이 바닥과 이루는 각도(도). 0 = 수평 스윙, 90 = 수직 스윙.
    궤적이 거의 직선이면 평면이 정해지지 않아 None."""
    if len(seg) < 3:
        return None
    x = seg - seg.mean(0)
    vals, vecs = np.linalg.eigh(x.T @ x)  # 고윳값 오름차순, 가장 작은 쪽이 평면의 법선
    if vals[1] <= 1e-6 * max(vals[2], 1e-12):
        return None
    # MediaPipe 는 y 가 세로축. 법선이 세로에 가까울수록 평면은 수평
    return int(round(float(np.degrees(np.arccos(min(1.0, abs(vecs[1, 0])))))))


def score(m, ref=None):
    """참고 점수. 항목마다 10점 만점이고, 종합은 기준이 있는 항목들의 평균.
    힘 전달(골반→어깨→팔꿈치→손목 3구간 중 순서가 맞는 비율), 프로 범위(범위 안 항목 비율),
    손목 속도(프로 기준 대비, 넘으면 만점)."""
    ref = ref or {}
    r1 = lambda x: round(x * 10) / 10  # analyze.js 와 같은 반올림(0.5 는 짝수 쪽)
    pk = m["chain_peaks"]
    parts = [("힘 전달", 10 * sum(pk[a] <= pk[b] for a, b in zip(CHAIN, CHAIN[1:])) / 3, 10)]
    checks = [(m["angles"][ph][k], r) for ph, rs in ref.get("angles", {}).items() for k, r in rs.items()
              if "min" in r and k in m["angles"].get(ph, {})]
    if m.get("swing_plane") is not None and "min" in ref.get("swing_plane", {}):
        checks.append((m["swing_plane"], ref["swing_plane"]))
    if checks:
        parts.append(("프로 범위", 10 * sum(r["min"] <= v <= r["max"] for v, r in checks) / len(checks), 10))
    sp = ref.get("impact_speed")
    if sp:
        parts.append(("손목 속도", 10 * min(1, m["impact_speed"] / sp.get("min", sp.get("value"))), 10))
    parts = [(n, r1(g), mx) for n, g, mx in parts]
    return r1(sum(g for _, g, _ in parts) / sum(mx for *_, mx in parts) * 10), parts


def report(m, fps, ref=None):
    """ref: pro_ranges.json 형식. 항목마다 {min, max} 범위 또는 {value} 참고값과 source."""
    ref = ref or {}
    used, feedback = [], []
    total, parts = score(m, ref)

    def check(v, r, label=None, key=None):
        if not r:
            return ""
        used.append(r["source"])
        if "min" not in r:
            return f" (프로 참고 {r['value']:g})"
        d = "low" if v < r["min"] else "high" if v > r["max"] else None
        if d and key in TIPS:
            feedback.append(f"[{label}] {key}: {TIPS[key][d]}")
        return f" (프로 {r['min']:g}~{r['max']:g} {'⚠' if d else '✓'})"

    lines = [f"스윙 점수: {total:.1f} / 10 (" + ", ".join(f"{n} {g:.1f}/{mx}" for n, g, mx in parts) + ")",
             f"임팩트 손목 속도: {m['impact_speed']:.1f} m/s (프레임 {m['phases']['임팩트']})"
             + check(m["impact_speed"], ref.get("impact_speed"))]
    for ph, a in m["angles"].items():
        r = ref.get("angles", {}).get(ph, {})
        lines.append(f"[{ph}] " + ", ".join(f"{k} {v}°" + check(v, r.get(k), ph, k) for k, v in a.items()))
    plane = m.get("swing_plane")
    lines.append("스윙 면 기울기: " + (f"{plane}°" + check(plane, ref.get("swing_plane"), "스윙", "스윙 면 기울기")
                                    if plane is not None else "측정 불가 (손목 궤적이 거의 직선)"))
    order = " → ".join(sorted(CHAIN, key=lambda k: m["chain_peaks"][k]))
    t = {k: (f - m["phases"]["임팩트"]) / fps * 1000 for k, f in m["chain_peaks"].items()}
    lines.append(f"힘 전달 순서: {order} " + ("✓ 정상" if m["chain_ok"] else "⚠ 순서가 어긋남 (팔로만 치는 스윙 의심)"))
    lines.append("  최고속도 시점(임팩트 기준): " + ", ".join(f"{k} {v:+.0f}ms" for k, v in t.items()))
    if not m["chain_ok"]:
        feedback.append(f"[힘 전달] {TIPS['힘 전달']}")
    if feedback:
        lines += ["", "피드백:"] + [f"  - {f}" for f in feedback]
    if used:
        lines += ["", "프로 기준 출처:"] + [f"  - {s}" for s in dict.fromkeys(used)]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--left", action="store_true", help="왼손잡이")
    ap.add_argument("--ref", default=PRO_RANGES, help="프로 기준 범위 JSON (기본: 논문 값 pro_ranges.json, make_ranges.py 로 직접 생성 가능)")
    a = ap.parse_args()

    raw, fps = extract(a.video)
    try:
        pts = smooth(raw, fps)
    except ValueError as e:
        sys.exit(str(e))
    m = analyze(pts, fps, "L" if a.left else "R")
    ref = json.loads(Path(a.ref).read_text()) if Path(a.ref).exists() else None
    text = report(m, fps, ref)
    print(text)

    speed = m.pop("speed")
    out = Path(a.video).with_suffix(".json")
    out.write_text(json.dumps({
        "fps": fps, "connections": CONNECTIONS,
        "wrist_index": int(L.LEFT_WRIST if a.left else L.RIGHT_WRIST),
        "frames": np.round(pts, 3).tolist(), "speed": np.round(speed, 2).tolist(),
        "metrics": m, "report": text,
    }, ensure_ascii=False))
    print(f"\n저장: {out}  (웹 페이지의 '저장한 결과 열기'로 3D 보기)")


if __name__ == "__main__":
    main()
