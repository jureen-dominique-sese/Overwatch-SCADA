"""
Overwatch SCADA - Backend API Module (Updated with Config)
"""
import requests
import csv
import io
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


class OverwatchAPI:
    def __init__(self):
        self.cache = []
        self.gc = None
        self.worksheet = None
        self.telegram_enabled = False
        self.last_alerted_faults = set()
        self._init_gspread()
        self._init_telegram()

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

    def get_faults(self):
        """Fetch faults from Google Sheets"""
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            reader = csv.reader(io.StringIO(response.text))
            next(reader)  # Skip header
            data = []

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
                        if fault_key not in self.last_alerted_faults:
                            print(f"🔔 New {fault['sev']} fault: {fault['id']}")
                            self.send_telegram_alert(fault)
                            self.last_alerted_faults.add(fault_key)

                except Exception as e:
                    print(f"⚠ Error processing row: {e}")
                    continue

            self.cache = data
            return data

        except Exception as e:
            print(f"⚠ Error fetching faults: {e}")
            return self.cache

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
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "err": str(e)}

    def get_stats(self):
        """Generate statistics"""
        if not self.cache:
            return {}

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