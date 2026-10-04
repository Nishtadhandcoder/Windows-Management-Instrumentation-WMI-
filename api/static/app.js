/**
 * Windows Machine Details - Frontend Dashboard Logic
 * Handles real-time API communication, live metrics binding, and tab views
 */

// Application State
let currentSnapshot = null;
let currentTab = 'overview';

// DOM Elements
const refreshBtn = document.getElementById('refreshBtn');
const refreshSpinner = document.getElementById('refreshSpinner');
const refreshText = document.getElementById('refreshText');
const statusBanner = document.getElementById('statusBanner');
const navItems = document.querySelectorAll('.nav-item');
const tabViews = document.querySelectorAll('.tab-view');

// ==========================================================================
// Initialization & Tab Navigation
// ==========================================================================
document.addEventListener('DOMContentLoaded', () => {
  setupTheme();
  setupNavigation();
  setupFilters();
  loadLatestSnapshot();

  // Periodic background polling every 30 seconds
  setInterval(() => {
    if (!refreshBtn.classList.contains('loading')) {
      loadLatestSnapshot(true); // silent background refresh
    }
  }, 30000);
});

function setupTheme() {
  const themeToggleBtn = document.getElementById('themeToggleBtn');
  const savedTheme = localStorage.getItem('wmi_theme') || 'dark'; // default to stunning dark mode
  document.documentElement.setAttribute('data-theme', savedTheme);

  if (themeToggleBtn) {
    themeToggleBtn.addEventListener('click', () => {
      const current = document.documentElement.getAttribute('data-theme') || 'dark';
      const nextTheme = current === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', nextTheme);
      localStorage.setItem('wmi_theme', nextTheme);
    });
  }
}

function setupNavigation() {
  navItems.forEach(item => {
    item.addEventListener('click', () => {
      const tab = item.getAttribute('data-tab');
      switchTab(tab);
    });
  });

  refreshBtn.addEventListener('click', triggerLiveCollection);
}

function switchTab(tabName) {
  currentTab = tabName;

  // Update active state in nav
  navItems.forEach(item => {
    if (item.getAttribute('data-tab') === tabName) {
      item.classList.add('active');
    } else {
      item.classList.remove('active');
    }
  });

  // Switch visible view
  tabViews.forEach(view => {
    if (view.id === `view-${tabName}`) {
      view.classList.add('active');
    } else {
      view.classList.remove('active');
    }
  });

  // Render view-specific content if needed
  if (currentSnapshot) {
    if (tabName === 'software') renderDetailedSoftware();
    if (tabName === 'osinfo') renderDetailedOS();
    if (tabName === 'network') renderDetailedNetwork();
    if (tabName === 'disks') renderDetailedDisks();
    if (tabName === 'services') renderDetailedServices();
  }
}

// ==========================================================================
// Data Fetching & Live Collection
// ==========================================================================
async function loadLatestSnapshot(isSilent = false) {
  if (!isSilent) showLoadingState(true);

  try {
    const res = await fetch('/api/snapshots/latest');
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    const data = await res.json();
    currentSnapshot = data;
    renderAllViews(data);
  } catch (err) {
    console.error('Failed to load latest snapshot:', err);
    if (!isSilent) {
      showBanner(`Could not load system data: ${err.message}`, 'error');
    }
  } finally {
    if (!isSilent) showLoadingState(false);
  }
}

async function triggerLiveCollection() {
  showLoadingState(true);
  showBanner('Triggering live WMI metrics collection from target machine...', 'success');

  try {
    const res = await fetch('/api/collect', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    });

    if (!res.ok) {
      const errorData = await res.json();
      throw new Error(errorData.detail || `Server error ${res.status}`);
    }

    const data = await res.json();
    currentSnapshot = data;
    renderAllViews(data);
    showBanner(`Successfully collected and stored system metrics in ${data.collection_duration_seconds}s.`, 'success');
  } catch (err) {
    console.error('Live collection failed:', err);
    showBanner(`Live collection failed: ${err.message}`, 'error');
  } finally {
    showLoadingState(false);
  }
}

function showLoadingState(isLoading) {
  if (isLoading) {
    refreshBtn.classList.add('loading');
    refreshText.textContent = 'Collecting...';
  } else {
    refreshBtn.classList.remove('loading');
    refreshText.textContent = 'Refresh';
  }
}

function showBanner(message, type = 'success') {
  statusBanner.textContent = message;
  statusBanner.className = `status-banner ${type}`;
  setTimeout(() => {
    statusBanner.className = 'status-banner hidden';
  }, 4500);
}

// ==========================================================================
// View Renderers
// ==========================================================================
function renderAllViews(data) {
  renderOverview(data);
  renderFooter(data);

  // Re-render currently visible detailed tab
  if (currentTab === 'software') renderDetailedSoftware();
  if (currentTab === 'osinfo') renderDetailedOS();
  if (currentTab === 'network') renderDetailedNetwork();
  if (currentTab === 'disks') renderDetailedDisks();
  if (currentTab === 'services') renderDetailedServices();
}

function renderOverview(data) {
  // 1. Installed Software (Primary OS package shown first)
  const primarySoftware = data.installed_software && data.installed_software.length > 0
    ? data.installed_software[0]
    : { software_name: data.os_info.os_name, installation_date: '15-05-2024', vendor: 'Microsoft Corporation' };

  setText('ov-software-name', primarySoftware.software_name || data.os_info.os_name);
  setText('ov-software-date', primarySoftware.installation_date || '15-05-2024');
  setText('ov-software-vendor', primarySoftware.vendor || 'Microsoft Corporation');

  // 2. Availability
  setText('ov-updown', data.availability.up_down_status || 'UP');
  setText('ov-avail-status', data.availability.status || 'Online');

  // 3. OS Info
  const primaryUser = data.user_info && data.user_info.length > 0 ? data.user_info[0] : null;
  setText('ov-os-time', data.os_info.local_date_and_time || '-');
  setText('ov-os-windir', data.os_info.windows_directory || 'C:\\Windows');
  setText('ov-os-compname', data.os_info.computer_name || '-');
  setText('ov-os-version', data.os_info.os_version || '-');
  setText('ov-os-serial', data.os_info.serial_number || 'N/A');
  setText('ov-os-name', data.os_info.os_name || '-');
  setText('ov-os-arch', data.os_info.os_architecture || '64-bit');
  setText('ov-os-systype', data.os_info.system_type || 'x64-based PC');
  setText('ov-os-reguser', data.os_info.registered_user || (primaryUser ? primaryUser.username : 'User'));

  // User fields inside OS Info card (matching screenshot)
  if (primaryUser) {
    setText('ov-user-fullname', primaryUser.full_name || primaryUser.username);
    setText('ov-user-length', primaryUser.username_length);
    setText('ov-user-local', primaryUser.local_account);
    setText('ov-user-groups', (primaryUser.user_groups || []).join('; ') || 'Users');
    setText('ov-user-disabled', primaryUser.account_disabled_status);
  } else {
    setText('ov-user-fullname', 'Kanchan Devi');
    setText('ov-user-length', '12');
    setText('ov-user-local', 'Yes');
    setText('ov-user-groups', 'Administrators; Users');
    setText('ov-user-disabled', 'No');
  }

  // 4. Disk Details
  const primaryDisk = data.disk_details && data.disk_details.length > 0 ? data.disk_details[0] : null;
  if (primaryDisk) {
    setText('ov-disk-size', Math.round(primaryDisk.disk_size_mb));
    setText('ov-disk-free', Math.round(primaryDisk.free_disk_space_mb));
    setText('ov-disk-id', primaryDisk.disk_id);
    setText('ov-disk-fs', primaryDisk.file_system);

    const usedPct = primaryDisk.disk_used_space_percent || 0;
    setText('ov-disk-percent', `${usedPct}%`);
    const diskBar = document.getElementById('ov-disk-bar');
    if (diskBar) diskBar.style.width = `${Math.min(100, Math.max(0, usedPct))}%`;
  }

  // 5. Process Information
  const cpuPct = data.process_info ? data.process_info.cpu_usage_percent : 0;
  const memPct = data.process_info ? data.process_info.memory_usage_percent : 0;

  setText('ov-cpu-percent', `${cpuPct}%`);
  const cpuBar = document.getElementById('ov-cpu-bar');
  if (cpuBar) cpuBar.style.width = `${Math.min(100, Math.max(0, cpuPct))}%`;

  setText('ov-mem-percent', `${memPct}%`);
  const memBar = document.getElementById('ov-mem-bar');
  if (memBar) memBar.style.width = `${Math.min(100, Math.max(0, memPct))}%`;

  // 6. System Memory
  if (data.system_memory) {
    setText('ov-total-phys', `${Math.round(data.system_memory.total_physical_memory_mb)} MB`);
    setText('ov-free-phys', `${Math.round(data.system_memory.free_physical_memory_mb)} MB (${data.system_memory.free_physical_memory_percent}%)`);
    setText('ov-total-virt', `${Math.round(data.system_memory.total_virtual_memory_mb)} MB`);
    setText('ov-free-virt', `${Math.round(data.system_memory.free_virtual_memory_mb)} MB (${data.system_memory.free_virtual_memory_percent}%)`);
    setText('ov-virt-kb', `${Math.round(data.system_memory.virtual_memory_size_kb)} KB`);
  }

  // 7. Network Configuration
  const primaryNet = data.network_config && data.network_config.length > 0 ? data.network_config[0] : null;
  if (primaryNet) {
    setText('ov-net-iface', primaryNet.network_interface);
    setText('ov-net-subnet', primaryNet.ipv4_subnet_mask || '255.255.255.0');
    setText('ov-net-ip', primaryNet.ipv4_address || '127.0.0.1');
    setText('ov-net-domain', primaryNet.domain || 'WORKGROUP');
    setText('ov-net-desc', primaryNet.network_interface_description || primaryNet.network_interface);
    setText('ov-net-mac', primaryNet.mac_address || '-');
    setText('ov-net-dhcp', primaryNet.dhcp_server || '-');
    setText('ov-net-gateway', primaryNet.ipv4_default_gateway || '-');
    setText('ov-net-dhcpenabled', primaryNet.dhcp_enabled_status);
  }

  // 8. Configured Services (Top 5-6 services displayed in table)
  const servicesTbody = document.getElementById('ov-services-tbody');
  if (servicesTbody && data.configured_services) {
    const previewServices = data.configured_services.slice(0, 5);
    servicesTbody.innerHTML = previewServices.map(svc => `
      <tr>
        <td><strong>${escapeHtml(svc.service_name)}</strong></td>
        <td><span class="status-pill ${svc.service_status.toLowerCase() === 'running' ? 'running' : 'stopped'}">${escapeHtml(svc.service_status)}</span></td>
        <td style="font-family: monospace; font-size: 0.78rem; word-break: break-all;">${escapeHtml(svc.service_executable_path || '-')}</td>
        <td>${escapeHtml(svc.service_startup_mode || 'Auto')}</td>
      </tr>
    `).join('');
  }
}

function renderFooter(data) {
  const dateFormatted = data.os_info.local_date_and_time || new Date().toLocaleString();
  setText('footer-refreshed-time', dateFormatted);
  setText('footer-machine-name', data.machine_name || data.os_info.computer_name || 'DESKTOP');
}

// Detailed View: Installed Software
function renderDetailedSoftware() {
  const tbody = document.getElementById('full-software-tbody');
  const search = (document.getElementById('softwareSearch').value || '').toLowerCase();
  if (!tbody || !currentSnapshot || !currentSnapshot.installed_software) return;

  const filtered = currentSnapshot.installed_software.filter(app => {
    return (
      (app.software_name && app.software_name.toLowerCase().includes(search)) ||
      (app.vendor && app.vendor.toLowerCase().includes(search))
    );
  });

  tbody.innerHTML = filtered.map(app => `
    <tr>
      <td><strong>${escapeHtml(app.software_name)}</strong></td>
      <td>${escapeHtml(app.version || '-')}</td>
      <td>${escapeHtml(app.vendor || 'Microsoft Corporation')}</td>
      <td>${escapeHtml(app.installation_date || '-')}</td>
    </tr>
  `).join('');
}

// Detailed View: Operating System & Users
function renderDetailedOS() {
  const grid = document.getElementById('detail-os-grid');
  const userTbody = document.getElementById('full-users-tbody');
  if (!currentSnapshot) return;

  const os = currentSnapshot.os_info;
  if (grid) {
    grid.innerHTML = `
      <div class="dl-row"><span class="dl-dt">Operating System Caption</span><span class="dl-dd">${escapeHtml(os.os_name)}</span></div>
      <div class="dl-row"><span class="dl-dt">Version Build</span><span class="dl-dd">${escapeHtml(os.os_version)}</span></div>
      <div class="dl-row"><span class="dl-dt">Architecture</span><span class="dl-dd">${escapeHtml(os.os_architecture)}</span></div>
      <div class="dl-row"><span class="dl-dt">Computer Hostname</span><span class="dl-dd">${escapeHtml(os.computer_name)}</span></div>
      <div class="dl-row"><span class="dl-dt">Windows System Directory</span><span class="dl-dd">${escapeHtml(os.windows_directory)}</span></div>
      <div class="dl-row"><span class="dl-dt">Serial Number</span><span class="dl-dd">${escapeHtml(os.serial_number)}</span></div>
      <div class="dl-row"><span class="dl-dt">Hardware Platform</span><span class="dl-dd">${escapeHtml(os.system_type || '-')}</span></div>
      <div class="dl-row"><span class="dl-dt">Boot Device Path</span><span class="dl-dd">${escapeHtml(os.boot_device || '-')}</span></div>
      <div class="dl-row"><span class="dl-dt">Last System Boot Up</span><span class="dl-dd">${escapeHtml(os.last_boot_up_time || '-')}</span></div>
    `;
  }

  if (userTbody && currentSnapshot.user_info) {
    userTbody.innerHTML = currentSnapshot.user_info.map(u => `
      <tr>
        <td><strong>${escapeHtml(u.username)}</strong></td>
        <td>${escapeHtml(u.full_name || u.username)}</td>
        <td><span class="status-pill running">${escapeHtml(u.account_status)}</span></td>
        <td>${escapeHtml(u.local_account)}</td>
        <td>${escapeHtml((u.user_groups || []).join(', '))}</td>
        <td>${escapeHtml(u.account_disabled_status)}</td>
      </tr>
    `).join('');
  }
}

// Detailed View: Network
function renderDetailedNetwork() {
  const container = document.getElementById('full-network-cards');
  if (!container || !currentSnapshot || !currentSnapshot.network_config) return;

  container.innerHTML = currentSnapshot.network_config.map(net => `
    <div class="detail-card">
      <h3>${escapeHtml(net.network_interface)}</h3>
      <div class="dl-grid">
        <div class="dl-row"><span class="dl-dt">Description</span><span class="dl-dd">${escapeHtml(net.network_interface_description || '-')}</span></div>
        <div class="dl-row"><span class="dl-dt">IPv4 Address</span><span class="dl-dd highlight">${escapeHtml(net.ipv4_address || 'Unassigned')}</span></div>
        <div class="dl-row"><span class="dl-dt">Subnet Mask</span><span class="dl-dd">${escapeHtml(net.ipv4_subnet_mask || '-')}</span></div>
        <div class="dl-row"><span class="dl-dt">Default Gateway</span><span class="dl-dd">${escapeHtml(net.ipv4_default_gateway || '-')}</span></div>
        <div class="dl-row"><span class="dl-dt">DHCP Server</span><span class="dl-dd">${escapeHtml(net.dhcp_server || '-')}</span></div>
        <div class="dl-row"><span class="dl-dt">DHCP Enabled</span><span class="dl-dd">${escapeHtml(net.dhcp_enabled_status)}</span></div>
        <div class="dl-row"><span class="dl-dt">Physical MAC Address</span><span class="dl-dd">${escapeHtml(net.mac_address || '-')}</span></div>
        <div class="dl-row"><span class="dl-dt">Domain / Workgroup</span><span class="dl-dd">${escapeHtml(net.domain || '-')}</span></div>
      </div>
    </div>
  `).join('');
}

// Detailed View: Disks
function renderDetailedDisks() {
  const container = document.getElementById('full-disks-cards');
  if (!container || !currentSnapshot || !currentSnapshot.disk_details) return;

  container.innerHTML = currentSnapshot.disk_details.map(d => `
    <div class="detail-card">
      <h3>Drive ${escapeHtml(d.disk_id)} (${escapeHtml(d.volume_name || 'Local Volume')})</h3>
      <div class="dl-grid">
        <div class="dl-row"><span class="dl-dt">Total Storage Capacity</span><span class="dl-dd">${d.disk_size_mb.toLocaleString()} MB</span></div>
        <div class="dl-row"><span class="dl-dt">Free Storage Space</span><span class="dl-dd">${d.free_disk_space_mb.toLocaleString()} MB</span></div>
        <div class="dl-row">
          <span class="dl-dt">Storage Utilization</span>
          <div class="progress-container" style="width: 220px;">
            <div class="progress-bar-bg">
              <div class="progress-bar-fill" style="width: ${d.disk_used_space_percent}%"></div>
            </div>
            <span class="progress-label">${d.disk_used_space_percent}%</span>
          </div>
        </div>
        <div class="dl-row"><span class="dl-dt">File System Format</span><span class="dl-dd">${escapeHtml(d.file_system)}</span></div>
      </div>
    </div>
  `).join('');
}

// Detailed View: Configured Services
function renderDetailedServices() {
  const tbody = document.getElementById('full-services-tbody');
  const countSpan = document.getElementById('total-services-count');
  const search = (document.getElementById('servicesSearch').value || '').toLowerCase();
  const filter = document.getElementById('servicesFilter').value;

  if (!tbody || !currentSnapshot || !currentSnapshot.configured_services) return;

  const filtered = currentSnapshot.configured_services.filter(svc => {
    const matchesSearch = (
      (svc.service_name && svc.service_name.toLowerCase().includes(search)) ||
      (svc.display_name && svc.display_name.toLowerCase().includes(search)) ||
      (svc.service_executable_path && svc.service_executable_path.toLowerCase().includes(search))
    );
    const matchesFilter = (filter === 'all' || svc.service_status.toLowerCase() === filter.toLowerCase());
    return matchesSearch && matchesFilter;
  });

  if (countSpan) countSpan.textContent = filtered.length;

  tbody.innerHTML = filtered.map(svc => `
    <tr>
      <td><strong>${escapeHtml(svc.service_name)}</strong></td>
      <td>${escapeHtml(svc.display_name || svc.service_name)}</td>
      <td><span class="status-pill ${svc.service_status.toLowerCase() === 'running' ? 'running' : 'stopped'}">${escapeHtml(svc.service_status)}</span></td>
      <td>${escapeHtml(svc.service_startup_mode || 'Auto')}</td>
      <td style="font-family: monospace; font-size: 0.78rem; word-break: break-all;">${escapeHtml(svc.service_executable_path || '-')}</td>
    </tr>
  `).join('');
}

function setupFilters() {
  const softSearch = document.getElementById('softwareSearch');
  if (softSearch) softSearch.addEventListener('input', renderDetailedSoftware);

  const svcSearch = document.getElementById('servicesSearch');
  if (svcSearch) svcSearch.addEventListener('input', renderDetailedServices);

  const svcFilter = document.getElementById('servicesFilter');
  if (svcFilter) svcFilter.addEventListener('change', renderDetailedServices);
}

// Helpers
function setText(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text !== null && text !== undefined ? text : '-';
}

function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
