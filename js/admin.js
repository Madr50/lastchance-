/* ═══════════════════════════════════════════════════
   𝕏 Admin Panel — Premium JS
   ═══════════════════════════════════════════════════ */

const tg     = window.Telegram?.WebApp;
const ADMIN  = 8989271393;
const toast  = document.getElementById('toast');
let toastT   = null;
let accountsData = [];

if (tg) { tg.ready(); tg.expand(); }

// ── Auth ──────────────────────────────────────────────
(function auth() {
  if (!tg) { reveal(); return; }                      // dev / browser preview
  const user = tg.initDataUnsafe?.user;
  if (!user || Number(user.id) !== ADMIN) {
    document.getElementById('accessDenied').classList.remove('hidden');
    return;
  }
  reveal();
})();

function reveal() {
  document.getElementById('adminApp').classList.remove('hidden');
  loadStats();
  loadAccounts();
  loadOrders();
}

// ── Nav tabs ──────────────────────────────────────────
document.querySelectorAll('.nav-link').forEach(link => {
  link.addEventListener('click', () => {
    document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    link.classList.add('active');
    document.getElementById(`tab-${link.dataset.tab}`).classList.add('active');
  });
});

// ── API helper ────────────────────────────────────────
function initData() { return tg?.initData || ''; }

async function api(url, opts = {}) {
  if (!opts.headers) opts.headers = {};
  opts.headers['X-Init-Data'] = initData();
  const res  = await fetch(url, opts);
  const json = await res.json();
  if (!res.ok) throw new Error(json.error || json.message || 'Request failed');
  return json;
}

// ── Stats ─────────────────────────────────────────────
async function loadStats() {
  try {
    const s = await api('/api/admin/stats');
    setText('statTotal',    s.total);
    setText('statAvail',    s.available);
    setText('statSold',     s.sold);
    setText('statReserved', s.reserved);
    setText('statRev',      '$' + Number(s.revenue).toFixed(2));
    setText('statOrders',   s.total_orders);

    // Nav badges
    const ba = document.getElementById('navBadgeAccounts');
    const bo = document.getElementById('navBadgeOrders');
    if (s.available > 0) { ba.textContent = s.available; ba.classList.add('show'); }
    if (s.total_orders > 0) { bo.textContent = s.total_orders; bo.classList.add('show'); }
  } catch (e) { showToast('⚠️ Could not load stats'); }
}
function setText(id, val) { const el = document.getElementById(id); if (el) el.textContent = val; }

// ── Accounts ──────────────────────────────────────────
async function loadAccounts() {
  try {
    accountsData = await api('/api/admin/accounts');
    renderAccounts(accountsData);
  } catch (e) { showToast('⚠️ Could not load accounts'); }
}

function renderAccounts(list) {
  const tbody = document.getElementById('accountsTbody');
  const empty = document.getElementById('accountsEmpty');
  if (!list.length) { tbody.innerHTML = ''; empty.classList.remove('hidden'); return; }
  empty.classList.add('hidden');
  tbody.innerHTML = list.map(a => `
    <tr data-id="${a.id}">
      <td style="color:var(--text-3)">#${a.id}</td>
      <td style="font-weight:600;max-width:180px;overflow:hidden;text-overflow:ellipsis">${esc(a.name)}</td>
      <td>${a.creation_year || '—'}</td>
      <td style="font-weight:700;color:var(--blue)">$${Number(a.price).toFixed(2)}</td>
      <td><span class="spill sp-${a.status}">${a.status}</span></td>
      <td style="color:var(--text-3)">${esc(a.category)}</td>
      <td>
        <div class="action-row">
          <button class="act-btn act-edit"  onclick="openEdit(${a.id})">✏️ Edit</button>
          <button class="act-btn act-sold"  onclick="markSold(${a.id})">✅ Sold</button>
          <button class="act-btn act-del"   onclick="delAccount(${a.id})">🗑️</button>
        </div>
      </td>
    </tr>`).join('');
}

document.getElementById('accountSearch').addEventListener('input', function() {
  const q = this.value.trim().toLowerCase();
  renderAccounts(accountsData.filter(a =>
    a.name.toLowerCase().includes(q) ||
    String(a.creation_year || '').includes(q) ||
    a.status.includes(q) ||
    (a.category || '').includes(q)
  ));
});

async function markSold(id) {
  if (!confirm('Mark this account as sold?')) return;
  try {
    const fd = new FormData(); fd.append('status','sold'); fd.append('initData', initData());
    await api(`/api/admin/accounts/${id}`, { method: 'PUT', body: fd });
    showToast('✅ Marked as sold');
    await Promise.all([loadAccounts(), loadStats()]);
  } catch (e) { showToast('❌ ' + e.message); }
}

async function delAccount(id) {
  if (!confirm('Delete this account permanently?')) return;
  try {
    await api(`/api/admin/accounts/${id}`, { method: 'DELETE' });
    showToast('🗑️ Deleted');
    await Promise.all([loadAccounts(), loadStats()]);
  } catch (e) { showToast('❌ ' + e.message); }
}

// ── Edit Modal ────────────────────────────────────────
function openEdit(id) {
  const a = accountsData.find(x => x.id === id);
  if (!a) return;
  setVal('editId',     a.id);
  setVal('editName',   a.name);
  setVal('editPrice',  a.price);
  setVal('editYear',   a.creation_year || '');
  setVal('editStatus', a.status);
  setVal('editDesc',   a.description || '');
  document.getElementById('editModal').classList.remove('hidden');
}
function setVal(id, v) { const el = document.getElementById(id); if (el) el.value = v; }

function closeEdit() { document.getElementById('editModal').classList.add('hidden'); }
document.getElementById('editClose').addEventListener('click', closeEdit);
document.getElementById('editCancel').addEventListener('click', closeEdit);
document.getElementById('editModal').addEventListener('click', e => { if (e.target.id === 'editModal') closeEdit(); });

document.getElementById('editForm').addEventListener('submit', async function(e) {
  e.preventDefault();
  const id = document.getElementById('editId').value;
  const fd = new FormData(this);
  fd.append('initData', initData());
  try {
    await api(`/api/admin/accounts/${id}`, { method: 'PUT', body: fd });
    showToast('💾 Saved');
    closeEdit();
    await Promise.all([loadAccounts(), loadStats()]);
  } catch (err) { showToast('❌ ' + err.message); }
});

// ── Add Form ──────────────────────────────────────────
const dropZone     = document.getElementById('dropZone');
const imageInput   = document.getElementById('imageInput');
const dropContent  = document.getElementById('dropContent');
const imagePreview = document.getElementById('imagePreview');
const previewImg   = document.getElementById('previewImg');
const removePreview= document.getElementById('removePreview');
const addResult    = document.getElementById('addResult');

// Drag & drop
dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('drag-over'); });
dropZone.addEventListener('dragleave',()  => dropZone.classList.remove('drag-over'));
dropZone.addEventListener('drop', e => {
  e.preventDefault(); dropZone.classList.remove('drag-over');
  const file = e.dataTransfer.files[0];
  if (file) { imageInput.files = e.dataTransfer.files; showPreview(file); }
});
imageInput.addEventListener('change', () => { if (imageInput.files[0]) showPreview(imageInput.files[0]); });

function showPreview(file) {
  const reader = new FileReader();
  reader.onload = ev => {
    previewImg.src = ev.target.result;
    dropContent.classList.add('hidden');
    imagePreview.classList.remove('hidden');
  };
  reader.readAsDataURL(file);
}
removePreview.addEventListener('click', () => {
  imageInput.value = '';
  previewImg.src   = '';
  imagePreview.classList.add('hidden');
  dropContent.classList.remove('hidden');
});

document.getElementById('resetBtn').addEventListener('click', () => {
  imageInput.value = '';
  previewImg.src   = '';
  imagePreview.classList.add('hidden');
  dropContent.classList.remove('hidden');
  addResult.classList.add('hidden');
});

document.getElementById('addForm').addEventListener('submit', async function(e) {
  e.preventDefault();
  const btn = document.getElementById('addSubmitBtn');
  btn.disabled = true; btn.textContent = '⏳ Adding…';

  const fd = new FormData(this);
  fd.append('initData', initData());
  try {
    const data = await api('/api/admin/accounts', { method: 'POST', body: fd });
    addResult.textContent = `✅ Account #${data.id} added successfully!`;
    addResult.className   = 'form-feedback feedback-ok';
    addResult.classList.remove('hidden');
    this.reset();
    imagePreview.classList.add('hidden');
    dropContent.classList.remove('hidden');
    showToast('✅ Account added!');
    await Promise.all([loadAccounts(), loadStats()]);
  } catch (err) {
    addResult.textContent = '❌ ' + err.message;
    addResult.className   = 'form-feedback feedback-err';
    addResult.classList.remove('hidden');
    showToast('❌ ' + err.message);
  } finally {
    btn.disabled = false; btn.textContent = '➕ Add Account';
  }
});

// ── Orders ────────────────────────────────────────────
async function loadOrders() {
  try {
    const orders = await api('/api/admin/orders');
    renderOrders(orders);
  } catch (e) { showToast('⚠️ Could not load orders'); }
}

function renderOrders(orders) {
  const tbody = document.getElementById('ordersTbody');
  const empty = document.getElementById('ordersEmpty');
  if (!orders.length) { tbody.innerHTML = ''; empty.classList.remove('hidden'); return; }
  empty.classList.add('hidden');

  const statuses = ['pending','paid','completed','cancelled'];
  tbody.innerHTML = orders.map(o => `
    <tr>
      <td style="color:var(--text-3)">#${o.id}</td>
      <td style="font-weight:600;max-width:160px;overflow:hidden;text-overflow:ellipsis">${esc(o.account_name || '—')}</td>
      <td>@${esc(o.buyer_username || 'unknown')}<br/><small style="color:var(--text-3)">${o.buyer_id}</small></td>
      <td><span class="spill sp-${o.status}">${o.status}</span></td>
      <td style="color:var(--text-3)">${fmtDate(o.created_at)}</td>
      <td>
        <select class="status-sel" onchange="updateOrder(${o.id}, this.value)">
          ${statuses.map(s=>`<option value="${s}"${s===o.status?' selected':''}>${s}</option>`).join('')}
        </select>
      </td>
    </tr>`).join('');
}

async function updateOrder(id, status) {
  try {
    await api(`/api/admin/orders/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', 'X-Init-Data': initData() },
      body: JSON.stringify({ status })
    });
    showToast(`📋 Order #${id} → ${status}`);
    loadStats();
  } catch (e) { showToast('❌ ' + e.message); }
}

// ── Helpers ───────────────────────────────────────────
function esc(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function fmtDate(ts) {
  if (!ts) return '—';
  return new Date(ts).toLocaleDateString('en-GB',{day:'2-digit',month:'short',year:'numeric'});
}
function showToast(msg, dur = 3500) {
  toast.textContent = msg;
  toast.classList.add('show');
  clearTimeout(toastT);
  toastT = setTimeout(() => toast.classList.remove('show'), dur);
}

// Auto-refresh stats every 60s
setInterval(loadStats, 60_000);
