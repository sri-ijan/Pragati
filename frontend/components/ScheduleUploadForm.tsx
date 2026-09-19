"use client";

import { useEffect, useState } from "react";
import type { ScheduleActivity } from "@/types/shared";
import { getSchedule, uploadSchedule } from "@/services/apiClient";

type Status = "idle" | "loading" | "uploading" | "error";

export default function ScheduleUploadForm({ projectId }: { projectId: string }) {
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  // Only ever set from an actual upload response — never fabricated. Stays
  // null on a refresh-triggered reload, since GET /schedule doesn't return
  // an import count and we're not going to invent one.
  const [imported, setImported] = useState<number | null>(null);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [activities, setActivities] = useState<ScheduleActivity[]>([]);

  // Restores the table on mount/refresh so an existing schedule doesn't
  // require re-uploading the file just to see it again.
  useEffect(() => {
    let cancelled = false;

    async function loadExistingSchedule() {
      setStatus("loading");
      setError(null);
      try {
        const existing = await getSchedule(projectId);
        if (!cancelled) {
          setActivities(existing);
          setStatus("idle");
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load existing schedule.");
          setStatus("error");
        }
      }
    }

    loadExistingSchedule();
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setStatus("uploading");
    setError(null);
    try {
      const result = await uploadSchedule(projectId, file);
      setImported(result.activities_imported);
      setWarnings(result.warnings);
      setActivities(await getSchedule(projectId));
      setStatus("idle");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
      setStatus("error");
    }
  }

  return (
    <div className="w-full max-w-2xl space-y-4">
      <h2 className="text-lg font-semibold">Upload schedule</h2>
      <div className="space-y-2">
        <label className="block text-sm font-medium">Schedule file (.xlsx/.xls/.csv)</label>
        <input
          type="file"
          accept=".xlsx,.xls,.csv"
          onChange={handleFileChange}
          disabled={status === "uploading"}
        />
      </div>

      {status === "loading" && activities.length === 0 && (
        <p className="text-sm text-gray-500">Loading existing schedule...</p>
      )}

      {error && <p className="text-sm text-red-600">{error}</p>}

      {imported !== null && (
        <div className="space-y-2">
          <p className="text-sm font-medium">{imported} activities imported.</p>
          {warnings.length > 0 && (
            <ul className="list-disc pl-5 text-sm text-amber-600">
              {warnings.map((w, i) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {activities.length > 0 && (
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b text-left">
              <th className="py-1 pr-4">Activity ID</th>
              <th className="py-1 pr-4">Discipline</th>
              <th className="py-1 pr-4">Description</th>
              <th className="py-1 pr-4">Planned Start</th>
              <th className="py-1 pr-4">Planned Finish</th>
            </tr>
          </thead>
          <tbody>
            {activities.map((a) => (
              <tr key={a.activity_id} className="border-b">
                <td className="py-1 pr-4">{a.activity_id}</td>
                <td className="py-1 pr-4">{a.discipline}</td>
                <td className="py-1 pr-4">{a.description}</td>
                <td className="py-1 pr-4">{a.planned_start}</td>
                <td className="py-1 pr-4">{a.planned_finish}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}