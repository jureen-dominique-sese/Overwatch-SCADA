/**
 * Overwatch SCADA - Statistics Interface Logic
 * Handles charts, metrics, and analytics visualization
 */

let charts = {};
let statsData = null;
let isInitialLoad = true;

// Initialize statistics
async function initStats() {
  try {
    await refreshStats();
  } catch(e) {
    console.error('Stats initialization error:', e);
  }
}

// Refresh statistics
async function refreshStats() {
  try {
<<<<<<< HEAD
    if (!forceRefresh && !isInitialLoad) return;
    
    const stats = await API.getStats(forceRefresh || isInitialLoad);
=======
    const stats = await API.getStats();
>>>>>>> parent of 8c5760d (WORKING CACHE)
    if(!stats) return;
    
    isInitialLoad = false;
    statsData = stats;
    updateStatCards(stats);
    updateCharts(stats);
    updateStatusBar(true, stats.total, new Date().toLocaleTimeString());
    
    console.log('✓ Statistics refreshed');
  } catch(e) {
    console.error('Stats refresh error:', e);
    updateStatusBar(false, 0, null);
  }
}

<<<<<<< HEAD
window.onCacheUpdate = () => refreshStats(true);

async function initStats() {
  try {
    await refreshStats(true);
  } catch(e) {
    console.error('Stats initialization error:', e);
  }
}

window.addEventListener('load', () => {
  initStats();
});

=======
>>>>>>> parent of 8c5760d (WORKING CACHE)
// Update stat cards
function updateStatCards(stats) {
  const grid = document.getElementById('statGrid');
  
  grid.innerHTML = `
    <div class="stat">
      <div class="stat-label">Total Faults</div>
      <div class="stat-val">${stats.total || 0}</div>
    </div>
    <div class="stat">
      <div class="stat-label">Today</div>
      <div class="stat-val">${stats.today || 0}</div>
    </div>
    <div class="stat">
      <div class="stat-label">This Week</div>
      <div class="stat-val">${stats.week || 0}</div>
    </div>
    <div class="stat ok">
      <div class="stat-label">Acknowledged</div>
      <div class="stat-val">${stats.ack || 0}</div>
    </div>
    <div class="stat crit">
      <div class="stat-label">Pending</div>
      <div class="stat-val">${stats.pend || 0}</div>
    </div>
    <div class="stat crit">
      <div class="stat-label">Critical</div>
      <div class="stat-val">${stats.crit || 0}</div>
    </div>
    <div class="stat warn">
      <div class="stat-label">Warning</div>
      <div class="stat-val">${stats.warn || 0}</div>
    </div>
    <div class="stat">
      <div class="stat-label">Info</div>
      <div class="stat-val">${stats.info || 0}</div>
    </div>
  `;
}

// Update all charts
function updateCharts(stats) {
  updateSeverityChart(stats);
  updateDeviceChart(stats);
  updateStatusChart(stats);
  updateTrendChart(stats);
}

// Severity distribution chart
function updateSeverityChart(stats) {
  const ctx = document.getElementById('chartSeverity');
  
  if(charts.severity) {
    charts.severity.destroy();
  }
  
  charts.severity = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Critical', 'Warning', 'Info'],
      datasets: [{
        data: [stats.crit || 0, stats.warn || 0, stats.info || 0],
        backgroundColor: ['#dc3545', '#ffc107', '#17a2b8'],
        borderWidth: 0
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: {
          position: 'bottom',
          labels: {
            color: '#cccccc',
            font: {
              size: 11
            }
          }
        }
      }
    }
  });
}

// Device distribution chart
function updateDeviceChart(stats) {
  const ctx = document.getElementById('chartDevice');
  
  if(charts.device) {
    charts.device.destroy();
  }
  
  const devices = stats.devs || {};
  
  charts.device = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: Object.keys(devices),
      datasets: [{
        label: 'Faults',
        data: Object.values(devices),
        backgroundColor: '#0078d4',
        borderWidth: 0
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: {
          display: false
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            color: '#858585',
            font: {
              size: 10
            }
          },
          grid: {
            color: '#3e3e42'
          }
        },
        x: {
          ticks: {
            color: '#858585',
            font: {
              size: 10
            }
          },
          grid: {
            display: false
          }
        }
      }
    }
  });
}

// Status overview chart
function updateStatusChart(stats) {
  const ctx = document.getElementById('chartStatus');
  
  if(charts.status) {
    charts.status.destroy();
  }
  
  charts.status = new Chart(ctx, {
    type: 'pie',
    data: {
      labels: ['Acknowledged', 'Pending'],
      datasets: [{
        data: [stats.ack || 0, stats.pend || 0],
        backgroundColor: ['#89d185', '#f48771'],
        borderWidth: 0
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: {
          position: 'bottom',
          labels: {
            color: '#cccccc',
            font: {
              size: 11
            }
          }
        }
      }
    }
  });
}

// Weekly trend chart (placeholder - requires historical data)
function updateTrendChart(stats) {
  const ctx = document.getElementById('chartTrend');
  
  if(charts.trend) {
    charts.trend.destroy();
  }
  
  // Generate sample weekly data
  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  const sampleData = days.map(() => Math.floor(Math.random() * 20));
  
  charts.trend = new Chart(ctx, {
    type: 'line',
    data: {
      labels: days,
      datasets: [{
        label: 'Faults',
        data: sampleData,
        borderColor: '#007acc',
        backgroundColor: 'rgba(0, 122, 204, 0.1)',
        tension: 0.4,
        fill: true
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: {
          display: false
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            color: '#858585',
            font: {
              size: 10
            }
          },
          grid: {
            color: '#3e3e42'
          }
        },
        x: {
          ticks: {
            color: '#858585',
            font: {
              size: 10
            }
          },
          grid: {
            display: false
          }
        }
      }
    }
  });
}

// Initialize on load
window.addEventListener('load', () => {
  initStats();
  setInterval(refreshStats, 5000);
});