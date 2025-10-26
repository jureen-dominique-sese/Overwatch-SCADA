/**
 * Overwatch SCADA - Logs Interface Logic
 * Handles table rendering, filtering, sorting, and data management
 */

let allLogs = [];
let filteredLogs = [];
let sortDirections = {};

// Initialize logs
async function initLogs() {
  try {
    await refreshLogs();
  } catch(e) {
    console.error('Logs initialization error:', e);
  }
}

// Refresh logs data
async function refreshLogs() {
  try {
    const faults = await API.getFaults();
    if(!faults) return;
    
    allLogs = faults;
    filteredLogs = [...faults];
    
    updateDeviceFilter(faults);
    renderTable(faults.slice(-100).reverse()); // Show last 100
    updateStatusBar(true, faults.length, new Date().toLocaleTimeString());
    
    console.log('✓ Logs refreshed');
  } catch(e) {
    console.error('Logs refresh error:', e);
    updateStatusBar(false, 0, null);
  }
}

// Update device filter options
function updateDeviceFilter(faults) {
  const select = document.getElementById('fdev');
  const devices = [...new Set(faults.map(f => f.device))];
  
  select.innerHTML = '<option value="">All Devices</option>';
  devices.forEach(device => {
    select.innerHTML += `<option value="${device}">${device}</option>`;
  });
}

// Render table rows
function renderTable(logs) {
  const tbody = document.getElementById('tbody');
  tbody.innerHTML = '';
  
  logs.forEach(f => {
    const row = tbody.insertRow();
    row.innerHTML = `
      <td>${f.id}</td>
      <td>${f.date}</td>
      <td>${f.time}</td>
      <td>${f.device}</td>
      <td>${f.dist}</td>
      <td><span class="badge ${f.sev.toLowerCase()}">${f.sev}</span></td>
      <td>${f.ack ? '✓ ' + f.status : '⚠ Pending'}</td>
      <td>${f.mod || '-'}</td>
      <td>
        <button class="btn btn-sm btn-1" onclick="viewOnMap(${f.lat}, ${f.lng})" 
                style="padding:4px 8px; margin:0; width:auto;">
          🔍 View
        </button>
      </td>
    `;
  });
}

// Filter logs based on criteria
function filterLogs() {
  try {
    const searchQuery = document.getElementById('search').value.toLowerCase();
    const deviceFilter = document.getElementById('fdev').value;
    const statusFilter = document.getElementById('fstat').value;
    const severityFilter = document.getElementById('fsev').value;
    
    filteredLogs = allLogs.filter(f => {
      const matchesSearch = 
        f.id.toLowerCase().includes(searchQuery) || 
        f.device.toLowerCase().includes(searchQuery);
      
      const matchesDevice = !deviceFilter || f.device === deviceFilter;
      
      const matchesStatus = !statusFilter || 
        (statusFilter === 'p' && !f.ack) || 
        (statusFilter === 'a' && f.ack);
      
      const matchesSeverity = !severityFilter || f.sev === severityFilter;
      
      return matchesSearch && matchesDevice && matchesStatus && matchesSeverity;
    });
    
    renderTable(filteredLogs.slice(-100).reverse());
    
  } catch(e) {
    console.error('Filter error:', e);
  }
}

// Clear all filters
function clearFilters() {
  document.getElementById('search').value = '';
  document.getElementById('fdev').value = '';
  document.getElementById('fstat').value = '';
  document.getElementById('fsev').value = '';
  filterLogs();
}

// Sort table by column
function sortTable(columnIndex) {
  try {
    const tbody = document.getElementById('tbody');
    const rows = Array.from(tbody.rows);
    
    const direction = sortDirections[columnIndex] === 'asc' ? 'desc' : 'asc';
    sortDirections[columnIndex] = direction;
    
    rows.sort((a, b) => {
      const aVal = a.cells[columnIndex].textContent.trim();
      const bVal = b.cells[columnIndex].textContent.trim();
      
      // Try numeric comparison
      const aNum = parseFloat(aVal);
      const bNum = parseFloat(bVal);
      
      if(!isNaN(aNum) && !isNaN(bNum)) {
        return direction === 'asc' ? aNum - bNum : bNum - aNum;
      }
      
      // String comparison
      return direction === 'asc' ? 
        aVal.localeCompare(bVal) : 
        bVal.localeCompare(aVal);
    });
    
    rows.forEach(row => tbody.appendChild(row));
    
  } catch(e) {
    console.error('Sort error:', e);
  }
}

// View fault on map (navigate to map interface)
function viewOnMap(lat, lng) {
  // Store coordinates in localStorage for map interface to read
  localStorage.setItem('mapFocus', JSON.stringify({lat, lng, zoom: 15}));
  window.location.href = 'map.html';
}

// Export logs
function exportLogs() {
  const filename = `fault_logs_${new Date().toISOString().split('T')[0]}.csv`;
  exportToCSV(filteredLogs, filename);
}

// Initialize on load
window.addEventListener('load', () => {
  initLogs();
  setInterval(refreshLogs, 5000);
});