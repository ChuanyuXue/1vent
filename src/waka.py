import requests
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import os
import json
from pathlib import Path
import logging

from config import STATS_DIR, LOG_DIR, TIMEZONE
from comms import get_local_date, get_local_datetime


def load_config() -> str:
    """Load WakaTime API key from environment variable

    Returns:
        WakaTime API key

    Raises:
        KeyError: If API key is not set
    """
    api_key = os.getenv("WAKATIME_API_KEY")
    if not api_key:
        raise KeyError("WakaTime API key not found in environment variables")
    return api_key


def setup_logging() -> None:
    """Setup logging configuration to save output to a file"""
    # Create logs directory if it doesn't exist
    log_dir = Path(LOG_DIR)
    log_dir.mkdir(exist_ok=True, parents=True)

    # Create log filename with date only
    date = get_local_date().strftime("%Y-%m-%d")
    log_file = log_dir / f"productivity_log_{date}.txt"

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
    )


class WakaTimeClient:
    """Client for interacting with the WakaTime API"""

    BASE_URL = "https://wakatime.com/api/v1"

    def __init__(self, api_key: str):
        """Initialize the WakaTime client

        Args:
            api_key: Your WakaTime API key
        """
        self.api_key = api_key
        self.headers = {"Authorization": f"Basic {self._encode_api_key(api_key)}"}

    def _encode_api_key(self, api_key: str) -> str:
        """Encode the API key in base64 format as required by WakaTime"""
        import base64

        return base64.b64encode(api_key.encode()).decode()

    def _make_request(
        self, endpoint: str, params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make a GET request to the WakaTime API

        Args:
            endpoint: API endpoint to call
            params: Optional query parameters

        Returns:
            JSON response from the API

        Raises:
            requests.exceptions.RequestException: If the request fails
        """
        url = f"{self.BASE_URL}/{endpoint}"
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()

    def get_user_stats(self, range: str = "last_7_days") -> Dict[str, Any]:
        """Get user's coding statistics

        Args:
            range: Time range for stats. Can be one of:
                  "last_7_days", "last_30_days", "last_6_months", "last_year", "all_time"

        Returns:
            Dictionary containing user's coding statistics
        """
        return self._make_request(f"users/current/stats/{range}")

    def get_summaries(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get user's coding summaries for a date range

        Args:
            start_date: Start date for the summary
            end_date: End date for the summary

        Returns:
            Dictionary containing user's coding summaries
        """
        params = {
            "start": start_date.strftime("%Y-%m-%d"),
            "end": end_date.strftime("%Y-%m-%d"),
        }
        return self._make_request("users/current/summaries", params)

    def get_today_status(self) -> Dict[str, Any]:
        """Get user's coding activity for today

        Returns:
            Dictionary containing today's coding activity
        """
        return self._make_request("users/current/status_bar/today")

    def get_all_time_since_today(self) -> Dict[str, Any]:
        """Get user's total coding time since account creation

        Returns:
            Dictionary containing all-time coding statistics
        """
        return self._make_request("users/current/all_time_since_today")

    def get_heartbeats(self, date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get user's heartbeats for a specific date

        Args:
            date: Date to get heartbeats for. Defaults to today if not provided.
                 Heartbeats will be returned from 12am until 11:59pm in user's timezone.

        Returns:
            Dictionary containing user's heartbeats data
        """
        if date is None:
            date = get_local_datetime()

        params = {"date": date.strftime("%Y-%m-%d")}

        return self._make_request("users/current/heartbeats", params)

    def get_today_heartbeats_summary(self) -> Dict[str, Any]:
        """Get a processed summary of today's heartbeats"""
        heartbeats = self.get_heartbeats()
        data = heartbeats.get("data", [])

        summary = {
            "total_coding_time": 0,
            "projects": dict(),  # Initialize as dict instead of empty {}
            "languages": dict(),
            "files": set(),  # Initialize as set for unique files
        }

        for heartbeat in data:
            # Track unique files
            if "entity" in heartbeat:
                summary["files"].add(heartbeat["entity"])

            # Track projects
            if "project" in heartbeat:
                project = heartbeat["project"]
                if project not in summary["projects"]:
                    summary["projects"][project] = 0
                summary["projects"][project] += 1

            # Track languages
            if "language" in heartbeat:
                language = heartbeat["language"]
                if language not in summary["languages"]:
                    summary["languages"][language] = 0
                summary["languages"][language] += 1

        # Convert set to list for JSON serialization
        summary["files"] = list(summary["files"])
        return summary

    def get_heartbeats_details(self, date: Optional[datetime] = None) -> None:
        """Print detailed information from heartbeats"""
        heartbeats = self.get_heartbeats(date)
        data = heartbeats.get("data", [])

        logging.info(f"\nFound {len(data)} heartbeats:")
        for heartbeat in data:
            logging.info("\n--- Heartbeat ---")
            logging.info(
                f"Time: {get_local_datetime().fromtimestamp(heartbeat['time']).strftime('%Y-%m-%d %H:%M:%S')}"
            )
            logging.info(
                f"Entity: {heartbeat.get('entity', 'N/A')}"
            )  # File path or domain
            logging.info(
                f"Type: {heartbeat.get('type', 'N/A')}"
            )  # file, app, or domain
            logging.info(
                f"Category: {heartbeat.get('category', 'N/A')}"
            )  # coding, debugging, etc.
            logging.info(f"Project: {heartbeat.get('project', 'N/A')}")
            logging.info(f"Language: {heartbeat.get('language', 'N/A')}")
            logging.info(f"Branch: {heartbeat.get('branch', 'N/A')}")

            # Code changes information
            if "lines" in heartbeat:
                logging.info(f"Total lines: {heartbeat['lines']}")
            if "line_additions" in heartbeat:
                logging.info(f"Lines added: {heartbeat['line_additions']}")
            if "line_deletions" in heartbeat:
                logging.info(f"Lines deleted: {heartbeat['line_deletions']}")

            # Cursor position
            if "lineno" in heartbeat:
                logging.info(f"Line number: {heartbeat['lineno']}")
            if "cursorpos" in heartbeat:
                logging.info(f"Cursor position: {heartbeat['cursorpos']}")

            logging.info(f"Is write: {heartbeat.get('is_write', False)}")
            if "dependencies" in heartbeat:
                logging.info(f"Dependencies: {heartbeat['dependencies']}")

    def get_coding_durations(
        self, date: Optional[datetime] = None, merge_threshold: int = 300
    ) -> List[Dict[str, Any]]:
        """Get coding durations by merging heartbeats that are close in time"""
        heartbeats = self.get_heartbeats(date)
        data = sorted(heartbeats.get("data", []), key=lambda x: x["time"])

        if not data:
            return []

        durations = []
        current_session = {
            "start_time": data[0]["time"],
            "end_time": data[0]["time"],
            "duration": 0,
            "activities": {
                "files": {},  # entity -> {duration, type}
                "projects": {},  # project -> duration
                "languages": {},  # language -> duration
                "categories": {},  # category -> duration
            },
            "line_changes": {"additions": 0, "deletions": 0},
        }

        # Initialize first activity with zero duration instead of data[0]['time']
        self._update_activity_duration(current_session, data[0], 0)

        for i in range(1, len(data)):
            current = data[i]
            prev = data[i - 1]
            time_diff = current["time"] - prev["time"]

            # If time difference is within threshold, extend current session
            if time_diff <= merge_threshold:
                current_session["end_time"] = current["time"]
                current_session["duration"] = (
                    current["time"] - current_session["start_time"]
                )

                # Add duration to previous activity (from prev heartbeat to current)
                if time_diff > 0:  # Only add positive durations
                    self._update_activity_duration(current_session, prev, time_diff)

                # Update line changes
                if current.get("line_additions"):
                    current_session["line_changes"]["additions"] += current[
                        "line_additions"
                    ]
                if current.get("line_deletions"):
                    current_session["line_changes"]["deletions"] += current[
                        "line_deletions"
                    ]

            else:
                # Add final duration to last activity of the session
                final_duration = current_session["end_time"] - prev["time"]
                if final_duration > 0:  # Only add positive durations
                    self._update_activity_duration(
                        current_session, prev, final_duration
                    )

                # Start new session
                durations.append(self._format_duration(current_session))
                current_session = {
                    "start_time": current["time"],
                    "end_time": current["time"],
                    "duration": 0,
                    "activities": {
                        "files": {},
                        "projects": {},
                        "languages": {},
                        "categories": {},
                    },
                    "line_changes": {
                        "additions": current.get("line_additions", 0),
                        "deletions": current.get("line_deletions", 0),
                    },
                }
                # Initialize first activity of new session with zero duration
                self._update_activity_duration(current_session, current, 0)

        # Add final duration to last activity of the last session
        final_duration = current_session["end_time"] - data[-1]["time"]
        if final_duration > 0:  # Only add positive durations
            self._update_activity_duration(current_session, data[-1], final_duration)

        # Add the last session
        durations.append(self._format_duration(current_session))
        return durations

    def _normalize_file_path(self, file_path: str) -> str:
        """Normalize file path to remove personal information and standardize format

        Args:
            file_path: Original file path

        Returns:
            Normalized file path
        """
        if not file_path:
            return file_path

        # Get just the file name from the path
        file_name = os.path.basename(file_path)
        return file_name

    def _update_activity_duration(
        self, session: Dict[str, Any], heartbeat: Dict[str, Any], duration: float
    ) -> None:
        """Update duration for each activity type in the session"""
        # Update file duration
        if "entity" in heartbeat:
            # Normalize the file path
            entity = self._normalize_file_path(heartbeat["entity"])
            if entity not in session["activities"]["files"]:
                session["activities"]["files"][entity] = {
                    "duration": 0,
                    "type": heartbeat.get("type", "unknown"),
                }
            session["activities"]["files"][entity]["duration"] += duration

        # Update project duration
        if "project" in heartbeat:
            project = heartbeat["project"]
            if project not in session["activities"]["projects"]:
                session["activities"]["projects"][project] = 0
            session["activities"]["projects"][project] += duration

        # Update language duration
        if "language" in heartbeat:
            language = heartbeat["language"]
            if language not in session["activities"]["languages"]:
                session["activities"]["languages"][language] = 0
            session["activities"]["languages"][language] += duration

        # Update category duration
        if "category" in heartbeat:
            category = heartbeat["category"]
            if category not in session["activities"]["categories"]:
                session["activities"]["categories"][category] = 0
            session["activities"]["categories"][category] += duration

    def _format_duration(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Format a coding session with readable times and durations"""
        start_dt = get_local_datetime().fromtimestamp(session["start_time"])
        end_dt = get_local_datetime().fromtimestamp(session["end_time"])

        # Convert durations from seconds to minutes
        formatted_activities = {
            "files": {
                entity: {
                    "duration_minutes": round(data["duration"] / 60, 2),
                    "type": data["type"],
                }
                for entity, data in session["activities"]["files"].items()
            },
            "projects": {
                project: round(duration / 60, 2)
                for project, duration in session["activities"]["projects"].items()
            },
            "languages": {
                language: round(duration / 60, 2)
                for language, duration in session["activities"]["languages"].items()
            },
            "categories": {
                category: round(duration / 60, 2)
                for category, duration in session["activities"]["categories"].items()
            },
        }

        return {
            "start_time": start_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": end_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "duration_seconds": round(session["duration"]),
            "duration_minutes": round(session["duration"] / 60, 2),
            "activities": formatted_activities,
            "line_changes": session["line_changes"],
        }

    def print_coding_durations(
        self, date: Optional[datetime] = None, min_duration: float = 3.0
    ) -> None:
        """Save coding durations to log file"""
        if date is None:
            date = get_local_datetime()
        durations = self.get_coding_durations(date)

        logging.info(f"\nFound {len(durations)} coding sessions:")
        for i, session in enumerate(durations, 1):
            if session["duration_minutes"] < min_duration:
                continue

            logging.info(f"\n=== Session {i} ===")
            logging.info(f"Time: {session['start_time']} to {session['end_time']}")
            logging.info(f"Total Duration: {session['duration_minutes']} minutes")

            logging.info("\nFiles:")
            significant_files = {
                file: data
                for file, data in session["activities"]["files"].items()
                if data["duration_minutes"] >= min_duration
            }
            if significant_files:
                for file, data in significant_files.items():
                    logging.info(
                        f"  - {file} ({data['type']}): {data['duration_minutes']} minutes"
                    )
            else:
                logging.info("  No files exceeded minimum duration threshold")

            logging.info("\nProjects:")
            significant_projects = {
                project: duration
                for project, duration in session["activities"]["projects"].items()
                if duration >= min_duration
            }
            if significant_projects:
                for project, duration in significant_projects.items():
                    logging.info(f"  - {project}: {duration} minutes")
            else:
                logging.info("  No projects exceeded minimum duration threshold")

            logging.info("\nLanguages:")
            significant_languages = {
                language: duration
                for language, duration in session["activities"]["languages"].items()
                if duration >= min_duration
            }
            if significant_languages:
                for language, duration in significant_languages.items():
                    logging.info(f"  - {language}: {duration} minutes")
            else:
                logging.info("  No languages exceeded minimum duration threshold")

            logging.info("\nCategories:")
            significant_categories = {
                category: duration
                for category, duration in session["activities"]["categories"].items()
                if duration >= min_duration
            }
            if significant_categories:
                for category, duration in significant_categories.items():
                    logging.info(f"  - {category}: {duration} minutes")
            else:
                logging.info("  No categories exceeded minimum duration threshold")

            logging.info(
                "\nLine Changes: +{additions} -{deletions}".format(
                    **session["line_changes"]
                )
            )

    def save_daily_stats(self, today_status: Dict, week_stats: Dict) -> None:
        """Save daily coding statistics to a JSON file

        Args:
            today_status: Today's coding status data
            week_stats: Weekly statistics data
        """
        stats_dir = Path(STATS_DIR)
        stats_dir.mkdir(exist_ok=True, parents=True)
        stats_file = stats_dir / "coding_stats.json"

        today = get_local_datetime().strftime("%Y-%m-%d")

        # Prepare today's stats
        daily_stats = {
            "date": today,
            "weekday": get_local_datetime().strftime("%A"),
            "total_hours": float(today_status["data"]["grand_total"]["decimal"]),
            "categories": {
                cat["name"]: cat["decimal"]
                for cat in today_status["data"].get("categories", [])
            },
            "languages": {
                lang["name"]: {"hours": lang["text"], "percent": lang["percent"]}
                for lang in today_status["data"].get("languages", [])
                if lang["text"] != "0 secs"
            },
        }

        # Load existing stats or create new file
        try:
            with stats_file.open("r") as f:
                all_stats = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            all_stats = {"daily_records": []}

        # Find and update today's entry if it exists, or append new entry
        today_index = next(
            (
                i
                for i, record in enumerate(all_stats["daily_records"])
                if record["date"] == today
            ),
            None,
        )

        if today_index is not None:
            all_stats["daily_records"][today_index] = daily_stats
        else:
            all_stats["daily_records"].append(daily_stats)

        # Save updated stats
        with stats_file.open("w") as f:
            json.dump(all_stats, f, indent=2)

    def get_productivity_analysis(self) -> None:
        """Analyze productivity metrics and save to log file"""
        # Get required data
        today = get_local_datetime()
        today_status = self.get_today_status()
        week_stats = self.get_user_stats("last_7_days")

        # Get current week's daily data using summaries endpoint
        end_date = today
        start_date = end_date - timedelta(days=6)  # Last 7 days
        week_summaries = self.get_summaries(start_date, end_date)

        # Save stats before analysis
        self.save_daily_stats(today_status, week_stats)

        # Load historical data
        stats_file = Path(STATS_DIR) / "coding_stats.json"
        try:
            with stats_file.open("r") as f:
                historical_data = json.load(f)
                records = historical_data["daily_records"]
        except (FileNotFoundError, json.JSONDecodeError):
            records = []

        logging.info("\n=== Productivity Analysis ===")

        # Today's summary
        try:
            today_total = today_status["data"]["grand_total"]["decimal"]
            logging.info(
                f"\nToday's Activity ({get_local_datetime().strftime('%Y-%m-%d')}):")
            logging.info(f"Total time: {today_total} hours")

            if "categories" in today_status["data"]:
                logging.info("\nActivity Breakdown:")
                for category in today_status["data"]["categories"]:
                    logging.info(
                        f"  - {category.get('name', 'Unknown')}: {category.get('decimal', 0)} hours"
                    )
        except (KeyError, TypeError):
            logging.info("\nNo activity recorded today")

        # Current week breakdown
        try:
            logging.info("\nCurrent Week Breakdown:")
            if "data" in week_summaries:
                logging.info("\nDaily Breakdown (Last 7 Days):")
                for day in week_summaries["data"]:
                    try:
                        date = datetime.fromisoformat(day["range"]["date"]).strftime(
                            "%A"
                        )
                        hours = float(day["grand_total"]["decimal"])
                        logging.info(f"  - {date}: {hours:.2f} hours")
                    except (KeyError, ValueError):
                        continue

                # Calculate 7-day average
                daily_totals = [
                    float(day["grand_total"]["decimal"])
                    for day in week_summaries["data"]
                ]
                if daily_totals:
                    week_avg = sum(daily_totals) / len(daily_totals)
                    logging.info(f"\n7-Day Average: {week_avg:.2f} hours")
                    if today_total:
                        weekly_performance = (float(today_total) / week_avg) * 100
                        logging.info(
                            f"Today vs 7-day average: {weekly_performance:.1f}%"
                        )

        except (KeyError, TypeError) as e:
            logging.error(f"Unable to fetch current week statistics: {e}")

        # Historical weekday analysis
        today_weekday = get_local_datetime().strftime("%A")
        weekday_records = [r for r in records if r["weekday"] == today_weekday]
        if weekday_records:
            logging.info(f"\nHistorical {today_weekday} Analysis:")
            avg_hours = sum(r["total_hours"] for r in weekday_records) / len(
                weekday_records
            )
            logging.info(f"\nHistorical {today_weekday} Average: {avg_hours:.2f} hours")
            if today_total:
                performance = (float(today_total) / avg_hours) * 100
                logging.info(
                    f"Today vs Historical {today_weekday} average: {performance:.1f}%"
                )
            logging.info(f"Previous {today_weekday}s:")
            for record in sorted(
                weekday_records, key=lambda x: x["date"], reverse=True
            )[:4]:
                logging.info(f"  - {record['date']}: {record['total_hours']:.2f} hours")

        # Weekly trends
        def get_week_number(date_str):
            return datetime.strptime(date_str, "%Y-%m-%d").isocalendar()[1]

        # Group records by week
        weekly_totals = {}
        for record in records:
            week = get_week_number(record["date"])
            if week not in weekly_totals:
                weekly_totals[week] = []
            weekly_totals[week].append(record["total_hours"])

        logging.info("\nWeekly Averages:")
        current_week = get_local_datetime().isocalendar()[1]
        for week in sorted(weekly_totals.keys(), reverse=True)[:4]:
            avg = sum(weekly_totals[week]) / len(weekly_totals[week])
            week_label = "Current Week" if week == current_week else f"Week {week}"
            logging.info(f"  {week_label}: {avg:.2f} hours/day")

        # Language breakdown (from API)
        try:
            if "languages" in week_stats["data"]:
                logging.info("\nLanguages Used (Last 7 Days):")
                for lang in week_stats["data"]["languages"][:5]:
                    name = lang.get("name", "Unknown")
                    text = lang.get("text", "0 hrs")
                    percent = lang.get("percent", 0)
                    logging.info(f"  - {name}: {text} ({percent}%)")
        except (KeyError, TypeError):
            logging.error("Unable to fetch language statistics")

        # Get current week breakdown from API
        try:
            logging.info("\nCurrent Week Breakdown:")
            if "data" in week_stats and "days" in week_stats["data"]:
                days = week_stats["data"]["days"]
                if days:
                    for day in sorted(days, key=lambda x: x["date"]):
                        try:
                            date = datetime.fromisoformat(day["date"]).strftime("%A")
                            # The grand_total object contains the daily totals
                            if "grand_total" in day and "decimal" in day["grand_total"]:
                                hours = float(day["grand_total"]["decimal"])
                                logging.info(f"  - {date}: {hours:.2f} hours")
                            else:
                                logging.info(f"  - {date}: 0.00 hours")
                        except Exception as e:
                            logging.error(f"Error processing day: {e}")
                            logging.error(f"Day data: {day}")
                else:
                    logging.info("No activity recorded in the last 7 days")
            else:
                logging.info("No daily data found in the response")

        except (KeyError, TypeError) as e:
            logging.error(f"Unable to fetch current week statistics: {e}")


# Example usage:
if __name__ == "__main__":
    try:
        # Setup logging first
        setup_logging()

        api_key = load_config()
        client = WakaTimeClient(api_key)

        # Log productivity analysis
        client.get_productivity_analysis()

        # Log detailed coding durations
        logging.info("\nAnalyzing today's coding sessions...")
        client.print_coding_durations()

    except (FileNotFoundError, KeyError) as e:
        logging.error(f"Configuration error: {e}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching data from WakaTime: {e}")
