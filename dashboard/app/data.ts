import { TrackerData } from "./types";

let cached: TrackerData | null = null;

export async function fetchTrackerData(): Promise<TrackerData> {
  if (cached) return cached;

  try {
    const response = await fetch("/data/tracker.json");
    const data = await response.json();
    cached = data as TrackerData;
    return cached;
  } catch (error) {
    console.error("Failed to load tracker data:", error);
    return { days: {}, generated: "" };
  }
}
