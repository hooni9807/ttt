"""사람이 매긴 점수로 스윙 평가 AI(선형 회귀)를 학습한다.

1) label.html 에서 데이터셋에 점수를 매기고 "점수 매긴 데이터 내려받기"로 ttt-labels-날짜.json 을 받는다.
2) uv run train_scorer.py ttt-labels-날짜.json -o scorer.json
   → 하나씩 빼고 맞혀 보는 검증(leave-one-out)의 평균 오차를 출력하고, 학습한 가중치를 scorer.json 에 저장한다.
"""
import argparse
import json
from pathlib import Path

import numpy as np

PHASES = ("백스윙", "임팩트", "피니시")
ANGLES = ("팔꿈치", "무릎", "몸통 꼬임")
CHAIN = ("골반", "어깨", "팔꿈치")


def features(m, fps):
    """분석 결과(metrics) → 숫자 특징. 이름과 값을 함께 돌려준다."""
    names, vals = [], []
    for ph in PHASES:
        for k in ANGLES:
            names.append(f"{ph} {k}"); vals.append(m["angles"][ph][k])
    names += ["손목 속도", "스윙 면", "힘 전달 순서"]
    vals += [m["impact_speed"], m["swing_plane"] if m.get("swing_plane") is not None else np.nan, float(m["chain_ok"])]
    imp = m["phases"]["임팩트"]
    for k in CHAIN:  # 각 부위가 가장 빨랐던 시점(임팩트 기준, 초)
        names.append(f"{k} 타이밍"); vals.append((m["chain_peaks"][k] - imp) / fps)
    return names, np.array(vals, dtype=float)


def fit(X, y, alpha=1.0):
    """표준화한 뒤 릿지 회귀. 빈 값(스윙 면 측정 불가)은 평균으로 채운다."""
    mean = np.nanmean(X, 0)
    X = np.where(np.isnan(X), mean, X)
    std = X.std(0)
    std[std == 0] = 1
    Z = (X - mean) / std
    w = np.linalg.solve(Z.T @ Z + alpha * np.eye(Z.shape[1]), Z.T @ (y - y.mean()))
    return {"mean": mean, "std": std, "w": w, "b": y.mean()}


def predict(model, X):
    X = np.where(np.isnan(X), model["mean"], X)
    return np.clip(((X - model["mean"]) / model["std"]) @ model["w"] + model["b"], 0, 10)


def loo_error(X, y, alpha):
    """하나씩 빼고 학습해서 뺀 것을 맞혀 본 평균 절대 오차(점)."""
    errs = []
    for i in range(len(y)):
        keep = np.arange(len(y)) != i
        errs.append(abs(predict(fit(X[keep], y[keep], alpha), X[i:i + 1])[0] - y[i]))
    return float(np.mean(errs))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("labels", help="label.html 에서 내려받은 JSON")
    ap.add_argument("-o", "--out", default="scorer.json")
    a = ap.parse_args()
    rows = json.loads(Path(a.labels).read_text())
    if len(rows) < 10:
        ap.error(f"점수 매긴 스윙이 {len(rows)}개예요. 최소 10개, 믿을 만하려면 50개 이상 필요해요.")
    names = features(rows[0]["metrics"], rows[0]["fps"])[0]
    X = np.array([features(r["metrics"], r["fps"])[1] for r in rows])
    y = np.array([r["label"]["score"] for r in rows], dtype=float)

    # 규제 세기는 하나씩 빼고 맞혀 본 오차가 가장 작은 값으로
    alpha = min((0.1, 1.0, 10.0, 100.0), key=lambda al: loo_error(X, y, al))
    err, base = loo_error(X, y, alpha), float(np.mean(np.abs(y - y.mean())))
    model = fit(X, y, alpha)
    print(f"스윙 {len(y)}개 · 사람 점수 평균 {y.mean():.1f}")
    print(f"평균 오차: AI {err:.2f}점 (모두 평균으로 찍으면 {base:.2f}점)")
    print("영향 큰 특징:")
    for i in np.argsort(-np.abs(model["w"]))[:5]:
        print(f"  {names[i]}: {'+' if model['w'][i] > 0 else '-'}{abs(model['w'][i]):.2f}점 / 표준편차")
    Path(a.out).write_text(json.dumps({
        "features": names, "mean": model["mean"].tolist(), "std": model["std"].tolist(),
        "weights": model["w"].tolist(), "bias": float(model["b"]), "alpha": alpha,
        "trained_on": len(y), "loo_mae": round(err, 3),
    }, ensure_ascii=False, indent=2))
    print(f"저장: {a.out}")


if __name__ == "__main__":
    main()
