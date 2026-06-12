export type ApiErrorDetails = Record<string, unknown> | unknown[] | null;

export type ApiErrorBody = {
  code: string;
  message: string;
  details: ApiErrorDetails;
};

export type ApiErrorResponse = {
  error: ApiErrorBody;
};

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

export type LanguageCode = "fr" | "nl" | "de" | "en";

export type Patient = {
  id: string;
  created_at: string;
  updated_at: string;
  first_name: string;
  last_name: string;
  date_of_birth: string;
  preferred_language: LanguageCode;
  email: string | null;
  phone: string | null;
  street_line1: string | null;
  street_line2: string | null;
  postal_code: string | null;
  city: string | null;
  country_code: string;
};

export type PatientCreate = {
  first_name: string;
  last_name: string;
  date_of_birth: string;
  preferred_language?: LanguageCode;
  email?: string | null;
  phone?: string | null;
  street_line1?: string | null;
  street_line2?: string | null;
  postal_code?: string | null;
  city?: string | null;
  country_code?: string;
};

export type PatientUpdate = {
  first_name?: string | null;
  last_name?: string | null;
  date_of_birth?: string | null;
  preferred_language?: LanguageCode | null;
  email?: string | null;
  phone?: string | null;
  street_line1?: string | null;
  street_line2?: string | null;
  postal_code?: string | null;
  city?: string | null;
  country_code?: string | null;
};

export type PatientListQuery = {
  q?: string;
  first_name?: string;
  last_name?: string;
  email?: string;
  city?: string;
  postal_code?: string;
  country_code?: string;
  preferred_language?: LanguageCode;
  offset?: number;
  limit?: number;
};

export type PatientListResponse = {
  items: Patient[];
  total: number;
  offset: number;
  limit: number;
};
