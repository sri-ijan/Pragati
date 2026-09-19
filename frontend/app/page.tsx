"use client";

import { useEffect, useState } from "react";
import ProjectCreateForm from "@/components/ProjectCreateForm";
import ScheduleUploadForm from "@/components/ScheduleUploadForm";
import FieldUpdateForm from "@/components/FieldUpdateForm";

// Frontend-only persistence so a page refresh doesn't drop the user back to
// the Create Project form. Not a backend session — just remembers the last
// project this browser created/used.
const PROJECT_ID_STORAGE_KEY = "setuai:projectId";

export default function Home() {
  const [projectId, setProjectId] = useState<string | null>(null);
  // Gates the first render so we don't flash "Create Project" before
  // localStorage has been checked (localStorage isn't available during SSR).
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    const stored = window.localStorage.getItem(PROJECT_ID_STORAGE_KEY);
    if (stored) setProjectId(stored);
    setHydrated(true);
  }, []);

  function handleProjectCreated(newProjectId: string) {
    window.localStorage.setItem(PROJECT_ID_STORAGE_KEY, newProjectId);
    setProjectId(newProjectId);
  }

  if (!hydrated) {
    return (
      <main className="flex min-h-screen flex-col items-center p-12">
        <div className="w-full max-w-2xl">
          <p className="text-sm text-gray-500">Loading...</p>
        </div>
      </main>
    );
  }

  return (
    <main className="flex min-h-screen flex-col items-center p-12">
      <div className="w-full max-w-2xl space-y-10">
        <div>
          <h1 className="text-2xl font-semibold">SetuAI</h1>
          <p className="mt-1 text-sm text-gray-500">
            Slice 1 (schedule upload) + Slice 2 (field update intake). No matching/extraction yet.
          </p>
        </div>

        {!projectId ? (
          <ProjectCreateForm onCreated={handleProjectCreated} />
        ) : (
          <>
            <p className="text-sm text-gray-500">Project ID: {projectId}</p>
            <ScheduleUploadForm projectId={projectId} />
            <FieldUpdateForm projectId={projectId} />
          </>
        )}
      </div>
    </main>
  );
}