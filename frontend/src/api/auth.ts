import { apiClient, type ApiClient } from "./client";
import type { CurrentUser, LoginRequest, TokenResponse } from "./types";

export function loginUser(
  payload: LoginRequest,
  client: ApiClient = apiClient,
): Promise<TokenResponse> {
  return client.post<TokenResponse, LoginRequest>("/auth/login", payload);
}

export function logoutUser(accessToken?: string, client: ApiClient = apiClient): Promise<void> {
  return client.post<void>("/auth/logout", undefined, { accessToken });
}

export function readCurrentUser(
  accessToken?: string,
  client: ApiClient = apiClient,
): Promise<CurrentUser> {
  return client.get<CurrentUser>("/auth/me", { accessToken });
}
