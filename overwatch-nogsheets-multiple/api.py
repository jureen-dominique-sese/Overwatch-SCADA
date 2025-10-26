"""
Overwatch SCADA - Backend API Module (Updated with Config & State Persistence)
"""
import requests
import csv
import io
import json
import os
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import asyncio
from telegram import Bot
from telegram.error import TelegramError

# Import configuration
try:
    from config import (
        SHEET_ID, SHEET_NAME, CREDENTIALS_FILE,
        TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_IDS,
        SEVERITY_THRESHOLDS
    )
except ImportError:
    # Fallback to hardcoded values
    SHEET_ID = "1f1OMSgWDZs7p7oxvsLQhNiWytlKpWaj1PLIOQgJKyKU"
    SHEET_NAME = "logger"
    CREDENTIALS_FILE = "credentials.json"
    TELEGRAM_BOT_TOKEN = "7853460988:AAH3eIhrYLcu9gmVzVu2Xq-hAgs1pUJk-wU"
    TELEGRAM_CHAT_IDS = ["6493927838"]
    SEVERITY_THRESHOLDS = {"CRITICAL": 2000, "WARNING": 1000, "INFO": 0}

# Define the path for the persistent state file
STATE_FILE = "overwatch_state.json"

class OverwatchAPI:
    def __init__(self):
        self.state_file = STATE_FILE
        # Load state from JSON, which now includes cache AND alerted faults
        loaded_state = self._load_state()
        self.cache = loaded_state['faults']
        self.last_alerted_faults = set(loaded_state['alerted_fault_keys'])
        
        self.gc = None
        self.worksheet = None
        self.telegram_enabled = False
        
        self._init_gspread()
        self._init_telegram()
        
        # Perform an initial check on startup in case sheet is newer than cache
        if self.cache:
            print(f"✓ Loaded {len(self.cache)} faults and {len(self.last_alerted_faults)} alerted faults from state. Checking for updates...")
            self.check_for_updates()
        else:
            print("No cache found. Performing initial fetch...")
            self.check_for_updates()


    def _load_state(self):
        """Load the last known state (faults and alerts) from the JSON file."""
        default_state = {"faults": [], "alerted_fault_keys": []}
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    # Ensure both keys exist
                    data.setdefault('faults', [])
                    data.setdefault('alerted_fault_keys', [])
                    return data
            except json.JSONDecodeError:
                print(f"⚠ Could not decode state file. Starting fresh.")
                return default_state
        return default_state

    def _save_state(self):
        """Save the current state (faults and alerts) to the JSON file."""
        try:
            state_data = {
                "faults": self.cache,
                "alerted_fault_keys": list(self.last_alerted_faults) # Convert set to list for JSON
            }
            with open(self.state_file, 'w') as f:
                json.dump(state_data, f, indent=2)
            print(f"✓ Saved {len(self.cache)} faults and {len(self.last_alerted_faults)} alerted faults to state file.")
        except IOError as e:
            print(f"⚠ Error saving state file: {e}")

    def _init_gspread(self):
        """Initialize Google Sheets connection"""
        try:
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            creds = ServiceAccountCredentials.from_json_keyfile_name(
                CREDENTIALS_FILE, scope
            )
            self.gc = gspread.authorize(creds)
            self.worksheet = self.gc.open_by_key(SHEET_ID).worksheet(SHEET_NAME)
            print("✓ Connected to Google Sheets")
        except Exception as e:
            print(f"⚠ Google Sheets connection failed: {e}")

    def _init_telegram(self):
        """Initialize Telegram bot"""
        try:
            if (TELEGRAM_BOT_TOKEN != "YOUR_BOT_TOKEN_HERE" and
                TELEGRAM_CHAT_IDS[0] != "YOUR_CHAT_ID_HERE"):
                asyncio.run(self._test_telegram_connection())
                self.telegram_enabled = True
                print("✓ Telegram bot initialized")
            else:
                print("⚠ Telegram not configured")
        except Exception as e:
            print(f"⚠ Telegram initialization failed: {e}")
            self.telegram_enabled = False

    async def _test_telegram_connection(self):
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        bot_info = await bot.get_me()
        print(f"✓ Bot connected: @{bot_info.username}")

    async def _send_telegram_message(self, fault):
        """Send telegram alert for a fault"""
        try:
            bot = Bot(token=TELEGRAM_BOT_TOKEN)
            message = (
                f"⚡ *FAULT DETECTION SYSTEM ALERT*\n"
                f"{'═' * 35}\n\n"
                f"🔴 *SEVERITY:* {fault['sev']}\n"
                f"📋 *REPORT ID:* `{fault['id']}`\n"
                f"⏰ *TIME:* {fault['date']} @ {fault['time']}\n\n"
                f"🏭 *EQUIPMENT*\n"
                f"├─ Device: {fault['device']}\n"
                f"├─ Distance: {fault['dist']}m\n"
                f"└─ GPS: {fault['lat']}, {fault['lng']}\n\n"
                f"📍 [View Location](https://www.google.com/maps?q={fault['lat']},{fault['lng']})\n\n"
                f"⚠️ *ACTION REQUIRED*\n"
                f"Immediate investigation needed.\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"_Overwatch SCADA System_"
            )

            for chat_id in TELEGRAM_CHAT_IDS:
                try:
                    await bot.send_message(
                        chat_id=chat_id, text=message,
                        parse_mode='Markdown', disable_web_page_preview=False
                    )
                    print(f"✓ Alert sent to {chat_id} for fault {fault['id']}")
                except TelegramError as e:
                    print(f"✗ Failed to send to {chat_id}: {e}")
        except Exception as e:
            print(f"❌ Telegram send error: {e}")

    def send_telegram_alert(self, fault):
        """Synchronous wrapper for telegram alerts"""
        if not self.telegram_enabled:
            return {"ok": False, "err": "Telegram not enabled"}
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._send_telegram_message(fault))
            loop.close()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "err": str(e)}

    def _calculate_severity(self, distance):
        """Calculate severity based on distance"""
        if distance > SEVERITY_THRESHOLDS["CRITICAL"]:
            return "CRITICAL"
        elif distance > SEVERITY_THRESHOLDS["WARNING"]:
            return "WARNING"
        else:
            return "INFO"
    
    def get_cached_data(self):
        """API endpoint to return the data currently in the cache."""
        return self.cache

    def check_for_updates(self):
        """
        Fetch faults from Google Sheets, compare to cache, and save if new.
        This is the main "check for updates" function.
        """
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"
        
        old_latest_fault_id = self.cache[-1]['id'] if self.cache else None
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            reader = csv.reader(io.StringIO(response.text))
            next(reader)  # Skip header
            data = []
            new_alerts_sent = False # Flag to see if we need to save the state

            for row in reader:
                try:
                    if len(row) < 7:
                        continue

                    dist = float(row[4])
                    sev = self._calculate_severity(dist)
                    status = row[7] if len(row) > 7 else ""

                    fault = {
                        "id": row[0],
                        "date": row[1],
                        "time": row[2],
                        "device": row[3],
                        "dist": dist,
                        "lat": float(row[5]),
                        "lng": float(row[6]),
                        "status": status,
                        "mod": row[8] if len(row) > 8 else "",
                        "ack": status.lower() in ["acknowledged", "resolved", "fixed"],
                        "sev": sev
                    }
                    data.append(fault)

                    # Auto-alert logic
                    if fault['sev'] in ["CRITICAL", "WARNING"] and not fault['ack']:
                        fault_key = f"{fault['id']}_{fault['date']}_{fault['time']}"
                        # This check is now persistent across restarts
                        if fault_key not in self.last_alerted_faults:
                            print(f"🔔 New {fault['sev']} fault detected: {fault['id']}")
                            self.send_telegram_alert(fault)
                            self.last_alerted_faults.add(fault_key)
                            new_alerts_sent = True # Mark that we need to save the state

                except Exception as e:
                    print(f"⚠ Error processing row: {e}")
                    continue

            new_latest_fault_id = data[-1]['id'] if data else None
            
            # Check if new data is actually different
            if new_latest_fault_id != old_latest_fault_id:
                print("✨ New data found. Updating cache.")
                self.cache = data
                self._save_state()  # Save new cache AND new alerts list
                return {"hasNewData": True, "data": self.cache}
            
            # If no new faults, but new alerts were sent (e.g., old fault seen for first time)
            elif new_alerts_sent:
                print("...No new faults, but new alerts sent. Saving alert state.")
                self._save_state() # Save the updated alerts list
                return {"hasNewData": False} # No new *fault data* to reload UI
            
            else:
                print("...No new data.")
                return {"hasNewData": False}

        except Exception as e:
            print(f"⚠ Error fetching faults: {e}")
            return {"hasNewData": False, "error": str(e)}

    def ack_fault(self, rid, status, name):
        """Acknowledge a fault"""
        if not self.worksheet:
            return {"ok": False, "err": "Not connected to Sheets"}
        try:
            cell = self.worksheet.find(rid)
            if not cell:
                return {"ok": False, "err": "Report ID not found"}

            self.worksheet.update_cell(cell.row, 8, status)
            self.worksheet.update_cell(cell.row, 9, name)
            print(f"✓ Fault {rid} acknowledged by {name}")
            
            # After acknowledging, force a data refresh to update the cache and state file
            self.check_for_updates()
            
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "err": str(e)}

    def get_stats(self):
        """Generate statistics *from the current cache*."""
        if not self.cache:
            # Load from state if cache is empty
            loaded_state = self._load_state()
            self.cache = loaded_state['faults']
            self.last_alerted_faults = set(loaded_state['alerted_fault_keys'])
            if not self.cache:
                return {} # Return empty if state is also empty

        today = datetime.now().date()
        week_ago = today - timedelta(days=7)

        stats = {
            "total": len(self.cache), "today": 0, "week": 0,
            "ack": 0, "pend": 0, "crit": 0, "warn": 0, "info": 0,
            "devs": {}
        }

        for f in self.cache:
            try:
                fd = datetime.strptime(f["date"], "%Y-%m-%d").date()

                if fd == today:
                    stats["today"] += 1
                if fd >= week_ago:
                    stats["week"] += 1

                stats["ack" if f["ack"] else "pend"] += 1

                sev_map = {"CRITICAL": "crit", "WARNING": "warn", "INFO": "info"}
                stats[sev_map[f["sev"]]] += 1

                stats["devs"][f["device"]] = stats["devs"].get(f["device"], 0) + 1
            except:
                pass

        return stats

    def test_telegram(self):
        """Send test alert"""
        if not self.telegram_enabled:
            return {"ok": False, "err": "Telegram not configured"}

        test_fault = {
            "id": "TEST-001", "device": "Test Device", "dist": 1500,
            "sev": "WARNING", "date": datetime.now().strftime("%Y-%m-%d"),
            "time": datetime.now().strftime("%H:%M:%S"),
            "lat": 13.621775, "lng": 123.194824
        }
        return self.send_telegram_alert(test_fault)