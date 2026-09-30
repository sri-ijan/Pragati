// SetuAI — API client scaffolding.
//
// Base URL + a generic JSON fetch helper only. Endpoint-specific functions
// (uploadSchedule, submitFieldReport, approveMatch, ...) are added slice by
// slice against docs/API.md — none exist yet, matching backend/api's current
// scope (health only).

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function fetchJson<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.error?.message ?? `Request failed: ${res.status}`);
  }

  return res.json() as Promise<T>;
}

// --- Slice 1: schedule upload ---
// Endpoint-specific calls, added as their slice lands (docs/API.md).

import type { Project, ScheduleActivity, UploadScheduleResponse } from "@shared/types";

export async function createProject(name: string): Promise<Project> {
  return fetchJson<Project>("/projects", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export async function uploadSchedule(
  projectId: string,
  file: File
): Promise<UploadScheduleResponse> {
  const form = new FormData();
  form.append("file", file);

  const res = await fetch(`${API_BASE_URL}/projects/${projectId}/schedule/upload`, {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.error?.message ?? `Upload failed: ${res.status}`);
  }

  return res.json() as Promise<UploadScheduleResponse>;
}

export async function getSchedule(projectId: string): Promise<ScheduleActivity[]> {
  return fetchJson<ScheduleActivity[]>(`/projects/${projectId}/schedule`);
}

// --- Slice 2: field report / document upload ---

export interface DocumentSummary {
  source_document_id: string;
  filename: string;
  content_type: string;
  status: string;
  uploaded_at: string;
  processable_now: boolean;
}

export async function uploadDocument(
  projectId: string,
  file: File
): Promise<{ source_document_id: string; filename: string; status: string }> {
  const form = new FormData();
  form.append("file", file);

  const res = await fetch(`${API_BASE_URL}/projects/${projectId}/documents/upload`, {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.error?.message ?? `Upload failed: ${res.status}`);
  }

  return res.json();
}

export async function getDocuments(projectId: string): Promise<DocumentSummary[]> {
  return fetchJson<DocumentSummary[]>(`/projects/${projectId}/documents`);
}

// --- Slice 3: AI extraction ---

import type { ExecutionEvent } from "@shared/types";

export async function extractEvent(
  projectId: string,
  sourceDocumentId: string
): Promise<{ events: ExecutionEvent[] }> {
  return fetchJson<{ events: ExecutionEvent[] }>(`/projects/${projectId}/extract`, {
    method: "POST",
    body: JSON.stringify({ source_document_id: sourceDocumentId }),
  });
}

export async function getEvents(projectId: string): Promise<ExecutionEvent[]> {
  return fetchJson<ExecutionEvent[]>(`/projects/${projectId}/events`);
}

// --- Slice 4: matching ---

import type { MatchRecord } from "@shared/types";

export async function matchEvent(eventId: string): Promise<{ event_id: string; candidates: MatchRecord[] }> {
  return fetchJson<{ event_id: string; candidates: MatchRecord[] }>(`/events/${eventId}/match`, {
    method: "POST",
  });
}

export async function getCandidates(eventId: string): Promise<{ event_id: string; candidates: MatchRecord[] }> {
  return fetchJson<{ event_id: string; candidates: MatchRecord[] }>(`/events/${eventId}/candidates`);
}