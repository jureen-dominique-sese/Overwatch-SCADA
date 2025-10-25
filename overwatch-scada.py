"""
Overwatch SCADA - Enhanced with Multiple Map Types & Transmission Linessad
"""

import webview
import requests
import csv
import io
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials

SHEET_ID = "1f1OMSgWDZs7p7oxvsLQhNiWytlKpWaj1PLIOQgJKyKU"
SHEET_NAME = "logger"
CREDENTIALS_FILE = "credentials.json"


class Api:
    def __init__(self):
        self.cache = []
        self.gc = None
        self.worksheet = None
        self._init_gspread()

    def _init_gspread(self):
        try:
            scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
            creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
            self.gc = gspread.authorize(creds)
            self.worksheet = self.gc.open_by_key(SHEET_ID).worksheet(SHEET_NAME)
            print("✓ Connected to Google Sheets")
        except Exception as e:
            print(f"⚠ Connection failed: {e}")

    def get_faults(self):
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            reader = csv.reader(io.StringIO(response.text))
            next(reader)
            data = []

            for row in reader:
                try:
                    if len(row) < 7:
                        continue
                    dist = float(row[4])
                    sev = "CRITICAL" if dist > 2000 else "WARNING" if dist > 1000 else "INFO"
                    status = row[7] if len(row) > 7 else ""
                    data.append({
                        "id": row[0], "date": row[1], "time": row[2], "device": row[3],
                        "dist": dist, "lat": float(row[5]), "lng": float(row[6]),
                        "status": status, "mod": row[8] if len(row) > 8 else "",
                        "ack": status.lower() in ["acknowledged", "resolved", "fixed"], "sev": sev
                    })
                except:
                    continue
            self.cache = data
            return data
        except:
            return self.cache

    def ack_fault(self, rid, status, name):
        if not self.worksheet:
            return {"ok": False, "err": "Not connected"}
        try:
            cell = self.worksheet.find(rid)
            if not cell:
                return {"ok": False, "err": "ID not found"}
            self.worksheet.update_cell(cell.row, 8, status)
            self.worksheet.update_cell(cell.row, 9, name)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "err": str(e)}

    def get_stats(self):
        if not self.cache:
            return {}
        today = datetime.now().date()
        week_ago = today - timedelta(days=7)
        stats = {"total": len(self.cache), "today": 0, "week": 0, "ack": 0, "pend": 0,
                 "crit": 0, "warn": 0, "info": 0, "devs": {}}
        for f in self.cache:
            try:
                fd = datetime.strptime(f["date"], "%Y-%m-%d").date()
                if fd == today:
                    stats["today"] += 1
                if fd >= week_ago:
                    stats["week"] += 1
                stats["ack" if f["ack"] else "pend"] += 1
                stats[{"CRITICAL": "crit", "WARNING": "warn", "INFO": "info"}[f["sev"]]] += 1
                stats["devs"][f["device"]] = stats["devs"].get(f["device"], 0) + 1
            except:
                pass
        return stats


HTML = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Overwatch SCADA</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.css">
<script src="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
:root{
  --bg:#1e1e1e;
  --bg-secondary:#252526;
  --bg-tertiary:#2d2d30;
  --panel:#252526;
  --text:#cccccc;
  --text-secondary:#858585;
  --border:#3e3e42;
  --accent:#007acc;
  --accent-hover:#1c97ea;
  --crit:#f48771;
  --warn:#cca700;
  --info:#4fc1ff;
  --ok:#89d185;
  --input-bg:#3c3c3c;
}
[dark]{
  --bg:#0d1117;
  --bg-secondary:#161b22;
  --bg-tertiary:#21262d;
  --panel:#161b22;
  --border:#30363d;
  --accent:#58a6ff;
  --input-bg:#0d1117;
}
*{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',system-ui,-apple-system,sans-serif}
body{background:var(--bg);color:var(--text);overflow:hidden;font-size:13px;line-height:1.5}
.top{
  background:var(--bg-secondary);
  border-bottom:1px solid var(--border);
  padding:0 20px;
  height:40px;
  display:flex;
  align-items:center;
  gap:20px;
}
.top-title{
  font-weight:600;
  color:var(--text);
  margin-right:auto;
  font-size:13px;
  letter-spacing:0.3px;
}
.top-btn{
  padding:6px 14px;
  cursor:pointer;
  border-radius:3px;
  font-size:12px;
  color:var(--text-secondary);
  transition:all 0.15s ease;
  border:1px solid transparent;
}
.top-btn:hover{
  background:var(--bg-tertiary);
  color:var(--text);
  border-color:var(--border);
}
.tabs{
  background:var(--bg-secondary);
  border-bottom:1px solid var(--border);
  display:flex;
  padding:0 20px;
  gap:4px;
}
.tab{
  padding:12px 20px;
  cursor:pointer;
  border-bottom:2px solid transparent;
  font-size:13px;
  color:var(--text-secondary);
  transition:all 0.15s ease;
  position:relative;
}
.tab:hover{
  background:var(--bg-tertiary);
  color:var(--text);
}
.tab.on{
  color:var(--accent);
  border-bottom-color:var(--accent);
  background:var(--bg);
}
.main{display:flex;height:calc(100vh - 111px)}
.content{display:none;flex:1}
.content.on{display:flex}
.map-view{display:flex;width:100%;position:relative;background:var(--bg)}
#map{flex:1}
.map-ctrl{
  position:absolute;
  top:16px;
  right:356px;
  z-index:1000;
  background:var(--panel);
  border-radius:4px;
  border:1px solid var(--border);
  box-shadow:0 4px 12px rgba(0,0,0,0.4);
  overflow:hidden;
  min-width:200px;
}
.map-ctrl-title{
  padding:10px 14px;
  background:var(--bg-tertiary);
  color:var(--text);
  font-weight:600;
  font-size:11px;
  text-transform:uppercase;
  letter-spacing:0.5px;
  border-bottom:1px solid var(--border);
}
.map-ctrl-opt{
  padding:10px 14px;
  cursor:pointer;
  font-size:12px;
  border-bottom:1px solid var(--border);
  display:flex;
  align-items:center;
  gap:10px;
  color:var(--text);
  transition:background 0.15s ease;
}
.map-ctrl-opt:last-child{border-bottom:none}
.map-ctrl-opt:hover{background:var(--bg-tertiary)}
.map-ctrl-opt.on{
  background:var(--bg-tertiary);
  color:var(--accent);
  border-left:2px solid var(--accent);
  padding-left:12px;
}
.side{
  width:340px;
  background:var(--panel);
  border-left:1px solid var(--border);
  overflow-y:auto;
  padding:20px;
  display:flex;
  flex-direction:column;
  gap:20px;
}
.side h3{
  font-size:12px;
  color:var(--text-secondary);
  text-transform:uppercase;
  letter-spacing:0.5px;
  margin-bottom:12px;
  font-weight:600;
}
.box{
  background:var(--bg-tertiary);
  border-radius:4px;
  padding:14px;
  font-size:12px;
  line-height:1.6;
  border:1px solid var(--border);
}
.box strong{color:var(--accent);font-weight:600}
.btn{
  width:100%;
  padding:10px;
  border:1px solid var(--border);
  border-radius:4px;
  cursor:pointer;
  font-size:12px;
  font-weight:500;
  margin-top:8px;
  transition:all 0.15s ease;
  background:var(--bg-tertiary);
  color:var(--text);
}
.btn:hover{
  background:var(--accent);
  color:#fff;
  border-color:var(--accent);
}
.btn-1{background:var(--accent);color:#fff;border-color:var(--accent)}
.btn-1:hover{background:var(--accent-hover)}
.btn-2{background:var(--bg-tertiary);color:var(--text)}
.btn-2:hover{background:var(--input-bg)}
.btn-ok{background:var(--ok);color:#000;border-color:var(--ok);font-weight:600}
.btn-ok:hover{opacity:0.85}
.tog{
  display:flex;
  align-items:center;
  justify-content:center;
  gap:8px;
  background:var(--input-bg);
  border-color:var(--border);
}
.tog.on{
  background:var(--ok);
  color:#000;
  border-color:var(--ok);
  font-weight:600;
}
.stats-view{padding:28px;overflow-y:auto;width:100%;background:var(--bg)}
.stats-view h2{
  margin-bottom:24px;
  color:var(--text);
  font-size:18px;
  font-weight:600;
  letter-spacing:0.3px;
}
.stat-grid{
  display:grid;
  grid-template-columns:repeat(auto-fit,minmax(200px,1fr));
  gap:16px;
  margin-bottom:28px;
}
.stat{
  background:var(--panel);
  border-radius:4px;
  padding:20px;
  border:1px solid var(--border);
  border-left:3px solid var(--accent);
}
.stat.crit{border-left-color:var(--crit)}
.stat.warn{border-left-color:var(--warn)}
.stat.ok{border-left-color:var(--ok)}
.stat-label{
  font-size:11px;
  color:var(--text-secondary);
  margin-bottom:8px;
  text-transform:uppercase;
  letter-spacing:0.5px;
  font-weight:600;
}
.stat-val{
  font-size:32px;
  font-weight:700;
  color:var(--text);
}
.chart-grid{
  display:grid;
  grid-template-columns:repeat(auto-fit,minmax(400px,1fr));
  gap:16px;
}
.chart{
  background:var(--panel);
  border-radius:4px;
  padding:20px;
  border:1px solid var(--border);
}
.chart h3{
  font-size:13px;
  color:var(--text);
  margin-bottom:16px;
  font-weight:600;
}
.logs-view{
  padding:20px;
  display:flex;
  flex-direction:column;
  gap:16px;
  overflow-y:auto;
  width:100%;
  background:var(--bg);
}
.filters{
  display:flex;
  gap:12px;
  flex-wrap:wrap;
  background:var(--panel);
  padding:16px;
  border-radius:4px;
  border:1px solid var(--border);
}
.inp{
  flex:1;
  min-width:200px;
  padding:8px 12px;
  border:1px solid var(--border);
  border-radius:4px;
  font-size:12px;
  background:var(--input-bg);
  color:var(--text);
  transition:border-color 0.15s ease;
}
.inp:focus{
  outline:none;
  border-color:var(--accent);
}
.sel{
  padding:8px 12px;
  border:1px solid var(--border);
  border-radius:4px;
  font-size:12px;
  background:var(--input-bg);
  color:var(--text);
  cursor:pointer;
}
.sel:focus{
  outline:none;
  border-color:var(--accent);
}
.btn-sm{padding:8px 14px;font-size:12px}
table{
  width:100%;
  border-collapse:collapse;
  background:var(--panel);
  border-radius:4px;
  overflow:hidden;
  border:1px solid var(--border);
}
th,td{
  padding:12px 16px;
  text-align:left;
  border-bottom:1px solid var(--border);
  font-size:12px;
}
th{
  background:var(--bg-tertiary);
  font-weight:600;
  cursor:pointer;
  user-select:none;
  color:var(--text-secondary);
  text-transform:uppercase;
  font-size:11px;
  letter-spacing:0.5px;
}
th:hover{background:var(--input-bg)}
tr:hover{background:var(--bg-tertiary)}
.badge{
  display:inline-block;
  padding:4px 9px;
  border-radius:3px;
  font-size:10px;
  font-weight:600;
  text-transform:uppercase;
  letter-spacing:0.3px;
}
.badge.crit{background:var(--crit);color:#000}
.badge.warn{background:var(--warn);color:#000}
.badge.info{background:var(--info);color:#000}
.status{
  background:var(--bg-secondary);
  border-top:1px solid var(--border);
  padding:0 20px;
  display:flex;
  align-items:center;
  gap:20px;
  font-size:11px;
  height:31px;
  color:var(--text-secondary);
}
.dot{
  width:8px;
  height:8px;
  border-radius:50%;
  background:var(--ok);
  animation:dot 2s infinite;
}
@keyframes dot{0%,100%{opacity:1}50%{opacity:0.4}}
.dot.err{background:var(--crit)}
.modal{
  display:none;
  position:fixed;
  top:0;
  left:0;
  width:100%;
  height:100%;
  background:rgba(0,0,0,0.75);
  align-items:center;
  justify-content:center;
  z-index:999;
  backdrop-filter:blur(4px);
}
.modal.on{display:flex}
.mbox{
  background:var(--panel);
  padding:28px;
  border-radius:6px;
  width:420px;
  border:1px solid var(--border);
  box-shadow:0 8px 32px rgba(0,0,0,0.6);
}
.mbox h3{
  margin-bottom:20px;
  font-size:16px;
  font-weight:600;
  color:var(--text);
}
.fg{margin-bottom:16px}
.fg label{
  display:block;
  margin-bottom:6px;
  font-size:12px;
  font-weight:500;
  color:var(--text-secondary);
  text-transform:uppercase;
  letter-spacing:0.3px;
}
.fg input,.fg select{
  width:100%;
  padding:10px 12px;
  border:1px solid var(--border);
  border-radius:4px;
  font-size:13px;
  background:var(--input-bg);
  color:var(--text);
  transition:border-color 0.15s ease;
}
.fg input:focus,.fg select:focus{
  outline:none;
  border-color:var(--accent);
}
.mact{display:flex;gap:12px;margin-top:20px}
.pulse{
  width:12px;
  height:12px;
  border-radius:50%;
  position:absolute;
  animation:pul 2s infinite;
}
@keyframes pul{
  0%{transform:scale(1);opacity:0.6}
  70%{transform:scale(2.5);opacity:0}
  100%{opacity:0}
}
.pulse.r{background:rgba(244,135,113,0.6)}
.pulse.b{background:rgba(0,122,204,0.6)}
.pulse.o{background:rgba(204,167,0,0.6)}
.flash{
  position:fixed;
  top:0;
  left:0;
  width:100%;
  height:100%;
  background:var(--crit);
  opacity:0;
  pointer-events:none;
  z-index:998;
}
.flash.on{animation:fla 0.4s 3}
@keyframes fla{0%,100%{opacity:0}50%{opacity:0.15}}
.chk{margin-right:6px;cursor:pointer}
::-webkit-scrollbar{width:10px;height:10px}
::-webkit-scrollbar-track{background:var(--bg)}
::-webkit-scrollbar-thumb{background:var(--border);border-radius:5px}
::-webkit-scrollbar-thumb:hover{background:var(--text-secondary)}
</style>
</head><body>

<div class="flash" id="flash"></div>

<div class="top">
  <div class="top-title">⚡ Overwatch SCADA - Region 5 Bicol</div>
  <div class="top-btn" onclick="exp()">📥 Export</div>
  <div class="top-btn" onclick="ref()">🔄 Refresh</div>
  <div class="top-btn" onclick="dark()">🌙 Dark</div>
</div>

<div class="tabs">
  <div class="tab on" onclick="sw('map')">🗺️ Map</div>
  <div class="tab" onclick="sw('stats')">📊 Stats</div>
  <div class="tab" onclick="sw('logs')">📋 Logs</div>
</div>

<div class="main">
  <div class="content on" id="map-content">
    <div class="map-view">
      <div id="map"></div>
      
      <div class="map-ctrl">
        <div class="map-ctrl-title">🗺️ MAP LAYERS</div>
        <div class="map-ctrl-opt on" onclick="chgMap('osm')">
          <input type="radio" name="maptype" class="chk" checked>Standard
        </div>
        <div class="map-ctrl-opt" onclick="chgMap('satellite')">
          <input type="radio" name="maptype" class="chk">Satellite
        </div>
        <div class="map-ctrl-opt" onclick="chgMap('terrain')">
          <input type="radio" name="maptype" class="chk">Terrain
        </div>
        <div class="map-ctrl-opt" onclick="chgMap('dark')">
          <input type="radio" name="maptype" class="chk">Dark Mode
        </div>
        <div class="map-ctrl-title">⚡ OVERLAYS</div>
        <div class="map-ctrl-opt" onclick="togOverlay('transmission')">
          <input type="checkbox" id="chk-trans" class="chk">Transmission Lines
        </div>
        <div class="map-ctrl-opt" onclick="togOverlay('substations')">
          <input type="checkbox" id="chk-subs" class="chk">Substations
        </div>
        <div class="map-ctrl-opt" onclick="togOverlay('coverage')">
          <input type="checkbox" id="chk-cov" class="chk">Service Areas
        </div>
      </div>
      
      <div class="side">
        <div><h3>📍 Latest</h3><div class="box" id="latest">Loading...</div></div>
        <div><h3>🎮 Actions</h3>
          <button class="btn tog" id="monitor" onclick="togMon()">📍 Monitor: OFF</button>
          <button class="btn btn-1" onclick="ref()">🔄 Refresh</button>
          <button class="btn btn-ok" onclick="showAck()">✔ Acknowledge</button>
          <button class="btn btn-2" onclick="zAll()">🎯 View All</button>
        </div>
        <div><h3>🔔 Alerts</h3>
          <button class="btn tog on" id="sound" onclick="togSnd()">🔊 Sound: ON</button>
        </div>
      </div>
    </div>
  </div>

  <div class="content" id="stats-content">
    <div class="stats-view">
      <h2 style="margin-bottom:20px;color:var(--accent)">📊 Statistics</h2>
      <div class="stat-grid" id="sgrid"></div>
      <div class="chart-grid">
        <div class="chart"><h3>Severity Distribution</h3><canvas id="c1"></canvas></div>
        <div class="chart"><h3>Faults by Device</h3><canvas id="c2"></canvas></div>
      </div>
    </div>
  </div>

  <div class="content" id="logs-content">
    <div class="logs-view">
      <div class="filters">
        <input class="inp" id="search" placeholder="🔍 Search..." oninput="filt()">
        <select class="sel" id="fdev" onchange="filt()"><option value="">All Devices</option></select>
        <select class="sel" id="fstat" onchange="filt()">
          <option value="">All Status</option><option value="p">Pending</option><option value="a">Acknowledged</option>
        </select>
        <select class="sel" id="fsev" onchange="filt()">
          <option value="">All Severity</option><option value="CRITICAL">Critical</option>
          <option value="WARNING">Warning</option><option value="INFO">Info</option>
        </select>
        <button class="btn btn-2 btn-sm" onclick="clr()">🗑️ Clear</button>
      </div>
      <div style="overflow-x:auto">
        <table><thead><tr>
          <th onclick="sort(0)">ID ⇅</th><th onclick="sort(1)">Date ⇅</th><th onclick="sort(2)">Time ⇅</th>
          <th onclick="sort(3)">Device ⇅</th><th onclick="sort(4)">Dist ⇅</th><th onclick="sort(5)">Severity ⇅</th>
          <th onclick="sort(6)">Status ⇅</th><th onclick="sort(7)">Modified ⇅</th><th>Act</th>
        </tr></thead><tbody id="tbody"></tbody></table>
      </div>
    </div>
  </div>
</div>

<div class="status">
  <div style="display:flex;align-items:center;gap:5px">
    <div class="dot" id="dot"></div><span id="conn">Connected</span>
  </div>
  <div>|</div>
  <div id="upd">Last: --:--:--</div>
  <div>|</div>
  <div id="cnt">Faults: 0</div>
  <div style="margin-left:auto">👤 Operator</div>
</div>

<div id="modal" class="modal">
  <div class="mbox">
    <h3>✔ Acknowledge Fault</h3>
    <div class="fg"><label>Report ID</label><input id="aid" placeholder="Enter ID"></div>
    <div class="fg"><label>Status</label>
      <select id="astat">
        <option>Acknowledged</option><option>Resolved</option>
        <option>Under Investigation</option><option>Fixed</option>
      </select>
    </div>
    <div class="fg"><label>Your Name</label><input id="aname" placeholder="Enter name"></div>
    <div class="mact">
      <button class="btn btn-2" style="flex:1" onclick="hideAck()">Cancel</button>
      <button class="btn btn-ok" style="flex:1" onclick="subAck()">Submit</button>
    </div>
  </div>
</div>

<script>
let map,data=[],circ=[],mon=false,snd=true,last=null,charts={},sdir={};
let currentLayer,transmissionLayer,substationLayer,coverageLayer;

const TRANSMISSION_LINES = [
  {from:[13.621775,123.194824],to:[13.148300,123.712400],voltage:230,name:'Naga-Daraga 230kV'},
  {from:[13.148300,123.712400],to:[14.112200,122.955300],voltage:230,name:'Daraga-Sorsogon 230kV'},
  {from:[13.621775,123.194824],to:[14.099578,122.955035],voltage:69,name:'Naga-Daet (via Camarines Norte) 69kV'},
  {from:[13.148300,123.712400],to:[13.1442028,123.7447158],voltage:69,name:'Daraga-Legazpi 69kV'},
  {from:[13.148300,123.712400],to:[13.432400,123.411500],voltage:69,name:'Daraga-Iriga 69kV'},
  {from:[14.112200,122.955300],to:[12.667904,123.8736101],voltage:69,name:'Sorsogon/Daet-Bulan 69kV'},
  {from:[13.621775,123.194824],to:[13.554725,123.274724],voltage:69,name:'Naga-Pili 69kV'},
  {from:[13.148300,123.712400],to:[13.595469,123.281256],voltage:69,name:'Daraga-Santo Domingo / Pili area 69kV'},
  {from:[13.621775,123.194824],to:[13.405867,123.4059345],voltage:34.5,name:'Naga Distribution (approx to Iriga area)'},
  {from:[13.1442028,123.7447158],to:[13.420537,123.418047],voltage:34.5,name:'Legazpi Distribution (approx)'}
];

const SUBSTATIONS = [
  {name:'Naga Substation (city center proxy)',lat:13.621775,lng:123.194824,voltage:230,type:'Transmission'},
  {name:'Daraga Substation (town center proxy)',lat:13.148300,lng:123.712400,voltage:230,type:'Transmission'},
  {name:'Sorsogon / Daet Substation (regional proxy)',lat:12.992710,lng:124.014746,voltage:230,type:'Transmission'},
  {name:'Legazpi Substation (city center / SM Legazpi)',lat:13.144203,lng:123.744716,voltage:69,type:'Distribution'},
  {name:'Iriga Substation (city center proxy)',lat:13.432400,lng:123.411500,voltage:69,type:'Distribution'},
  {name:'Daet Substation (CANORECO / Daet center)',lat:14.112200,lng:122.955300,voltage:69,type:'Distribution'},
  {name:'Pili Substation (Pili town center proxy)',lat:13.554725,lng:123.274724,voltage:69,type:'Distribution'},
  {name:'Bulan Substation (Bulan town center proxy)',lat:12.667904,lng:123.873610,voltage:69,type:'Distribution'}
];

const COVERAGE_AREAS = [
  {name:'CASURECO II (Naga)',center:[13.621775,123.194824],radius:25000,color:'#ff6b6b'},
  {name:'ALECO (Legazpi)',center:[13.144203,123.744716],radius:30000,color:'#4ecdc4'},
  {name:'SORECO II (Sorsogon)',center:[12.992710,124.014746],radius:28000,color:'#45b7d1'},
  {name:'CASURECO I (Libmanan)',center:[13.695335,123.061928],radius:22000,color:'#96ceb4'},
  {name:'CANORECO (Daet)',center:[14.112200,122.955300],radius:20000,color:'#ffeaa7'}
];


function init(){

  try{
    map=L.map('map').setView([13.41,123.35],9);
    currentLayer=L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{
      attribution:'© OpenStreetMap'
    }).addTo(map);
    
    transmissionLayer=L.layerGroup();
    substationLayer=L.layerGroup();
    coverageLayer=L.layerGroup();
    
    // Try OSM first, fall back to manual data if it fails
    fetchOSMPowerLines();
    
    drawSubstations();
    drawCoverageAreas();
    ref();setInterval(ref,8000);
    }catch(e){console.error('Init error:',e);}
  }

function drawTransmissionLines(){
  TRANSMISSION_LINES.forEach(line=>{
    const color=line.voltage===230?'#e74c3c':line.voltage===69?'#3498db':'#2ecc71';
    const weight=line.voltage===230?4:line.voltage===69?3:2;
    const opacity=line.voltage===230?0.8:0.6;
    const polyline=L.polyline([line.from,line.to],{
      color:color,weight:weight,opacity:opacity,
      dashArray:line.voltage===34.5?'5,10':null
    });
    polyline.bindPopup('<b>'+line.name+'</b><br>Voltage: '+line.voltage+' kV<br>'+
      'Type: '+(line.voltage>=230?'Transmission':line.voltage>=69?'Sub-transmission':'Distribution'));
    transmissionLayer.addLayer(polyline);
  });
}

function drawSubstations(){
  SUBSTATIONS.forEach(sub=>{
    const isTransmission = sub.voltage >= 230;
    const color = isTransmission ? '#f48771' : '#4fc1ff';
    const bgColor = isTransmission ? 'rgba(244,135,113,0.2)' : 'rgba(79,193,255,0.2)';
    
    const icon = L.divIcon({
      html: `
        <div style="position:relative;text-align:center;">
          <!-- Outer glow -->
          <div style="
            position:absolute;
            width:32px;
            height:32px;
            top:-8px;
            left:-8px;
            border-radius:50%;
            background:${bgColor};
            animation:subGlow 2s ease-in-out infinite;
          "></div>
          <!-- Main icon -->
          <div style="
            position:relative;
            width:20px;
            height:20px;
            background:${color};
            border:2px solid #fff;
            border-radius:4px;
            box-shadow:0 3px 10px rgba(0,0,0,0.5);
            display:flex;
            align-items:center;
            justify-content:center;
            font-weight:bold;
            font-size:10px;
            color:#000;
          ">⚡</div>
          <!-- Label -->
          <div style="
            position:absolute;
            top:24px;
            left:50%;
            transform:translateX(-50%);
            background:rgba(37,37,38,0.95);
            color:#ccc;
            padding:4px 9px;
            border-radius:3px;
            font-size:10px;
            white-space:nowrap;
            border:1px solid #3e3e42;
            font-weight:600;
            box-shadow:0 2px 6px rgba(0,0,0,0.4);
          ">${sub.name.replace(' Substation','')}<br/>
          <span style="font-size:9px;color:#858585;">${sub.voltage}kV</span>
          </div>
        </div>
      `,
      className:'',
      iconSize:[20,60],
      iconAnchor:[10,10]
    });
    
    const marker = L.marker([sub.lat,sub.lng],{icon:icon});
    
    marker.bindPopup(`
      <div style="font-family:'Segoe UI',sans-serif;min-width:200px;">
        <div style="
          font-weight:600;
          font-size:14px;
          margin-bottom:10px;
          color:#007acc;
          padding-bottom:8px;
          border-bottom:1px solid #3e3e42;
        ">
          ${sub.name}
        </div>
        <table style="width:100%;font-size:11px;line-height:1.8;">
          <tr>
            <td style="color:#858585;font-weight:500;">Voltage:</td>
            <td style="color:#ccc;text-align:right;font-weight:600;">${sub.voltage} kV</td>
          </tr>
          <tr>
            <td style="color:#858585;font-weight:500;">Type:</td>
            <td style="color:#ccc;text-align:right;">${sub.type}</td>
          </tr>
          <tr>
            <td style="color:#858585;font-weight:500;">Latitude:</td>
            <td style="color:#ccc;text-align:right;font-family:monospace;">${sub.lat.toFixed(5)}</td>
          </tr>
          <tr>
            <td style="color:#858585;font-weight:500;">Longitude:</td>
            <td style="color:#ccc;text-align:right;font-family:monospace;">${sub.lng.toFixed(5)}</td>
          </tr>
        </table>
      </div>
    `);
    
    substationLayer.addLayer(marker);
  });
}

function drawCoverageAreas(){
  COVERAGE_AREAS.forEach(area=>{
    const circle=L.circle(area.center,{
      radius:area.radius,color:area.color,fillColor:area.color,
      fillOpacity:0.1,opacity:0.4,weight:2,dashArray:'5,10'
    });
    circle.bindPopup('<b>'+area.name+'</b><br>Service Coverage Area');
    coverageLayer.addLayer(circle);
  });
}

function chgMap(type){
  try{
    map.removeLayer(currentLayer);
    switch(type){
      case 'satellite':
        currentLayer=L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',{attribution:'© Esri'});
        break;
      case 'terrain':
        currentLayer=L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',{attribution:'© OpenTopoMap'});
        break;
      case 'dark':
        currentLayer=L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',{attribution:'© CartoDB'});
        break;
      default:
        currentLayer=L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© OpenStreetMap'});
    }
    currentLayer.addTo(map);
    document.querySelectorAll('.map-ctrl-opt').forEach((el,i)=>{
      if(i<4){el.classList.remove('on');el.querySelector('input').checked=false;}
    });
    event.target.closest('.map-ctrl-opt').classList.add('on');
    event.target.closest('.map-ctrl-opt').querySelector('input').checked=true;
  }catch(e){console.error('Map change error:',e);}
}

function togOverlay(type){
  try{
    const checkbox=document.getElementById('chk-'+type.substring(0,type==='transmission'?5:type==='substations'?4:3));
    switch(type){
      case 'transmission':
        if(map.hasLayer(transmissionLayer)){map.removeLayer(transmissionLayer);checkbox.checked=false;}
        else{map.addLayer(transmissionLayer);checkbox.checked=true;}
        break;
      case 'substations':
        if(map.hasLayer(substationLayer)){map.removeLayer(substationLayer);checkbox.checked=false;}
        else{map.addLayer(substationLayer);checkbox.checked=true;}
        break;
      case 'coverage':
        if(map.hasLayer(coverageLayer)){map.removeLayer(coverageLayer);checkbox.checked=false;}
        else{map.addLayer(coverageLayer);checkbox.checked=true;}
        break;
    }
  }catch(e){console.error('Overlay toggle error:',e);}
}

async function ref(){
  try{
    const d=await window.pywebview.api.get_faults();
    if(!d||!d.length)return;
    data=d;
    const l=d[d.length-1];
    if(snd&&last&&l.id!==last){beep(l.sev);flash();}
    if(mon&&last&&l.id!==last)map.setView([l.lat,l.lng],14);
    last=l.id;
    upLat(l);upMap(d);upTab(d);upDev(d);upBar(d);
  }catch(e){console.error('Refresh error:',e);}
}

function upLat(f){
  try{
    const s=f.ack?'✓ Ack':'⚠ Pending';
    document.getElementById('latest').innerHTML='<strong>'+f.id+'</strong> '+s+'<br>Device: '+f.device+
      '<br>Dist: '+f.dist+' m<br>Sev: '+f.sev+'<br>Time: '+f.date+' '+f.time;
  }catch(e){console.error('Update latest error:',e);}
}

function upMap(d){
  try{
    // Clear all previous layers (circles AND markers)
    circ.forEach(layer => map.removeLayer(layer));
    circ = [];

    d.forEach(f => {
      const col = f.ack ? '#0078d4' : f.sev === 'CRITICAL' ? '#dc3545' : f.sev === 'WARNING' ? '#ffc107' : '#17a2b8';
      
      // 1. Create the circle
      const c = L.circle([f.lat, f.lng], {
        color: col,
        fillColor: col,
        fillOpacity: 0.2,
        radius: f.dist
      }).addTo(map);

      // 2. Create the pulsing icon marker
      const pc = f.ack ? 'b' : f.sev === 'CRITICAL' ? 'r' : 'o';
      const ic = L.divIcon({
        html: '<div class="pulse ' + pc + '"></div>',
        className: '',
        iconSize: [12, 12]
      });
      const marker = L.marker([f.lat, f.lng], {icon: ic}).addTo(map);

      // 3. Create the new popup content with a button
      // We use CSS variables to match your dark/light theme
      const popupBtnStyle = `
        padding: 6px 12px;
        background: var(--accent);
        color: #fff;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        font-weight: 600;
        font-family: 'Segoe UI', sans-serif;
        margin-top: 10px;
        width: 100%;
        transition: background 0.15s ease;
      `;
      
      const popupContent = `
        <div style="font-family: 'Segoe UI', sans-serif; font-size: 13px; line-height: 1.6; color: var(--text);">
          <b style="font-size: 14px; color: var(--accent);">${f.id}</b><br>
          <b>Device:</b> ${f.device}<br>
          <b>Dist:</b> ${f.dist} m<br>
          <b>Severity:</b> ${f.sev}<br>
          <b>Status:</b> ${f.ack ? ('✓ ' + f.status) : '⚠ Pending'}<br>
          <button style="${popupBtnStyle}" 
                  onmouseover="this.style.background='var(--accent-hover)'"
                  onmouseout="this.style.background='var(--accent)'"
                  onclick="clickAck('${f.id}')">
            ✔ Acknowledge
          </button>
        </div>
      `;

      // 4. Bind popup to both circle and marker
      c.bindPopup(popupContent);
      marker.bindPopup(popupContent);

      // 5. Add both layers to the circ array to be cleared on next refresh
      circ.push(c);
      circ.push(marker);
    });
  } catch(e) {
    console.error('Map update error:', e);
  }
}

function upTab(d){
  try{
    const tb=document.getElementById('tbody');tb.innerHTML='';
    d.slice(-50).reverse().forEach(f=>{
      const r=tb.insertRow();
      r.innerHTML='<td>'+f.id+'</td><td>'+f.date+'</td><td>'+f.time+'</td><td>'+f.device+
        '</td><td>'+f.dist+'</td><td><span class="badge '+f.sev.toLowerCase()+'">'+f.sev+'</span></td>'+
        '<td>'+(f.ack?'✓ '+f.status:'⚠ Pending')+'</td><td>'+(f.mod||'-')+'</td>'+
        '<td><button class="btn btn-sm btn-1" onclick="zm('+f.lat+','+f.lng+')" style="padding:4px 8px">🔍</button></td>';
    });
  }catch(e){console.error('Table update error:',e);}
}

function upDev(d){
  try{
    const s=document.getElementById('fdev');
    const devs=[...new Set(d.map(f=>f.device))];
    s.innerHTML='<option value="">All Devices</option>';
    devs.forEach(dv=>s.innerHTML+='<option>'+dv+'</option>');
  }catch(e){console.error('Device update error:',e);}
}

function upBar(d){
  try{
    document.getElementById('dot').classList.remove('err');
    document.getElementById('conn').textContent='Connected';
    document.getElementById('cnt').textContent='Faults: '+d.length;
    document.getElementById('upd').textContent='Last: '+new Date().toLocaleTimeString();
  }catch(e){console.error('Status bar error:',e);}
}

async function ldStats(){
  try{
    const s=await window.pywebview.api.get_stats();
    document.getElementById('sgrid').innerHTML=
      '<div class="stat"><div class="stat-label">Total</div><div class="stat-val">'+s.total+'</div></div>'+
      '<div class="stat"><div class="stat-label">Today</div><div class="stat-val">'+s.today+'</div></div>'+
      '<div class="stat"><div class="stat-label">This Week</div><div class="stat-val">'+s.week+'</div></div>'+
      '<div class="stat ok"><div class="stat-label">Acknowledged</div><div class="stat-val">'+s.ack+'</div></div>'+
      '<div class="stat crit"><div class="stat-label">Pending</div><div class="stat-val">'+s.pend+'</div></div>'+
      '<div class="stat crit"><div class="stat-label">Critical</div><div class="stat-val">'+s.crit+'</div></div>'+
      '<div class="stat warn"><div class="stat-label">Warning</div><div class="stat-val">'+s.warn+'</div></div>'+
      '<div class="stat"><div class="stat-label">Info</div><div class="stat-val">'+s.info+'</div></div>';
    
    if(charts.c1)charts.c1.destroy();
    charts.c1=new Chart(document.getElementById('c1'),{
      type:'doughnut',
      data:{labels:['Critical','Warning','Info'],datasets:[{data:[s.crit,s.warn,s.info],
        backgroundColor:['#dc3545','#ffc107','#17a2b8']}]},
      options:{responsive:true,plugins:{legend:{position:'bottom'}}}
    });
    
    if(charts.c2)charts.c2.destroy();
    charts.c2=new Chart(document.getElementById('c2'),{
      type:'bar',
      data:{labels:Object.keys(s.devs),datasets:[{label:'Faults',data:Object.values(s.devs),
        backgroundColor:'#0078d4'}]},
      options:{responsive:true,plugins:{legend:{display:false}},scales:{y:{beginAtZero:true}}}
    });
  }catch(e){console.error('Stats load error:',e);}
}

function sw(t){
  try{
    document.querySelectorAll('.tab').forEach(x=>x.classList.remove('on'));
    event.target.classList.add('on');
    document.querySelectorAll('.content').forEach(x=>x.classList.remove('on'));
    document.getElementById(t+'-content').classList.add('on');
    if(t==='stats')ldStats();
  }catch(e){console.error('Tab switch error:',e);}
}

function filt(){
  try{
    const q=document.getElementById('search').value.toLowerCase();
    const dv=document.getElementById('fdev').value;
    const st=document.getElementById('fstat').value;
    const sv=document.getElementById('fsev').value;
    document.querySelectorAll('#tbody tr').forEach(r=>{
      const c=r.cells;
      const mq=c[0].textContent.toLowerCase().includes(q)||c[3].textContent.toLowerCase().includes(q);
      const md=!dv||c[3].textContent===dv;
      const ms=!st||(st==='p'&&c[6].textContent.includes('Pending'))||(st==='a'&&!c[6].textContent.includes('Pending'));
      const mv=!sv||c[5].textContent.includes(sv);
      r.style.display=(mq&&md&&ms&&mv)?'':'none';
    });
  }catch(e){console.error('Filter error:',e);}
}

function sort(i){
  try{
    const tb=document.getElementById('tbody');
    const rs=Array.from(tb.rows);
    const d=sdir[i]==='a'?'d':'a';sdir[i]=d;
    rs.sort((a,b)=>{
      const av=a.cells[i].textContent.trim(),bv=b.cells[i].textContent.trim();
      const an=parseFloat(av),bn=parseFloat(bv);
      if(!isNaN(an)&&!isNaN(bn))return d==='a'?an-bn:bn-an;
      return d==='a'?av.localeCompare(bv):bv.localeCompare(av);
    });
    rs.forEach(r=>tb.appendChild(r));
  }catch(e){console.error('Sort error:',e);}
}

function clr(){
  try{
    document.getElementById('search').value='';
    document.getElementById('fdev').value='';
    document.getElementById('fstat').value='';
    document.getElementById('fsev').value='';
    filt();
  }catch(e){console.error('Clear error:',e);}
}

function togMon(){
  try{
    mon=!mon;
    const b=document.getElementById('monitor');
    b.classList.toggle('on',mon);
    b.textContent=mon?'🎯 Monitor: ON':'📍 Monitor: OFF';
  }catch(e){console.error('Toggle monitor error:',e);}
}

function togSnd(){
  try{
    snd=!snd;
    const b=document.getElementById('sound');
    b.classList.toggle('on',snd);
    b.textContent=snd?'🔊 Sound: ON':'🔇 Sound: OFF';
  }catch(e){console.error('Toggle sound error:',e);}
}

function dark(){
  try{
    document.documentElement.toggleAttribute('dark');
  }catch(e){console.error('Dark mode error:',e);}
}

function zm(la,ln){
  try{
    sw('map');
    setTimeout(()=>map.setView([la,ln],15),100);
  }catch(e){console.error('Zoom error:',e);}
}

function zAll(){
  try{
    if(!data.length)return;
    map.fitBounds(L.latLngBounds(data.map(f=>[f.lat,f.lng])),{padding:[50,50]});
  }catch(e){console.error('Zoom all error:',e);}
}

function beep(s){
  try{
    const ctx=new(window.AudioContext||window.webkitAudioContext)();
    const osc=ctx.createOscillator(),gain=ctx.createGain();
    osc.connect(gain);gain.connect(ctx.destination);
    osc.frequency.value=s==='CRITICAL'?800:s==='WARNING'?600:400;
    gain.gain.setValueAtTime(0.3,ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01,ctx.currentTime+0.4);
    osc.start();osc.stop(ctx.currentTime+0.4);
  }catch(e){console.error('Beep error:',e);}
}

function flash(){
  try{
    document.getElementById('flash').classList.add('on');
    setTimeout(()=>document.getElementById('flash').classList.remove('on'),1200);
  }catch(e){console.error('Flash error:',e);}
}

function clickAck(id) {
  try {
    // Pre-fill the Report ID input field
    document.getElementById('aid').value = id;
    // Show the modal
    showAck();
  } catch(e) {
    console.error('Click ack error:', e);
  }
}
function showAck(){
  try{
    document.getElementById('modal').classList.add('on');
  }catch(e){console.error('Show ack error:',e);}
}

function hideAck(){
  try{
    document.getElementById('modal').classList.remove('on');
  }catch(e){console.error('Hide ack error:',e);}
}

async function subAck(){
  try{
    const id=document.getElementById('aid').value.trim();
    const st=document.getElementById('astat').value;
    const nm=document.getElementById('aname').value.trim();
    if(!id||!nm){alert('Fill all fields');return;}
    const r=await window.pywebview.api.ack_fault(id,st,nm);
    if(r.ok){alert('✓ Acknowledged!');hideAck();ref();}
    else alert('Error: '+r.err);
  }catch(e){console.error('Submit ack error:',e);}
}

function exp(){
  try{
    if(!data.length){alert('No data');return;}
    let csv='ID,Date,Time,Device,Dist,Lat,Lng,Severity,Status,Modified\\n';
    data.forEach(f=>{
      csv+=f.id+','+f.date+','+f.time+','+f.device+','+f.dist+','+
        f.lat+','+f.lng+','+f.sev+','+(f.status||'Pending')+','+(f.mod||'')+'\\n';
    });
    const blob=new Blob([csv],{type:'text/csv'});
    const url=URL.createObjectURL(blob);
    const a=document.createElement('a');
    a.href=url;a.download='faults_'+new Date().toISOString().split('T')[0]+'.csv';
    a.click();URL.revokeObjectURL(url);
  }catch(e){console.error('Export error:',e);}
}

window.addEventListener('load',init);
let osmLoaded = false;

async function fetchOSMPowerLines() {
  if (osmLoaded) return;
  
  try {
    document.getElementById('conn').textContent = 'Loading power lines...';
    
    const query = `[out:json][timeout:25];
      (
        way["power"="line"](12.2,122.5,14.5,124.5);
        way["power"="minor_line"](12.2,122.5,14.5,124.5);
      );
      out geom;`;
    
    const response = await fetch('https://overpass-api.de/api/interpreter', {
      method: 'POST',
      body: query
    });
    
    if (!response.ok) throw new Error('OSM API failed');
    
    const data = await response.json();
    let count = 0;
    
    data.elements.forEach(line => {
      if (line.type === 'way' && line.geometry && line.geometry.length > 1) {
        const coords = line.geometry.map(n => [n.lat, n.lon]);
        const voltage = line.tags.voltage || line.tags['voltage:primary'] || 'unknown';
        const cables = line.tags.cables || 'unknown';
        const operator = line.tags.operator || 'Unknown';
        
        // Determine color and weight by voltage
        let color, weight;
        const v = parseInt(voltage);
        
        if (v >= 230000 || voltage.includes('230')) {
          color = '#e74c3c'; weight = 5;
        } else if (v >= 69000 || voltage.includes('69')) {
          color = '#3498db'; weight = 4;
        } else if (v >= 34500 || voltage.includes('34.5') || voltage.includes('34500')) {
          color = '#2ecc71'; weight = 3;
        } else if (v >= 13800 || voltage.includes('13.8') || voltage.includes('13800')) {
          color = '#f39c12'; weight = 2;
        } else {
          color = '#95a5a6'; weight = 2;
        }
        
        const polyline = L.polyline(coords, {
          color: color,
          weight: weight,
          opacity: 0.7
        });
        
        polyline.bindPopup(
          '<b>⚡ Power Line</b><br>' +
          'Voltage: ' + voltage + '<br>' +
          'Cables: ' + cables + '<br>' +
          'Operator: ' + operator + '<br>' +
          'Source: OpenStreetMap'
        );
        
        transmissionLayer.addLayer(polyline);
        count++;
      }
    });
    
    osmLoaded = true;
    console.log('✓ Loaded ' + count + ' power lines from OSM');
    document.getElementById('conn').textContent = 'Connected';
    
  } catch (error) {
    console.error('OSM load failed:', error);
    document.getElementById('conn').textContent = 'OSM unavailable - using manual data';
    // Fall back to manual TRANSMISSION_LINES data
    drawTransmissionLines();
  }
}
</script></body></html>
"""


def main():
    api = Api()
    webview.create_window("Overwatch SCADA", html=HTML, js_api=api, width=1500, height=850, resizable=True)
    webview.start(debug=True)


if __name__ == "__main__":
    main()