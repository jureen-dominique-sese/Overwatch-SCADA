"""
Overwatch SCADA - Live Fault Locator
------------------------------------
PyWebView backend fetching live fault data from Google Sheets.
UI is in index.html.
"""

import webview
import requests
import csv
import io
from typing import Optional, Dict, Any

# ---------------------------
# CONFIGURATION
# ---------------------------
SHEET_ID = "1f1OMSgWDZs7p7oxvsLQhNiWytlKpWaj1PLIOQgJKyKU"
SHEET_NAME = "logger"


# ---------------------------
# PYTHON API exposed to JS
# ---------------------------
class Api:
    def __init__(self):
        self.latest_data: Optional[Dict[str, Any]] = None

    def get_latest_faults(self):
        """Fetch all rows from Google Sheet and return JSON."""
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"
        response = requests.get(url)
        response.raise_for_status()
        reader = csv.reader(io.StringIO(response.text))
        headers = next(reader, [])
        data = []

        for row in reader:
            try:
                reportID, date, time_, deviceID, distance, lat, lng = row
                data.append({
                    "reportID": reportID,
                    "date": date,
                    "time": time_,
                    "deviceID": deviceID,
                    "distance": float(distance),
                    "lat": float(lat),
                    "lng": float(lng)
                })
            except Exception:
                continue

        if data:
            self.latest_data = data[-1]
        return data

    def get_latest(self):
        """Return only the most recent log entry."""
        return self.latest_data


# ---------------------------
# RUN APP
# ---------------------------
def main():
    api = Api()
    window = webview.create_window(
        "Overwatch SCADA - Fault Locator",
        url="index.html",  # Load from local HTML file
        js_api=api,
        width=1300,
        height=750,
        resizable=True,
    )
    webview.start(debug=True)


if __name__ == "__main__":
    main()
