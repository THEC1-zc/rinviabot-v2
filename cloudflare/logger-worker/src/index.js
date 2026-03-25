function unauthorized() {
  return new Response(JSON.stringify({ ok: false, error: "Unauthorized" }), {
    status: 401,
    headers: { "content-type": "application/json" },
  });
}

function jsonResponse(payload, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function normalizeString(value) {
  if (value === null || value === undefined) return "";
  return String(value);
}

async function ingest(request, env) {
  const auth = request.headers.get("authorization") || "";
  const expected = `Bearer ${env.LOG_INGEST_TOKEN || ""}`;

  if (!env.LOG_INGEST_TOKEN || auth !== expected) {
    return unauthorized();
  }

  let body;
  try {
    body = await request.json();
  } catch {
    return jsonResponse({ ok: false, error: "Invalid JSON body" }, 400);
  }

  const ts = normalizeString(body.ts);
  const traceId = normalizeString(body.trace_id);
  const stage = normalizeString(body.stage);

  if (!ts || !traceId || !stage) {
    return jsonResponse({
      ok: false,
      error: "Missing required fields: ts, trace_id, stage",
    }, 400);
  }

  const payloadJson = JSON.stringify(body);
  const textPreview = normalizeString(body.text).slice(0, 500);

  const stmt = env.DB.prepare(`
    INSERT INTO pipeline_events (
      ts,
      trace_id,
      stage,
      chat_id,
      message_id,
      user_id,
      username,
      text_preview,
      source,
      payload_json
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `).bind(
    ts,
    traceId,
    stage,
    normalizeString(body.chat_id),
    normalizeString(body.message_id),
    normalizeString(body.user_id),
    normalizeString(body.username),
    textPreview,
    normalizeString(body.source || "rinviabot-render"),
    payloadJson
  );

  const result = await stmt.run();
  return jsonResponse({ ok: true, result });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === "GET" && url.pathname === "/health") {
      const result = await env.DB.prepare("SELECT 1 AS ok").first();
      return jsonResponse({ ok: true, db: result });
    }

    if (request.method === "POST" && url.pathname === "/ingest") {
      return ingest(request, env);
    }

    return jsonResponse({ ok: false, error: "Not found" }, 404);
  },
};
