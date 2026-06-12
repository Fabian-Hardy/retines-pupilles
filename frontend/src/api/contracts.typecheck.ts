import { ApiClient, ApiError } from "./client";
import type {
  ApiErrorResponse,
  PatientCreate,
  PatientListQuery,
  PatientListResponse,
  PatientUpdate,
} from "./types";

const standardError = {
  error: {
    code: "validation_error",
    message: "Request validation failed",
    details: [{ loc: ["body", "email"], msg: "Invalid email", type: "value_error" }],
  },
} satisfies ApiErrorResponse;

const patientList = {
  items: [],
  total: 0,
  offset: 0,
  limit: 20,
} satisfies PatientListResponse;

const patientListQuery = {
  q: "dupont",
  preferred_language: "fr",
  offset: 0,
  limit: 20,
} satisfies PatientListQuery;

const patientCreate = {
  first_name: "Anne",
  last_name: "Dupont",
  date_of_birth: "1980-01-01",
  preferred_language: "fr",
  email: null,
} satisfies PatientCreate;

const patientUpdate = {
  city: "Bruxelles",
  country_code: null,
  phone: null,
} satisfies PatientUpdate;

const client = new ApiClient({
  baseUrl: "/api/v1",
  fetcher: async () => new Response(JSON.stringify(patientList)),
});

void client.get<PatientListResponse>("/patients", { query: patientListQuery });
void client.post<PatientCreate, PatientCreate>("/patients", patientCreate);
void client.patch<PatientUpdate, PatientUpdate>("/patients/patient-id", patientUpdate);

const apiError = new ApiError({
  code: standardError.error.code,
  details: standardError.error.details,
  message: standardError.error.message,
  status: 422,
});

const errorStatus: number = apiError.status;
const errorCode: string = apiError.code;
const errorDetails = apiError.details;

void errorStatus;
void errorCode;
void errorDetails;
