"use client";

import { useState, useEffect } from "react";
import { fetchTrackerData } from "./data";
import { TrackerData } from "./types";
import { ThemeToggle } from "./components/ThemeToggle";
import { YearHeatmap } from "./components/YearHeatmap";
import { YearStats } from "./components/YearStats";
import { DayDetail } from "./components/DayDetail";
import { OuraTrends } from "./components/OuraTrends";
import { TravelSection } from "./components/TravelSection";

export default function Dashboard() {
  const [data, setData] = useState<TrackerData>({ days: {}, generated: "" });
  const [loading, setLoading] = useState(true);
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);

  const year = new Date().getFullYear();

  useEffect(() => {
    fetchTrackerData().then((d) => {
      setData(d);
      setLoading(false);
    });
  }, []);

  const selectedData = selectedDate
    ? data.days[selectedDate.toISOString().split("T")[0]]
    : null;

  if (loading) {
    return (
      <main className="min-h-screen flex items-center justify-center">
        <p className="text-[var(--subtle)]">Loading...</p>
      </main>
    );
  }

  const dayCount = Object.keys(data.days).length;

  return (
    <main className="min-h-screen px-6 py-16 md:px-12 md:py-24 lg:px-24 lg:py-32 max-w-6xl mx-auto">
      {/* Theme toggle */}
      <div className="fixed top-6 right-6 z-50">
        <ThemeToggle />
      </div>

      {/* Header */}
      <header className="mb-8">
        <h1 className="text-4xl md:text-5xl font-medium tracking-tight mb-2">
          Personal Tracker — {year}
        </h1>
        <p className="text-[var(--subtle)]">
          {dayCount > 0
            ? `${dayCount} days tracked — Click any day to see details`
            : "No data yet. Run the pipeline to get started."}
        </p>
        {data.generated && (
          <p className="text-xs text-[var(--subtle)] mt-1">
            Last updated: {data.generated}
          </p>
        )}
      </header>

      {/* Year Stats Summary */}
      {dayCount > 0 && <YearStats days={data.days} />}

      {/* Year Heatmap */}
      <YearHeatmap
        year={year}
        days={data.days}
        selectedDate={selectedDate}
        onSelectDate={setSelectedDate}
      />

      {/* Selected Day Detail */}
      {selectedDate && (
        <section className="border-t border-[var(--border)] pt-8 mb-12">
          <DayDetail data={selectedData} date={selectedDate} />
        </section>
      )}

      {/* Travel */}
      {data.travel && (data.travel.trips.length > 0 || data.travel.flights.length > 0) && (
        <TravelSection travel={data.travel} />
      )}

      {/* Oura Trend Charts */}
      {dayCount > 0 && (
        <section className="border-t border-[var(--border)] pt-8">
          <OuraTrends days={data.days} />
        </section>
      )}

      {/* Footer */}
      <footer className="pt-8 mt-8 border-t border-[var(--border)] text-[var(--subtle)] text-sm">
        <p>Personal Tracker — Data pipeline + dashboard</p>
      </footer>
    </main>
  );
}
