import { apiClient, type ApiClient } from "./client";
import type {
  Patient,
  PatientCreate,
  PatientListQuery,
  PatientListResponse,
  PatientUpdate,
} from "./types";

export function listPatients(
  query: PatientListQuery = {},
  client: ApiClient = apiClient,
): Promise<PatientListResponse> {
  return client.get<PatientListResponse>("/patients", { query });
}

export function getPatient(patientId: string, client: ApiClient = apiClient): Promise<Patient> {
  return client.get<Patient>(patientPath(patientId));
}

export function createPatient(
  payload: PatientCreate,
  client: ApiClient = apiClient,
): Promise<Patient> {
  return client.post<Patient, PatientCreate>("/patients", payload);
}

export function updatePatient(
  patientId: string,
  payload: PatientUpdate,
  client: ApiClient = apiClient,
): Promise<Patient> {
  return client.patch<Patient, PatientUpdate>(patientPath(patientId), payload);
}

export function deletePatient(patientId: string, client: ApiClient = apiClient): Promise<void> {
  return client.delete(patientPath(patientId));
}

function patientPath(patientId: string): string {
  return `/patients/${encodeURIComponent(patientId)}`;
}
