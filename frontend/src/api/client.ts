import type { ApiErrorDetails, ApiErrorResponse } from "./types";

type Fetcher = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;
type QueryValue = string | number | boolean | null | undefined;
type QueryParams = Record<string, QueryValue>;

export type ApiRequestOptions = {
  accessToken?: string | null | undefined;
  headers?: HeadersInit;
  query?: QueryParams;
  signal?: AbortSignal;
};

export type ApiClientConfig = {
  accessToken?: string | null;
  baseUrl?: string;
  fetcher?: Fetcher;
};

export const DEFAULT_API_BASE_URL = "/api/v1";

const GENERIC_ERROR_MESSAGE = "La requête a échoué.";
const NETWORK_ERROR_MESSAGE = "Connexion au serveur impossible.";

export class ApiError extends Error {
  readonly code: string;
  readonly details: ApiErrorDetails;
  readonly originalError: unknown;
  readonly status: number;

  constructor({
    code,
    details,
    message,
    originalError,
    status,
  }: {
    code: string;
    details: ApiErrorDetails;
    message: string;
    originalError?: unknown;
    status: number;
  }) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.details = details;
    this.originalError = originalError;
    this.status = status;
  }
}

export class ApiClient {
  private accessToken: string | null;
  private readonly baseUrl: string;
  private readonly fetcher: Fetcher;

  constructor(config: ApiClientConfig = {}) {
    this.accessToken = config.accessToken ?? null;
    this.baseUrl = normalizeBaseUrl(config.baseUrl ?? getConfiguredApiBaseUrl());
    this.fetcher = config.fetcher ?? fetch.bind(globalThis);
  }

  setAccessToken(accessToken: string): void {
    this.accessToken = accessToken;
  }

  clearAccessToken(): void {
    this.accessToken = null;
  }

  get<TResponse>(path: string, options: ApiRequestOptions = {}): Promise<TResponse> {
    return this.request<TResponse>(path, { ...options, method: "GET" });
  }

  post<TResponse, TPayload = undefined>(
    path: string,
    payload?: TPayload,
    options: ApiRequestOptions = {},
  ): Promise<TResponse> {
    return this.request<TResponse>(path, { ...options, body: payload, method: "POST" });
  }

  patch<TResponse, TPayload>(
    path: string,
    payload: TPayload,
    options: ApiRequestOptions = {},
  ): Promise<TResponse> {
    return this.request<TResponse>(path, { ...options, body: payload, method: "PATCH" });
  }

  delete(path: string, options: ApiRequestOptions = {}): Promise<void> {
    return this.request<void>(path, { ...options, method: "DELETE" });
  }

  private async request<TResponse>(
    path: string,
    options: ApiRequestOptions & { body?: unknown; method: string },
  ): Promise<TResponse> {
    const headers = createHeaders(options.headers);
    const accessToken = options.accessToken === undefined ? this.accessToken : options.accessToken;

    if (accessToken) {
      headers.set("Authorization", `Bearer ${accessToken}`);
    }

    let body: BodyInit | undefined;
    if ("body" in options && options.body !== undefined) {
      headers.set("Content-Type", "application/json");
      body = JSON.stringify(options.body);
    }

    let response: Response;
    try {
      const requestInit: RequestInit = {
        headers,
        method: options.method,
      };

      if (body !== undefined) {
        requestInit.body = body;
      }

      if (options.signal) {
        requestInit.signal = options.signal;
      }

      response = await this.fetcher(buildUrl(this.baseUrl, path, options.query), requestInit);
    } catch (error) {
      throw new ApiError({
        code: "network_error",
        details: null,
        message: NETWORK_ERROR_MESSAGE,
        originalError: error,
        status: 0,
      });
    }

    if (!response.ok) {
      throw await readApiError(response);
    }

    if (response.status === 204) {
      return undefined as TResponse;
    }

    return (await response.json()) as TResponse;
  }
}

export const apiClient = new ApiClient();

function getConfiguredApiBaseUrl(): string {
  return import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL;
}

function normalizeBaseUrl(baseUrl: string): string {
  const trimmedBaseUrl = baseUrl.trim();

  if (trimmedBaseUrl === "") {
    return DEFAULT_API_BASE_URL;
  }

  return trimmedBaseUrl.endsWith("/") ? trimmedBaseUrl.slice(0, -1) : trimmedBaseUrl;
}

function buildUrl(baseUrl: string, path: string, query?: QueryParams): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const search = new URLSearchParams();

  Object.entries(query ?? {}).forEach(([key, value]) => {
    if (value !== null && value !== undefined) {
      search.set(key, String(value));
    }
  });

  const queryString = search.toString();
  return `${baseUrl}${normalizedPath}${queryString ? `?${queryString}` : ""}`;
}

function createHeaders(headers?: HeadersInit): Headers {
  const requestHeaders = new Headers(headers);
  requestHeaders.set("Accept", "application/json");
  return requestHeaders;
}

async function readApiError(response: Response): Promise<ApiError> {
  const body = await readJsonBody(response);

  if (isApiErrorResponse(body)) {
    return new ApiError({
      code: body.error.code,
      details: body.error.details,
      message: body.error.message,
      status: response.status,
    });
  }

  return new ApiError({
    code: response.status === 0 ? "network_error" : "http_error",
    details: null,
    message: response.statusText || GENERIC_ERROR_MESSAGE,
    status: response.status,
  });
}

async function readJsonBody(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

function isApiErrorResponse(value: unknown): value is ApiErrorResponse {
  if (!isRecord(value) || !isRecord(value.error)) {
    return false;
  }

  return (
    typeof value.error.code === "string" &&
    typeof value.error.message === "string" &&
    isApiErrorDetails(value.error.details)
  );
}

function isApiErrorDetails(value: unknown): value is ApiErrorDetails {
  return value === null || Array.isArray(value) || isRecord(value);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
