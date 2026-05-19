<template>
  <div class="shell">
    <header class="topbar">
      <div>
        <h1>LLM ComputeOps & Eval Hub</h1>
        <p>Day 1 local validation console</p>
      </div>
      <nav>
        <a href="/deployment" target="_blank" rel="noreferrer">部署文档</a>
        <a href="/api/docs" target="_blank" rel="noreferrer">API Docs</a>
      </nav>
    </header>

    <main>
      <aside class="stack">
        <section>
          <h2>账户</h2>
          <label>
            用户名
            <input v-model.trim="username" autocomplete="username">
          </label>
          <label>
            密码
            <span class="password-field">
              <input
                v-model="password"
                :type="passwordVisible ? 'text' : 'password'"
                autocomplete="current-password"
              >
              <button
                class="icon-button password-toggle"
                type="button"
                :aria-label="passwordVisible ? '隐藏密码' : '显示密码'"
                @click="passwordVisible = !passwordVisible"
              >
                <svg
                  v-if="passwordVisible"
                  viewBox="0 0 24 24"
                  aria-hidden="true"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <path d="m2 2 20 20" />
                  <path d="M10.6 10.6a2 2 0 0 0 2.8 2.8" />
                  <path d="M9.9 4.2A10.7 10.7 0 0 1 12 4c7 0 10 8 10 8a18.5 18.5 0 0 1-2.1 3.2" />
                  <path d="M6.6 6.6C3.5 8.7 2 12 2 12s3 8 10 8a9.7 9.7 0 0 0 5.4-1.6" />
                </svg>
                <svg
                  v-else
                  viewBox="0 0 24 24"
                  aria-hidden="true"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" />
                  <circle cx="12" cy="12" r="3" />
                </svg>
              </button>
            </span>
          </label>
          <div class="actions">
            <button :disabled="busy.auth" @click="register">注册</button>
            <button class="secondary" :disabled="busy.auth" @click="login">登录</button>
          </div>
          <StatusLine :status="status.auth" />
        </section>

        <section>
          <h2>API Key</h2>
          <label>
            Key 名称
            <input v-model.trim="keyName">
          </label>
          <div class="actions">
            <button :disabled="busy.key" @click="createApiKey">生成 API Key</button>
          </div>
          <StatusLine :status="status.key" />
          <pre v-if="apiKey" class="secret">{{ apiKey }}</pre>
        </section>

        <section>
          <h2>当前凭证</h2>
          <label>
            Access Token
            <textarea v-model.trim="accessToken" spellcheck="false" />
          </label>
          <label>
            API Key
            <textarea v-model.trim="apiKey" spellcheck="false" />
          </label>
        </section>
      </aside>

      <div class="stack">
        <section>
          <div class="section-head">
            <h2>模型与聊天</h2>
            <button class="secondary" :disabled="busy.models" @click="loadModels">
              加载模型
            </button>
          </div>
          <StatusLine :status="status.models" />

          <div class="grid">
            <label>
              模型
              <select v-model="selectedModel">
                <option v-for="item in models" :key="item.model" :value="item.model">
                  {{ item.model }} ({{ item.provider }})
                </option>
              </select>
            </label>
            <label>
              Max Tokens
              <input v-model.number="maxTokens" type="number" min="1" max="4096">
            </label>
          </div>

          <label>
            Temperature
            <input v-model.number="temperature" type="number" min="0" max="2" step="0.1">
          </label>
          <label>
            用户消息
            <textarea v-model="prompt" />
          </label>

          <div class="actions">
            <button :disabled="busy.chat" @click="sendChat">
              发送到 /v1/chat/completions
            </button>
          </div>
          <StatusLine :status="status.chat" />
          <pre class="result">{{ chatResult }}</pre>
        </section>

        <section>
          <div class="section-head">
            <h2>请求日志</h2>
            <button class="secondary" :disabled="busy.logs" @click="loadLogs">
              刷新日志
            </button>
          </div>
          <StatusLine :status="status.logs" />
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Request ID</th>
                  <th>Status</th>
                  <th>Model</th>
                  <th>Latency</th>
                  <th>Prompt</th>
                  <th>Output/Error</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in logs" :key="item.request_id">
                  <td class="nowrap">{{ item.request_id }}</td>
                  <td>{{ item.status }}</td>
                  <td>{{ item.model }}</td>
                  <td>{{ formatLatency(item.e2e_latency_ms) }}</td>
                  <td>{{ item.prompt_preview }}</td>
                  <td>{{ item.output_preview || item.error_type }}</td>
                </tr>
                <tr v-if="logs.length === 0">
                  <td colspan="6" class="empty">暂无日志</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section>
          <div class="section-head">
            <h2>批量评测</h2>
            <button class="secondary" :disabled="busy.evalRuns" @click="loadEvalRuns">
              刷新 Eval Runs
            </button>
          </div>
          <StatusLine :status="status.eval" />
          <div class="grid">
            <label>
              Case File
              <input v-model.trim="evalCaseFile">
            </label>
            <label>
              Model
              <select v-model="selectedModel">
                <option v-for="item in models" :key="item.model" :value="item.model">
                  {{ item.model }} ({{ item.provider }})
                </option>
              </select>
            </label>
          </div>
          <div class="grid">
            <label>
              Concurrency
              <input v-model.number="evalConcurrency" type="number" min="1" max="32">
            </label>
            <label>
              Timeout ms
              <input v-model.number="evalTimeoutMs" type="number" min="1">
            </label>
          </div>
          <label>
            Retry Count
            <input v-model.number="evalRetryCount" type="number" min="0" max="10">
          </label>
          <div class="actions">
            <button :disabled="busy.eval" @click="runEval">运行 Eval</button>
          </div>
          <pre class="result">{{ evalResult }}</pre>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Run ID</th>
                  <th>Status</th>
                  <th>Model</th>
                  <th>Total</th>
                  <th>Pass</th>
                  <th>Fail</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in evalRuns" :key="item.run_id">
                  <td class="nowrap">{{ item.run_id }}</td>
                  <td>{{ item.status }}</td>
                  <td>{{ item.model }}</td>
                  <td>{{ item.total_cases }}</td>
                  <td>{{ item.eval_pass_count }}</td>
                  <td>{{ item.eval_fail_count }}</td>
                </tr>
                <tr v-if="evalRuns.length === 0">
                  <td colspan="6" class="empty">暂无 Eval Run</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from "vue";
import { ApiError, apiRequest } from "./api";

type StatusKind = "idle" | "loading" | "success" | "error";

type StatusState = {
  kind: StatusKind;
  message: string;
};

type ModelItem = {
  provider: string;
  model: string;
  display_name?: string;
  active: boolean;
};

type RequestLog = {
  request_id: string;
  model: string;
  provider: string;
  status: string;
  prompt_preview: string | null;
  output_preview: string | null;
  input_tokens: number | null;
  output_tokens: number | null;
  total_tokens: number | null;
  e2e_latency_ms: number | null;
  ttft_ms: number | null;
  tokens_per_second: number | null;
  error_type: string | null;
  created_at: string;
};

type EvalRun = {
  run_id: string;
  status: string;
  model: string;
  total_cases: number;
  eval_pass_count: number;
  eval_fail_count: number;
};

const username = ref("demo");
const password = ref("123456");
const passwordVisible = ref(false);
const keyName = ref("local-test-key");
const accessToken = ref("");
const apiKey = ref("");
const models = ref<ModelItem[]>([
  {
    provider: "ollama",
    model: "qwen2.5:1.5b",
    display_name: "Qwen2.5 1.5B via Ollama",
    active: true
  }
]);
const selectedModel = ref("qwen2.5:1.5b");
const temperature = ref(0.2);
const maxTokens = ref(128);
const prompt = ref("用一句话解释什么是 TTFT");
const chatResult = ref("");
const logs = ref<RequestLog[]>([]);
const evalCaseFile = ref("eval_cases/smoke_cases.jsonl");
const evalConcurrency = ref(2);
const evalTimeoutMs = ref(60000);
const evalRetryCount = ref(1);
const evalResult = ref("");
const evalRuns = ref<EvalRun[]>([]);

const busy = reactive({
  auth: false,
  key: false,
  models: false,
  chat: false,
  logs: false,
  eval: false,
  evalRuns: false
});

const status = reactive<Record<string, StatusState>>({
  auth: idle(),
  key: idle(),
  models: idle(),
  chat: idle(),
  logs: idle(),
  eval: idle(),
  evalRuns: idle()
});

const authHeader = computed(() => ({ Authorization: `Bearer ${accessToken.value}` }));
const apiKeyHeader = computed(() => ({ Authorization: `Bearer ${apiKey.value}` }));

async function register() {
  await run("auth", async () => {
    const body = await apiRequest<{ user_id: string; username: string }>(
      "/api/auth/register",
      {
        method: "POST",
        body: JSON.stringify({ username: username.value, password: password.value })
      }
    );
    status.auth = ok(`注册成功: ${body.user_id}`);
  });
}

async function login() {
  await run("auth", async () => {
    const body = await apiRequest<{ access_token: string; user_id: string }>(
      "/api/auth/login",
      {
        method: "POST",
        body: JSON.stringify({ username: username.value, password: password.value })
      }
    );
    accessToken.value = body.access_token;
    status.auth = ok(`登录成功: ${body.user_id}`);
  });
}

async function createApiKey() {
  await run("key", async () => {
    requireValue(accessToken.value, "请先登录，再生成 API Key");
    const body = await apiRequest<{
      api_key: string;
      api_key_prefix: string;
      name: string | null;
    }>("/api/api-keys", {
      method: "POST",
      headers: authHeader.value,
      body: JSON.stringify({ name: keyName.value || null })
    });
    apiKey.value = body.api_key;
    status.key = ok(`创建成功，prefix: ${body.api_key_prefix}`);
  });
}

async function loadModels() {
  await run("models", async () => {
    const token = accessToken.value || apiKey.value;
    requireValue(token, "请先登录或填写 API Key");
    const body = await apiRequest<{ models: ModelItem[] }>("/api/models", {
      headers: { Authorization: `Bearer ${token}` }
    });
    models.value = body.models;
    if (body.models[0]) selectedModel.value = body.models[0].model;
    status.models = ok(`加载模型成功: ${body.models.length}`);
  });
}

async function sendChat() {
  await run("chat", async () => {
    requireValue(apiKey.value, "请先生成或填写 API Key");
    chatResult.value = "";
    const body = await apiRequest<unknown>("/v1/chat/completions", {
      method: "POST",
      headers: apiKeyHeader.value,
      body: JSON.stringify({
        model: selectedModel.value,
        messages: [{ role: "user", content: prompt.value }],
        temperature: temperature.value,
        max_tokens: maxTokens.value,
        stream: false,
        metadata: { source: "vue_web_ui", prompt_version: "v1" }
      })
    });
    chatResult.value = JSON.stringify(body, null, 2);
    const record = body as { request_id?: string };
    status.chat = ok(`成功: ${record.request_id || "request complete"}`);
  });
}

async function loadLogs() {
  await run("logs", async () => {
    requireValue(accessToken.value, "请先登录，再查看请求日志");
    const body = await apiRequest<{ requests: RequestLog[] }>("/api/requests?limit=20", {
      headers: authHeader.value
    });
    logs.value = body.requests;
    status.logs = ok(`已加载 ${body.requests.length} 条日志`);
  });
}

async function runEval() {
  await run("eval", async () => {
    requireValue(accessToken.value, "请先登录，再运行 Eval");
    evalResult.value = "";
    const body = await apiRequest<unknown>("/api/eval/runs", {
      method: "POST",
      headers: authHeader.value,
      body: JSON.stringify({
        name: "web-smoke-eval",
        model: selectedModel.value,
        case_file: evalCaseFile.value,
        concurrency: evalConcurrency.value,
        timeout_ms: evalTimeoutMs.value,
        retry_count: evalRetryCount.value
      })
    });
    evalResult.value = JSON.stringify(body, null, 2);
    const record = body as { run_id?: string };
    status.eval = ok(`完成: ${record.run_id || "eval run"}`);
    await loadEvalRuns();
  });
}

async function loadEvalRuns() {
  await run("evalRuns", async () => {
    requireValue(accessToken.value, "请先登录，再查看 Eval Runs");
    const body = await apiRequest<{ runs: EvalRun[] }>("/api/eval/runs", {
      headers: authHeader.value
    });
    evalRuns.value = body.runs;
    status.eval = ok(`已加载 ${body.runs.length} 个 Eval Run`);
  });
}

async function run(key: keyof typeof busy, action: () => Promise<void>) {
  busy[key] = true;
  status[key] = loading("请求中...");
  try {
    await action();
  } catch (error) {
    status[key] = fail(formatError(error));
  } finally {
    busy[key] = false;
  }
}

function requireValue(value: string, message: string) {
  if (!value.trim()) {
    throw new Error(message);
  }
}

function formatError(error: unknown): string {
  if (error instanceof ApiError) {
    return `HTTP ${error.status}: ${error.message}`;
  }
  if (error instanceof Error) return error.message;
  return String(error);
}

function formatLatency(value: number | null): string {
  if (value === null) return "";
  return `${Math.round(value)} ms`;
}

function idle(): StatusState {
  return { kind: "idle", message: "" };
}

function loading(message: string): StatusState {
  return { kind: "loading", message };
}

function ok(message: string): StatusState {
  return { kind: "success", message };
}

function fail(message: string): StatusState {
  return { kind: "error", message };
}
</script>

<script lang="ts">
import { defineComponent, type PropType } from "vue";

export default {
  components: {
    StatusLine: defineComponent({
      props: {
        status: {
          type: Object as PropType<{ kind: string; message: string }>,
          required: true
        }
      },
      template: '<p class="status" :class="status.kind">{{ status.message }}</p>'
    })
  }
};
</script>
