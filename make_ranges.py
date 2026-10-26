"""프로 스윙 분석 JSON 여러 개 → 프로 기준 범위 JSON (평균 ± 표준편차).

1) 프로 스윙 영상마다: uv run swing.py 프로1.mp4   (→ 프로1.json)
2) 범위 만들기:        uv run make_ranges.py 프로1.json 프로2.json ... -o my_pro.json
3) 내 스윙과 비교:     uv run swing.py 내스윙.mp4 --ref my_pro.json
"""
import argparse
import json
from pathlib import Path

import numpy as np

PHASES = ("백스윙", "임팩트", "피니시")


def ranges(metrics, source):
    def r(vals):
        mean, sd = np.mean(vals), np.std(vals, ddof=1)
        return {"min": round(float(mean - sd), 1), "max": round(float(mean + sd), 1), "source": source}

    planes = [m["swing_plane"] for m in metrics if m.get("swing_plane") is not None]
    out = {
        "impact_speed": r([m["impact_speed"] for m in metrics]),
        "angles": {ph: {k: r([m["angles"][ph][k] for m in metrics]) for k in metrics[0]["angles"][ph]}
                   for ph in PHASES},
    }
    if len(planes) >= 2:
        out["swing_plane"] = r(planes)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("analyses", nargs="+", help="swing.py 가 만든 프로 스윙 JSON (2개 이상)")
    ap.add_argument("-o", "--out", default="my_pro.json")
    a = ap.parse_args()
    if len(a.analyses) < 2:
        ap.error("범위를 만들려면 프로 스윙 JSON 이 2개 이상 필요합니다.")
    metrics = [json.loads(Path(p).read_text())["metrics"] for p in a.analyses]
    source = f"프로 스윙 영상 {len(metrics)}개 평균 ± 표준편차 ({', '.join(Path(p).stem for p in a.analyses)})"
    Path(a.out).write_text(json.dumps(ranges(metrics, source), ensure_ascii=False, indent=2))
    print(f"저장: {a.out}")


if __name__ == "__main__":
    main()
