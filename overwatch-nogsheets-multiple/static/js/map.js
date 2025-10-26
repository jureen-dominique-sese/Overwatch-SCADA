/**
 * Overwatch SCADA - Map Interface Logic
 * Handles Leaflet map, markers, overlays, and geospatial visualization
 */

let map, currentLayer;
let transmissionLayer, substationLayer, coverageLayer;
let faultMarkers = [];
let monitorMode = false;
let soundEnabled = true;
let lastFaultId = null;
let allFaults = [];
function hasLoadedBefore() {
  return localStorage.getItem('map_loaded') === 'true'; // Change key per file
}

function markAsLoaded() {
  localStorage.setItem('map_loaded', 'true'); // Change key per file
}

// Geographic data
const TRANSMISSION_LINES = [
  {from:[13.621775,123.194824],to:[13.148300,123.712400],voltage:230,name:'Naga-Daraga 230kV'},
  {from:[13.148300,123.712400],to:[14.112200,122.955300],voltage:230,name:'Daraga-Sorsogon 230kV'},
  {from:[13.621775,123.194824],to:[14.099578,122.955035],voltage:69,name:'Naga-Daet 69kV'},
  {from:[13.148300,123.712400],to:[13.1442028,123.7447158],voltage:69,name:'Daraga-Legazpi 69kV'},
  {from:[13.148300,123.712400],to:[13.432400,123.411500],voltage:69,name:'Daraga-Iriga 69kV'},
  {from:[14.112200,122.955300],to:[12.667904,123.8736101],voltage:69,name:'Sorsogon-Bulan 69kV'},
  {from:[13.621775,123.194824],to:[13.554725,123.274724],voltage:69,name:'Naga-Pili 69kV'},
  {from:[13.621775,123.194824],to:[13.405867,123.4059345],voltage:34.5,name:'Naga Distribution'},
  {from:[13.1442028,123.7447158],to:[13.420537,123.418047],voltage:34.5,name:'Legazpi Distribution'}
];

const SUBSTATIONS = [
  {name:'Naga Substation',lat:13.621775,lng:123.194824,voltage:230,type:'Transmission'},
  {name:'Daraga Substation',lat:13.148300,lng:123.712400,voltage:230,type:'Transmission'},
  {name:'Sorsogon Substation',lat:12.992710,lng:124.014746,voltage:230,type:'Transmission'},
  {name:'Legazpi Substation',lat:13.144203,lng:123.744716,voltage:69,type:'Distribution'},
  {name:'Iriga Substation',lat:13.432400,lng:123.411500,voltage:69,type:'Distribution'},
  {name:'Daet Substation',lat:14.112200,lng:122.955300,voltage:69,type:'Distribution'},
  {name:'Pili Substation',lat:13.554725,lng:123.274724,voltage:69,type:'Distribution'},
  {name:'Bulan Substation',lat:12.667904,lng:123.873610,voltage:69,type:'Distribution'}
];

const COVERAGE_AREAS = [
  {name:'CASURECO II (Naga)',center:[13.621775,123.194824],radius:25000,color:'#ff6b6b'},
  {name:'ALECO (Legazpi)',center:[13.144203,123.744716],radius:30000,color:'#4ecdc4'},
  {name:'SORECO II (Sorsogon)',center:[12.992710,124.014746],radius:28000,color:'#45b7d1'},
  {name:'CASURECO I (Libmanan)',center:[13.695335,123.061928],radius:22000,color:'#96ceb4'},
  {name:'CANORECO (Daet)',center:[14.112200,122.955300],radius:20000,color:'#ffeaa7'}
];

// Initialize map
function initMap() {
  try {
    map = L.map('map').setView([13.41, 123.35], 9);
    
    currentLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap'
    }).addTo(map);
    
    transmissionLayer = L.layerGroup();
    substationLayer = L.layerGroup();
    coverageLayer = L.layerGroup();
    
    drawTransmissionLines();
    drawSubstations();
    drawCoverageAreas();
    
    console.log('✓ Map initialized');
  } catch(e) {
    console.error('Map initialization error:', e);
  }
}

// Draw transmission lines
function drawTransmissionLines() {
  TRANSMISSION_LINES.forEach(line => {
    const color = line.voltage === 230 ? '#e74c3c' : 
                  line.voltage === 69 ? '#3498db' : '#2ecc71';
    const weight = line.voltage === 230 ? 4 : 
                   line.voltage === 69 ? 3 : 2;
    const opacity = line.voltage === 230 ? 0.8 : 0.6;
    
    const polyline = L.polyline([line.from, line.to], {
      color: color,
      weight: weight,
      opacity: opacity,
      dashArray: line.voltage === 34.5 ? '5,10' : null
    });
    
    polyline.bindPopup(
      `<b>${line.name}</b><br>` +
      `Voltage: ${line.voltage} kV<br>` +
      `Type: ${line.voltage >= 230 ? 'Transmission' : line.voltage >= 69 ? 'Sub-transmission' : 'Distribution'}`
    );
    
    transmissionLayer.addLayer(polyline);
  });
}

// Draw substations
function drawSubstations() {
  SUBSTATIONS.forEach(sub => {
    const isTransmission = sub.voltage >= 230;
    const color = isTransmission ? '#f48771' : '#4fc1ff';
    const bgColor = isTransmission ? 'rgba(244,135,113,0.2)' : 'rgba(79,193,255,0.2)';
    
    const icon = L.divIcon({
      html: `
        <div style="position:relative;text-align:center;">
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
      className: '',
      iconSize: [20, 60],
      iconAnchor: [10, 10]
    });
    
    const marker = L.marker([sub.lat, sub.lng], {icon: icon});
    
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

// Draw coverage areas
function drawCoverageAreas() {
  COVERAGE_AREAS.forEach(area => {
    const circle = L.circle(area.center, {
      radius: area.radius,
      color: area.color,
      fillColor: area.color,
      fillOpacity: 0.1,
      opacity: 0.4,
      weight: 2,
      dashArray: '5,10'
    });
    
    circle.bindPopup(`<b>${area.name}</b><br>Service Coverage Area`);
    coverageLayer.addLayer(circle);
  });
}

// Change map type
function changeMapType(type) {
  try {
    map.removeLayer(currentLayer);
    
    switch(type) {
      case 'satellite':
        currentLayer = L.tileLayer(
          'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
          {attribution: '© Esri'}
        );
        break;
      case 'terrain':
        currentLayer = L.tileLayer(
          'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
          {attribution: '© OpenTopoMap'}
        );
        break;
      case 'dark':
        currentLayer = L.tileLayer(
          'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
          {attribution: '© CartoDB'}
        );
        break;
      default:
        currentLayer = L.tileLayer(
          'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
          {attribution: '© OpenStreetMap'}
        );
    }
    
    currentLayer.addTo(map);
    
    // Update radio buttons
    document.querySelectorAll('.map-ctrl-opt').forEach((el, i) => {
      if(i < 4) {
        el.classList.remove('on');
        el.querySelector('input').checked = false;
      }
    });
    event.target.closest('.map-ctrl-opt').classList.add('on');
    event.target.closest('.map-ctrl-opt').querySelector('input').checked = true;
    
  } catch(e) {
    console.error('Map change error:', e);
  }
}

// Toggle overlay layers
function toggleOverlay(type) {
  try {
    const checkboxes = {
      'transmission': document.getElementById('chk-trans'),
      'substations': document.getElementById('chk-subs'),
      'coverage': document.getElementById('chk-cov')
    };
    
    const layers = {
      'transmission': transmissionLayer,
      'substations': substationLayer,
      'coverage': coverageLayer
    };
    
    const layer = layers[type];
    const checkbox = checkboxes[type];
    
    if(map.hasLayer(layer)) {
      map.removeLayer(layer);
      checkbox.checked = false;
    } else {
      map.addLayer(layer);
      checkbox.checked = true;
    }
  } catch(e) {
    console.error('Overlay toggle error:', e);
  }
}

// Update fault markers on map
function updateMapMarkers(faults) {
  try {
    // Clear existing markers
    faultMarkers.forEach(marker => map.removeLayer(marker));
    faultMarkers = [];
    
    faults.forEach(f => {
      const col = f.ack ? '#0078d4' : 
                   f.sev === 'CRITICAL' ? '#dc3545' : 
                   f.sev === 'WARNING' ? '#ffc107' : '#17a2b8';
      
      // Create circle for fault radius
      const circle = L.circle([f.lat, f.lng], {
        color: col,
        fillColor: col,
        fillOpacity: 0.2,
        radius: f.dist
      }).addTo(map);
      
      // Create pulsing marker
      const pulseClass = f.ack ? 'b' : f.sev === 'CRITICAL' ? 'r' : 'o';
      const icon = L.divIcon({
        html: `<div class="pulse ${pulseClass}"></div>`,
        className: '',
        iconSize: [12, 12]
      });
      
      const marker = L.marker([f.lat, f.lng], {icon: icon}).addTo(map);
      
      // Create popup content
      const popupContent = `
        <div style="font-family: 'Segoe UI', sans-serif; font-size: 13px; line-height: 1.6; color: var(--text);">
          <b style="font-size: 14px; color: var(--accent);">${f.id}</b><br>
          <b>Device:</b> ${f.device}<br>
          <b>Distance:</b> ${f.dist} m<br>
          <b>Severity:</b> ${f.sev}<br>
          <b>Status:</b> ${f.ack ? ('✓ ' + f.status) : '⚠ Pending'}<br>
          <button style="
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
          " 
          onmouseover="this.style.background='var(--accent-hover)'"
          onmouseout="this.style.background='var(--accent)'"
          onclick="openAckModal('${f.id}')">
            ✔ Acknowledge
          </button>
        </div>
      `;
      
      circle.bindPopup(popupContent);
      marker.bindPopup(popupContent);
      
      faultMarkers.push(circle);
      faultMarkers.push(marker);
    });
    
    console.log(`✓ Updated ${faults.length} fault markers`);
  } catch(e) {
    console.error('Map markers update error:', e);
  }
}

// Update latest fault display
function updateLatestFault(fault) {
  const latestEl = document.getElementById('latest');
  if(latestEl && fault) {
    const status = fault.ack ? '✓ Ack' : '⚠ Pending';
    latestEl.innerHTML = 
      `<strong>${fault.id}</strong> ${status}<br>` +
      `Device: ${fault.device}<br>` +
      `Distance: ${fault.dist} m<br>` +
      `Severity: ${fault.sev}<br>` +
      `Time: ${fault.date} ${fault.time}`;
  }
}

// Refresh map data
async function refreshMap() {
  try {
<<<<<<< HEAD
    if (!forceRefresh && !isInitialLoad) return;
    
    const faults = await API.getFaults(forceRefresh || isInitialLoad);
=======
    const faults = await API.getFaults();
>>>>>>> parent of 8c5760d (WORKING CACHE)
    if(!faults || !faults.length) return;
    
    isInitialLoad = false;
    allFaults = faults;
    const latest = faults[faults.length - 1];
    
    if(soundEnabled && lastFaultId && latest.id !== lastFaultId) {
      beep(latest.sev);
      flash();
    }
    
    if(monitorMode && lastFaultId && latest.id !== lastFaultId) {
      map.setView([latest.lat, latest.lng], 14);
    }
    
    lastFaultId = latest.id;
    
    updateMapMarkers(faults);
    updateLatestFault(latest);
    updateStatusBar(true, faults.length, new Date().toLocaleTimeString());
    
  } catch(e) {
    console.error('Map refresh error:', e);
    updateStatusBar(false, 0, null);
  }
}

<<<<<<< HEAD
window.onCacheUpdate = () => refreshMap(true);

window.addEventListener('load', () => {
  initMap();
  refreshMap(true);
});

window.onCacheUpdate = function() {
  refreshMap(false);  // Use cached data when other window updates
};


=======
>>>>>>> parent of 8c5760d (WORKING CACHE)
// Toggle monitor mode
function toggleMonitor() {
  monitorMode = !monitorMode;
  const btn = document.getElementById('monitor');
  btn.classList.toggle('on', monitorMode);
  btn.textContent = monitorMode ? '🎯 Monitor: ON' : '📍 Monitor: OFF';
}

// Toggle sound alerts
function toggleSound() {
  soundEnabled = !soundEnabled;
  const btn = document.getElementById('sound');
  btn.classList.toggle('on', soundEnabled);
  btn.textContent = soundEnabled ? '🔊 Sound: ON' : '🔇 Sound: OFF';
}

// Zoom to show all faults
function zoomAll() {
  try {
    if(!allFaults.length) return;
    const bounds = L.latLngBounds(allFaults.map(f => [f.lat, f.lng]));
    map.fitBounds(bounds, {padding: [50, 50]});
  } catch(e) {
    console.error('Zoom all error:', e);
  }
}

// Acknowledgment modal functions
function showAckModal() {
  document.getElementById('modal').classList.add('on');
}

function hideAckModal() {
  document.getElementById('modal').classList.remove('on');
}

function openAckModal(faultId) {
  document.getElementById('aid').value = faultId;
  showAckModal();
}

async function submitAck() {
  try {
    const id = document.getElementById('aid').value.trim();
    const status = document.getElementById('astat').value;
    const name = document.getElementById('aname').value.trim();
    
    if(!id || !name) {
      alert('Please fill all fields');
      return;
    }
    
    const result = await API.ackFault(id, status, name);
    
    if(result.ok) {
      alert('✓ Fault acknowledged successfully!');
      hideAckModal();
      refreshMap();
    } else {
      alert('Error: ' + result.err);
    }
  } catch(e) {
    console.error('Submit acknowledgment error:', e);
    alert('Error submitting acknowledgment');
  }
}

// Initialize on load
window.addEventListener('load', () => {
  initMap();
  refreshMap();
  setInterval(refreshMap, 3000);
});