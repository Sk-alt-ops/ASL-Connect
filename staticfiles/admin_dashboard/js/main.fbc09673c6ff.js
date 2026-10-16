/* ===================================================================
 * ASL Connect -- Admin Dashboard JavaScript
 * ===================================================================
 * Manages the single-page admin panel: navigation, API calls, data
 * rendering for dashboard stats, users, gestures, alphabet symbols,
 * contact messages, support tickets, notifications, profile, and the
 * design studio (section + page-level theming).
 *
 * Architecture:
 *   - Page navigation via showPage()          ->  section 1
 *   - API helper via apiCall()                ->  section 2
 *   - Feature-specific modules (sections 3-11)
 *   - Design Studio state / fields            ->  sections 12-14
 *   - Design Studio save/switch/preview       ->  sections 15-20
 *   - Page-load initialisation                ->  section 21
 * =================================================================== */


/* ===================================================================
 * 1. PAGE NAVIGATION
 * ===================================================================
 * Maps page IDs to {title, subtitle} for the top-bar header.
 * showPage() activates a panel, updates the nav highlight, and
 * triggers the relevant data-loading function.
 * =================================================================== */

const pageTitles = {
  dashboard:      { t: 'Dashboard',          s: 'Manage your ASL Connect platform' },
  users:          { t: 'Users',             s: 'Manage platform users' },
  gestures:       { t: 'Gestures',          s: 'Manage ASL gesture library' },
  alphabet:       { t: 'Alphabet',          s: 'Manage ASL alphabet symbols' },
  'contact-admin':{ t: 'Contact Messages',  s: 'Manage incoming contact messages' },
  support:        { t: 'Support',           s: 'Manage support tickets' },
  contact:        { t: 'Contact Us',        s: 'We would love to hear from you' },
  notifications:  { t: 'Notifications',     s: 'All caught up!' },
  settings:       { t: 'Settings',          s: 'Customize your experience' },
  profile:        { t: 'My Profile',        s: 'Manage your account information' },
  design:         { t: 'Page Design Manager', s: 'Customize design per page' }
};

function showPage(id) {
  /* Activate the panel matching *id*, update the top-bar title and
   * sidebar highlight, then trigger data loading for that section. */
  document.querySelectorAll('.section-panel').forEach(p => p.classList.remove('active'));
  document.getElementById('page-' + id).classList.add('active');

  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  const nav = document.querySelector(`.nav-item[onclick="showPage('${id}')"]`);
  if (nav) nav.classList.add('active');

  const info = pageTitles[id] || { t: id, s: '' };
  document.getElementById('topbar-title').textContent = info.t;
  document.getElementById('topbar-sub').textContent = info.s;

  closeSidebar();
  window.scrollTo(0, 0);

  /* Lazy-load data only when the user navigates to that page. */
  if (id === 'dashboard')      { loadDashboardStats(); loadDashboardRecentActivity(); loadDashboardUsers(); loadContactMessages(); loadSupportTickets(); }
  if (id === 'users')          loadUsers();
  if (id === 'gestures')       { loadCategories(); loadGestures(); }
  if (id === 'alphabet')       loadAlphabetSymbols();
  if (id === 'contact-admin')  loadContactMessages();
  if (id === 'support')        loadSupportTickets();
  if (id === 'notifications')  loadNotifications();

  /* Toggle the design-studio sub-navigation bar. */
  if (id === 'design') {
    document.getElementById('design-topbar-nav').style.display = 'flex';
    initDesignManager();
  } else {
    const nav = document.getElementById('design-topbar-nav');
    if (nav) nav.style.display = 'none';
  }
}

function showUsersPage(filterType) {
  const filter = document.getElementById('users-type-filter');
  if (filter) filter.value = filterType || 'all';
  showPage('users');
}

function openSidebar() {
  document.getElementById('sidebar').classList.add('open');
  document.getElementById('overlay').classList.add('open');
}

function closeSidebar() {
  document.getElementById('sidebar').classList.remove('open');
  document.getElementById('overlay').classList.remove('open');
}

function toggleSidebar() {
  const main = document.getElementById('mainContent');
  const toggle = document.getElementById('sidebarToggle');
  const isCollapsed = main.classList.toggle('sidebar-collapsed');
  toggle.innerHTML = isCollapsed
    ? '<i class="ti ti-chevron-right"></i>'
    : '<i class="ti ti-chevron-left"></i>';
  try { localStorage.setItem('admin_sidebar_collapsed', isCollapsed ? '1' : '0'); } catch(e) {}
}

document.addEventListener('DOMContentLoaded', function() {
  try {
    if (localStorage.getItem('admin_sidebar_collapsed') === '1') {
      document.getElementById('mainContent').classList.add('sidebar-collapsed');
      document.getElementById('sidebarToggle').innerHTML = '<i class="ti ti-chevron-right"></i>';
    }
  } catch(e) {}
});

function signOut() {
  if (confirm('Are you sure you want to sign out?')) {
    window.location.href = '/auth/logout/';
  }
}


/* ===================================================================
 * 2. API HELPER
 * ===================================================================
 * Provides a thin fetch wrapper that automatically attaches CSRF tokens
 * for unsafe methods.  Used by all feature-specific modules below.
 * =================================================================== */

function csrfSafeMethod(method) {
  return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}

function getCookie(name) {
  /* Read a named cookie from document.cookie (used for CSRF token). */
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

const csrftoken = getCookie('csrftoken');

document.addEventListener('DOMContentLoaded', () => showPage('dashboard'));

function apiCall(url, method, body) {
  /* Generic fetch wrapper: serialises body as JSON, attaches CSRF token,
   * and returns the parsed JSON response. */
  const options = {
    method: method,
    headers: { 'Content-Type': 'application/json' }
  };
  if (!csrfSafeMethod(method)) {
    options.headers['X-CSRFToken'] = csrftoken;
  }
  if (body) options.body = JSON.stringify(body);
  return fetch(url, options).then(r => r.json());
}


/* ===================================================================
 * 3. CATEGORIES MANAGEMENT (Gesture library)
 * ===================================================================
 * Load, render, add, and delete categories for ASL gesture grouping.
 * Used by both the Gestures panel and the Alphabet panel.
 * =================================================================== */

let categories = [];

function loadCategories() {
  const wrap = document.querySelector('.categories-wrap');
  wrap.innerHTML = '<span style="color:var(--text3);font-size:13px;padding:8px 0">Loading categories...</span>';
  apiCall('/categories/api/categories/', 'GET')
    .then(data => {
      if (data.success) {
        categories = data.categories;
        renderCategories();
        populateCategorySelect();
        renderGestureFilters();
      }
    })
    .catch(() => {
      wrap.innerHTML = '<span style="color:var(--red);font-size:13px;padding:8px 0">Failed to load categories</span>';
    });
}

function renderCategories() {
  const wrap = document.querySelector('.categories-wrap');
  if (categories.length === 0) {
    wrap.innerHTML = '<span style="color:var(--text3);font-size:13px;padding:8px 0">No categories yet. Add one below.</span>';
    return;
  }
  wrap.innerHTML = categories.map(c =>
    `<span class="cat-pill" style="background:${c.color}20;border-color:${c.color}40">
      <i class="${c.icon}" style="color:${c.color}"></i> ${c.name}
      <button class="remove" onclick="deleteCategory(${c.id})" title="Delete">x</button>
    </span>`
  ).join('');
}

function populateCategorySelect() {
  const selects = document.querySelectorAll('#gesture-category-select, #edit-category-select');
  selects.forEach(sel => {
    sel.innerHTML = '<option value="">Select category</option>' +
      categories.map(c => `<option value="${c.id}">${c.name}</option>`).join('');
  });
}

function addCategory() {
  const name  = document.getElementById('cat-name').value.trim();
  const icon  = document.getElementById('cat-icon').value.trim() || 'ti ti-hand-stop';
  const color = document.getElementById('cat-color').value.trim() || '#3b82f6';
  if (!name) { alert('Category name is required'); return; }

  apiCall('/categories/api/categories/create/', 'POST', { name, icon, color })
    .then(data => {
      if (data.success) {
        document.getElementById('cat-name').value = '';
        showToast('Category created!');
        loadCategories();
      } else {
        alert(data.error || 'Failed to create category');
      }
    });
}

function deleteCategory(id) {
  if (!confirm('Delete this category? All gestures in it will also be deleted.')) return;
  apiCall(`/categories/api/categories/${id}/delete/`, 'DELETE')
    .then(data => {
      if (data.success) { showToast('Category deleted'); loadCategories(); loadGestures(); }
      else { alert(data.error || 'Failed to delete'); }
    });
}


/* ===================================================================
 * 4. GESTURES MANAGEMENT
 * ===================================================================
 * Load, filter, upload, edit, and delete ASL gesture entries.
 * Gestures are rendered as a grid of thumbnails with metadata.
 * =================================================================== */

let gestures = [];
let gestureFilterCategoryId = null;

function loadGestures() {
  const grid = document.getElementById('gesture-grid');
  grid.innerHTML = '<div style="grid-column:1/-1;text-align:center;padding:30px;color:var(--text3)">Loading gestures...</div>';
  let url = '/categories/api/gestures/';
  if (gestureFilterCategoryId) url += '?category_id=' + gestureFilterCategoryId;
  apiCall(url, 'GET')
    .then(data => {
      if (data.success) { gestures = data.gestures; renderGestures(); updateStatCounts(); }
    })
    .catch(() => {
      grid.innerHTML = '<div style="grid-column:1/-1;text-align:center;padding:30px;color:var(--red)">Failed to load gestures</div>';
    });
}

function renderGestureFilters() {
  const wrap = document.getElementById('gesture-filter-wrap');
  if (!wrap) return;
  const allActive = gestureFilterCategoryId === null ? 'active' : '';
  let html = `<span class="cat-pill filter-pill ${allActive}" data-category-id="" style="cursor:pointer" onclick="filterGestures(null)">All</span>`;
  categories.forEach(c => {
    const active = gestureFilterCategoryId === c.id ? 'active' : '';
    html += `<span class="cat-pill filter-pill ${active}" data-category-id="${c.id}" style="cursor:pointer;background:${c.color}20;border-color:${c.color}40" onclick="filterGestures(${c.id})"><i class="${c.icon}" style="color:${c.color}"></i> ${c.name}</span>`;
  });
  wrap.innerHTML = html;
}

function filterGestures(categoryId) {
  gestureFilterCategoryId = categoryId;
  renderGestureFilters();
  loadGestures();
}

function renderGestures() {
  const grid = document.getElementById('gesture-grid');
  const countEl = document.getElementById('gesture-count');
  if (countEl) countEl.textContent = `(${gestures.length})`;
  if (gestures.length === 0) {
    grid.innerHTML = '<div style="grid-column:1/-1;text-align:center;padding:30px;color:var(--text3)"><i class="ti ti-hand-stop" style="font-size:40px;opacity:0.3;display:block;margin-bottom:10px"></i>No gestures yet. Upload one above.</div>';
    return;
  }
  grid.innerHTML = gestures.map(g => {
    const isImage = g.video_url && /\.(jpe?g|png|gif|webp|bmp|svg)(\?.*)?$/i.test(g.video_url);
    const mediaHtml = g.video_url
      ? (isImage
          ? `<img src="${g.video_url}" style="width:100%;height:100%;object-fit:cover" alt="${escapeHtml(g.title)}">`
          : `<video src="${g.video_url}" style="width:100%;height:100%;object-fit:cover" muted controls></video>`)
      : '<i class="ti ti-video" style="font-size:28px;opacity:0.3"></i>';
    return `<div class="gesture-item">
      <div class="gesture-thumb">${mediaHtml}</div>
      <div class="gesture-meta">
        <strong>${escapeHtml(g.title)}</strong>
        <span>${escapeHtml(g.translation)}</span>
        <span style="font-size:10px;color:var(--text3)">${escapeHtml(g.category_name)}</span>
      </div>
      <div class="gesture-actions">
        <button class="edit-btn" onclick="openEditModal(${g.id})" title="Edit"><i class="ti ti-pencil"></i></button>
        <button class="delete-btn" onclick="deleteGesture(${g.id})" title="Delete"><i class="ti ti-trash"></i></button>
      </div>
    </div>`;
  }).join('');
}

function uploadGesture() {
  const translation = document.getElementById('gesture-translation').value.trim();
  const categoryId  = document.getElementById('gesture-category-select').value;
  const videoInput  = document.getElementById('gesture-video');
  if (!translation) { alert('Translation is required'); return; }
  if (!categoryId)  { alert('Please select a category'); return; }
  if (!videoInput.files.length) { alert('Please select a file'); return; }

  const formData = new FormData();
  formData.append('translation', translation);
  formData.append('category_id', categoryId);
  formData.append('video', videoInput.files[0]);

  const btn = document.getElementById('upload-gesture-btn');
  btn.disabled = true;
  btn.innerHTML = '<i class="ti ti-loader"></i>Uploading...';

  fetch('/categories/api/gestures/create/', {
    method: 'POST',
    headers: { 'X-CSRFToken': csrftoken },
    body: formData
  })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        document.getElementById('gesture-translation').value = '';
        videoInput.value = '';
        showToast('Gesture uploaded!');
        loadGestures();
        loadCategories();
      } else {
        alert(data.error || 'Failed to upload gesture');
      }
    })
    .catch(() => alert('Network error'))
    .finally(() => {
      btn.disabled = false;
      btn.innerHTML = '<i class="ti ti-upload"></i>Upload Gesture';
    });
}

function deleteGesture(id) {
  if (!confirm('Delete this gesture?')) return;
  apiCall(`/categories/api/gestures/${id}/delete/`, 'DELETE')
    .then(data => {
      if (data.success) { showToast('Gesture deleted'); loadGestures(); loadCategories(); }
      else { alert(data.error || 'Failed to delete'); }
    });
}

/* -- Edit Gesture Modal -- */
function openEditModal(id) {
  const gesture = gestures.find(g => g.id === id);
  if (!gesture) return;
  document.getElementById('edit-gesture-id').value = gesture.id;
  document.getElementById('edit-gesture-translation').value = gesture.translation || '';
  document.getElementById('edit-category-select').value = gesture.category_id || '';
  document.getElementById('edit-gesture-modal').style.display = 'flex';
}

function closeEditModal() {
  document.getElementById('edit-gesture-modal').style.display = 'none';
}

function saveGestureEdit() {
  const id = document.getElementById('edit-gesture-id').value;
  const translation = document.getElementById('edit-gesture-translation').value.trim();
  const categoryId  = document.getElementById('edit-category-select').value;
  if (!translation) { alert('Translation is required'); return; }
  if (!categoryId)  { alert('Please select a category'); return; }

  const btn = document.querySelector('#edit-gesture-modal .btn-primary');
  btn.disabled = true;
  btn.innerHTML = '<i class="ti ti-loader"></i>Saving...';

  apiCall(`/categories/api/gestures/${id}/update/`, 'PUT', {
    translation: translation,
    category_id: parseInt(categoryId)
  })
    .then(data => {
      if (data.success) { showToast('Gesture updated!'); closeEditModal(); loadGestures(); }
      else { alert(data.error || 'Failed to update gesture'); }
    })
    .catch(() => alert('Network error'))
    .finally(() => {
      btn.disabled = false;
      btn.innerHTML = '<i class="ti ti-device-floppy"></i> Save Changes';
    });
}

function updateStatCounts() {
  const statGestures = document.querySelector('.stat-card:nth-child(3) .stat-info strong');
  if (statGestures) statGestures.textContent = gestures.length;
  const statCategories = document.querySelector('.stat-card:nth-child(2) .stat-info strong');
  if (statCategories) statCategories.textContent = categories.length;
}


/* ===================================================================
 * 5. ALPHABET SYMBOLS (A-Z / 0-9)
 * ===================================================================
 * Load existing ASL symbol images and provide per-character upload
 * buttons for the full A-Z and 0-9 range.
 * =================================================================== */

function loadAlphabetSymbols() {
  const grid = document.getElementById('alpha-grid');
  grid.innerHTML = '<div style="grid-column:1/-1;text-align:center;padding:30px;color:var(--text3)">Loading symbols...</div>';
  apiCall('/categories/api/asl-symbols/', 'GET').then(data => {
    const symbols  = data.success ? (data.symbols || []) : [];
    const symbolMap = {};
    symbols.forEach(s => { symbolMap[s.character] = s; });

    const letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('');
    const numbers = '0123456789'.split('');

    let html = '<div style="margin-bottom:16px"><h4 style="font-size:14px;font-weight:700;margin-bottom:10px">Alphabets (A-Z)</h4><div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(90px,1fr));gap:8px">';
    letters.forEach(l => {
      const sym = symbolMap[l];
      const hasImage = sym && sym.image_url;
      html += `<div class="alpha-card" style="${hasImage ? '' : 'opacity:0.5'}">
        <div class="alpha-card-header">
          <span class="alpha-letter">${l}</span>
          <span class="alpha-check" style="${hasImage ? 'background:#d1fae5;color:#059669' : 'background:#f3f4f6;color:#9ca3af'}"><i class="ti ${hasImage ? 'ti-check' : 'ti-hourglass'}"></i></span>
        </div>
        ${hasImage
          ? `<img src="${sym.image_url}" alt="${l}" style="width:100%;height:70px;object-fit:contain;background:#f9fafb;border-radius:6px;margin-bottom:6px">`
          : `<div class="alpha-img-placeholder">${l}</div>`}
        <button class="alpha-btn" onclick="uploadSymbol('alphabet','${l}')"><i class="ti ti-upload"></i>${hasImage ? 'Update' : 'Upload'}</button>
      </div>`;
    });
    html += '</div></div><div style="margin-top:20px"><h4 style="font-size:14px;font-weight:700;margin-bottom:10px">Numbers (0-9)</h4><div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(90px,1fr));gap:8px">';
    numbers.forEach(n => {
      const sym = symbolMap[n];
      const hasImage = sym && sym.image_url;
      html += `<div class="alpha-card" style="${hasImage ? '' : 'opacity:0.5'}">
        <div class="alpha-card-header">
          <span class="alpha-letter">${n}</span>
          <span class="alpha-check" style="${hasImage ? 'background:#d1fae5;color:#059669' : 'background:#f3f4f6;color:#9ca3af'}"><i class="ti ${hasImage ? 'ti-check' : 'ti-hourglass'}"></i></span>
        </div>
        ${hasImage
          ? `<img src="${sym.image_url}" alt="${n}" style="width:100%;height:70px;object-fit:contain;background:#f9fafb;border-radius:6px;margin-bottom:6px">`
          : `<div class="alpha-img-placeholder">${n}</div>`}
        <button class="alpha-btn" onclick="uploadSymbol('number','${n}')"><i class="ti ti-upload"></i>${hasImage ? 'Update' : 'Upload'}</button>
      </div>`;
    });
    html += '</div></div>';
    grid.innerHTML = html;
    updateAlphabetStat(symbols.length);
  }).catch(() => {
    grid.innerHTML = '<div style="grid-column:1/-1;text-align:center;padding:30px;color:var(--red)">Failed to load symbols</div>';
  });
}

function uploadSymbol(type, character) {
  /* Create a hidden file input, let the user pick an image, then POST
   * it to the symbol upload endpoint. */
  const input = document.createElement('input');
  input.type   = 'file';
  input.accept = 'image/png,image/jpeg,image/gif,image/svg+xml';
  input.onchange = function(e) {
    const file = e.target.files[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('image', file);
    fetch(`/categories/api/asl-symbols/upload/${type}/${character}/`, {
      method: 'POST',
      headers: { 'X-CSRFToken': csrftoken },
      body: formData
    })
      .then(r => r.json())
      .then(data => {
        if (data.success) { showToast(`Symbol ${character} uploaded!`); loadAlphabetSymbols(); }
        else { alert(data.error || 'Upload failed'); }
      })
      .catch(() => alert('Network error'));
  };
  input.click();
}

function updateAlphabetStat(count) {
  const el = document.querySelector('.stat-card:nth-child(4) .stat-info strong');
  if (el) el.textContent = count;
}


/* ===================================================================
 * 6. DASHBOARD STATS & ACTIVITY
 * ===================================================================
 * Load platform-level statistics and recent activity feed for the
 * dashboard overview panel.
 * =================================================================== */

function loadDashboardStats() {
  apiCall('/admin-panel/api/dashboard/stats/', 'GET').then(data => {
    if (data.success) {
      const s = data.stats;
      document.getElementById('stat-total-users').textContent    = s.total_users;
      document.getElementById('stat-asl-users').textContent     = s.asl_users;
      document.getElementById('stat-gestures').textContent      = s.gestures;
      document.getElementById('stat-symbols').textContent       = s.symbols;
      document.getElementById('stat-open-tickets').textContent  = s.open_tickets;
      document.getElementById('stat-contact-count').textContent = s.contact_messages;
      updateChartStats();
    }
  }).catch(err => console.error('Dashboard stats error:', err));
}

function loadDashboardRecentActivity() {
  const container = document.getElementById('recent-activity-container');
  if (!container) return;
  apiCall('/admin-panel/api/dashboard/recent-activity/', 'GET').then(data => {
    if (!data.success || data.activities.length === 0) {
      container.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text3);font-size:12px"><i class="ti ti-inbox" style="display:block;font-size:20px;margin-bottom:6px;opacity:0.3"></i>No recent activity</div>';
      return;
    }
    container.innerHTML = data.activities.map(a =>
      `<div style="display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid var(--border)">
        <div style="width:32px;height:32px;border-radius:7px;background:${a.bg};display:flex;align-items:center;justify-content:center;color:${a.color};font-size:14px;flex-shrink:0"><i class="${a.icon}"></i></div>
        <div style="flex:1">
          <p style="font-size:12px;font-weight:600;color:var(--text)">${escapeHtml(a.description)}</p>
          <p style="font-size:10px;color:var(--text3)">${a.time}</p>
        </div>
      </div>`
    ).join('');
  }).catch(() => {
    container.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text3);font-size:12px">Failed to load activity</div>';
  });
}

/* -- Charts -- */
function renderUserGrowthChart() {
  const container = document.getElementById('user-growth-chart');
  if (!container) return;
  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  const values = [12, 19, 8, 24, 15, 30, 22];
  const max = Math.max(...values);
  container.innerHTML = values.map((v, i) => {
    const h = Math.max((v / max) * 160, 6);
    const color = i === values.length - 1 ? 'var(--accent)' : 'var(--accent-light)';
    return `<div class="chart-bar" style="height:${h}px">
      <div class="chart-bar-fill" style="height:100%;background:${i === values.length - 1 ? 'linear-gradient(180deg, var(--accent), var(--accent2))' : color}"></div>
      <div class="chart-bar-tooltip">${v}</div>
      <div class="chart-bar-label">${days[i]}</div>
    </div>`;
  }).join('');
}

function renderChatActivityChart() {
  const container = document.getElementById('chat-activity-chart');
  if (!container) return;
  const labels = ['6am', '9am', '12pm', '3pm', '6pm', '9pm'];
  const values = [4, 14, 28, 22, 36, 18];
  const max = Math.max(...values);
  container.innerHTML = values.map((v, i) => {
    const h = Math.max((v / max) * 160, 6);
    return `<div class="chart-bar" style="height:${h}px">
      <div class="chart-bar-fill" style="height:100%;background:linear-gradient(180deg, var(--teal), #5eead4)"></div>
      <div class="chart-bar-tooltip">${v} msgs</div>
      <div class="chart-bar-label">${labels[i]}</div>
    </div>`;
  }).join('');
}

function updateChartStats() {
  document.getElementById('chart-total-users').textContent = document.getElementById('stat-total-users').textContent;
  renderUserGrowthChart();
  renderChatActivityChart();
}


/* ===================================================================
 * 7. USERS LIST
 * ===================================================================
 * Load all platform users into a table with type badges and join dates.
 * Supports search and type filtering.  View button opens a detail modal.
 * =================================================================== */

let usersFilterTimeout;

function filterUsers() {
  clearTimeout(usersFilterTimeout);
  usersFilterTimeout = setTimeout(loadUsers, 300);
}

function loadUsers() {
  const tbody = document.getElementById('users-tbody');
  if (!tbody) return;
  const search = document.getElementById('users-search-input').value.trim();
  const type   = document.getElementById('users-type-filter').value;
  let url = '/admin-panel/api/users/?type=' + encodeURIComponent(type);
  if (search) url += '&search=' + encodeURIComponent(search);
  tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:30px;color:var(--text3)"><i class="ti ti-loader" style="display:block;font-size:24px;margin-bottom:8px;opacity:0.3"></i>Loading users...</td></tr>';
  apiCall(url, 'GET').then(data => {
    if (!data.success || data.users.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:30px;color:var(--text3)">No users found</td></tr>';
      return;
    }
    const usersCount = document.getElementById('users-count');
    if (usersCount) usersCount.textContent = `(${data.total})`;
    tbody.innerHTML = data.users.map(u => {
      const userType = u.is_superuser ? 'Admin' : u.is_asl_user ? 'ASL User' : 'Normal';
      const badge    = u.is_superuser ? 'badge-admin' : u.is_asl_user ? 'badge-asl' : 'badge-blue';
      const icon     = u.is_superuser ? 'ti-shield-check' : u.is_asl_user ? 'ti-hand-stop' : 'ti-user';
      const color    = u.is_superuser ? '#ef4444' : u.is_asl_user ? '#f97316' : '#2563eb';
      const initial  = u.full_name ? u.full_name[0].toUpperCase() : u.username[0].toUpperCase();
      return `<tr>
        <td><div class="user-row-info">
          <div class="av-sm" style="background:${color}">${escapeHtml(initial)}</div>
          <div><strong style="font-size:13px;font-weight:700">${escapeHtml(u.full_name)}</strong></div>
        </div></td>
        <td style="font-size:13px;color:var(--text2)">${escapeHtml(u.email)}</td>
        <td><span class="badge ${badge}"><i class="ti ${icon}" style="font-size:9px"></i>${userType}</span></td>
        <td style="font-size:12px;color:var(--text3)"><i class="ti ti-calendar" style="font-size:12px"></i> ${u.date_joined}</td>
        <td><div style="display:flex;gap:6px"><button class="btn btn-outline btn-xs" onclick="viewUser(${u.id})"><i class="ti ti-eye"></i>View</button></div></td>
      </tr>`;
    }).join('');
  }).catch(() => {
    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:30px;color:var(--red)">Failed to load users</td></tr>';
  });
}

function viewUser(userId) {
  const modal = document.getElementById('user-view-modal');
  modal.style.display = 'flex';
  document.getElementById('user-view-name').textContent = 'Loading...';
  document.getElementById('user-view-username').textContent = '--';
  document.getElementById('user-view-email').textContent = '--';
  document.getElementById('user-view-first-name').textContent = '--';
  document.getElementById('user-view-last-name').textContent = '--';
  document.getElementById('user-view-status').textContent = '--';
  document.getElementById('user-view-joined').textContent = '--';
  apiCall('/admin-panel/api/users/' + userId + '/', 'GET').then(data => {
    if (!data.success) {
      document.getElementById('user-view-name').textContent = 'User not found';
      return;
    }
    const u = data.user;
    document.getElementById('user-view-name').textContent = u.full_name;
    document.getElementById('user-view-username').textContent = u.username;
    document.getElementById('user-view-email').textContent = u.email;
    document.getElementById('user-view-first-name').textContent = u.first_name || '--';
    document.getElementById('user-view-last-name').textContent = u.last_name || '--';
    document.getElementById('user-view-joined').textContent = u.date_joined;

    const userType = u.is_superuser ? 'Admin' : u.is_asl_user ? 'ASL User' : 'Normal';
    const badgeClass = u.is_superuser ? 'badge-admin' : u.is_asl_user ? 'badge-asl' : 'badge-blue';
    const icon = u.is_superuser ? 'ti-shield-check' : u.is_asl_user ? 'ti-hand-stop' : 'ti-user';
    const color = u.is_superuser ? '#ef4444' : u.is_asl_user ? '#f97316' : '#2563eb';
    const initial = u.full_name ? u.full_name[0].toUpperCase() : u.username[0].toUpperCase();

    document.getElementById('user-view-avatar').textContent = initial;
    document.getElementById('user-view-avatar').style.background = color;
    document.getElementById('user-view-type-badge').className = 'badge ' + badgeClass;
    document.getElementById('user-view-type-badge').innerHTML = '<i class="ti ' + icon + '" style="font-size:9px"></i>' + userType;

    const statusEl = document.getElementById('user-view-status');
    if (u.is_active) {
      statusEl.innerHTML = '<span style="color:var(--green);display:flex;align-items:center;gap:4px"><i class="ti ti-circle-check"></i>Active</span>';
    } else {
      statusEl.innerHTML = '<span style="color:var(--red);display:flex;align-items:center;gap:4px"><i class="ti ti-circle-x"></i>Inactive</span>';
    }
  }).catch(() => {
    document.getElementById('user-view-name').textContent = 'Failed to load user';
  });
}

function closeUserViewModal() {
  document.getElementById('user-view-modal').style.display = 'none';
}


/* ===================================================================
 * 7b. DASHBOARD USERS OVERVIEW
 * ===================================================================
 * Load and render a compact user list on the dashboard page with a
 * type filter dropdown (All / ASL / Normal).
 * =================================================================== */

let dashboardUsersFilterTimeout;

function filterDashboardUsers() {
  clearTimeout(dashboardUsersFilterTimeout);
  dashboardUsersFilterTimeout = setTimeout(loadDashboardUsers, 300);
}

function loadDashboardUsers() {
  const tbody = document.getElementById('dashboard-users-tbody');
  if (!tbody) return;
  const type = document.getElementById('dashboard-user-filter').value;
  let url = '/admin-panel/api/users/?type=' + encodeURIComponent(type);
  tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;padding:20px;color:var(--text3)"><i class="ti ti-loader" style="display:block;font-size:20px;margin-bottom:6px;opacity:0.3"></i>Loading users...</td></tr>';
  apiCall(url, 'GET').then(data => {
    if (!data.success || data.users.length === 0) {
      tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;padding:20px;color:var(--text3)">No users found</td></tr>';
      return;
    }
    tbody.innerHTML = data.users.slice(0, 10).map(u => {
      const userType = u.is_superuser ? 'Admin' : u.is_asl_user ? 'ASL User' : 'Normal';
      const badge    = u.is_superuser ? 'badge-admin' : u.is_asl_user ? 'badge-asl' : 'badge-blue';
      const icon     = u.is_superuser ? 'ti-shield-check' : u.is_asl_user ? 'ti-hand-stop' : 'ti-user';
      const color    = u.is_superuser ? '#ef4444' : u.is_asl_user ? '#f97316' : '#2563eb';
      const initial  = u.full_name ? u.full_name[0].toUpperCase() : u.username[0].toUpperCase();
      return `<tr style="cursor:pointer" onclick="viewUser(${u.id})">
        <td><div class="user-row-info">
          <div class="av-sm" style="background:${color}">${escapeHtml(initial)}</div>
          <div><strong style="font-size:13px;font-weight:700">${escapeHtml(u.full_name)}</strong></div>
        </div></td>
        <td style="font-size:13px;color:var(--text2)">${escapeHtml(u.email)}</td>
        <td><span class="badge ${badge}"><i class="ti ${icon}" style="font-size:9px"></i>${userType}</span></td>
        <td style="font-size:12px;color:var(--text3)"><i class="ti ti-calendar" style="font-size:12px"></i> ${u.date_joined}</td>
      </tr>`;
    }).join('');
  }).catch(() => {
    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;padding:20px;color:var(--red)">Failed to load users</td></tr>';
  });
}


/* ===================================================================
 * 8. CONTACT MESSAGES
 * ===================================================================
 * Load, filter, render, reply to, and mark-read contact form
 * submissions from the landing page.
 * =================================================================== */

let allContactMessages = [];

function loadContactMessages() {
  const container = document.getElementById('contact-messages-container');
  container.innerHTML = '<div class="empty-state" style="padding:40px;text-align:center;color:var(--text3)"><i class="ti ti-loader" style="font-size:40px;display:block;margin-bottom:12px;opacity:0.3"></i>Loading messages...</div>';
  apiCall('/admin-panel/api/contact-messages/', 'GET').then(data => {
    if (data.success) {
      allContactMessages = data.messages;
      renderContactMessages(allContactMessages);
      document.getElementById('contact-count').textContent = `(${data.total})`;
      updateContactBadge(data.unread);
    } else {
      container.innerHTML = '<div class="empty-state" style="padding:40px;text-align:center;color:var(--text3)"><i class="ti ti-alert-circle" style="font-size:40px;display:block;margin-bottom:12px;opacity:0.3"></i>Failed to load messages</div>';
    }
  }).catch(() => {
    container.innerHTML = '<div class="empty-state" style="padding:40px;text-align:center;color:var(--text3)"><i class="ti ti-wifi-off" style="font-size:40px;display:block;margin-bottom:12px;opacity:0.3"></i>Network error</div>';
  });
}

let contactFilterTimeout;
function filterContactMessages() {
  clearTimeout(contactFilterTimeout);
  contactFilterTimeout = setTimeout(() => {
  const search  = document.getElementById('contact-search-input').value.toLowerCase().trim();
  const status  = document.getElementById('contact-status-filter').value;
  let filtered  = allContactMessages;
  if (search) {
    filtered = filtered.filter(m =>
      m.name.toLowerCase().includes(search) ||
      m.email.toLowerCase().includes(search) ||
      m.subject.toLowerCase().includes(search) ||
      m.message.toLowerCase().includes(search)
    );
  }
  if (status === 'unread')  filtered = filtered.filter(m => !m.is_read);
  else if (status === 'read')    filtered = filtered.filter(m => m.is_read);
  else if (status === 'replied') filtered = filtered.filter(m => m.is_replied);
  renderContactMessages(filtered);
  }, 300);
}

function renderContactMessages(messages) {
  const container = document.getElementById('contact-messages-container');
  if (messages.length === 0) {
    container.innerHTML = '<div class="empty-state" style="padding:40px;text-align:center;color:var(--text3)"><i class="ti ti-inbox" style="font-size:40px;display:block;margin-bottom:12px;opacity:0.3"></i>No messages found</div>';
    return;
  }
  container.innerHTML = messages.map(m => `
    <div class="msg-card ${m.is_read ? '' : 'unread'}" data-id="${m.id}">
      <div class="msg-header">
        <div style="display:flex;align-items:center;gap:10px">
          <div class="av-sm" style="background:${getAvatarColor(m.name)};width:36px;height:36px;font-size:13px">${m.name.charAt(0).toUpperCase()}</div>
          <div>
            <div style="display:flex;align-items:center;gap:8px">
              <span class="msg-sender">${escapeHtml(m.name)}</span>
              ${!m.is_read ? '<span class="badge badge-new"><i class="ti ti-sparkles" style="font-size:9px"></i>New</span>' : ''}
              ${m.is_replied ? '<span class="badge" style="background:#d1fae5;color:#059669;font-size:9px"><i class="ti ti-circle-check" style="font-size:9px"></i>Replied</span>' : ''}
            </div>
            <span class="msg-email">${escapeHtml(m.email)}</span>
          </div>
        </div>
        <span class="msg-time"><i class="ti ti-clock" style="font-size:12px"></i> ${m.created_at_human}</span>
      </div>
      <div class="msg-subject"><i class="ti ti-message" style="font-size:13px;color:var(--text3)"></i> ${escapeHtml(m.subject || '(no subject)')}</div>
      <div class="msg-body">${escapeHtml(m.message)}</div>
      ${m.is_replied
        ? `<div class="admin-reply"><strong><i class="ti ti-shield-check" style="font-size:11px"></i> Admin Reply</strong><p>${escapeHtml(m.reply_message)}</p><span style="font-size:11px;color:var(--text3)"><i class="ti ti-clock" style="font-size:11px"></i> ${m.replied_at}</span></div>`
        : ''}
      <div class="reply-form">
        <input type="text" id="reply-input-${m.id}" placeholder="Write a reply..." onkeypress="if(event.key==='Enter')sendReply(${m.id})">
        <button class="btn btn-primary btn-sm" onclick="sendReply(${m.id})"><i class="ti ti-send"></i>Send</button>
        ${!m.is_read ? `<button class="btn btn-outline btn-sm" onclick="markRead(${m.id})" style="margin-left:6px"><i class="ti ti-eye"></i>Mark Read</button>` : ''}
      </div>
    </div>`
  ).join('');
}

function sendReply(messageId) {
  const input = document.getElementById('reply-input-' + messageId);
  const reply = input.value.trim();
  if (!reply) return;
  const btn = input.nextElementSibling;
  btn.disabled = true;
  btn.innerHTML = '<i class="ti ti-loader"></i>Sending...';
  apiCall('/admin-panel/api/contact-messages/' + messageId + '/reply/', 'POST', { reply: reply })
    .then(data => {
      if (data.success) { input.value = ''; loadContactMessages(); }
      else { alert(data.error || 'Failed to send reply'); btn.disabled = false; btn.innerHTML = '<i class="ti ti-send"></i>Send'; }
    })
    .catch(() => { alert('Network error'); btn.disabled = false; btn.innerHTML = '<i class="ti ti-send"></i>Send'; });
}

function markRead(messageId) {
  apiCall('/admin-panel/api/contact-messages/' + messageId + '/mark-read/', 'POST', {})
    .then(data => { if (data.success) loadContactMessages(); });
}


/* ===================================================================
 * 9. SUPPORT TICKETS
 * ===================================================================
 * Load, render, and manage support tickets with text and video
 * responses for normal and ASL users.
 * =================================================================== */

let allSupportTickets = [];

function loadSupportTickets() {
  const container = document.getElementById('page-support');
  if (!container) return;
  apiCall('/admin-panel/api/support-tickets/', 'GET').then(data => {
    if (data.success) {
      allSupportTickets = data.tickets;
      renderSupportStats(data.stats);
      renderSupportTickets(allSupportTickets);
    }
  }).catch(() => {});
}

function renderSupportStats(stats) {
  /* Update both the top stat cards and the dashboard support summary. */
  const statEls = document.querySelectorAll('#page-support .sup-stat strong');
  if (statEls.length >= 4) {
    statEls[0].textContent = stats.open || 0;
    statEls[1].textContent = stats.in_progress || 0;
    statEls[2].textContent = stats.resolved || 0;
    statEls[3].textContent = stats.asl || 0;
  }
  ['sup-open', 'sup-in-progress', 'sup-resolved', 'sup-asl'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.textContent = stats[id.replace('sup-', '').replace('-', '_')] || 0;
  });
}

function renderSupportTickets(tickets) {
  /* Render the full support ticket list with reply forms. */
  const container = document.querySelector('#page-support .card');
  if (!container) return;
  const titleSpan = container.querySelector('.card-title span');
  if (titleSpan) titleSpan.textContent = `(${tickets.length})`;

  let msgContainer = container.querySelector('.support-tickets-list');
  if (!msgContainer) {
    msgContainer = document.createElement('div');
    msgContainer.className = 'support-tickets-list';
    container.appendChild(msgContainer);
  }

  if (tickets.length === 0) {
    msgContainer.innerHTML = '<div class="empty-state" style="padding:40px;text-align:center;color:var(--text3)"><i class="ti ti-headset" style="font-size:40px;display:block;margin-bottom:12px;opacity:0.3"></i>No support tickets yet</div>';
    return;
  }

  msgContainer.innerHTML = tickets.map(t => {
    const isAsl = t.ticket_type === 'asl';
    const statusBadge = t.status === 'resolved' || t.status === 'closed'
      ? 'badge-resolved'
      : t.status === 'in_progress' ? 'badge-progress' : 'badge';
    const initial = (t.user.full_name || t.user.username)[0].toUpperCase();
    /* Build actions dropdown for status changes. */
    const statusActions = ['open', 'in_progress', 'resolved', 'closed']
      .filter(s => s !== t.status)
      .map(s => `<div onclick="updateTicketStatus(${t.id},'${s}')">${s.replace('_', ' ').toUpperCase()}</div>`)
      .join('');

    return `<div class="sup-msg" data-id="${t.id}">
      <div class="sup-msg-head">
        <div class="av-sm" style="background:${isAsl ? 'var(--amber)' : 'var(--blue)'}">${initial}</div>
        <span class="sup-msg-name">${escapeHtml(t.user.full_name)}</span>
        <span class="badge ${statusBadge}"><i class="ti ti-circle-check" style="font-size:9px"></i>${t.status.replace('_', ' ').toUpperCase()}</span>
        ${isAsl
          ? '<span class="badge badge-asl"><i class="ti ti-hand-stop" style="font-size:9px"></i>ASL</span>'
          : '<span class="badge badge-blue"><i class="ti ti-user" style="font-size:9px"></i>NORMAL</span>'}
        <span class="sup-msg-time"><i class="ti ti-clock" style="font-size:12px"></i> ${t.created_at_human}</span>
        <div class="sup-status-menu" style="position:relative;margin-left:auto">
          <button class="btn btn-outline btn-xs" onclick="this.nextElementSibling.classList.toggle('show')"><i class="ti ti-chevron-down"></i> Status</button>
          <div class="sup-status-dropdown" style="display:none;position:absolute;top:100%;right:0;background:#fff;border:1px solid var(--border);border-radius:8px;box-shadow:0 4px 16px rgba(0,0,0,0.1);z-index:10;min-width:120px">${statusActions}</div>
        </div>
      </div>
      ${t.subject ? `<p style="font-size:14px;font-weight:500;color:var(--text)">${escapeHtml(t.subject)}</p>` : ''}
      <p style="font-size:13px;color:var(--text2);margin:4px 0">${escapeHtml(t.issue_description)}</p>
      ${t.video_url
        ? `<div class="video-box">
             <div class="video-box-header">
               <div style="display:flex;align-items:center;gap:7px"><i class="ti ti-video"></i>Video from ${escapeHtml(t.user.username)}</div>
               <a href="${t.video_url}" class="btn btn-outline btn-xs" download><i class="ti ti-download"></i>Download</a>
             </div>
             <video src="${t.video_url}" style="width:100%;max-height:200px;background:#000" controls></video>
           </div>`
        : ''}
      ${t.admin_response_text
        ? `<div style="margin-top:10px;padding:12px;background:var(--blue-bg);border-radius:8px">
             <strong style="font-size:12px;color:var(--blue)"><i class="ti ti-shield-check" style="font-size:11px"></i> Admin Reply</strong>
             <p style="font-size:13px;margin:4px 0 0">${escapeHtml(t.admin_response_text)}</p>
           </div>`
        : ''}
      ${t.admin_response_video_url
        ? `<div style="margin-top:10px">
             <div style="font-size:12px;font-weight:600;color:var(--blue);margin-bottom:4px"><i class="ti ti-video"></i> Admin Video Reply</div>
             <video src="${t.admin_response_video_url}" style="width:100%;max-height:200px;background:#000" controls></video>
           </div>`
        : ''}
      <div class="reply-actions">
        ${isAsl
          ? `<div style="margin-top:10px">
               <input type="file" id="video-reply-${t.id}" accept="video/*" style="display:none" onchange="sendVideoResponse(${t.id},this.files[0])">
               <button class="btn btn-outline btn-sm" onclick="document.getElementById('video-reply-${t.id}').click()"><i class="ti ti-video"></i>Send Video Reply</button>
               <input type="text" id="admin-text-reply-${t.id}" placeholder="Optional text with video..." style="margin-top:6px;width:100%">
             </div>`
          : `<div style="display:flex;gap:8px;align-items:center;margin-top:10px">
               <input type="text" id="admin-text-reply-${t.id}" placeholder="Type your response..." style="flex:1">
               <button class="btn btn-primary btn-sm" onclick="sendTextResponse(${t.id})"><i class="ti ti-send"></i>Send Reply</button>
             </div>`}
      </div>
    </div>`;
  }).join('');
}

function sendTextResponse(ticketId) {
  const input = document.getElementById('admin-text-reply-' + ticketId);
  const responseText = input ? input.value.trim() : '';
  if (!responseText) { showToast('Please enter a response', true); return; }
  apiCall('/admin-panel/api/support-tickets/' + ticketId + '/respond/', 'POST', {
    response_text: responseText,
    status: 'in_progress'
  })
    .then(data => {
      if (data.success) { showToast('Response sent!'); if (input) input.value = ''; loadSupportTickets(); }
      else { showToast(data.error || 'Failed to send', true); }
    })
    .catch(() => showToast('Network error', true));
}

function sendVideoResponse(ticketId, file) {
  if (!file) return;
  const formData = new FormData();
  formData.append('response_video', file);
  formData.append('status', 'in_progress');
  fetch('/admin-panel/api/support-tickets/' + ticketId + '/respond/', {
    method: 'POST',
    headers: { 'X-CSRFToken': csrftoken },
    body: formData
  })
    .then(r => r.json())
    .then(data => {
      if (data.success) { showToast('Video response sent!'); loadSupportTickets(); }
      else { showToast(data.error || 'Failed to send', true); }
    })
    .catch(() => showToast('Network error', true));
}

function updateTicketStatus(ticketId, status) {
  apiCall('/admin-panel/api/support-tickets/' + ticketId + '/status/', 'POST', { status: status })
    .then(data => {
      if (data.success) { showToast('Status updated to ' + status); loadSupportTickets(); }
      else { showToast(data.error || 'Failed to update', true); }
    })
    .catch(() => showToast('Network error', true));
}

function updateContactBadge(unread) {
  const badge = document.getElementById('admin-contact-badge');
  if (badge) { badge.textContent = unread; badge.style.display = unread > 0 ? 'inline' : 'none'; }
  const statCounter = document.getElementById('stat-contact-count');
  if (statCounter) statCounter.textContent = allContactMessages.length;
  const statUnread = document.getElementById('stat-contact-unread');
  if (statUnread) statUnread.innerHTML = '<i class="ti ti-clock"></i>' + unread + ' unread';
}

function getAvatarColor(name) {
  const colors = ['#3b82f6', '#8b5cf6', '#ef4444', '#f59e0b', '#10b981', '#06b6d4', '#f97316', '#ec4899'];
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
  return colors[Math.abs(hash) % colors.length];
}

function escapeHtml(text) {
  if (!text) return '';
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function showToast(msg, isError) {
  const container = document.getElementById('toastContainer');
  if (!container) {
    const c = document.createElement('div');
    c.id = 'toastContainer';
    c.className = 'toast-container';
    document.body.appendChild(c);
  }
  const t = document.createElement('div');
  t.className = 'toast ' + (isError ? 'toast-error' : 'toast-success');
  t.innerHTML = '<i class="ti ' + (isError ? 'ti-alert-circle' : 'ti-check-circle') + '"></i>' + msg;
  const container2 = document.getElementById('toastContainer');
  container2.appendChild(t);
  setTimeout(() => {
    t.style.animation = 'toastOut 0.3s ease forwards';
    setTimeout(() => t.remove(), 300);
  }, 3000);
}


/* ===================================================================
 * 10. NOTIFICATIONS
 * ===================================================================
 * Load, render, and mark-read in-app notifications for the admin user.
 * =================================================================== */

function loadNotifications() {
  apiCall('/notifications/', 'GET').then(data => {
    if (data.success) { renderNotifications(data.notifications); updateUnreadCount(); }
  });
}

function renderNotifications(notifications) {
  const container = document.querySelector('#page-notifications .notif-container');
  if (!container) return;
  if (notifications.length === 0) {
    container.innerHTML = `<div class="notif-empty"><div class="icon-circle"><i class="ti ti-bell-off"></i></div><h3>No notification now</h3></div>`;
    return;
  }
  container.innerHTML = `
    <div style="display:flex;justify-content:flex-end;margin-bottom:12px;gap:8px">
      <button class="btn btn-outline btn-sm" onclick="loadNotifications()"><i class="ti ti-refresh"></i> Refresh</button>
      <button class="btn btn-primary btn-sm" onclick="markAllRead()"><i class="ti ti-check"></i> Mark all read</button>
    </div>
    ${notifications.map(n => {
      const isUnread = !n.is_read;
      let icon = 'ti ti-bell'; let color = 'var(--red)';
      if (n.type === 'friend_request' || n.type === 'friend_accepted') { icon = 'ti ti-user-plus'; color = 'var(--blue)'; }
      else if (n.type === 'message')         { icon = 'ti ti-message'; color = 'var(--accent)'; }
      else if (n.type === 'contact_form')     { icon = 'ti ti-mail'; color = 'var(--teal)'; }
      else if (n.type === 'support_request' || n.type === 'support_response') { icon = 'ti ti-headset'; color = 'var(--amber)'; }
      return `<div style="display:flex;align-items:center;gap:12px;padding:14px 0;border-bottom:1px solid var(--border);${isUnread ? 'background:var(--blue-bg);margin:0 -16px;padding:14px 16px;border-radius:8px;' : ''}">
        <div style="width:36px;height:36px;border-radius:50%;background:var(--bg);display:flex;align-items:center;justify-content:center;color:${color};flex-shrink:0"><i class="${icon}" style="font-size:14px"></i></div>
        <div style="flex:1;min-width:0">
          <div style="font-weight:${isUnread ? '600' : '400'};font-size:14px;color:var(--text)">${escapeHtml(n.title)}</div>
          <div style="font-size:13px;color:var(--text2);margin-top:2px">${escapeHtml(n.message)}</div>
          <div style="font-size:11px;color:var(--text3);margin-top:4px"><i class="ti ti-clock"></i> ${new Date(n.created_at).toLocaleDateString()}</div>
        </div>
        ${isUnread ? `<button class="btn btn-outline btn-xs" onclick="markNotifRead(${n.id})" style="flex-shrink:0"><i class="ti ti-check"></i></button>` : ''}
      </div>`;
    }).join('')}`;
}

function updateUnreadCount() {
  apiCall('/notifications/unread-count/', 'GET').then(data => {
    if (data.success) {
      const badge = document.querySelector('.nav-item[onclick*="notifications"] .nav-badge');
      if (badge) { badge.textContent = data.count; badge.style.display = data.count > 0 ? 'inline' : 'none'; }
      const dot = document.querySelector('.notif-dot');
      if (dot) {
        let db = dot.querySelector('.notif-dot-badge');
        if (!db) {
          db = document.createElement('span');
          db.className = 'notif-dot-badge';
          db.style.cssText = 'position:absolute;top:-4px;right:-4px;background:var(--red);color:#fff;font-size:9px;font-weight:700;width:18px;height:18px;border-radius:50%;display:flex;align-items:center;justify-content:center;border:2px solid #fff;line-height:1';
          dot.style.position = 'relative';
          dot.appendChild(db);
        }
        db.textContent = data.count;
        db.style.display = data.count > 0 ? 'flex' : 'none';
      }
    }
  });
}

function markNotifRead(notifId) {
  apiCall('/notifications/mark-read/', 'POST', { notification_id: notifId })
    .then(() => { loadNotifications(); updateUnreadCount(); });
}

function markAllRead() {
  apiCall('/notifications/mark-read/', 'POST', {})
    .then(() => { loadNotifications(); updateUnreadCount(); });
}


/* ===================================================================
 * 11. PROFILE & PASSWORD
 * ===================================================================
 * Admin profile editing (name, username, email, picture) and password
 * change handling.
 * =================================================================== */

function previewAdminProfilePic(input) {
  const file = input.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = function(e) {
    document.getElementById('admin-pic-preview-img').src = e.target.result;
    document.getElementById('admin-pic-preview').style.display = 'block';
  };
  reader.readAsDataURL(file);
}

function handleAdminUpdateProfile() {
  const fullName = document.getElementById('admin-profile-full-name').value.trim();
  const username = document.getElementById('admin-profile-username').value.trim();
  const email    = document.getElementById('admin-profile-email').value.trim();
  const file     = document.getElementById('admin-profile-pic-input').files[0];
  if (!fullName || !username || !email) { showToast('Please fill in all fields.'); return; }

  const btn = document.querySelector('#page-profile .btn-primary');
  btn.disabled = true;
  btn.innerHTML = '<i class="ti ti-loader"></i>Saving...';

  const formData = new FormData();
  formData.append('full_name', fullName);
  formData.append('username', username);
  formData.append('email', email);
  if (file) formData.append('profile_picture', file);

  fetch('/auth/update-profile/', {
    method: 'POST',
    headers: { 'X-CSRFToken': csrftoken },
    body: formData
  })
    .then(r => r.json())
    .then(data => {
      btn.disabled = false;
      btn.innerHTML = '<i class="ti ti-device-floppy"></i>Save Changes';
      if (data.success) {
        showToast('Profile updated!');
        document.getElementById('admin-profile-name-display').textContent = fullName;
      } else {
        showToast(data.error || 'Failed to update profile');
      }
    })
    .catch(() => {
      btn.disabled = false;
      btn.innerHTML = '<i class="ti ti-device-floppy"></i>Save Changes';
      showToast('Network error');
    });
}

function handleAdminChangePassword() {
  const currentPassword  = document.getElementById('admin-current-password').value;
  const newPassword      = document.getElementById('admin-new-password').value;
  const confirmPassword  = document.getElementById('admin-confirm-password').value;
  if (!currentPassword || !newPassword || !confirmPassword) { showToast('Please fill in all password fields.'); return; }
  if (newPassword !== confirmPassword) { showToast('New passwords do not match.'); return; }
  if (newPassword.length < 8) { showToast('Password must be at least 8 characters.'); return; }

  const btn = document.querySelector('#page-settings .btn-primary.btn-sm');
  btn.disabled = true;
  btn.innerHTML = '<i class="ti ti-loader"></i>Updating...';

  fetch('/auth/change-password/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrftoken },
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
      confirm_password: confirmPassword
    })
  })
    .then(r => r.json())
    .then(data => {
      btn.disabled = false;
      btn.innerHTML = '<i class="ti ti-key"></i> Update Password';
      if (data.success) {
        showToast('Password changed successfully!');
        document.getElementById('admin-current-password').value = '';
        document.getElementById('admin-new-password').value = '';
        document.getElementById('admin-confirm-password').value = '';
      } else {
        showToast(data.error || 'Failed to change password');
      }
    })
    .catch(() => {
      btn.disabled = false;
      btn.innerHTML = '<i class="ti ti-key"></i> Update Password';
      showToast('Network error');
    });
}


/* ===================================================================
 * 12. DESIGN STUDIO -- STATE VARIABLES
 * ===================================================================
 * Track the currently active page, section, design data, and dirty
 * state for the design studio.
 * =================================================================== */

let currentDesignPage     = 'landing';
let currentDesignSection  = 'hero';
let designPages           = [];
let designSettingsCache   = {};
let designDirty           = false;
let currentSectionSettings = {};
let sectionDefaults       = {};


/* ===================================================================
 * 13. DESIGN STUDIO -- SECTION FIELD DEFINITIONS
 * ===================================================================
 * Schema for each section's editable fields, grouped by category
 * (text, colors, fonts, images, videos, buttons, layout).
 * =================================================================== */

const SECTION_FIELD_DEFS = {
  hero: {
    text: [
      { key: 'text_badge', label: 'Badge Text', type: 'text' },
      { key: 'text_heading', label: 'Heading', type: 'text' },
      { key: 'text_description', label: 'Description', type: 'textarea' },
      { key: 'text_primary_btn', label: 'Primary Button Text', type: 'text' },
      { key: 'text_secondary_btn', label: 'Secondary Button Text', type: 'text' },
    ],
    colors: [
      { key: 'color_overlay', label: 'Overlay Color', type: 'color' },
      { key: 'color_text', label: 'Text Color', type: 'color' },
      { key: 'color_accent', label: 'Accent Color', type: 'color' },
    ],
    fonts: [
      { key: 'font_heading', label: 'Heading Font', type: 'font' },
      { key: 'font_body', label: 'Body Font', type: 'font' },
      { key: 'font_heading_size', label: 'Heading Size', type: 'size' },
    ],
    images: [
      { key: 'image_background', label: 'Background Image', type: 'image' },
    ],
    videos: [
      { key: 'video_background', label: 'Background Video', type: 'video' },
    ],
    buttons: [
      { key: 'button_primary_style', label: 'Primary Button Style', type: 'select', options: ['fill', 'outline', 'ghost'] },
      { key: 'button_secondary_style', label: 'Secondary Button Style', type: 'select', options: ['fill', 'outline', 'ghost'] },
      { key: 'button_border_radius', label: 'Button Border Radius', type: 'size' },
    ],
    layout: [
      { key: 'layout_fullscreen', label: 'Full Screen', type: 'toggle' },
      { key: 'layout_centered', label: 'Centered Content', type: 'toggle' },
      { key: 'layout_padding', label: 'Section Padding', type: 'size' },
      { key: 'layout_container_width', label: 'Container Width', type: 'size' },
      { key: 'stats_display', label: 'Stats Display', type: 'select', options: ['inline', 'hidden'] },
    ],
  },
  features: {
    text: [
      { key: 'text_heading', label: 'Heading', type: 'text' },
      { key: 'text_description', label: 'Description', type: 'textarea' },
    ],
    colors: [
      { key: 'color_background', label: 'Background Color', type: 'color' },
      { key: 'color_text', label: 'Text Color', type: 'color' },
      { key: 'color_card_bg', label: 'Card Background', type: 'color' },
      { key: 'color_card_border', label: 'Card Border', type: 'color' },
      { key: 'color_accent', label: 'Accent Color', type: 'color' },
    ],
    fonts: [
      { key: 'font_heading', label: 'Heading Font', type: 'font' },
      { key: 'font_body', label: 'Body Font', type: 'font' },
      { key: 'font_heading_size', label: 'Heading Size', type: 'size' },
    ],
    images: [], videos: [], buttons: [],
    layout: [
      { key: 'layout_columns', label: 'Columns', type: 'select', options: ['2', '3', '4'] },
      { key: 'layout_padding', label: 'Section Padding', type: 'size' },
      { key: 'layout_container_width', label: 'Container Width', type: 'size' },
    ],
  },
  statistics: {
    text: [
      { key: 'text_heading', label: 'Heading', type: 'text' },
      { key: 'text_description', label: 'Description', type: 'textarea' },
    ],
    colors: [
      { key: 'color_gradient_start', label: 'Gradient Start', type: 'color' },
      { key: 'color_gradient_end', label: 'Gradient End', type: 'color' },
      { key: 'color_text', label: 'Text Color', type: 'color' },
      { key: 'color_value', label: 'Value Color', type: 'color' },
    ],
    fonts: [
      { key: 'font_heading', label: 'Heading Font', type: 'font' },
      { key: 'font_body', label: 'Body Font', type: 'font' },
      { key: 'font_heading_size', label: 'Heading Size', type: 'size' },
      { key: 'font_value_size', label: 'Value Size', type: 'size' },
    ],
    images: [], videos: [], buttons: [],
    layout: [
      { key: 'layout_padding', label: 'Section Padding', type: 'size' },
      { key: 'layout_container_width', label: 'Container Width', type: 'size' },
    ],
  },
  about: {
    text: [
      { key: 'text_badge', label: 'Badge Text', type: 'text' },
      { key: 'text_heading', label: 'Heading', type: 'text' },
      { key: 'text_description', label: 'Description', type: 'textarea' },
    ],
    colors: [
      { key: 'color_background', label: 'Background Color', type: 'color' },
      { key: 'color_text', label: 'Text Color', type: 'color' },
      { key: 'color_card_bg', label: 'Card Background', type: 'color' },
      { key: 'color_accent', label: 'Accent Color', type: 'color' },
    ],
    fonts: [
      { key: 'font_heading', label: 'Heading Font', type: 'font' },
      { key: 'font_body', label: 'Body Font', type: 'font' },
      { key: 'font_heading_size', label: 'Heading Size', type: 'size' },
    ],
    images: [
      { key: 'image_about', label: 'About Image', type: 'image' },
    ],
    videos: [], buttons: [],
    layout: [
      { key: 'layout_columns', label: 'Columns', type: 'select', options: ['1', '2', '3', '4'] },
      { key: 'layout_padding', label: 'Section Padding', type: 'size' },
      { key: 'layout_container_width', label: 'Container Width', type: 'size' },
    ],
  },
  testimonials: {
    text: [
      { key: 'text_heading', label: 'Heading', type: 'text' },
      { key: 'text_description', label: 'Description', type: 'textarea' },
    ],
    colors: [
      { key: 'color_background', label: 'Background Color', type: 'color' },
      { key: 'color_text', label: 'Text Color', type: 'color' },
      { key: 'color_card_bg', label: 'Card Background', type: 'color' },
      { key: 'color_accent', label: 'Accent Color', type: 'color' },
    ],
    fonts: [
      { key: 'font_heading', label: 'Heading Font', type: 'font' },
      { key: 'font_body', label: 'Body Font', type: 'font' },
      { key: 'font_heading_size', label: 'Heading Size', type: 'size' },
    ],
    images: [], videos: [], buttons: [],
    layout: [
      { key: 'layout_columns', label: 'Columns', type: 'select', options: ['1', '2', '3', '4'] },
      { key: 'layout_padding', label: 'Section Padding', type: 'size' },
      { key: 'layout_container_width', label: 'Container Width', type: 'size' },
    ],
  },
  cta: {
    text: [
      { key: 'text_heading', label: 'Heading', type: 'text' },
      { key: 'text_description', label: 'Description', type: 'textarea' },
      { key: 'text_button', label: 'Button Text', type: 'text' },
    ],
    colors: [
      { key: 'color_gradient_start', label: 'Gradient Start', type: 'color' },
      { key: 'color_gradient_end', label: 'Gradient End', type: 'color' },
      { key: 'color_text', label: 'Text Color', type: 'color' },
      { key: 'color_button_bg', label: 'Button Background', type: 'color' },
      { key: 'color_button_text', label: 'Button Text', type: 'color' },
    ],
    fonts: [
      { key: 'font_heading', label: 'Heading Font', type: 'font' },
      { key: 'font_body', label: 'Body Font', type: 'font' },
      { key: 'font_heading_size', label: 'Heading Size', type: 'size' },
    ],
    images: [], videos: [],
    buttons: [
      { key: 'button_border_radius', label: 'Button Border Radius', type: 'size' },
    ],
    layout: [
      { key: 'layout_padding', label: 'Section Padding', type: 'size' },
      { key: 'layout_container_width', label: 'Container Width', type: 'size' },
    ],
  },
  footer: {
    text: [
      { key: 'text_logo_text', label: 'Logo Text', type: 'text' },
      { key: 'text_description', label: 'Description', type: 'textarea' },
      { key: 'text_copyright', label: 'Copyright Text', type: 'text' },
    ],
    colors: [
      { key: 'color_background', label: 'Background Color', type: 'color' },
      { key: 'color_text', label: 'Text Color', type: 'color' },
      { key: 'color_link', label: 'Link Color', type: 'color' },
      { key: 'color_link_hover', label: 'Link Hover Color', type: 'color' },
      { key: 'color_divider', label: 'Divider Color', type: 'color' },
    ],
    fonts: [
      { key: 'font_heading', label: 'Heading Font', type: 'font' },
      { key: 'font_body', label: 'Body Font', type: 'font' },
    ],
    images: [
      { key: 'image_logo', label: 'Logo Image', type: 'image' },
    ],
    videos: [], buttons: [],
    layout: [
      { key: 'layout_padding', label: 'Section Padding', type: 'size' },
      { key: 'layout_container_width', label: 'Container Width', type: 'size' },
    ],
  },
  how_it_works: {
    text: [
      { key: 'text_heading', label: 'Heading', type: 'text' },
      { key: 'text_description', label: 'Description', type: 'textarea' },
    ],
    colors: [
      { key: 'color_background', label: 'Background Color', type: 'color' },
      { key: 'color_text', label: 'Text Color', type: 'color' },
      { key: 'color_card_bg', label: 'Card Background', type: 'color' },
      { key: 'color_accent', label: 'Accent Color', type: 'color' },
    ],
    fonts: [
      { key: 'font_heading', label: 'Heading Font', type: 'font' },
      { key: 'font_body', label: 'Body Font', type: 'font' },
      { key: 'font_heading_size', label: 'Heading Size', type: 'size' },
    ],
    images: [], videos: [], buttons: [],
    layout: [
      { key: 'layout_columns', label: 'Columns', type: 'select', options: ['2', '3', '4'] },
      { key: 'layout_padding', label: 'Section Padding', type: 'size' },
      { key: 'layout_container_width', label: 'Container Width', type: 'size' },
    ],
  },
  contact: {
    text: [
      { key: 'text_heading', label: 'Heading', type: 'text' },
      { key: 'text_description', label: 'Description', type: 'textarea' },
      { key: 'text_info_heading', label: 'Info Heading', type: 'text' },
      { key: 'text_info_text', label: 'Info Text', type: 'textarea' },
    ],
    colors: [
      { key: 'color_background', label: 'Background Color', type: 'color' },
      { key: 'color_text', label: 'Text Color', type: 'color' },
      { key: 'color_card_bg', label: 'Card Background', type: 'color' },
      { key: 'color_accent', label: 'Accent Color', type: 'color' },
      { key: 'color_form_bg', label: 'Form Background', type: 'color' },
    ],
    fonts: [
      { key: 'font_heading', label: 'Heading Font', type: 'font' },
      { key: 'font_body', label: 'Body Font', type: 'font' },
      { key: 'font_heading_size', label: 'Heading Size', type: 'size' },
    ],
    images: [], videos: [], buttons: [],
    layout: [
      { key: 'layout_padding', label: 'Section Padding', type: 'size' },
      { key: 'layout_container_width', label: 'Container Width', type: 'size' },
    ],
  },
};

const CATEGORY_ICONS = {
  text: 'ti ti-typography',
  colors: 'ti ti-palette',
  fonts: 'ti ti-text-size',
  images: 'ti ti-photo',
  videos: 'ti ti-video',
  buttons: 'ti ti-click',
  icons: 'ti ti-icons',
  layout: 'ti ti-dimensions',
};

const CATEGORY_LABELS = {
  text: 'Text Content',
  colors: 'Colors',
  fonts: 'Fonts & Typography',
  images: 'Images',
  videos: 'Videos',
  buttons: 'Buttons',
  icons: 'Icons',
  layout: 'Layout Settings',
};


/* ===================================================================
 * 14. DESIGN STUDIO -- SECTION MANAGEMENT (render, collect, upload)
 * ===================================================================
 * Renders the section sidebar with field inputs, collects changes,
 * and manages file uploads for section images/videos.
 * =================================================================== */

function loadDesignPages() {
  return fetch('/admin-panel/api/page-design/')
    .then(r => r.json())
    .then(data => {
      if (data.success) designPages = data.pages;
      return data;
    });
}

function loadSectionSettings(sectionName) {
  return fetch('/admin-panel/api/section-design/' + sectionName + '/?page=' + currentDesignPage)
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        currentSectionSettings = data.section.settings || {};
        sectionDefaults = data.section.defaults || {};
        return data.section;
      }
      return null;
    });
}

function renderSectionSettings(sectionName, settings) {
  const container = document.getElementById('sec-controls-scroll');
  const defs = SECTION_FIELD_DEFS[sectionName];
  if (!defs) {
    container.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text3)">No settings available for this section.</div>';
    return;
  }
  let html = '';
  for (const [category, fields] of Object.entries(defs)) {
    if (fields.length === 0) continue;
    html += `<div class="ds-group">
      <div class="ds-group-header" onclick="toggleDesignCategory(this)">
        <div class="ds-group-title"><i class="${CATEGORY_ICONS[category] || 'ti ti-settings'}"></i><span>${CATEGORY_LABELS[category] || category}</span></div>
        <div class="ds-group-actions"><span class="ds-group-count">${fields.length}</span><i class="ti ti-chevron-down"></i></div>
      </div>
      <div class="ds-group-body open"><div class="ds-field-grid">`;
    for (const field of fields) {
      const val = settings[field.key] !== undefined ? settings[field.key] : '';
      html += renderField(field, val);
    }
    html += `</div></div></div>`;
  }
  /* Visibility toggle: always shown at the bottom. */
  html += `<div class="ds-group" style="border-color:var(--green-light)">
    <div class="ds-group-header" style="background:var(--green-bg);color:var(--green)">
      <div class="ds-group-title"><i class="ti ti-eye"></i><span>Section Visibility</span></div>
    </div>
    <div class="ds-group-body open">
      <div class="ds-field-grid" style="grid-template-columns:1fr">
        <div class="ds-field" style="display:flex;align-items:center;gap:12px;padding:8px 0">
          <label class="ds-toggle-label" style="flex:1;cursor:pointer"><strong style="font-size:13px">Show this section on the website</strong></label>
          <label class="toggle" style="margin:0">
            <input type="checkbox" id="sec-visibility-toggle" ${settings.is_visible !== false ? 'checked' : ''} onchange="onSectionSettingChange()">
            <span class="toggle-slider"></span>
          </label>
        </div>
      </div>
    </div>
  </div>`;
  container.innerHTML = html;
}

function renderField(field, value) {
  const key = field.key;
  const safeVal = (value !== undefined && value !== null) ? String(value).replace(/"/g, '&quot;') : '';
  switch (field.type) {
    case 'text':
      return `<div class="ds-field ds-field-full"><label>${field.label}</label><input type="text" class="sec-input" data-key="${key}" value="${safeVal}" oninput="onSectionSettingChange()" placeholder="Enter ${field.label.toLowerCase()}"></div>`;
    case 'textarea':
      return `<div class="ds-field ds-field-full"><label>${field.label}</label><textarea class="sec-textarea" data-key="${key}" oninput="onSectionSettingChange()" placeholder="Enter ${field.label.toLowerCase()}">${safeVal}</textarea></div>`;
    case 'color':
      return `<div class="ds-field"><label>${field.label}</label><div class="ds-color-input"><input type="color" class="sec-color" data-key="${key}" value="${toHexColor(safeVal)}" oninput="onSectionColorChange(this)"><input type="text" class="sec-color-txt" data-key="${key}" value="${safeVal}" oninput="onSectionColorTextChange(this)"></div></div>`;
    case 'font':
      const fonts = ['Inter, sans-serif', 'Plus Jakarta Sans, sans-serif', 'Poppins, sans-serif', 'Roboto, sans-serif', 'Nunito, sans-serif', 'Georgia, serif', 'system-ui, sans-serif'];
      return `<div class="ds-field"><label>${field.label}</label><select class="sec-select" data-key="${key}" onchange="onSectionSettingChange()">${fonts.map(f => `<option value="${f}" ${safeVal === f ? 'selected' : ''}>${f.split(',')[0]}</option>`).join('')}</select></div>`;
    case 'size':
      const sizes = ['24px','28px','32px','36px','40px','48px','56px','60px','64px','70px','80px','100px','120px','1100px','1140px','1200px','1280px','1320px'];
      return `<div class="ds-field"><label>${field.label}</label><select class="sec-select" data-key="${key}" onchange="onSectionSettingChange()">${sizes.map(s => `<option value="${s}" ${safeVal === s ? 'selected' : ''}>${s}</option>`).join('')}</select></div>`;
    case 'select':
      return `<div class="ds-field"><label>${field.label}</label><select class="sec-select" data-key="${key}" onchange="onSectionSettingChange()">${(field.options || []).map(o => `<option value="${o}" ${safeVal === o ? 'selected' : ''}>${o.charAt(0).toUpperCase() + o.slice(1)}</option>`).join('')}</select></div>`;
    case 'toggle':
      const checked = (value === true || value === 'true' || value === '1');
      return `<div class="ds-field" style="grid-column:1/-1;display:flex;align-items:center;gap:12px;padding:4px 0"><label style="flex:1;font-size:13px;font-weight:600;cursor:pointer">${field.label}</label><label class="toggle" style="margin:0"><input type="checkbox" class="sec-toggle" data-key="${key}" ${checked ? 'checked' : ''} onchange="onSectionSettingChange()"><span class="toggle-slider"></span></label></div>`;
    case 'image':
      return `<div class="ds-field ds-field-full"><label>${field.label}</label><div class="sec-upload-wrap"><div class="sec-upload-preview" id="sec-upload-preview-${key}">${safeVal ? `<img src="${safeVal}" style="max-width:100%;max-height:80px;border-radius:6px;object-fit:cover">` : '<span style="color:var(--text3)">No image</span>'}</div><button class="ds-btn ds-btn-ghost btn-sm" onclick="uploadSectionFile('${key}')" type="button"><i class="ti ti-upload"></i> ${safeVal ? 'Change' : 'Upload'}</button>${safeVal ? `<button class="ds-btn ds-btn-ghost btn-sm" onclick="removeSectionFile('${key}')" type="button" style="color:var(--red)"><i class="ti ti-trash"></i></button>` : ''}</div></div>`;
    case 'video':
      return `<div class="ds-field ds-field-full"><label>${field.label}</label><div class="sec-upload-wrap"><div class="sec-upload-preview" id="sec-upload-preview-${key}">${safeVal ? '<span style="font-size:12px;color:var(--text2)"><i class="ti ti-video"></i> Video uploaded</span>' : '<span style="color:var(--text3)">No video</span>'}</div><button class="ds-btn ds-btn-ghost btn-sm" onclick="uploadSectionFile('${key}')" type="button"><i class="ti ti-upload"></i> ${safeVal ? 'Change' : 'Upload'}</button>${safeVal ? `<button class="ds-btn ds-btn-ghost btn-sm" onclick="removeSectionFile('${key}')" type="button" style="color:var(--red)"><i class="ti ti-trash"></i></button>` : ''}</div></div>`;
    default:
      return `<div class="ds-field"><label>${field.label}</label><input type="text" class="sec-input" data-key="${key}" value="${safeVal}" oninput="onSectionSettingChange()"></div>`;
  }
}

function toHexColor(val) {
  if (!val) return '#000000';
  if (/^#[0-9a-f]{6}$/i.test(val)) return val;
  if (/^#[0-9a-f]{3}$/i.test(val)) return '#' + val[1]+val[1]+val[2]+val[2]+val[3]+val[3];
  const m = val.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
  if (m) return '#' + [m[1],m[2],m[3]].map(v => parseInt(v).toString(16).padStart(2, '0')).join('');
  return '#000000';
}

function onSectionSettingChange() {
  designDirty = true;
  collectSectionSettings();
  updateSectionStatus();
}

function onSectionColorChange(el) {
  const key = el.dataset.key;
  const txt = document.querySelector(`.sec-color-txt[data-key="${key}"]`);
  if (txt) txt.value = el.value;
  currentSectionSettings[key] = el.value;
  designDirty = true;
  updateSectionStatus();
}

function onSectionColorTextChange(el) {
  const key = el.dataset.key;
  const colorInput = document.querySelector(`.sec-color[data-key="${key}"]`);
  if (colorInput) colorInput.value = toHexColor(el.value);
  currentSectionSettings[key] = el.value;
  designDirty = true;
  updateSectionStatus();
}

function collectSectionSettings() {
  document.querySelectorAll('.sec-input').forEach(el => { currentSectionSettings[el.dataset.key] = el.value; });
  document.querySelectorAll('.sec-textarea').forEach(el => { currentSectionSettings[el.dataset.key] = el.value; });
  document.querySelectorAll('.sec-select').forEach(el => { currentSectionSettings[el.dataset.key] = el.value; });
  document.querySelectorAll('.sec-color').forEach(el => { currentSectionSettings[el.dataset.key] = el.value; });
  document.querySelectorAll('.sec-toggle').forEach(el => { currentSectionSettings[el.dataset.key] = el.checked; });
  const visToggle = document.getElementById('sec-visibility-toggle');
  if (visToggle) currentSectionSettings['is_visible'] = visToggle.checked;
}

function uploadSectionFile(key) {
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = 'image/*,video/*';
  input.onchange = function(e) {
    const file = e.target.files[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    const btn = document.querySelector(`[onclick="uploadSectionFile('${key}')"]`);
    if (btn) { btn.disabled = true; btn.innerHTML = '<i class="ti ti-loader"></i>Uploading...'; }
    fetch('/admin-panel/api/section-design/upload/', {
      method: 'POST',
      headers: { 'X-CSRFToken': csrftoken },
      body: formData
    })
      .then(r => r.json())
      .then(data => {
        if (data.success) {
          currentSectionSettings[key] = data.url;
          designDirty = true;
          updateSectionStatus();
          renderSectionSettings(currentDesignSection, currentSectionSettings);
          showToast('File uploaded!');
        } else {
          showToast(data.error || 'Upload failed', true);
        }
      })
      .catch(() => showToast('Upload failed', true))
      .finally(() => {
        if (btn) { btn.disabled = false; btn.innerHTML = '<i class="ti ti-upload"></i> Upload'; }
      });
  };
  input.click();
}

function removeSectionFile(key) {
  if (!confirm('Remove this file?')) return;
  currentSectionSettings[key] = '';
  designDirty = true;
  renderSectionSettings(currentDesignSection, currentSectionSettings);
  updateSectionStatus();
  showToast('File removed');
}


/* ===================================================================
 * 15. DESIGN STUDIO -- PAGE / SECTION SWITCHING
 * ===================================================================
 * Handles navigation between pages (landing vs dashboards vs auth)
 * and between sections within the landing page.
 * =================================================================== */

function switchDesignPage(pageName) {
  if (designDirty && currentDesignPage === 'landing') {
    if (!confirm('You have unsaved changes. Switch page anyway?')) return;
  }
  currentDesignPage = pageName;
  currentDesignSection = 'hero';
  designDirty = false;

  document.querySelectorAll('.design-page-tab').forEach(t => t.classList.remove('active'));
  const tab = document.querySelector(`.design-page-tab[data-page="${pageName}"]`);
  if (tab) tab.classList.add('active');

  const pageInfo = designPages.find(p => p.page_name === pageName);
  const label = pageInfo ? pageInfo.label : pageName;
  document.getElementById('design-current-page-label').textContent = label;

  if (pageName === 'landing') {
    document.getElementById('design-page-title').textContent = 'Home Page Design Manager';
    document.getElementById('design-page-sub').textContent = 'Customize every section of your Home page \u2014 text, colors, fonts, images, and layout';
    document.getElementById('section-editor-sidebar').style.display = 'block';
    document.getElementById('design-global-editor').style.display = 'none';
    document.getElementById('design-section-badge').style.display = 'flex';
    switchDesignSection('hero');
  } else {
    document.getElementById('design-page-title').textContent = 'Design: ' + label;
    document.getElementById('design-page-sub').textContent = 'Customize ' + label + ' appearance independently';
    document.getElementById('section-editor-sidebar').style.display = 'none';
    document.getElementById('design-global-editor').style.display = 'block';
    document.getElementById('design-section-badge').style.display = 'none';
    loadDesignPageSettings(pageName).then(pageData => {
      if (pageData) applyDesignSettingsToForm(pageData.settings);
      designDirty = false;
      updateSectionStatus();
    });
  }
  refreshDesignPreview();
}

function switchDesignPageSection(sectionName) {
  if (currentDesignPage !== 'landing') {
    currentDesignPage = 'landing';
    designDirty = false;
    document.getElementById('section-editor-sidebar').style.display = 'block';
    document.getElementById('design-global-editor').style.display = 'none';
    document.getElementById('design-section-badge').style.display = 'flex';
    document.getElementById('design-page-title').textContent = 'Home Page Design Manager';
    document.getElementById('design-page-sub').textContent = 'Customize every section of your Home page \u2014 text, colors, fonts, images, and layout';
  }
  switchDesignSection(sectionName);
}

function switchDesignSection(sectionName) {
  if (designDirty) {
    if (!confirm('You have unsaved changes in this section. Switch section anyway?')) return;
  }
  currentDesignSection = sectionName;
  designDirty = false;

  document.querySelectorAll('.ds-section-tab').forEach(t => t.classList.remove('active'));
  const sectionTab = document.querySelector(`.ds-section-tab[data-section="${sectionName}"]`);
  if (sectionTab) sectionTab.classList.add('active');

  document.querySelectorAll('.design-page-tab').forEach(t => t.classList.remove('active'));
  const sectionPageTab = document.querySelector(`.design-page-tab[data-section="${sectionName}"]`);
  if (sectionPageTab) sectionPageTab.classList.add('active');
  else {
    const pageTab = document.querySelector(`.design-page-tab[data-page="${currentDesignPage}"]`);
    if (pageTab) pageTab.classList.add('active');
  }

  const sectionLabels = {
    hero: 'Hero Section',
    how_it_works: 'How It Works Section',
    features: 'Features Section',
    statistics: 'Statistics Section',
    about: 'About Section',
    testimonials: 'Testimonials Section',
    cta: 'CTA Section',
    contact: 'Contact Section',
    footer: 'Footer Section',
  };
  document.getElementById('design-current-section-label').textContent =
    sectionLabels[sectionName] || sectionName.charAt(0).toUpperCase() + sectionName.slice(1) + ' Section';

  loadSectionSettings(sectionName).then(data => {
    if (data) renderSectionSettings(sectionName, data.settings || {});
    designDirty = false;
    updateSectionStatus();
  });
  refreshDesignPreview();
}


/* ===================================================================
 * 16. DESIGN STUDIO -- SAVE / RESET / PUBLISH
 * ===================================================================
 * API calls to persist section changes, reset to defaults, and
 * publish the current page design.
 * =================================================================== */

function saveDesignSection() {
  collectSectionSettings();
  const btn = document.getElementById('design-save-btn');
  btn.disabled = true;
  btn.innerHTML = '<i class="ti ti-loader"></i>Saving...';
  fetch('/admin-panel/api/section-design/' + currentDesignSection + '/save/?page=' + currentDesignPage, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrftoken },
    body: JSON.stringify({ settings: currentSectionSettings })
  })
    .then(r => r.json())
    .then(data => {
      btn.disabled = false;
      btn.innerHTML = '<i class="ti ti-device-floppy"></i> Save Changes';
      if (data.success) { showToast('Section settings saved!'); designDirty = false; updateSectionStatus(); refreshDesignPreview(); }
      else { showToast(data.error || 'Failed to save', true); }
    })
    .catch(() => { btn.disabled = false; btn.innerHTML = '<i class="ti ti-device-floppy"></i> Save Changes'; showToast('Network error', true); });
}

function resetDesignSection() {
  if (!confirm('Reset this section to default settings? This cannot be undone.')) return;
  const btn = document.getElementById('design-reset-btn');
  btn.disabled = true;
  btn.innerHTML = '<i class="ti ti-loader"></i>Resetting...';
  fetch('/admin-panel/api/section-design/' + currentDesignSection + '/reset/?page=' + currentDesignPage, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrftoken }
  })
    .then(r => r.json())
    .then(data => {
      btn.disabled = false;
      btn.innerHTML = '<i class="ti ti-history"></i> Reset Section';
      if (data.success) { showToast('Section reset to defaults!'); switchDesignSection(currentDesignSection); }
      else { showToast(data.error || 'Failed to reset', true); }
    })
    .catch(() => { btn.disabled = false; btn.innerHTML = '<i class="ti ti-history"></i> Reset Section'; showToast('Network error', true); });
}

function publishDesignPage() {
  const btn = document.getElementById('design-publish-btn');
  btn.disabled = true;
  btn.innerHTML = '<i class="ti ti-loader"></i>Publishing...';
  fetch('/admin-panel/api/page-design/' + currentDesignPage + '/publish/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrftoken }
  })
    .then(r => r.json())
    .then(data => {
      btn.disabled = false;
      btn.innerHTML = '<i class="ti ti-circle-check"></i> Publish';
      if (data.success) { showToast('Design published!'); loadDesignPages(); }
      else { showToast(data.error || 'Failed to publish', true); }
    })
    .catch(() => { btn.disabled = false; btn.innerHTML = '<i class="ti ti-circle-check"></i> Publish'; showToast('Network error', true); });
}


/* ===================================================================
 * 17. DESIGN STUDIO -- GLOBAL DESIGN (non-landing pages)
 * ===================================================================
 * For non-landing pages (auth, dashboards), renders the global CSS
 * variable editor with color, font, layout controls grouped by
 * category.  Supports quick theme presets.
 * =================================================================== */

function loadDesignPageSettings(pageName) {
  return fetch('/admin-panel/api/page-design/' + pageName + '/')
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        designSettingsCache[pageName] = data.page.settings;
        return data.page;
      }
      return null;
    });
}

function applyDesignSettingsToForm(settings) {
  document.querySelectorAll('.ds-clr').forEach(el => {
    const key = el.dataset.key;
    if (settings[key] !== undefined) {
      el.value = settings[key];
      const txt = document.querySelector(`.ds-clr-txt[data-key="${key}"]`);
      if (txt) txt.value = settings[key];
    }
  });
  document.querySelectorAll('.ds-clr-txt').forEach(el => {
    const key = el.dataset.key;
    const ci = document.querySelector(`.ds-clr[data-key="${key}"]`);
    if (ci) el.value = ci.value;
  });
  document.querySelectorAll('.ds-sel').forEach(el => {
    const key = el.dataset.key;
    if (settings[key] !== undefined) el.value = settings[key];
  });
}

function collectDesignSettings() {
  const settings = {};
  document.querySelectorAll('.ds-clr').forEach(el => { settings[el.dataset.key] = el.value; });
  document.querySelectorAll('.ds-sel').forEach(el => { settings[el.dataset.key] = el.value; });
  return settings;
}

function saveDesignPage() {
  const btn = document.getElementById('design-save-btn');
  btn.disabled = true;
  btn.innerHTML = '<i class="ti ti-loader"></i>Saving...';
  const settings = collectDesignSettings();
  fetch('/admin-panel/api/page-design/' + currentDesignPage + '/save/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrftoken },
    body: JSON.stringify({ settings: settings, apply_globally: false })
  })
    .then(r => r.json())
    .then(data => {
      btn.disabled = false;
      btn.innerHTML = '<i class="ti ti-device-floppy"></i> Save Changes';
      if (data.success) { showToast('Design settings saved!'); designDirty = false; updateSectionStatus(); refreshDesignPreview(); loadDesignPages(); }
      else { showToast(data.error || 'Failed to save', true); }
    })
    .catch(() => { btn.disabled = false; btn.innerHTML = '<i class="ti ti-device-floppy"></i> Save Changes'; showToast('Network error', true); });
}

function resetDesignPage() {
  if (!confirm('Reset all design settings for this page to defaults? This cannot be undone.')) return;
  const btn = document.getElementById('design-reset-btn');
  btn.disabled = true;
  btn.innerHTML = '<i class="ti ti-loader"></i>Resetting...';
  fetch('/admin-panel/api/page-design/' + currentDesignPage + '/reset/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrftoken }
  })
    .then(r => r.json())
    .then(data => {
      btn.disabled = false;
      btn.innerHTML = '<i class="ti ti-history"></i> Reset to Default';
      if (data.success) { showToast('Design reset to defaults!'); switchDesignPage(currentDesignPage); }
      else { showToast(data.error || 'Failed to reset', true); }
    })
    .catch(() => { btn.disabled = false; btn.innerHTML = '<i class="ti ti-history"></i> Reset to Default'; showToast('Network error', true); });
}


/* ===================================================================
 * 18. DESIGN STUDIO -- PREVIEW & THEMES
 * ===================================================================
 * Refreshes the live iframe preview and provides quick theme presets
 * that batch-change multiple color settings at once.
 * =================================================================== */

function refreshDesignPreview() {
  document.querySelectorAll('#preview-iframe, #preview-iframe2').forEach(iframe => {
    if (iframe) iframe.src = '/frontend/?t=' + Date.now() + '&page=' + currentDesignPage;
  });
}

function changePreviewDevice(device) {
  document.querySelectorAll('#design-preview-frame, #design-preview-frame2').forEach(frame => {
    frame.className = 'ds-preview-frame preview-' + device;
  });
}

const THEME_PRESETS = {
  modern:   { primary_color: '#6366f1', primary_dark: '#4f46e5', background_color: '#f8fafc', text_primary: '#1e293b', secondary_color: '#8b5cf6' },
  ocean:    { primary_color: '#0891b2', primary_dark: '#0e7490', background_color: '#ecfeff', text_primary: '#0f172a', secondary_color: '#06b6d4' },
  sunset:   { primary_color: '#f59e0b', primary_dark: '#d97706', background_color: '#fffbeb', text_primary: '#1c1917', secondary_color: '#f97316' },
  forest:   { primary_color: '#059669', primary_dark: '#047857', background_color: '#f0fdf4', text_primary: '#052e16', secondary_color: '#10b981' },
  midnight: { primary_color: '#3b82f6', primary_dark: '#2563eb', background_color: '#0f172a', text_primary: '#f1f5f9', secondary_color: '#6366f1' },
};

function applyThemePreset(themeName) {
  const preset = THEME_PRESETS[themeName];
  if (!preset) return;
  for (const [key, value] of Object.entries(preset)) {
    const ci = document.querySelector(`.ds-clr[data-key="${key}"]`);
    const ti = document.querySelector(`.ds-clr-txt[data-key="${key}"]`);
    if (ci) ci.value = value;
    if (ti) ti.value = value;
  }
  designDirty = true;
  updateSectionStatus();
  showToast('Theme applied! Save to keep changes.');
}


/* ===================================================================
 * 19. DESIGN STUDIO -- UI HELPERS
 * ===================================================================
 * Collapse/expand categories, update status indicators, and filter
 * settings by keyboard search.
 * =================================================================== */

function toggleDesignCategory(header) {
  const body = header.nextElementSibling;
  const icon = header.querySelector('.ti-chevron-down');
  if (body && icon) {
    body.classList.toggle('open');
    icon.style.transform = body.classList.contains('open') ? 'rotate(0deg)' : 'rotate(-90deg)';
  }
}

function updateSectionStatus() {
  const statusEl = document.getElementById('design-status');
  if (statusEl) {
    const label = document.getElementById('design-current-page-label').textContent;
    statusEl.innerHTML = '<i class="ti ti-info-circle"></i> Editing: <strong>' + label + '</strong>'
      + (designDirty ? ' <span style="color:var(--amber)">(unsaved)</span>' : '');
  }
  document.querySelectorAll('#preview-status-badge, #preview-status-badge2').forEach(badge => {
    if (badge) {
      badge.className = 'ds-preview-badge ' + (designDirty ? 'unsaved' : 'saved');
      badge.innerHTML = designDirty
        ? '<i class="ti ti-info-circle"></i> Unsaved changes'
        : '<i class="ti ti-check-circle"></i> All changes saved';
    }
  });
}

function filterSectionSettings(query) {
  const q = query.toLowerCase().trim();
  document.querySelectorAll('#sec-controls-scroll .ds-group').forEach(g => {
    g.style.display = (!q || g.textContent.toLowerCase().includes(q)) ? '' : 'none';
  });
}

function filterDesignSettings(query) {
  const q = query.toLowerCase().trim();
  document.querySelectorAll('#ds-controls-scroll .ds-group').forEach(g => {
    g.style.display = (!q || g.textContent.toLowerCase().includes(q)) ? '' : 'none';
  });
}


/* ===================================================================
 * 20. DESIGN STUDIO -- INIT
 * ===================================================================
 * One-time setup when the user first opens the Design Studio panel.
 * Loads page list, resets state, and renders the hero section.
 * =================================================================== */

function initDesignManager() {
  currentDesignPage = 'landing';
  currentDesignSection = 'hero';
  document.querySelectorAll('.design-page-tab').forEach(t => t.classList.remove('active'));
  const firstTab = document.querySelector('.design-topbar-nav-inner .design-page-tab[data-page="landing"]');
  if (firstTab) firstTab.classList.add('active');
  loadDesignPages().then(() => {
    document.getElementById('section-editor-sidebar').style.display = 'block';
    document.getElementById('design-global-editor').style.display = 'none';
    document.getElementById('design-section-badge').style.display = 'flex';
    document.getElementById('design-page-title').textContent = 'Home Page Design Manager';
    document.getElementById('design-page-sub').textContent = 'Customize every section of your Home page \u2014 text, colors, fonts, images, and layout';
    switchDesignSection('hero');
  });
}


/* ===================================================================
 * 21. INIT -- Run on page load
 * ===================================================================
 * Pre-loads contact messages, categories, support tickets, and
 * notification count so the sidebar badges are populated before
 * the user navigates.
 * =================================================================== */

document.addEventListener('DOMContentLoaded', function() {
  loadContactMessages();
  loadCategories();
  loadSupportTickets();
  updateUnreadCount();
});
