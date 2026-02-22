"use client";

import { useMemo } from "react";
import { DayData } from "../types";

export function YearStats({ days }: { days: Record<string, DayData> }) {
  const daysList = Object.values(days);

  const stats = useMemo(() => {
    const workouts = daysList.filter((d) => d.habits.workout).length;
    const saunas = daysList.filter((d) => d.habits.sauna).length;
    const meditations = daysList.filter((d) => d.habits.meditation).length;
    const sleepDays = daysList.filter((d) => d.sleep);
    const avgSleep = sleepDays.length > 0
      ? sleepDays.reduce((sum, d) => sum + (d.sleep || 0), 0) / sleepDays.length
      : 0;
    const hrDays = daysList.filter((d) => d.restingHR);
    const avgHR = hrDays.length > 0
      ? hrDays.reduce((sum, d) => sum + (d.restingHR || 0), 0) / hrDays.length
      : 0;
    const scoreDays = daysList.filter((d) => d.readinessScore);
    const avgReadiness = scoreDays.length > 0
      ? scoreDays.reduce((sum, d) => sum + (d.readinessScore || 0), 0) / scoreDays.length
      : 0;

    return { workouts, saunas, meditations, avgSleep, avgHR, avgReadiness, totalDays: daysList.length };
  }, [daysList]);

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3 mb-8">
      <StatCard label="Days Tracked" value={stats.totalDays} />
      <StatCard label="Workouts" value={stats.workouts} />
      <StatCard label="Saunas" value={stats.saunas} />
      <StatCard label="Meditations" value={stats.meditations} />
      <StatCard label="Avg Sleep" value={`${stats.avgSleep.toFixed(1)}h`} />
      <StatCard label="Avg HR" value={stats.avgHR > 0 ? Math.round(stats.avgHR) : "—"} />
      <StatCard label="Avg Readiness" value={stats.avgReadiness > 0 ? Math.round(stats.avgReadiness) : "—"} />
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="p-3 rounded-lg bg-[var(--card)] border border-[var(--border)]">
      <p className="text-xs text-[var(--subtle)]">{label}</p>
      <p className="text-lg font-medium">{value}</p>
    </div>
  );
}
