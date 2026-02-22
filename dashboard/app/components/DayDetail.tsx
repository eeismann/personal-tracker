"use client";

import { DayData } from "../types";

export function DayDetail({ data, date }: { data: DayData | null | undefined; date: Date }) {
  if (!data) {
    return (
      <div className="text-center text-[var(--subtle)] py-12">
        <p className="text-lg">No data for this day</p>
        <p className="text-sm mt-2">
          {date.toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric", year: "numeric" })}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-2xl md:text-3xl font-medium">
          {date.toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" })}
        </h3>
        {data.location && <p className="text-[var(--subtle)]">{data.location}</p>}
      </div>

      {/* Habits */}
      <div className="grid grid-cols-3 gap-4">
        <div className={`p-4 rounded-lg border ${data.habits.workout ? "border-emerald-500 bg-emerald-500/10" : "border-[var(--border)]"}`}>
          <p className="text-sm text-[var(--subtle)] mb-1">Workout</p>
          <p className="font-medium capitalize">{data.habits.workout || "Rest"}</p>
        </div>
        <div className={`p-4 rounded-lg border ${data.habits.sauna ? "border-emerald-500 bg-emerald-500/10" : "border-[var(--border)]"}`}>
          <p className="text-sm text-[var(--subtle)] mb-1">Sauna</p>
          <p className="font-medium">{data.habits.sauna ? "Yes" : "No"}</p>
        </div>
        <div className={`p-4 rounded-lg border ${data.habits.meditation ? "border-emerald-500 bg-emerald-500/10" : "border-[var(--border)]"}`}>
          <p className="text-sm text-[var(--subtle)] mb-1">Meditation</p>
          <p className="font-medium">{data.habits.meditation ? "Yes" : "No"}</p>
        </div>
      </div>

      {/* Oura Scores */}
      {(data.sleepScore || data.readinessScore || data.activityScore) && (
        <div className="grid grid-cols-3 gap-4">
          <div className="p-4 rounded-lg border border-[var(--border)]">
            <p className="text-sm text-[var(--subtle)] mb-1">Sleep Score</p>
            <p className="text-xl font-medium">{data.sleepScore ?? "—"}</p>
          </div>
          <div className="p-4 rounded-lg border border-[var(--border)]">
            <p className="text-sm text-[var(--subtle)] mb-1">Readiness</p>
            <p className="text-xl font-medium">{data.readinessScore ?? "—"}</p>
          </div>
          <div className="p-4 rounded-lg border border-[var(--border)]">
            <p className="text-sm text-[var(--subtle)] mb-1">Activity</p>
            <p className="text-xl font-medium">{data.activityScore ?? "—"}</p>
          </div>
        </div>
      )}

      {/* Health metrics */}
      <div className="grid grid-cols-3 gap-4">
        <div className="p-4 rounded-lg border border-[var(--border)]">
          <p className="text-sm text-[var(--subtle)] mb-1">Sleep</p>
          <p className="text-xl font-medium">{data.sleep ? `${data.sleep}h` : "—"}</p>
        </div>
        <div className="p-4 rounded-lg border border-[var(--border)]">
          <p className="text-sm text-[var(--subtle)] mb-1">Resting HR</p>
          <p className="text-xl font-medium">{data.restingHR ? `${data.restingHR} bpm` : "—"}</p>
        </div>
        <div className="p-4 rounded-lg border border-[var(--border)]">
          <p className="text-sm text-[var(--subtle)] mb-1">Steps</p>
          <p className="text-xl font-medium">{data.steps ? data.steps.toLocaleString() : "—"}</p>
        </div>
      </div>

      {/* Time tracking */}
      <div className="grid grid-cols-3 gap-4">
        <div className="p-4 rounded-lg border border-[var(--border)]">
          <p className="text-sm text-[var(--subtle)] mb-1">Work</p>
          <p className="text-xl font-medium">{data.timeWorking ? `${Math.round(data.timeWorking / 60)}h` : "—"}</p>
        </div>
        <div className="p-4 rounded-lg border border-[var(--border)]">
          <p className="text-sm text-[var(--subtle)] mb-1">Mood</p>
          <p className="text-xl font-medium">{data.mood ? `${data.mood}/5` : "—"}</p>
        </div>
        <div className="p-4 rounded-lg border border-[var(--border)]">
          <p className="text-sm text-[var(--subtle)] mb-1">Energy</p>
          <p className="text-xl font-medium">{data.energy ? `${data.energy}/5` : "—"}</p>
        </div>
      </div>

      {/* Weather */}
      {data.weatherHighF && (
        <div className="p-4 rounded-lg border border-[var(--border)]">
          <p className="text-sm text-[var(--subtle)] mb-1">Weather</p>
          <p className="font-medium">{data.weatherHighF}°F — {data.weatherCondition || "Unknown"}</p>
        </div>
      )}

      {data.notes && (
        <div className="p-4 rounded-lg border border-[var(--border)]">
          <p className="text-sm text-[var(--subtle)] mb-2">Notes</p>
          <p>{data.notes}</p>
        </div>
      )}
    </div>
  );
}
