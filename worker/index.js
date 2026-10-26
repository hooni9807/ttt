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
  const order = Array.isArray(b?.order) && b.order.length === 4 && b.order.every(x => CHAIN.includes(x)) ? b.order : null;
  if (!order) throw new Error("order");
  const off = (Array.isArray(b?.off) ? b.off : []).slice(0, 10).map(o => {
    if (![...PHASES, "스윙"].includes(o.phase) || ![...ANGLES, "스윙 면 기울기"].includes(o.metric) || !["low", "high"].includes(o.status)) throw new Error("off");
    return { phase: o.phase, metric: o.metric, status: o.status, value: num(o.value, 0, 180), min: num(o.min, 0, 180), max: num(o.max, 0, 180) };
  });
  return {
    angles, order, off,
    hand: b.hand === "L" ? "왼손" : "오른손",
    speed: num(b.speed, 0, 40), plane: b.plane == null ? null : num(b.plane, 0, 90),
    chainOk: b.chainOk === true, score: num(b.score, 0, 10),
  };
}

function prompt(d) {
  const lines = [
    `손잡이: ${d.hand}잡이 (포핸드)`,
    `종합 참고 점수: ${d.score ?? "없음"} / 10`,
    `임팩트 손목 속도: ${d.speed} m/s (프로 참고값 약 5.5 m/s, 측정 방식이 달라 참고만)`,
    `스윙 면 기울기: ${d.plane ?? "측정 불가"}° (0° 수평, 90° 수직)`,
    ...PHASES.map(ph => `${ph} 관절 각도: ` + ANGLES.map(k => `${k} ${d.angles[ph][k]}°`).join(", ")),
    `힘 전달(각 부위가 가장 빨라진 순서): ${d.order.join(" → ")} (${d.chainOk ? "정상 순서" : "순서 어긋남"})`,
    d.off.length
      ? "프로 범위를 벗어난 항목: " + d.off.map(o => `${o.phase} ${o.metric} ${o.value}° (프로 ${o.min}~${o.max}°, ${o.status === "low" ? "작음" : "큼"})`).join("; ")
      : "프로 범위를 벗어난 항목: 없음 (팔꿈치·몸통 꼬임은 기준이 없어 판정하지 않음)",
  ];
  return [
    { role: "system", content: "너는 생활체육 탁구 동호인을 돕는 친절한 코치다. 아래 측정값만 근거로 조언한다. 측정값에 없는 내용은 지어내지 않는다. 의학적 진단이나 부상 판단은 하지 않는다. 한국어 해요체로 쓴다. 우선순위: 힘 전달 순서가 어긋났으면 그것을 오늘의 과제로 가장 먼저 다루고, 정상이면 프로 범위를 벗어난 항목 중 하나를 고른다. '잘하고 있는 점'은 프로 범위 안에 든 항목이나 정상인 힘 전달 순서처럼 근거가 있는 것에서만 고르고, 근거가 없으면 '꾸준히 영상을 찍어 확인하는 습관'처럼 일반적인 칭찬을 한다." },
    { role: "user", content: `다음은 폰 영상으로 분석한 내 포핸드 스윙 측정값이야.\n${lines.join("\n")}\n\n다음 형식으로 답해 줘. 다른 말은 붙이지 마.\n오늘의 과제: (가장 중요한 한 가지, 한 문장)\n왜 중요해요: (측정값을 근거로 한두 문장)\n연습 방법: (집이나 탁구장에서 할 수 있는 드릴 하나, 횟수 포함)\n잘하고 있는 점: (한 문장)\n/no_think` }, // Qwen3: 생각 과정 없이 바로 답하게
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
      const out = await env.AI.run(MODEL, { messages: prompt(data), max_tokens: 800, temperature: 0.4 });
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
