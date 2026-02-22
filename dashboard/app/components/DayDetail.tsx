"use client";

import { DayData } from "../types";

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="p-4 rounded-lg border border-[var(--border)]">
      <p className="text-sm text-[var(--subtle)] mb-1">{label}</p>
      <p className="text-xl font-medium">{value}</p>
    </div>
  );
}

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
      <div className="grid grid-cols-3 gap-4">
        <Metric label="Sleep Score" value={data.sleepScore != null ? String(data.sleepScore) : "\u2014"} />
        <Metric label="Readiness" value={data.readinessScore != null ? String(data.readinessScore) : "\u2014"} />
        <Metric label="Activity" value={data.activityScore != null ? String(data.activityScore) : "\u2014"} />
      </div>

      {/* Health metrics */}
      <div className="grid grid-cols-3 gap-4">
        <Metric label="Sleep" value={data.sleep != null ? `${data.sleep}h` : "\u2014"} />
        <Metric label="Resting HR" value={data.restingHR != null ? `${data.restingHR} bpm` : "\u2014"} />
        <Metric label="Steps" value={data.steps != null ? data.steps.toLocaleString() : "\u2014"} />
      </div>

      {/* Time & wellness */}
      <div className="grid grid-cols-3 gap-4">
        <Metric label="Work" value={data.timeWorking ? `${Math.round(data.timeWorking / 60)}h` : "\u2014"} />
        <Metric label="Mood" value={data.mood != null ? `${data.mood}/5` : "\u2014"} />
        <Metric label="Energy" value={data.energy != null ? `${data.energy}/5` : "\u2014"} />
      </div>

      {/* Weather */}
      {data.weatherHighF != null && (
        <div className="p-4 rounded-lg border border-[var(--border)]">
          <p className="text-sm text-[var(--subtle)] mb-1">Weather</p>
          <p className="font-medium">{data.weatherHighF}&deg;F &mdash; {data.weatherCondition || "Unknown"}</p>
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
