"use client";

import { useState } from "react";
import { createProject } from "@/services/apiClient";

export default function ProjectCreateForm({
  onCreated,
}: {
  onCreated: (projectId: string) => void;
}) {
  const [name, setName] = useState("");
  const [status, setStatus] = useState<"idle" | "creating" | "error">("idle");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setStatus("creating");
    setError(null);
    try {
      const project = await createProject(name.trim());
      onCreated(project.project_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create project.");
      setStatus("error");
    }
  }

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-2xl space-y-2">
      <label className="block text-sm font-medium">Project name</label>
      <input
        className="w-full rounded border px-3 py-2"
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="Refinery Expansion Demo"
      />
      <button
        type="submit"
        disabled={status === "creating"}
        className="rounded bg-black px-4 py-2 text-white disabled:opacity-50"
      >
        {status === "creating" ? "Creating..." : "Create project"}
      </button>
      {error && <p className="text-sm text-red-600">{error}</p>}
    </form>
  );
}
