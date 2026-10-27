// TTT AI 코치 (Cloudflare Worker + Workers AI)
// - Google 로그인(Firebase) 토큰을 직접 검증해서 로그인한 사람만 쓴다.
// - 1인당 하루 DAILY 번까지 (KV 에 사용 횟수 기록).
// - 받는 것은 숫자·판정뿐이고, 프롬프트는 서버가 만든다(자유 문장은 받지 않음).
const ORIGINS = ["https://hooni9807.github.io", "http://127.0.0.1:8811", "http://localhost:8811"];
const PROJECT = "ttt-swing";
const DAILY = 20;
const MODEL = "@cf/qwen/qwen3-30b-a3b-fp8";
const JWKS = "https://www.googleapis.com/service_accounts/v1/jwk/securetoken@system.gserviceaccount.com";

let jwksCache = null;
async function verifyIdToken(token) {
  const [h, p, s] = token.split(".");
  if (!s) throw new Error("bad token");
  const dec = x => JSON.parse(new TextDecoder().decode(b64(x)));
  const header = dec(h), payload = dec(p), now = Date.now() / 1000;
  if (header.alg !== "RS256") throw new Error("alg");
  if (payload.aud !== PROJECT || payload.iss !== `https://securetoken.google.com/${PROJECT}`) throw new Error("aud");
  if (!(payload.exp > now && payload.iat <= now + 60 && payload.sub)) throw new Error("time");
  if (!jwksCache || jwksCache.until < Date.now()) {
    const r = await fetch(JWKS);
    jwksCache = { keys: (await r.json()).keys, until: Date.now() + 3600e3 };
  }
  const jwk = jwksCache.keys.find(k => k.kid === header.kid);
  if (!jwk) throw new Error("kid");
  const key = await crypto.subtle.importKey("jwk", jwk, { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["verify"]);
  const ok = await crypto.subtle.verify("RSASSA-PKCS1-v1_5", key, b64(s), new TextEncoder().encode(`${h}.${p}`));
  if (!ok) throw new Error("sig");
  return payload.sub;
}
function b64(s) {
  const bin = atob(s.replace(/-/g, "+").replace(/_/g, "/") + "===".slice((s.length + 3) % 4));
  return Uint8Array.from(bin, c => c.charCodeAt(0));
}

// 받은 값 검증: 숫자는 범위 안, 문자열은 정해진 것만
const PHASES = ["백스윙", "임팩트", "피니시"], ANGLES = ["팔꿈치", "무릎", "몸통 꼬임"], CHAIN = ["골반", "어깨", "팔꿈치", "손목"];
const num = (v, lo, hi) => (typeof v === "number" && Number.isFinite(v) && v >= lo && v <= hi ? Math.round(v * 10) / 10 : null);
function clean(b) {
  const angles = {};
  for (const ph of PHASES) for (const k of ANGLES) {
    const v = num(b?.angles?.[ph]?.[k], 0, 180);
    if (v === null) throw new Error("angles");
    (angles[ph] ??= {})[k] = v;
  }
  const timing = {};
  for (const k of CHAIN) {
    const t = b?.timing?.[k];
    const v = num(t?.ms, -600, 400);
    if (v === null) throw new Error("timing");
    timing[k] = { ms: v, status: ["ok", "low", "high"].includes(t.status) ? t.status : null, min: num(t.min, -600, 400), max: num(t.max, -600, 400) };
  }
  const off = (Array.isArray(b?.off) ? b.off : []).slice(0, 10).map(o => {
    if (![...PHASES, "스윙"].includes(o.phase) || ![...ANGLES, "스윙 면 기울기"].includes(o.metric) || !["low", "high"].includes(o.status)) throw new Error("off");
    return { phase: o.phase, metric: o.metric, status: o.status, value: num(o.value, 0, 180), min: num(o.min, 0, 180), max: num(o.max, 0, 180) };
  });
  // 손목 위치(선택). 높이는 정해진 말만, 거리는 cm
  const HEIGHTS = ["무릎보다 아래", "무릎 높이", "허벅지 높이", "허리 높이", "가슴 높이", "어깨~턱 높이", "이마 높이 이상"];
  const place = {};
  for (const ph of PHASES) {
    const p = b?.place?.[ph];
    if (p && HEIGHTS.includes(p.height)) place[ph] = { height: p.height, dist: num(p.dist, 0, 200) };
  }
  return {
    angles, timing, off, place,
    hand: b.hand === "L" ? "왼손" : "오른손",
    speed: num(b.speed, 0, 40), plane: b.plane == null ? null : num(b.plane, 0, 90),
    chainOk: typeof b.chainOk === "boolean" ? b.chainOk : null, score: num(b.score, 0, 10),
  };
}

// 항목별로 "각도가 이러면 몸이 어떻게 되고 → 공이 어떻게 되고 → 어떻게 고치는지". 모델이 지어내지 않게 근거를 준다.
const MEANING = {
  "백스윙 팔꿈치": {
    low: ["팔꿈치가 많이 접혀 라켓이 몸에 붙은 채로 백스윙이 작아요", "스윙 거리가 짧아져 드라이브에 힘과 회전이 덜 실려요", "팔꿈치를 펴면서 라켓을 오른쪽 허리 옆~뒤까지 빼 주세요"],
    high: ["팔꿈치가 거의 펴진 채 팔 전체를 뒤로 빼요", "팔을 통째로 휘두르게 돼 타점이 흔들리고 다음 공 준비가 늦어요", "팔꿈치를 살짝 접어 라켓을 허리 높이 옆에 두세요"],
  },
  "백스윙 무릎": {
    low: ["무릎을 너무 깊게 굽혀 자세가 많이 낮아요", "일어서는 데 시간이 걸려 다음 공 대응이 늦어요", "무릎을 조금 세워 발끝 위에 무릎이 오게 하세요"],
    high: ["무릎이 거의 펴져 자세가 높아요", "하체 힘을 못 쓰고 아래에서 위로 끌어올리는 드라이브가 어려워요", "무릎을 더 굽혀 무게중심을 낮추고 오른발에 체중을 실으세요"],
  },
  "백스윙 몸통 꼬임": {
    low: ["백스윙 때 어깨를 덜 돌려 몸통이 정면을 보고 있어요", "몸통 회전 힘을 못 쓰고 팔로만 치게 돼요", "오른쪽 어깨를 뒤로 더 돌려 상체를 꼬아 주세요"],
    high: ["어깨를 너무 많이 돌려 몸이 뒤로 돌아가 있어요", "되돌아오는 데 시간이 걸려 타점이 늦어지기 쉬워요", "어깨 회전을 조금 줄여 공을 계속 볼 수 있는 만큼만 돌리세요"],
  },
  "임팩트 팔꿈치": {
    low: ["임팩트 때 팔꿈치가 너무 접혀 공을 몸 가까이에서 맞혀요", "팔이 답답하게 끼어 힘이 공에 다 전달되지 않아요", "공을 몸 앞쪽 조금 떨어진 곳에서 맞히도록 팔꿈치를 펴 주세요"],
    high: ["임팩트 때 팔이 거의 펴져 공을 몸에서 멀리 맞혀요", "팔 끝으로만 치게 돼 컨트롤과 힘이 약해져요", "한 발 더 다가가 팔꿈치를 살짝 접은 채 맞히세요"],
  },
  "임팩트 무릎": {
    low: ["임팩트 때 무릎이 너무 굽어 있어요", "몸이 낮게 묶여 다음 동작이 느려요", "무릎을 조금 세우며 위로 밀어 올리듯 치세요"],
    high: ["임팩트 때 무릎이 펴져 몸이 일찍 일어서요", "하체로 밀어 주는 힘이 빠져 공이 약해져요", "임팩트까지 무릎 굽힘을 유지하세요"],
  },
  "임팩트 몸통 꼬임": {
    low: ["임팩트 전에 몸통이 먼저 정면으로 열려요", "몸이 앞서고 팔이 늦게 따라와 공에 힘이 덜 실려요", "임팩트 순간까지 몸통을 조금 더 꼬인 채로 두세요"],
    high: ["임팩트 때 몸통이 아직 덜 돌아와 있어요", "공을 늦게(몸 옆이나 뒤에서) 맞히게 돼요", "몸통을 더 일찍 돌려 몸 앞에서 맞히세요"],
  },
  "피니시 팔꿈치": {
    low: ["피니시 때 팔꿈치가 너무 접혀 스윙이 짧게 끊겨요", "공을 끝까지 밀어 주지 못해 공 길이가 짧아져요", "팔을 이마 앞쪽으로 끝까지 뻗듯 마무리하세요"],
    high: ["피니시 때 팔이 앞으로 쭉 뻗어요", "스윙이 앞으로만 나가 회전이 덜 걸려요", "팔꿈치를 접으며 라켓을 이마 앞~왼쪽 위로 가져가세요"],
  },
  "피니시 무릎": {
    low: ["피니시 때도 무릎이 많이 굽어 있어요", "다음 공을 위한 복귀가 늦어요", "치고 나서 무릎을 살짝 세워 기본자세로 돌아오세요"],
    high: ["피니시 때 무릎이 다 펴져 몸이 떠요", "균형이 무너져 연속 공격이 어려워요", "치고 나서도 무릎을 살짝 굽힌 채 버티세요"],
  },
  "피니시 몸통 꼬임": {
    low: ["피니시 때 몸통이 너무 많이 돌아가요", "몸이 열려 다음 공 준비가 늦어요", "몸통 회전을 가슴이 정면을 볼 정도까지만 하세요"],
    high: ["피니시 때 몸통 회전이 덜 끝났어요", "스윙이 짧아지고 팔로만 치게 돼요", "오른쪽 어깨가 앞으로 나올 때까지 몸통을 끝까지 돌리세요"],
  },
  "스윙 스윙 면 기울기": {
    low: ["스윙이 너무 앞으로만(수평으로) 나가요", "공을 앞으로 밀기만 해서 각도가 얇아지고 회전이 적어요", "라켓 시작 위치를 무릎 높이까지 내려 아래에서 위로 스윙하세요"],
    high: ["스윙이 너무 위로만(세로로) 올라가요", "공이 위로 뜨고 앞으로 나가는 힘이 약해요", "라켓을 앞으로 더 밀어 이마 앞쪽으로 마무리하세요"],
  },
};

// 각도를 몸 모양으로 바꿔 말하기 (코치가 "팔이 ㄴ자" 처럼 말할 수 있게)
function shape(metric, v) {
  if (metric === "팔꿈치") return v < 80 ? "팔이 V자로 많이 접힘" : v < 100 ? "팔이 ㄴ자(직각)" : v < 130 ? "직각보다 조금 펴진 팔" : v < 160 ? "팔이 대부분 펴짐" : "팔이 거의 일자로 펴짐";
  if (metric === "무릎") return v < 110 ? "의자에 앉듯 깊게 굽힘" : v < 135 ? "무릎을 확실히 굽힌 낮은 자세" : v < 155 ? "무릎을 살짝 굽힘" : "무릎이 거의 펴져 선 자세";
  if (metric === "몸통 꼬임") return v < 10 ? "어깨와 골반이 같은 방향(꼬임 거의 없음)" : v < 30 ? "어깨가 골반보다 조금 더 돌아감" : v < 50 ? "어깨가 골반보다 확실히 더 돌아가 가슴이 옆을 봄" : "어깨가 등 쪽으로 크게 돌아감";
  if (metric === "스윙 면 기울기") return v < 25 ? "거의 수평으로 앞으로 미는 궤도" : v < 45 ? "앞쪽 위로 비스듬히 올라가는 궤도" : v < 65 ? "대각선보다 더 세워 올라가는 궤도" : "거의 아래에서 위로 수직에 가까운 궤도";
  return "";
}

function prompt(d) {
  // 힌트는 오른손잡이 기준이라 왼손잡이면 오른쪽↔왼쪽을 바꾼다
  const side = t => d.hand === "왼손" ? t.replace(/오른|왼/g, w => (w === "오른" ? "왼" : "오른")) : t;
  const r1 = x => Math.round(x * 10) / 10;
  // 고칠 점: 각도·스윙 면은 범위 밖 정도가 큰 순서, 목표는 범위 가운데
  const issues = d.off.map(o => {
    const target = Math.round((o.min + o.max) / 2), need = Math.round(o.status === "low" ? o.min - o.value : o.value - o.max);
    const [cause, effect, fix] = (MEANING[`${o.phase} ${o.metric}`]?.[o.status] ?? ["", "", ""]).map(side);
    const pl = d.place[o.phase];
    return { size: need / (o.max - o.min), text:
      `- ${o.phase === "스윙" ? "" : o.phase + " "}${o.metric}: 지금 ${o.value}°(${shape(o.metric, o.value)}), 도 대표 선수 ${o.min}~${o.max}° → 최소 ${need}° ${o.status === "low" ? "더 크게" : "더 작게"}, 목표 약 ${target}°(${shape(o.metric, target)})` +
      (pl ? `\n  이때 손목 위치: ${pl.height}, 몸 중심에서 약 ${pl.dist}cm` : "") +
      `\n  원인 힌트: ${cause}\n  결과 힌트: ${effect}\n  해결 힌트: ${fix}` };
  }).sort((a, b) => b.size - a.size).map(x => x.text);
  if (d.speed < 5.6) issues.push(`- 임팩트 손목 속도: 지금 ${d.speed} m/s, 도 대표 선수 5.6~6.9 m/s → ${r1(5.6 - d.speed)} m/s 더 빠르게` +
    "\n  결과 힌트: 공 위력이 약해요\n  해결 힌트: 위 각도들을 먼저 고친 뒤 임팩트 순간에만 힘을 모아 손목과 팔을 빠르게 채 주세요");
  for (const k of CHAIN) {
    const t = d.timing[k];
    if (t.min == null || t.status === "ok" || !t.status) continue;
    issues.push(`- ${k} 회전이 가장 빨라진 시점: 임팩트 ${t.ms > 0 ? "+" : ""}${t.ms}ms, 도 대표 선수 +${t.min}~+${t.max}ms → ${t.status === "low" ? "너무 일찍 돌고 멈춰요" : "너무 늦게까지 돌아요"}` +
      `\n  해결 힌트: ${t.status === "low" ? "임팩트 뒤까지 골반·어깨를 계속 돌려 끝까지 밀어 주세요" : "골반·어깨를 조금 더 일찍 돌리기 시작하세요"}`);
  }
  const good = d.off.length < 10 ? PHASES.flatMap(ph => ANGLES.filter(k => !d.off.some(o => o.phase === ph && o.metric === k)).map(k => `${ph} ${k} ${d.angles[ph][k]}°`)) : [];

  const facts = [
    `손잡이: ${d.hand}잡이 (포핸드 드라이브)`,
    `임팩트 손목 속도: ${d.speed} m/s (도 대표 선수 5.6~6.9 m/s)`,
    `스윙 면 기울기: ${d.plane ?? "측정 불가"}° (0° 수평으로만 나감, 90° 위로만 올라감)`,
    ...PHASES.map(ph => `${ph} 각도: ` + ANGLES.map(k => `${k} ${d.angles[ph][k]}°(${shape(k, d.angles[ph][k])})`).join(", ") +
      (d.place[ph] ? ` / 손목 위치: ${d.place[ph].height}, 몸 중심에서 약 ${d.place[ph].dist}cm` : "")),
    "(팔꿈치 180°=다 펴짐, 무릎 180°=다 펴짐, 몸통 꼬임=어깨선과 골반선이 엇갈린 각도)",
    "고칠 점(중요한 순서):", ...(issues.length ? issues : ["- 없음"]),
    `프로 범위 안인 항목: ${good.join(", ") || "없음"}`,
  ];
  return [
    { role: "system", content: "너는 탁구장에서 동호인 옆에 서서 포핸드 드라이브를 봐 주는 코치다. 칭찬보다 고칠 점 피드백이 중심이다. " +
      "고칠 점마다 원인, 그래서 생기는 결과, 해결 방법이 한 흐름으로 이어지게 말한다. 측정 수치(지금 몇 °)와 목표 수치(몇 °까지, 몇 ° 더)를 꼭 넣고, " +
      "각도는 반드시 몸 모양으로 풀어서 말하고(예: 112°면 '직각보다 조금 펴진 팔'), 측정된 손목 위치(높이, 몸 중심에서 몇 cm)를 넣어 지금 라켓이 어디 있고 어디까지 가야 하는지 말한다. " +
      "주어진 수치와 힌트만 근거로 쓰고, 없는 수치는 지어내지 않는다. 숫자는 주어진 값을 그대로 쓴다. 의학적 진단은 하지 않는다.\n" +
      "말투 규칙: 한국어 해요체, 사람이 옆에서 말하듯 자연스럽게 이어서 말한다. '원인:', '결과:', '해결:' 같은 꼬리표, 번호, 글머리표, 볼드, 이모지를 쓰지 않는다. " +
      "'그래서', '그러니까', '그러면'처럼 말로 잇는 접속어를 쓰되 같은 접속어를 반복하지 않는다. 짧은 문장과 긴 문장을 섞는다. " +
      "번역투('~을 통해', '~에 대해', '~에 있어서', '~를 가지다'), 이중피동('되어지다', '보여지다'), '결론적으로', '중요합니다', '~하는 것이 좋습니다' 같은 상투 표현은 쓰지 않는다. " +
      "인사말이나 '도움이 되길 바라요' 같은 맺음말도 붙이지 않는다." },
    { role: "user", content: `내 포핸드 스윙 측정값이야.\n${facts.join("\n")}\n\n` +
      "고칠 점을 중요한 순서로 최대 3개까지, 하나에 한 문단씩 말해 줘. 각 문단은 '지금 ~가 ~°라서 ~하니까, ~해요. ~°까지(~° 더) ~해 보세요'처럼 원인-결과-해결이 이어지는 말로 써 줘. " +
      "마지막 문단에서는 첫 번째 고칠 점을 위한 연습 하나(횟수 포함)를 권하고, 프로 범위 안인 항목 하나를 수치와 함께 짧게 칭찬해 줘. " +
      "고칠 점이 없으면 잘된 점과 유지할 연습만 한 문단으로 말해 줘.\n/no_think" }, // Qwen3: 생각 과정 없이 바로 답하게
  ];
}

const cors = origin => ({
  "Access-Control-Allow-Origin": ORIGINS.includes(origin) ? origin : ORIGINS[0],
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Authorization, Content-Type",
  "Vary": "Origin",
});
const json = (body, status, origin) => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json; charset=utf-8", ...cors(origin) } });

export default {
  async fetch(req, env) {
    const origin = req.headers.get("Origin") || "";
    if (req.method === "OPTIONS") return new Response(null, { headers: cors(origin) });
    if (req.method !== "POST") return json({ error: "POST 만 받아요" }, 405, origin);
    if (!ORIGINS.includes(origin)) return json({ error: "허용되지 않은 사이트" }, 403, origin);

    let uid;
    try { uid = await verifyIdToken((req.headers.get("Authorization") || "").replace(/^Bearer /, "")); }
    catch { return json({ error: "로그인이 필요해요" }, 401, origin); }

    let data;
    try { data = clean(await req.json()); } catch { return json({ error: "분석 값이 올바르지 않아요" }, 400, origin); }

    const day = new Date(Date.now() + 9 * 3600e3).toISOString().slice(0, 10); // 한국 날짜 기준
    const key = `${uid}:${day}`, used = Number(await env.LIMIT.get(key)) || 0;
    if (used >= DAILY) return json({ error: `오늘은 AI 코치를 ${DAILY}번 모두 썼어요. 내일 다시 써 주세요.` }, 429, origin);
    await env.LIMIT.put(key, String(used + 1), { expirationTtl: 2 * 86400 });

    try {
      const out = await env.AI.run(MODEL, { messages: prompt(data), max_tokens: 1200, temperature: 0.3 });
      // Qwen3 은 OpenAI 형식(choices), Llama 계열은 response 로 답한다. 혹시 남은 생각(<think>) 부분은 지운다.
      const text = (out.choices?.[0]?.message?.content ?? out.response ?? "").replace(/<think>[\s\S]*?<\/think>/g, "").trim();
      if (!text) throw new Error("empty");
      return json({ text, left: DAILY - used - 1 }, 200, origin);
    } catch (e) {
      return json({ error: "AI 코치가 지금 답하지 못했어요. 잠시 뒤 다시 시도해 주세요." }, 502, origin);
    }
  },
};
export { clean, prompt }; // 테스트에서 프롬프트를 확인하려고 내보냄
