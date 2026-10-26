"""탁구 스윙 영상 → 3D 자세 → 스윙 수치.

사용법: uv run swing.py 영상.mp4 [--left] [--ref 프로기준.json]
결과: 콘솔 리포트 + 영상.json (viewer.html 에서 열기)
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
    phases = dict(zip(PHASES, (int(np.argmax(dist[:impact + 1])), impact, impact + int(np.argmax(dist[impact:])))))

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
        "speed": speed,
    }


def report(m, fps, ref=None):
    """ref: pro_ranges.json 형식. 항목마다 {min, max} 범위 또는 {value} 참고값과 source."""
    ref = ref or {}
    used, feedback = [], []

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

    lines = [f"임팩트 손목 속도: {m['impact_speed']:.1f} m/s (프레임 {m['phases']['임팩트']})"
             + check(m["impact_speed"], ref.get("impact_speed"))]
    for ph, a in m["angles"].items():
        r = ref.get("angles", {}).get(ph, {})
        lines.append(f"[{ph}] " + ", ".join(f"{k} {v}°" + check(v, r.get(k), ph, k) for k, v in a.items()))
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
    print(f"\n저장: {out}  (viewer.html 에서 열기)")


if __name__ == "__main__":
    main()
