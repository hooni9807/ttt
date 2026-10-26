// swing.py 의 smooth / analyze / report 를 브라우저용으로 옮긴 것.
// 한쪽을 고치면 다른 쪽도 고칠 것 — test_swing.py 가 두 결과를 대조한다.
export const PHASES = ["백스윙", "임팩트", "피니시"];
export const CHAIN = ["골반", "어깨", "팔꿈치", "손목"];
const BACK_SEC = 0.8, FOLLOW_SEC = 0.6; // 백스윙·피니시를 찾는 범위(임팩트 기준 초)
const J = {
  LEFT_SHOULDER: 11, RIGHT_SHOULDER: 12, LEFT_ELBOW: 13, RIGHT_ELBOW: 14, LEFT_WRIST: 15, RIGHT_WRIST: 16,
  LEFT_HIP: 23, RIGHT_HIP: 24, LEFT_KNEE: 25, RIGHT_KNEE: 26, LEFT_ANKLE: 27, RIGHT_ANKLE: 28,
};
export const wristIndex = hand => (hand === "L" ? J.LEFT_WRIST : J.RIGHT_WRIST);

const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const norm = a => Math.hypot(a[0], a[1], a[2]);
const argmax = a => a.reduce((best, v, i) => (v > a[best] ? i : best), 0);
const deg = r => (r * 180) / Math.PI;
// Python 의 f"{x:.0f}" 와 같은 반올림 (0.5 는 짝수 쪽으로)
export const roundHalfEven = x => {
  const r = Math.round(x);
  return Math.abs(x % 1) === 0.5 && r % 2 ? r - 1 : r;
};
const gradient = a => a.map((v, i) => (i === 0 ? a[1] - a[0] : i === a.length - 1 ? v - a[i - 1] : (a[i + 1] - a[i - 1]) / 2));
const unwrap = a => {
  let off = 0;
  return a.map((v, i) => {
    if (i && v - a[i - 1] > Math.PI) off -= 2 * Math.PI;
    else if (i && v - a[i - 1] < -Math.PI) off += 2 * Math.PI;
    return v + off;
  });
};

// pts: 프레임마다 33개 관절 [x, y, z], 사람이 안 잡힌 프레임은 null
export function smooth(pts, fps) {
  const n = pts.length, win = Math.max(3, Math.floor(fps / 20) | 1), h = win >> 1;
  const ok = pts.flatMap((p, i) => (p ? [i] : []));
  if (ok.length < 2) throw new Error("영상에서 사람을 거의 찾지 못했습니다. 몸 전체가 화면에 나오게 찍어 주세요.");
  const out = pts.map(() => Array.from({ length: 33 }, () => [0, 0, 0]));
  const v = new Array(n);
  for (let j = 0; j < 33; j++) {
    for (let d = 0; d < 3; d++) {
      for (let i = 0, k = 0; i < n; i++) {
        while (k < ok.length - 1 && ok[k + 1] <= i) k++;
        const a = ok[k], b = ok[Math.min(k + 1, ok.length - 1)];
        const va = pts[a][j][d], vb = pts[b][j][d];
        v[i] = i <= a ? va : i >= b ? vb : va + ((vb - va) * (i - a)) / (b - a);
      }
      for (let i = 0; i < n; i++) {
        let s = 0;
        for (let o = -h; o <= h; o++) s += v[Math.min(n - 1, Math.max(0, i + o))];
        out[i][j][d] = s / win;
      }
    }
  }
  return out;
}

export function analyze(pts, fps, hand = "R") {
  const S = hand === "R" ? "RIGHT" : "LEFT";
  const col = idx => pts.map(f => f[idx]);
  const side = name => col(J[`${S}_${name}`]);
  const wrist = side("WRIST");
  const speed = wrist.map((p, i) => (i ? norm(sub(p, wrist[i - 1])) * fps : 0));

  // 임팩트 = 손목이 가장 빠른 순간, 백스윙/피니시 = 그 앞뒤로 손목이 가장 멀리 간 순간
  const impact = argmax(speed);
  const dist = wrist.map(p => norm(sub(p, wrist[impact])));
  // 영상 속 다른 움직임을 빼려고 임팩트 앞 0.8초, 뒤 0.6초 안에서만 찾는다
  const b0 = Math.max(0, impact - Math.trunc(BACK_SEC * fps)), f1 = Math.min(wrist.length, impact + Math.trunc(FOLLOW_SEC * fps) + 1);
  const phases = { 백스윙: b0 + argmax(dist.slice(b0, impact + 1)), 임팩트: impact, 피니시: impact + argmax(dist.slice(impact, f1)) };

  const angle = (A, B, C) => A.map((a, i) => {
    const v1 = sub(a, B[i]), v2 = sub(C[i], B[i]);
    return deg(Math.acos(Math.max(-1, Math.min(1, dot(v1, v2) / (norm(v1) * norm(v2))))));
  });
  const yaw = (l, r) => unwrap(l.map((p, i) => Math.atan2(r[i][2] - p[2], r[i][0] - p[0]))).map(deg);
  const hips = yaw(col(J.LEFT_HIP), col(J.RIGHT_HIP));
  const shoulders = yaw(col(J.LEFT_SHOULDER), col(J.RIGHT_SHOULDER));
  const elbow = angle(side("SHOULDER"), side("ELBOW"), side("WRIST"));
  const knee = angle(side("HIP"), side("KNEE"), side("ANKLE"));
  const twist = shoulders.map((s, i) => Math.abs(((((s - hips[i] + 180) % 360) + 360) % 360) - 180));

  // 힘 전달: 백스윙~임팩트 사이에서 골반 → 어깨 → 팔꿈치 → 손목 순으로 최고 속도에 도달해야 함
  const rate = x => gradient(x).map(g => Math.abs(g) * fps);
  const b = phases.백스윙;
  const series = [rate(hips), rate(shoulders), rate(elbow), speed];
  const peaks = Object.fromEntries(CHAIN.map((k, i) => [k, b + argmax(series[i].slice(b, impact + 1))]));

  return {
    impact_speed: Math.round(speed[impact] * 100) / 100,
    phases,
    angles: Object.fromEntries(Object.entries(phases).map(([ph, f]) => [ph, {
      팔꿈치: Math.round(elbow[f]), 무릎: Math.round(knee[f]), "몸통 꼬임": Math.round(twist[f]),
    }])),
    chain_peaks: peaks,
    chain_ok: CHAIN.every((k, i) => !i || peaks[CHAIN[i - 1]] <= peaks[k]),
    speed,
    series: { 팔꿈치: elbow, 무릎: knee, "몸통 꼬임": twist }, // 웹 화면의 프레임별 수치용 (swing.py 에는 없음)
  };
}

// 프로 기준과 비교한 판정. ref: pro_ranges.json 형식, tips: tips.json
// status: ok / low / high (범위 비교), ref (참고값만 있음)
export function evaluate(m, ref = {}, tips = {}) {
  const sources = new Set();
  const judge = (v, r) => {
    if (!r) return null;
    sources.add(r.source);
    if (r.min === undefined) return { ...r, status: "ref" };
    return { ...r, status: v < r.min ? "low" : v > r.max ? "high" : "ok" };
  };
  const speed = judge(m.impact_speed, ref.impact_speed);
  const rows = [];
  for (const [phase, a] of Object.entries(m.angles)) {
    for (const [metric, value] of Object.entries(a)) {
      const r = judge(value, ref.angles?.[phase]?.[metric]);
      const tip = r && (r.status === "low" || r.status === "high") ? tips[metric]?.[r.status] : undefined;
      rows.push({ phase, metric, value, ref: r, tip });
    }
  }
  return { speed, rows, chainTip: m.chain_ok ? undefined : tips["힘 전달"], sources: [...sources], score: score(m, ref) };
}

// 참고 점수 (swing.py score 와 같은 규칙). 항목마다 10점 만점이고, 종합은 기준이 있는 항목들의 평균.
// 힘 전달(3구간 중 순서가 맞는 비율), 프로 범위(범위 안 항목 비율), 손목 속도(프로 기준 대비, 넘으면 만점).
export function score(m, ref = {}) {
  const r1 = x => roundHalfEven(x * 10) / 10;
  const pk = m.chain_peaks;
  const parts = [["힘 전달", (10 * CHAIN.slice(1).filter((k, i) => pk[CHAIN[i]] <= pk[k]).length) / 3, 10]];
  const checks = [];
  for (const [ph, rs] of Object.entries(ref.angles ?? {})) {
    for (const [k, r] of Object.entries(rs)) {
      if (r.min !== undefined && m.angles[ph]?.[k] !== undefined) checks.push([m.angles[ph][k], r]);
    }
  }
  if (checks.length) parts.push(["프로 범위", (10 * checks.filter(([v, r]) => r.min <= v && v <= r.max).length) / checks.length, 10]);
  const sp = ref.impact_speed;
  if (sp) parts.push(["손목 속도", 10 * Math.min(1, m.impact_speed / (sp.min ?? sp.value)), 10]);
  const rounded = parts.map(([n, g, mx]) => [n, r1(g), mx]);
  const total = r1((rounded.reduce((s, p) => s + p[1], 0) / rounded.reduce((s, p) => s + p[2], 0)) * 10);
  return { total, parts: rounded };
}

export function report(m, fps, ref = {}, tips = {}) {
  const e = evaluate(m, ref, tips);
  const mark = r => (!r ? "" : r.status === "ref" ? ` (프로 참고 ${r.value})` : ` (프로 ${r.min}~${r.max} ${r.status === "ok" ? "✓" : "⚠"})`);
  const lines = [
    `스윙 점수: ${e.score.total.toFixed(1)} / 10 (` + e.score.parts.map(([n, g, mx]) => `${n} ${g.toFixed(1)}/${mx}`).join(", ") + ")",
    `임팩트 손목 속도: ${m.impact_speed.toFixed(1)} m/s (프레임 ${m.phases.임팩트})` + mark(e.speed),
  ];
  for (const ph of Object.keys(m.angles)) {
    lines.push(`[${ph}] ` + e.rows.filter(r => r.phase === ph).map(r => `${r.metric} ${r.value}°` + mark(r.ref)).join(", "));
  }
  const feedback = e.rows.filter(r => r.tip).map(r => `[${r.phase}] ${r.metric}: ${r.tip}`);
  if (e.chainTip) feedback.push(`[힘 전달] ${e.chainTip}`);
  const order = [...CHAIN].sort((x, y) => m.chain_peaks[x] - m.chain_peaks[y]).join(" → ");
  lines.push(`힘 전달 순서: ${order} ` + (m.chain_ok ? "✓ 정상" : "⚠ 순서가 어긋남 (팔로만 치는 스윙 의심)"));
  lines.push("  최고속도 시점(임팩트 기준): " + CHAIN.map(k => {
    const ms = roundHalfEven(((m.chain_peaks[k] - m.phases.임팩트) / fps) * 1000);
    return `${k} ${ms >= 0 ? "+" : ""}${ms}ms`;
  }).join(", "));
  if (feedback.length) lines.push("", "피드백:", ...feedback.map(f => `  - ${f}`));
  if (e.sources.length) lines.push("", "프로 기준 출처:", ...e.sources.map(s => `  - ${s}`));
  return lines.join("\n");
}
