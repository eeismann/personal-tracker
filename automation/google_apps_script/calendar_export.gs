/**
 * Google Apps Script: Calendar → Google Sheet
 *
 * Exports one row per calendar event, including titles.
 *
 * Setup:
 * 1. Go to https://script.google.com and create a new project
 * 2. Paste this entire script
 * 3. Run setupSheet() once to create the spreadsheet
 * 4. Run setupWeeklyTrigger() once to schedule automatic weekly runs
 * 5. Copy the spreadsheet URL and add it to your .env as GOOGLE_SHEET_URL
 *
 * The script runs every Sunday at 11pm and captures the full past week (Mon-Sun).
 */

var EVENTS_SHEET = "events";
var SUMMARY_SHEET = "daily_summary";

/**
 * One-time setup: creates both sheets with headers.
 * Run this manually first, then note the spreadsheet URL.
 */
function setupSheet() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();

  // Events sheet — one row per event
  var evSheet = ss.getSheetByName(EVENTS_SHEET);
  if (!evSheet) evSheet = ss.insertSheet(EVENTS_SHEET);
  var evHeaders = [
    "date", "day_of_week", "title", "start_time", "end_time",
    "duration_hr", "guest_count", "is_recurring", "status", "calendar"
  ];
  evSheet.getRange(1, 1, 1, evHeaders.length).setValues([evHeaders]);
  evSheet.getRange(1, 1, 1, evHeaders.length).setFontWeight("bold");
  for (var i = 1; i <= evHeaders.length; i++) evSheet.autoResizeColumn(i);

  // Daily summary sheet — one row per day (auto-computed)
  var sumSheet = ss.getSheetByName(SUMMARY_SHEET);
  if (!sumSheet) sumSheet = ss.insertSheet(SUMMARY_SHEET);
  var sumHeaders = [
    "date", "day_of_week", "first_event_time", "last_event_time",
    "total_work_hr", "meeting_count", "meeting_hr", "focus_hr",
    "longest_meeting_hr", "back_to_back_count", "event_titles"
  ];
  sumSheet.getRange(1, 1, 1, sumHeaders.length).setValues([sumHeaders]);
  sumSheet.getRange(1, 1, 1, sumHeaders.length).setFontWeight("bold");
  for (var j = 1; j <= sumHeaders.length; j++) sumSheet.autoResizeColumn(j);

  Logger.log("Sheets ready. URL: " + ss.getUrl());
}

/**
 * One-time setup: creates a weekly trigger (every Sunday at 11pm).
 */
function setupWeeklyTrigger() {
  var triggers = ScriptApp.getProjectTriggers();
  for (var i = 0; i < triggers.length; i++) {
    if (triggers[i].getHandlerFunction() === "exportPastWeek") {
      ScriptApp.deleteTrigger(triggers[i]);
    }
  }
  ScriptApp.newTrigger("exportPastWeek")
    .timeBased()
    .onWeekDay(ScriptApp.WeekDay.SUNDAY)
    .atHour(23)
    .create();
  Logger.log("Weekly trigger created: every Sunday at 11pm");
}

/**
 * Main function: exports the past 7 days (Monday through Sunday).
 */
function exportPastWeek() {
  var today = new Date();
  var endDate = new Date(today);
  endDate.setDate(today.getDate() - ((today.getDay() + 0) % 7));
  endDate.setHours(23, 59, 59, 999);
  var startDate = new Date(endDate);
  startDate.setDate(endDate.getDate() - 6);
  startDate.setHours(0, 0, 0, 0);
  exportDateRange(startDate, endDate);
}

/**
 * Export a custom date range.
 */
function exportDateRange(startDate, endDate) {
  var calendar = CalendarApp.getDefaultCalendar();
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var evSheet = ss.getSheetByName(EVENTS_SHEET);
  var sumSheet = ss.getSheetByName(SUMMARY_SHEET);

  if (!evSheet || !sumSheet) {
    Logger.log("Sheets not found. Run setupSheet() first.");
    return;
  }

  // Get existing dates in events sheet to avoid duplicates
  var existingDates = {};
  if (evSheet.getLastRow() > 1) {
    var dateCol = evSheet.getRange(2, 1, evSheet.getLastRow() - 1, 1).getValues();
    for (var i = 0; i < dateCol.length; i++) {
      if (dateCol[i][0]) existingDates[dateCol[i][0].toString()] = true;
    }
  }
  // Also check summary sheet
  if (sumSheet.getLastRow() > 1) {
    var sumDateCol = sumSheet.getRange(2, 1, sumSheet.getLastRow() - 1, 1).getValues();
    for (var s = 0; s < sumDateCol.length; s++) {
      if (sumDateCol[s][0]) existingDates[sumDateCol[s][0].toString()] = true;
    }
  }

  var eventRows = [];
  var summaryRows = [];
  var current = new Date(startDate);

  while (current <= endDate) {
    var dateStr = formatDate(current);

    if (existingDates[dateStr]) {
      current.setDate(current.getDate() + 1);
      continue;
    }

    var dayEnd = new Date(current);
    dayEnd.setHours(23, 59, 59, 999);

    var calEvents = calendar.getEvents(current, dayEnd);
    var result = processDayEvents(current, calEvents);
    eventRows = eventRows.concat(result.eventRows);
    summaryRows.push(result.summaryRow);

    current.setDate(current.getDate() + 1);
  }

  if (summaryRows.length === 0) {
    Logger.log("No new days to export.");
    return;
  }

  // Append event rows
  if (eventRows.length > 0) {
    var evLast = evSheet.getLastRow();
    evSheet.getRange(evLast + 1, 1, eventRows.length, eventRows[0].length).setValues(eventRows);
    if (evSheet.getLastRow() > 2) {
      evSheet.getRange(2, 1, evSheet.getLastRow() - 1, evSheet.getLastColumn())
        .sort([{column: 1, ascending: true}, {column: 4, ascending: true}]);
    }
  }

  // Append summary rows
  var sumLast = sumSheet.getLastRow();
  sumSheet.getRange(sumLast + 1, 1, summaryRows.length, summaryRows[0].length).setValues(summaryRows);
  if (sumSheet.getLastRow() > 2) {
    sumSheet.getRange(2, 1, sumSheet.getLastRow() - 1, sumSheet.getLastColumn())
      .sort({column: 1, ascending: true});
  }

  Logger.log("Exported " + summaryRows.length + " days, " + eventRows.length + " events (" + formatDate(startDate) + " to " + formatDate(endDate) + ")");
}

/**
 * Process all events for a single day.
 * Returns both individual event rows and a daily summary row.
 */
function processDayEvents(date, events) {
  var dayOfWeek = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"][date.getDay()];
  var dateStr = formatDate(date);

  var meetings = [];
  var eventRows = [];

  for (var i = 0; i < events.length; i++) {
    var event = events[i];

    // Skip all-day events
    if (event.isAllDayEvent()) continue;

    // Skip events you declined
    var myStatus = event.getMyStatus();
    if (myStatus === CalendarApp.GuestStatus.NO) continue;

    var title = event.getTitle();
    var startTime = event.getStartTime();
    var endTime = event.getEndTime();
    var durationHr = (endTime - startTime) / (1000 * 60 * 60);
    durationHr = Math.round(durationHr * 100) / 100;
    var guestCount = event.getGuestList(false).length;
    var isRecurring = event.isRecurringEvent();
    var statusStr = myStatus ? myStatus.toString() : "";
    var calName = event.getOriginalCalendarId();

    // Add to event rows
    eventRows.push([
      dateStr, dayOfWeek, title, formatTime(startTime), formatTime(endTime),
      durationHr, guestCount, isRecurring, statusStr, calName
    ]);

    // For summary, skip focus/block/lunch type events
    var titleLower = title.toLowerCase();
    if (titleLower.indexOf("focus") > -1 || titleLower.indexOf("block") > -1 ||
        titleLower.indexOf("lunch") > -1 || titleLower.indexOf("commute") > -1) continue;

    meetings.push({
      title: title,
      start: startTime,
      end: endTime,
      durationHr: durationHr
    });
  }

  // Build summary
  if (meetings.length === 0) {
    return {
      eventRows: eventRows,
      summaryRow: [dateStr, dayOfWeek, "", "", 0, 0, 0, 0, 0, 0, ""]
    };
  }

  meetings.sort(function(a, b) { return a.start - b.start; });

  var firstEvent = formatTime(meetings[0].start);
  var lastEvent = formatTime(meetings[meetings.length - 1].end);
  var totalWorkHr = (meetings[meetings.length - 1].end - meetings[0].start) / (1000 * 60 * 60);
  totalWorkHr = Math.round(totalWorkHr * 100) / 100;

  var meetingHr = 0;
  var longestMeetingHr = 0;
  var titles = [];
  for (var j = 0; j < meetings.length; j++) {
    meetingHr += meetings[j].durationHr;
    if (meetings[j].durationHr > longestMeetingHr) {
      longestMeetingHr = meetings[j].durationHr;
    }
    titles.push(meetings[j].title);
  }
  meetingHr = Math.round(meetingHr * 100) / 100;
  longestMeetingHr = Math.round(longestMeetingHr * 100) / 100;

  var focusHr = Math.max(0, totalWorkHr - meetingHr);
  focusHr = Math.round(focusHr * 100) / 100;

  var backToBack = 0;
  for (var k = 1; k < meetings.length; k++) {
    var gap = (meetings[k].start - meetings[k - 1].end) / (1000 * 60);
    if (gap <= 5) backToBack++;
  }

  // Join titles with " | " separator
  var eventTitles = titles.join(" | ");

  return {
    eventRows: eventRows,
    summaryRow: [
      dateStr, dayOfWeek, firstEvent, lastEvent,
      totalWorkHr, meetings.length, meetingHr, focusHr,
      longestMeetingHr, backToBack, eventTitles
    ]
  };
}

function formatDate(date) {
  return Utilities.formatDate(date, Session.getScriptTimeZone(), "yyyy-MM-dd");
}

function formatTime(date) {
  return Utilities.formatDate(date, Session.getScriptTimeZone(), "HH:mm");
}

/**
 * Backfill the past N weeks. Run from the editor via backfill3Months().
 */
function backfill(weeks) {
  var today = new Date();
  var endDate = new Date(today);
  var startDate = new Date(today);
  startDate.setDate(today.getDate() - (weeks * 7));
  startDate.setHours(0, 0, 0, 0);
  endDate.setHours(23, 59, 59, 999);
  exportDateRange(startDate, endDate);
}

/** Run from editor: backfills 3 months */
function backfill3Months() { backfill(12); }

/** Run from editor: backfills 6 months */
function backfill6Months() { backfill(26); }

/** Run from editor: backfills 1 year */
function backfill1Year() { backfill(52); }

/** Clear all data and re-export. Useful if you changed the schema. */
function resetAndBackfill() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var evSheet = ss.getSheetByName(EVENTS_SHEET);
  var sumSheet = ss.getSheetByName(SUMMARY_SHEET);
  if (evSheet && evSheet.getLastRow() > 1) {
    evSheet.deleteRows(2, evSheet.getLastRow() - 1);
  }
  if (sumSheet && sumSheet.getLastRow() > 1) {
    sumSheet.deleteRows(2, sumSheet.getLastRow() - 1);
  }
  Logger.log("Cleared all data. Running 3-month backfill...");
  backfill(12);
}
