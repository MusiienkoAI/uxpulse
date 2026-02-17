type UXPulseEvent = {
  event_id: string;
  name: string;
  ts: string;
  user_id: string;
  session_id: string;
  platform: "ios" | "android";
  app_version: string;
  os_version: string;
  device_model: string;
  screen?: string;
  source?: string;
  props?: Record<string, unknown>;
};

type SDKConfig = {
  baseUrl: string;
  userId: string;
  sessionId: string;
  platform: "ios" | "android";
  appVersion: string;
  osVersion: string;
  deviceModel: string;
};

let cfg: SDKConfig | null = null;
const queue: UXPulseEvent[] = [];
let flushTimer: ReturnType<typeof setInterval> | null = null;

export function initUXPulse(config: SDKConfig): void {
  cfg = config;
  if (!flushTimer) {
    flushTimer = setInterval(() => {
      void flushEvents();
    }, 5000);
  }
}

export function trackScreen(screen: string, source?: string): void {
  trackEvent("screen_view", { screen, source });
}

export async function trackedFetch(
  endpoint: string,
  init?: RequestInit & { screen?: string; source?: string }
): Promise<Response> {
  const start = Date.now();
  try {
    const res = await fetch(endpoint, init);
    const apiMs = Date.now() - start;
    trackEvent(res.ok ? "api_ok" : "api_error", {
      screen: init?.screen,
      source: init?.source,
      endpoint,
      status: res.status,
      api_ms: apiMs,
    });
    return res;
  } catch (err) {
    const apiMs = Date.now() - start;
    trackEvent("api_error", {
      screen: init?.screen,
      source: init?.source,
      endpoint,
      api_ms: apiMs,
      error: err instanceof Error ? err.message : String(err),
    });
    throw err;
  }
}

export function trackEvent(
  name: string,
  opts?: { screen?: string; source?: string } & Record<string, unknown>
): void {
  if (!cfg) {
    return;
  }
  const event: UXPulseEvent = {
    event_id: `evt_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    name,
    ts: new Date().toISOString(),
    user_id: cfg.userId,
    session_id: cfg.sessionId,
    platform: cfg.platform,
    app_version: cfg.appVersion,
    os_version: cfg.osVersion,
    device_model: cfg.deviceModel,
    screen: opts?.screen,
    source: opts?.source,
    props: opts ?? {},
  };
  queue.push(event);
}

export async function flushEvents(): Promise<void> {
  if (!cfg || queue.length === 0) {
    return;
  }
  const payload = { events: queue.splice(0, queue.length) };
  await fetch(`${cfg.baseUrl}/v1/events/batch`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}
