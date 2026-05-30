export type LoginRequest = {
  email: string;
  password: string;
};

export type TokenResponse = {
  access_token: string;
  token_type: "bearer";
};

export type CurrentUser = {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
  updated_at: string;
};

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

const AUTH_API_BASE = "/api/v1/auth";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

async function readErrorMessage(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json();

    if (isRecord(body) && typeof body.detail === "string") {
      return body.detail;
    }
  } catch {
    return "La requête a échoué.";
  }

  return "La requête a échoué.";
}

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new ApiError(response.status, await readErrorMessage(response));
  }

  return (await response.json()) as T;
}

export async function loginUser(payload: LoginRequest): Promise<TokenResponse> {
  const response = await fetch(`${AUTH_API_BASE}/login`, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  return readJson<TokenResponse>(response);
}

export async function readCurrentUser(accessToken: string): Promise<CurrentUser> {
  const response = await fetch(`${AUTH_API_BASE}/me`, {
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
  });

  return readJson<CurrentUser>(response);
}
