"""공개 데이터셋으로 TTT 표준(프로 범위)과 공 속도 예측 AI 를 만든다.

데이터: Lyu et al. 2025 "Table Tennis Forehand Stroke Mediapipe Datasets" (figshare 28881086, CC BY 4.0)
  - 도 대표 여자 선수 34명, 포핸드 340개, MediaPipe 33관절 3D, 100fps, 오른쪽 앞 45° 촬영(왼손잡이는 좌우 반전)
  - 공 속도(km/h): 원 논문처럼 공이 화면을 나가기 전 6프레임 좌표로 공 속도를 맞히는 모델을 먼저 만들고, 각 스트로크에 적용한다.

사용: uv run build_standard.py data/figshare
결과: pro_ranges.json (표준 범위), ballspeed_model.json (자세 → 공 속도 예측 AI)
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from swing import analyze, smooth
from train_scorer import features, fit

FPS = 100
SOURCE = ("Lyu et al. 2025, Front. Sports Act. Living — 도 대표 여자 선수 34명 포핸드 340개 (MediaPipe, 100fps, "
          "figshare 28881086, CC BY 4.0). 평균 ± 표준편차")


def load(folder):
    """메타데이터 순서대로 참가자마다 (step2 좌표, step3 구간) 묶음"""
    meta = json.loads((folder / "meta.json").read_text())
    groups, cur = [], {}
    for f in meta["files"]:
        if f["name"].startswith("step"):
            cur[f["name"].split("_")[0]] = folder / f"{f['id']}_{f['name']}"
            if len(cur) == 3:
                groups.append(cur); cur = {}
    speed = next(folder / f"{f['id']}_{f['name']}" for f in meta["files"] if f["name"] == "speed_final.csv")
    return groups, pd.read_csv(speed)


def ball_features(xy):
    """공 좌표 6개(x1,y1..x6,y6) → 이동량 특징. 방향과 상관없이 쓰려고 가로 이동은 절댓값."""
    xy = np.asarray(xy, float).reshape(-1, 6, 2)
    d = np.diff(xy, axis=1)
    dx, dy = np.abs(d[..., 0]), d[..., 1]
    return np.column_stack([dx, dy, dx.mean(1), dx.mean(1) ** 2, xy[:, :, 1].mean(1), np.ones(len(xy))])


def fit_ball_model(speed_df):
    cols = [f"{a}{i}" for i in range(1, 7) for a in "XY"]
    X, y = ball_features(speed_df[cols].to_numpy()), speed_df["Measured_speed"].to_numpy()
    idx = np.random.default_rng(0).permutation(len(y)); cut = int(len(y) * 0.8)
    tr, te = idx[:cut], idx[cut:]
    w = np.linalg.lstsq(X[tr], y[tr], rcond=None)[0]
    pred = X[te] @ w
    r2 = 1 - np.sum((pred - y[te]) ** 2) / np.sum((y[te] - y[te].mean()) ** 2)
    rmse = float(np.sqrt(np.mean((pred - y[te]) ** 2)))
    w = np.linalg.lstsq(X, y, rcond=None)[0]  # 검증 뒤 전체로 다시 학습
    return w, r2, rmse


def main():
    folder = Path(sys.argv[1] if len(sys.argv) > 1 else "data/figshare")
    groups, speed_df = load(folder)
    w_ball, r2, rmse = fit_ball_model(speed_df)
    print(f"공 속도 모델(공 좌표 → km/h): 시험 R² {r2:.3f}, 오차 {rmse:.2f} km/h (원 논문 R² 0.981, 1.40 km/h)")

    rows, hit_err = [], []
    for player, g in enumerate(groups):
        pos = pd.read_excel(g["step2"]).to_numpy(float).reshape(-1, 33, 3)
        seg = pd.read_excel(g["step3"])
        ball = ball_features(seg[[f"{a}{i}" for i in range(1, 7) for a in "xy"]].to_numpy()) @ w_ball
        for (_, s), v in zip(seg.iterrows(), ball):
            a, b = int(s["in"]), int(s["out"])
            if b - a < 30 or b >= len(pos):
                continue
            m = analyze(smooth(pos[a:b + 1], FPS), FPS, "R")  # 왼손잡이도 영상이 반전돼 있어 오른손 기준
            hit_err.append(m["phases"]["임팩트"] + a - int(s["hit_point"]))
            m.pop("speed")
            rows.append({"player": player, "metrics": m, "ball_speed": float(v)})
    hit_err = np.array(hit_err)
    print(f"스트로크 {len(rows)}개 분석 · 우리 임팩트 판정과 데이터의 실제 임팩트 차이: 중앙값 {np.median(np.abs(hit_err)):.0f}프레임"
          f" ({np.median(np.abs(hit_err)) * 10:.0f}ms), 3프레임 이내 {np.mean(np.abs(hit_err) <= 3) * 100:.0f}%")

    # 원 논문처럼 공 속도가 튀는 스트로크(선수별 평균 ± 2SD 밖)는 뺀다
    bs = np.array([r["ball_speed"] for r in rows]); pl = np.array([r["player"] for r in rows])
    keep = np.ones(len(rows), bool)
    for p in np.unique(pl):
        i = pl == p
        keep[i] = np.abs(bs[i] - bs[i].mean()) <= 2 * bs[i].std() + 1e-9
    rows = [r for r, k in zip(rows, keep) if k]
    print(f"이상치 제외 후 {len(rows)}개 · 예상 공 속도 {np.mean([r['ball_speed'] for r in rows]):.1f} ± {np.std([r['ball_speed'] for r in rows]):.1f} km/h")

    # 1) 표준 범위: 평균 ± 표준편차
    def rng(vals):
        vals = np.asarray([v for v in vals if v is not None], float)
        mu, sd = vals.mean(), vals.std(ddof=1)
        return {"min": round(float(mu - sd), 1), "max": round(float(mu + sd), 1), "source": SOURCE}
    ms = [r["metrics"] for r in rows]
    ranges = {
        "_note": "공개 데이터셋(도 대표 여자 선수 34명)을 TTT 와 같은 코드로 분석한 평균 ± 표준편차. 촬영 각도(오른쪽 앞 45°)가 사용자 영상과 다를 수 있어 참고용.",
        "impact_speed": rng(m["impact_speed"] for m in ms),
        "angles": {ph: {k: rng(m["angles"][ph][k] for m in ms) for k in ("팔꿈치", "무릎", "몸통 꼬임")}
                   for ph in ("백스윙", "임팩트", "피니시")},
        "swing_plane": rng(m["swing_plane"] for m in ms),
        # 힘 전달 타이밍(임팩트 기준 ms): 각 부위가 가장 빨라진 시점의 평균 ± 표준편차.
        # 손목은 임팩트 정의상 늘 0, 팔꿈치는 선수마다 너무 흩어져서(SD 200ms) 골반·어깨만 기준으로 쓴다.
        "chain": {k: {kk: int(round(v)) if kk != "source" else v for kk, v in rng(m["chain_ms"][k] for m in ms).items()}
                  for k in ("골반", "어깨")},
    }
    Path("pro_ranges.json").write_text(json.dumps(ranges, ensure_ascii=False, indent=2) + "\n")
    print("저장: pro_ranges.json")

    # 2) 자세 → 공 속도 AI. 같은 선수의 다른 스트로크가 학습에 섞이지 않게 선수 단위로 빼고 검증한다.
    names = features(ms[0], FPS)[0]
    X = np.array([features(m, FPS)[1] for m in ms]); y = np.array([r["ball_speed"] for r in rows])
    pl = np.array([r["player"] for r in rows])

    def predict(model, X):
        X = np.where(np.isnan(X), model["mean"], X)
        return ((X - model["mean"]) / model["std"]) @ model["w"] + model["b"]

    def cv(alpha):
        err = []
        for p in np.unique(pl):
            tr, te = pl != p, pl == p
            err += list(np.abs(predict(fit(X[tr], y[tr], alpha), X[te]) - y[te]))
        return float(np.mean(err))
    alpha = min((1.0, 10.0, 100.0, 1000.0), key=cv)
    err = cv(alpha)
    base = float(np.mean([np.mean(np.abs(y[pl == p] - y[pl != p].mean())) for p in np.unique(pl) for _ in [0]]))
    model = fit(X, y, alpha)
    print(f"공 속도 예측 AI: 선수 단위 검증 평균 오차 {err:.2f} km/h (평균으로만 찍으면 {base:.2f} km/h)")
    print("공 속도와 관련 큰 특징:")
    for i in np.argsort(-np.abs(model["w"]))[:6]:
        print(f"  {names[i]}: {'+' if model['w'][i] > 0 else '-'}{abs(model['w'][i]):.2f} km/h / 표준편차")
    Path("ballspeed_model.json").write_text(json.dumps({
        "features": names, "mean": model["mean"].tolist(), "std": model["std"].tolist(),
        "weights": model["w"].tolist(), "bias": float(model["b"]), "alpha": alpha,
        "unit": "km/h", "trained_on": len(y), "players": int(len(np.unique(pl))),
        "cv_mae": round(err, 2), "baseline_mae": round(base, 2),
        "ball_speed_mean": round(float(y.mean()), 1), "ball_speed_sd": round(float(y.std()), 1),
        "source": SOURCE,
    }, ensure_ascii=False, indent=2) + "\n")
    print("저장: ballspeed_model.json")


if __name__ == "__main__":
    main()
