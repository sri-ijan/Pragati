"use client";

import { useState } from "react";
import type { ExecutionEvent, MatchRecord } from "@/types/shared";
import type { DocumentSummary } from "@/services/apiClient";
import { extractEvent, getDocuments, matchEvent, uploadDocument } from "@/services/apiClient";

type ExtractionState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "success"; event: ExecutionEvent }
  | { kind: "error"; message: string };

type MatchState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "success"; candidates: MatchRecord[] }
  | { kind: "error"; message: string };

function decisionLabel(decision: MatchRecord["decision"]): string {
  switch (decision) {
    case "auto_match":
      return "Suggested match";
    case "review_required":
      return "Needs review";
    case "unmatched":
      return "Unmatched";
    default:
      return decision;
  }
}

export default function FieldUpdateForm({ projectId }: { projectId: string }) {
  const [text, setText] = useState("");
  const [status, setStatus] = useState<"idle" | "uploading" | "error">("idle");
  const [error, setError] = useState<string | null>(null);
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [extractions, setExtractions] = useState<Record<string, ExtractionState>>({});
  const [matches, setMatches] = useState<Record<string, MatchState>>({});

  async function refresh() {
    setDocuments(await getDocuments(projectId));
  }

  async function submit(file: File) {
    setStatus("uploading");
    setError(null);
    try {
      await uploadDocument(projectId, file);
      await refresh();
      setStatus("idle");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
      setStatus("error");
    }
  }

  async function handleTextSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;
    const file = new File([text.trim()], `field-update-${Date.now()}.txt`, {
      type: "text/plain",
    });
    await submit(file);
    setText("");
  }

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) await submit(file);
  }

  async function handleExtract(sourceDocumentId: string) {
    setExtractions((prev) => ({ ...prev, [sourceDocumentId]: { kind: "loading" } }));
    try {
      const result = await extractEvent(projectId, sourceDocumentId);
      const event = result.events[0];
      setExtractions((prev) => ({
        ...prev,
        [sourceDocumentId]: event
          ? { kind: "success", event }
          : { kind: "error", message: "No structured event was returned." },
      }));
    } catch (err) {
      setExtractions((prev) => ({
        ...prev,
        [sourceDocumentId]: {
          kind: "error",
          message: err instanceof Error ? err.message : "Extraction failed.",
        },
      }));
    }
  }

  async function handleMatch(eventId: string) {
    setMatches((prev) => ({ ...prev, [eventId]: { kind: "loading" } }));
    try {
      const result = await matchEvent(eventId);
      setMatches((prev) => ({ ...prev, [eventId]: { kind: "success", candidates: result.candidates } }));
    } catch (err) {
      setMatches((prev) => ({
        ...prev,
        [eventId]: { kind: "error", message: err instanceof Error ? err.message : "Matching failed." },
      }));
    }
  }

  return (
    <div className="w-full max-w-2xl space-y-4">
      <h2 className="text-lg font-semibold">Submit a field update</h2>

      <form onSubmit={handleTextSubmit} className="space-y-2">
        <textarea
          className="w-full rounded border px-3 py-2 text-sm"
          rows={3}
          placeholder="24 inch spool erection at Rack B completed today."
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <button
          type="submit"
          disabled={status === "uploading"}
          className="rounded bg-black px-4 py-2 text-sm text-white disabled:opacity-50"
        >
          {status === "uploading" ? "Submitting..." : "Submit text update"}
        </button>
      </form>

      <div>
        <label className="block text-sm font-medium">
          Or upload a DPR / spreadsheet / image (.pdf, .txt, .docx, .xlsx, .csv, .jpg, .png)
        </label>
        <input
          type="file"
          accept=".pdf,.txt,.docx,.xlsx,.csv,.jpg,.jpeg,.png"
          onChange={handleFileChange}
          disabled={status === "uploading"}
        />
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <button onClick={refresh} className="text-sm font-medium text-gray-700 underline">
        Load submitted updates
      </button>

      {documents.length > 0 && (
        <ul className="space-y-3 text-sm">
          {documents.map((d) => {
            const extraction = extractions[d.source_document_id] ?? { kind: "idle" as const };
            const matchState =
              extraction.kind === "success"
                ? matches[extraction.event.event_id] ?? { kind: "idle" as const }
                : { kind: "idle" as const };

            return (
              <li key={d.source_document_id} className="border-b pb-3">
                <div className="flex items-center justify-between py-1">
                  <span>{d.filename}</span>
                  <div className="flex items-center gap-3">
                    <span className="text-gray-500">
                      {d.processable_now ? "received" : "received — extraction not supported for this file type"}
                    </span>
                    {d.processable_now && (
                      <button
                        onClick={() => handleExtract(d.source_document_id)}
                        disabled={extraction.kind === "loading"}
                        className="rounded border px-2 py-1 text-xs font-medium disabled:opacity-50"
                      >
                        {extraction.kind === "loading" ? "Extracting..." : "Extract"}
                      </button>
                    )}
                  </div>
                </div>

                {extraction.kind === "error" && (
                  <p className="text-xs text-red-600">{extraction.message}</p>
                )}

                {extraction.kind === "success" && (
                  <div className="mt-2 space-y-2 rounded border border-amber-300 bg-amber-50 p-3">
                    <p className="text-xs font-semibold uppercase tracking-wide text-amber-700">
                      AI-extracted structured event
                    </p>
                    <table className="w-full text-xs">
                      <tbody>
                        <tr>
                          <td className="pr-3 font-medium text-gray-600">Discipline</td>
                          <td>{extraction.event.discipline}</td>
                        </tr>
                        <tr>
                          <td className="pr-3 font-medium text-gray-600">Activity</td>
                          <td>{extraction.event.activity_description}</td>
                        </tr>
                        <tr>
                          <td className="pr-3 font-medium text-gray-600">Action</td>
                          <td>{extraction.event.action}</td>
                        </tr>
                        <tr>
                          <td className="pr-3 font-medium text-gray-600">Status</td>
                          <td>{extraction.event.status}</td>
                        </tr>
                        <tr>
                          <td className="pr-3 font-medium text-gray-600">Location</td>
                          <td>{extraction.event.location}</td>
                        </tr>
                        <tr>
                          <td className="pr-3 font-medium text-gray-600">Event date</td>
                          <td>{extraction.event.event_date}</td>
                        </tr>
                        {extraction.event.quantity !== null && (
                          <tr>
                            <td className="pr-3 font-medium text-gray-600">Quantity</td>
                            <td>
                              {extraction.event.quantity}
                              {extraction.event.unit ?? ""}
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                    <div className="border-t border-amber-200 pt-2">
                      <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                        Raw field evidence
                      </p>
                      <p className="text-xs italic text-gray-600">{extraction.event.raw_text}</p>
                    </div>

                    <div className="border-t border-amber-200 pt-2">
                      <button
                        onClick={() => handleMatch(extraction.event.event_id)}
                        disabled={matchState.kind === "loading"}
                        className="rounded border border-amber-400 bg-white px-2 py-1 text-xs font-medium disabled:opacity-50"
                      >
                        {matchState.kind === "loading" ? "Matching..." : "Find Schedule Matches"}
                      </button>

                      {matchState.kind === "error" && (
                        <p className="mt-2 text-xs text-red-600">{matchState.message}</p>
                      )}

                      {matchState.kind === "success" && (
                        <div className="mt-2 space-y-2">
                          <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                            Schedule candidates
                          </p>
                          {matchState.candidates.length === 0 ? (
                            <p className="text-xs text-gray-500">
                              No schedule activities of a matching discipline were found.
                            </p>
                          ) : (
                            matchState.candidates.map((candidate) => (
                              <div
                                key={candidate.candidate_activity_id}
                                className="rounded border border-gray-200 bg-white p-2 text-xs"
                              >
                                <div className="flex items-center justify-between">
                                  <span className="font-medium">{candidate.candidate_activity_id}</span>
                                  <span>
                                    {Math.round(candidate.final_confidence * 100)}% —{" "}
                                    {decisionLabel(candidate.decision)}
                                  </span>
                                </div>

                                <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-gray-600">
                                  <div>
                                    <dt className="font-medium">Final confidence</dt>
                                    <dd>{candidate.final_confidence.toFixed(4)}</dd>
                                  </div>
                                  <div>
                                    <dt className="font-medium">Decision</dt>
                                    <dd>{candidate.decision}</dd>
                                  </div>
                                  <div>
                                    <dt className="font-medium">Semantic score</dt>
                                    <dd>{candidate.semantic_score.toFixed(4)}</dd>
                                  </div>
                                  <div>
                                    <dt className="font-medium">Metadata score</dt>
                                    <dd>{candidate.metadata_score.toFixed(4)}</dd>
                                  </div>
                                  <div>
                                    <dt className="font-medium">Temporal score</dt>
                                    <dd>{candidate.temporal_score.toFixed(4)}</dd>
                                  </div>
                                  <div>
                                    <dt className="font-medium">LLM score</dt>
                                    <dd>{candidate.llm_score.toFixed(4)}</dd>
                                  </div>
                                  <div>
                                    <dt className="font-medium">Terminology score</dt>
                                    <dd>{candidate.terminology_score.toFixed(4)}</dd>
                                  </div>
                                </dl>

                                {candidate.reason.length > 0 && (
                                  <div className="mt-2 border-t border-gray-100 pt-2">
                                    <p className="font-medium text-gray-600">Reasons</p>
                                    <ul className="mt-1 list-disc pl-4 text-gray-600">
                                      {candidate.reason.map((r, i) => (
                                        <li key={i}>{r}</li>
                                      ))}
                                    </ul>
                                  </div>
                                )}
                              </div>
                            ))
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}