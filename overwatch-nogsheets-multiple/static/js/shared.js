    /**
 * Overwatch SCADA - Shared JavaScript Utilities
 * API wrapper and common functions
 */

// API Wrapper for pywebview
const API = {
  async getFaults() {
    return await window.pywebview.api.get_faults();
  },
  
  async getStats() {
    return await window.pywebview.api.get_stats();
  },
  
  async ackFault(id, status, name) {
    return await window.pywebview.api.ack_fault(id, status, name);
  },
  
  async testTelegram() {
    return await window.pywebview.api.test_telegram();
  }
};

// Sound alerts
function beep(severity) {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);
    
    osc.frequency.value = 
      severity === 'CRITICAL' ? 800 : 
      severity === 'WARNING' ? 600 : 400;
    
    gain.gain.setValueAtTime(0.3, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.4);
    osc.start();
    osc.stop(ctx.currentTime + 0.4);
  } catch(e) {
    console.error('Beep error:', e);
  }
}

// Visual flash alert
function flash() {
  const flashEl = document.getElementById('flash');
  if (flashEl) {
    flashEl.classList.add('on');
    setTimeout(() => flashEl.classList.remove('on'), 1200);
  }
}

// Toggle dark mode
function toggleDarkMode() {
  document.documentElement.toggleAttribute('dark');
  localStorage.setItem('darkMode', document.documentElement.hasAttribute('dark'));
}

// Initialize dark mode from storage
function initDarkMode() {
  if (localStorage.getItem('darkMode') === 'true') {
    document.documentElement.setAttribute('dark', '');
  }
}

// Format date/time
function formatDateTime(date, time) {
  return `${date} ${time}`;
}

// Update status bar
function updateStatusBar(connected, faultCount, lastUpdate) {
  const dot = document.getElementById('dot');
  const conn = document.getElementById('conn');
  const cnt = document.getElementById('cnt');
  const upd = document.getElementById('upd');
  
  if (dot) dot.classList.toggle('err', !connected);
  if (conn) conn.textContent = connected ? 'Connected' : 'Disconnected';
  if (cnt) cnt.textContent = `Faults: ${faultCount}`;
  if (upd) upd.textContent = `Last: ${lastUpdate || '--:--:--'}`;
}

// Export to CSV
function exportToCSV(data, filename) {
  try {
    if (!data || !data.length) {
      alert('No data to export');
      return;
    }
    
    let csv = 'ID,Date,Time,Device,Dist,Lat,Lng,Severity,Status,Modified\n';
    data.forEach(f => {
      csv += `${f.id},${f.date},${f.time},${f.device},${f.dist},` +
             `${f.lat},${f.lng},${f.sev},${f.status || 'Pending'},${f.mod || ''}\n`;
    });
    
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename || `faults_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  } catch(e) {
    console.error('Export error:', e);
  }
}

// Initialize on load
window.addEventListener('load', initDarkMode);