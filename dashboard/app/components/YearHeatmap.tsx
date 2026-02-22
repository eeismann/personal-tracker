"use client";

import { useMemo } from "react";
import { DayData } from "../types";

function getYearGrid(year: number) {
  const weeks: Date[][] = [];
  const startDate = new Date(year, 0, 1);
  const firstMonday = new Date(startDate);
  firstMonday.setDate(firstMonday.getDate() - ((firstMonday.getDay() + 6) % 7));

  const currentDate = new Date(firstMonday);
  const endDate = new Date(year, 11, 31);

  while (currentDate <= endDate || weeks.length < 53) {
    const week: Date[] = [];
    for (let i = 0; i < 7; i++) {
      week.push(new Date(currentDate));
      currentDate.setDate(currentDate.getDate() + 1);
    }
    weeks.push(week);
    if (currentDate.getFullYear() > year && weeks.length >= 52) break;
  }

  return weeks;
}

function getDayScore(day: DayData | undefined): number {
  if (!day) return 0;
  let score = 0;
  const total = 3;
  if (day.habits.workout) score += 1;
  if (day.habits.sauna) score += 1;
  if (day.habits.meditation) score += 1;
  return score / total;
}

function getScoreColor(score: number, isToday: boolean, isFuture: boolean): string {
  if (isFuture) return "bg-[var(--subtle)]/5";

  let bgColor = "bg-[var(--subtle)]/10";
  if (score > 0 && score <= 0.33) bgColor = "bg-emerald-200 dark:bg-emerald-900";
  else if (score > 0.33 && score <= 0.66) bgColor = "bg-emerald-400 dark:bg-emerald-700";
  else if (score > 0.66) bgColor = "bg-emerald-600 dark:bg-emerald-500";

  if (isToday) return `${bgColor} ring-2 ring-[var(--foreground)]`;
  return bgColor;
}

export function YearHeatmap({
  year,
  days,
  selectedDate,
  onSelectDate,
}: {
  year: number;
  days: Record<string, DayData>;
  selectedDate: Date | null;
  onSelectDate: (date: Date | null) => void;
}) {
  const weeks = useMemo(() => getYearGrid(year), [year]);
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const dayLabels = ["M", "T", "W", "T", "F", "S", "S"];

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  return (
    <section className="mb-12">
      {/* Month labels */}
      <div className="flex mb-2 ml-8">
        {months.map((month) => (
          <div key={month} className="text-xs text-[var(--subtle)]" style={{ width: `${100 / 12}%` }}>
            {month}
          </div>
        ))}
      </div>

      <div className="flex gap-[3px]">
        {/* Day labels */}
        <div className="flex flex-col gap-[3px] mr-2">
          {dayLabels.map((day, i) => (
            <div key={i} className="w-3 h-3 md:w-[14px] md:h-[14px] flex items-center justify-center text-[10px] text-[var(--subtle)]">
              {i % 2 === 0 ? day : ""}
            </div>
          ))}
        </div>

        {/* Grid */}
        <div className="flex gap-[3px] overflow-x-auto pb-2">
          {weeks.map((week, weekIndex) => (
            <div key={weekIndex} className="flex flex-col gap-[3px]">
              {week.map((date, dayIndex) => {
                const dateStr = date.toISOString().split("T")[0];
                const cellDate = new Date(date);
                cellDate.setHours(0, 0, 0, 0);
                const isToday = cellDate.getTime() === today.getTime();
                const isFuture = cellDate > today;
                const score = getDayScore(days[dateStr]);
                const isSelected = selectedDate?.toISOString().split("T")[0] === dateStr;

                return (
                  <button
                    key={dayIndex}
                    onClick={() => !isFuture && onSelectDate(isSelected ? null : date)}
                    disabled={isFuture}
                    className={`
                      w-3 h-3 md:w-[14px] md:h-[14px] rounded-sm transition-all duration-200
                      ${getScoreColor(score, isToday, isFuture)}
                      ${isSelected ? "ring-2 ring-[var(--foreground)] scale-150 z-10" : ""}
                      ${!isFuture ? "hover:scale-125 hover:z-10 cursor-pointer" : "cursor-default"}
                    `}
                    title={`${dateStr}${days[dateStr] ? ` — Score: ${Math.round(score * 100)}%` : ""}`}
                  />
                );
              })}
            </div>
          ))}
        </div>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 mt-4 text-sm text-[var(--subtle)]">
        <span>Less</span>
        <div className="flex gap-1">
          <div className="w-3 h-3 rounded-sm bg-[var(--subtle)]/10" />
          <div className="w-3 h-3 rounded-sm bg-emerald-200 dark:bg-emerald-900" />
          <div className="w-3 h-3 rounded-sm bg-emerald-400 dark:bg-emerald-700" />
          <div className="w-3 h-3 rounded-sm bg-emerald-600 dark:bg-emerald-500" />
        </div>
        <span>More habits</span>
      </div>
    </section>
  );
}
