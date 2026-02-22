"use client";

import { useMemo } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { DayData } from "../types";

function formatDate(dateStr: string) {
  const d = new Date(dateStr + "T00:00:00");
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export function OuraTrends({ days }: { days: Record<string, DayData> }) {
  const chartData = useMemo(() => {
    return Object.entries(days)
      .filter(([, d]) => d.sleepScore || d.readinessScore)
      .sort(([a], [b]) => a.localeCompare(b))
      .slice(-60) // Last 60 days
      .map(([date, d]) => ({
        date,
        label: formatDate(date),
        sleepScore: d.sleepScore,
        readinessScore: d.readinessScore,
        activityScore: d.activityScore,
      }));
  }, [days]);

  const sleepData = useMemo(() => {
    return Object.entries(days)
      .filter(([, d]) => d.sleep)
      .sort(([a], [b]) => a.localeCompare(b))
      .slice(-60)
      .map(([date, d]) => ({
        date,
        label: formatDate(date),
        sleep: d.sleep,
        restingHR: d.restingHR,
      }));
  }, [days]);

  if (chartData.length === 0) {
    return (
      <div className="text-center text-[var(--subtle)] py-8">
        <p>No Oura data yet. Run the pipeline to import data.</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Oura Scores */}
      <div>
        <h3 className="text-lg font-medium mb-4">Oura Scores (Last 60 Days)</h3>
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis
                dataKey="label"
                tick={{ fontSize: 11, fill: "var(--subtle)" }}
                interval={Math.floor(chartData.length / 6)}
              />
              <YAxis
                domain={[40, 100]}
                tick={{ fontSize: 11, fill: "var(--subtle)" }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "var(--card)",
                  border: "1px solid var(--border)",
                  borderRadius: 8,
                  color: "var(--foreground)",
                }}
              />
              <Line
                type="monotone"
                dataKey="sleepScore"
                stroke="#6366f1"
                strokeWidth={2}
                dot={false}
                name="Sleep"
              />
              <Line
                type="monotone"
                dataKey="readinessScore"
                stroke="#10b981"
                strokeWidth={2}
                dot={false}
                name="Readiness"
              />
              <Line
                type="monotone"
                dataKey="activityScore"
                stroke="#f59e0b"
                strokeWidth={2}
                dot={false}
                name="Activity"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Sleep Duration + HR */}
      {sleepData.length > 0 && (
        <div>
          <h3 className="text-lg font-medium mb-4">Sleep Duration (Last 60 Days)</h3>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={sleepData}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis
                  dataKey="label"
                  tick={{ fontSize: 11, fill: "var(--subtle)" }}
                  interval={Math.floor(sleepData.length / 6)}
                />
                <YAxis
                  domain={[4, 10]}
                  tick={{ fontSize: 11, fill: "var(--subtle)" }}
                  unit="h"
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "var(--card)",
                    border: "1px solid var(--border)",
                    borderRadius: 8,
                    color: "var(--foreground)",
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="sleep"
                  stroke="#8b5cf6"
                  strokeWidth={2}
                  dot={false}
                  name="Hours"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
}
