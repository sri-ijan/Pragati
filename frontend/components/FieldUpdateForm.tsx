"use client";

import { useState } from "react";
import type { DocumentSummary } from "@/services/apiClient";
import { getDocuments, uploadDocument } from "@/services/apiClient";

export default function FieldUpdateForm({ projectId }: { projectId: string }) {
  const [text, setText] = useState("");
  const [status, setStatus] = useState<"idle" | "uploading" | "error">("idle");
  const [error, setError] = useState<string | null>(null);
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);

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
    // A typed update is wrapped as a .txt file — same upload endpoint/contract
    // handles it, no separate "text update" shape needed.
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

      <button
        onClick={refresh}
        className="text-sm font-medium text-gray-700 underline"
      >
        Load submitted updates
      </button>

      {documents.length > 0 && (
        <ul className="space-y-1 text-sm">
          {documents.map((d) => (
            <li key={d.source_document_id} className="flex items-center justify-between border-b py-1">
              <span>{d.filename}</span>
              <span className="text-gray-500">
                {d.processable_now ? "received" : "received — extraction not built yet"}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}