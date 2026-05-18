export type ApiErrorBody = {
  detail?: unknown;
  error?: {
    type?: string;
    message?: string;
  };
};

export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(status: number, message: string, body: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    }
  });

  const text = await response.text();
  let body: unknown = null;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = text;
  }

  if (!response.ok) {
    throw new ApiError(response.status, errorMessage(response.status, body), body);
  }

  return body as T;
}

export function errorMessage(status: number, body: unknown): string {
  const typed = body as ApiErrorBody | null;

  if (typed?.error?.type || typed?.error?.message) {
    const type = typed.error.type ? `${typed.error.type}: ` : "";
    return `${type}${typed.error.message || `HTTP ${status}`}`;
  }

  if (Array.isArray(typed?.detail)) {
    return typed.detail
      .map((item) => {
        if (typeof item !== "object" || item === null) return String(item);
        const record = item as Record<string, unknown>;
        const loc = Array.isArray(record.loc) ? record.loc.join(".") : "body";
        return `${loc}: ${record.msg || "validation error"}`;
      })
      .join("; ");
  }

  if (typeof typed?.detail === "string") {
    return typed.detail;
  }

  if (typeof body === "string" && body.trim()) {
    return body;
  }

  return `HTTP ${status}`;
}
