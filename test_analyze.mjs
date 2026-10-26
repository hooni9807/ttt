// analyze.js 결과가 swing.py 와 같은지 대조. test_swing.py 가 픽스처를 만들어 실행한다.
import { readFileSync } from "node:fs";
import { analyze, report, smooth } from "./analyze.js";

const fx = JSON.parse(readFileSync(process.argv[2], "utf8"));
const tips = JSON.parse(readFileSync(new URL("./tips.json", import.meta.url), "utf8"));
for (const c of fx.cases) {
  const m = analyze(smooth(c.pts, c.fps), c.fps);
  const py = c.expected;
  const fail = msg => { throw new Error(`fps=${c.fps}: ${msg}\nJS: ${JSON.stringify(m)}\nPY: ${JSON.stringify(py)}`); };
  if (JSON.stringify(m.phases) !== JSON.stringify(py.phases)) fail("phases");
  if (JSON.stringify(m.chain_peaks) !== JSON.stringify(py.chain_peaks)) fail("chain_peaks");
  if (m.chain_ok !== py.chain_ok) fail("chain_ok");
  if (Math.abs(m.impact_speed - py.impact_speed) > 0.011) fail("impact_speed");
  for (const ph in py.angles) for (const k in py.angles[ph])
    if (Math.abs(m.angles[ph][k] - py.angles[ph][k]) > 1) fail(`angle ${ph} ${k}`);
  report(m, c.fps, fx.ref, tips); // 예외 없이 만들어지는지만 확인
}
console.log("js ok");
