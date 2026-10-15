const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const path = require("node:path");
const { test } = require("node:test");
const vm = require("node:vm");
const ts = require("typescript");

// Compile the API module in isolation so tests use Node's real UTF-8 stream primitives.
const compiled = ts.transpileModule(readFileSync(path.join(__dirname, "../lib/api.ts"), "utf8"), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
}).outputText;

function api(fetch) {
  const exports = {};
  vm.runInNewContext(compiled, { exports, fetch, process: { env: {} }, TextDecoder });
  return exports;
}

const done = { type: "done", translation: "안녕하세요!", source: "eng_Latn", target: "kor_Hang", engine: "ollama" };
const args = ["Hello!", "eng_Latn", "kor_Hang", "ollama", {}];
const encode = (value) => new TextEncoder().encode(value);
const record = (value) => JSON.stringify(value) + "\n";

function streamed(chunks) {
  return new Response(new ReadableStream({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(typeof chunk === "string" ? encode(chunk) : chunk);
      controller.close();
    },
  }), { headers: { "Content-Type": "application/x-ndjson" } });
}

test("streams Korean across arbitrary byte boundaries and accepts a final record without newline", async () => {
  const bytes = encode(record({ type: "delta", text: "안녕" }) + "\r\n" + record({ type: "delta", text: "하세요!" }) + JSON.stringify(done));
  const deltas = [];
  const result = await api(async () => streamed(Array.from(bytes, (byte) => Uint8Array.of(byte))))
    .translateStream(...args, (text) => deltas.push(text));
  assert.deepEqual(deltas, ["안녕", "하세요!"]);
  assert.equal(result.translation, done.translation);
});

test("delivers partial output while the server is still generating", async () => {
  let controller;
  const response = new Response(new ReadableStream({ start(value) { controller = value; } }));
  let sawDelta;
  const partial = new Promise((resolve) => { sawDelta = resolve; });
  let finished = false;
  const result = api(async () => response).translateStream(...args, sawDelta).then((value) => {
    finished = true;
    return value;
  });
  controller.enqueue(encode(record({ type: "delta", text: "안녕" })));
  assert.equal(await partial, "안녕");
  assert.equal(finished, false);
  controller.enqueue(encode(record(done)));
  assert.equal((await result).translation, done.translation);
});

test("truncated output cannot be mistaken for a successful translation", async () => {
  const translate = api(async () => streamed([record({ type: "delta", text: "Partial" })])).translateStream;
  await assert.rejects(translate(...args, () => {}), /interrupted before it finished/);
});

test("stream errors after partial output reject and never retry", async () => {
  let calls = 0;
  const translate = api(async () => {
    calls++;
    return streamed([record({ type: "delta", text: "Partial" }) + record({ type: "error", detail: "Provider unavailable", status: 502 })]);
  }).translateStream;
  await assert.rejects(translate(...args, () => {}), /Provider unavailable/);
  assert.equal(calls, 1);
});

test("abort prevents later buffered deltas and completion from updating a stale request", async () => {
  const abort = new AbortController();
  const deltas = [];
  const translate = api(async () => streamed([
    record({ type: "delta", text: "First" }) + record({ type: "delta", text: "Stale" }) + record(done),
  ])).translateStream;
  await assert.rejects(translate(...args, (delta) => {
    deltas.push(delta);
    abort.abort();
  }, abort.signal), { name: "AbortError" });
  assert.deepEqual(deltas, ["First"]);
});

test("only missing streaming routes fall back to the legacy endpoint with the same headers", async () => {
  for (const status of [404, 405]) {
    const calls = [];
    const translate = api(async (url, options) => {
      calls.push({ url, options });
      return calls.length === 1
        ? new Response("", { status })
        : Response.json(done);
    }).translateStream;
    const keys = { openrouter: "test-only-key", openrouter_model: "vendor/model" };
    const result = await translate(...args.slice(0, 4), keys, () => {});
    assert.equal(result.translation, done.translation);
    assert.equal(calls.length, 2);
    assert.ok(calls[0].url.endsWith("/api/translate/stream"));
    assert.ok(calls[1].url.endsWith("/api/translate"));
    assert.equal(calls[1].options.headers["X-OpenRouter-Key"], keys.openrouter);
    assert.equal(calls[1].options.headers["X-OpenRouter-Model"], keys.openrouter_model);
    assert.equal(calls[1].options.body, calls[0].options.body);
  }
});

test("HTTP validation, limits and inference errors never invoke fallback", async () => {
  for (const status of [400, 401, 422, 429, 500, 502, 503]) {
    let calls = 0;
    const translate = api(async () => {
      calls++;
      return Response.json({ detail: "Request failed" }, { status });
    }).translateStream;
    await assert.rejects(translate(...args, () => {}), /Request failed/);
    assert.equal(calls, 1);
  }
});

test("malformed records and invalid done events fail instead of caching a partial result", async () => {
  for (const record of ["not-json\n", '{"type":"done"}\n', '{"type":"unexpected"}\n']) {
    await assert.rejects(api(async () => streamed([record])).translateStream(...args, () => {}), /response was invalid/);
  }
});
