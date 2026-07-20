/* ═══════════════════════════════════════════════════
   𝕏 Admin Panel — Premium JS v2
   ═══════════════════════════════════════════════════ */
'use strict';

const tg    = window.Telegram?.WebApp;
const ADMIN = 8989271393;
const toast = document.getElementById('toast');
let toastT  = null;
let accountsData = [];

if (tg) { tg.ready(); tg.expand(); }

// ── Auth ──────────────────────────────────────────────
(function auth() {
  if (!tg) { reveal(); return; }          // dev / browser mode — bypass
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

// ── Tab Navigation ────────────────────────────────────
document.querySelectorAll('.nav-link').forEach(link => {
  link.addEventListener('click', () => switchTab(link.dataset.tab));
});

function switchTab(name) {
  document.querySelectorAll('.nav-link').forEach(l => {
    l.classList.toggle('active', l.dataset.tab === name);
  });
  document.querySelectorAll('.tab').forEach(t => {
    t.classList.toggle('active', t.id === `tab-${name}`);
  });
}

// ── API helper ────────────────────────────────────────
function initData() { return tg?.initData || ''; }

async function api(url, opts = {}) {
  if (!opts.headers) opts.headers = {};
  opts.headers['X-Init-Data'] = initData();
  const res  = await fetch(url, opts);
  const json = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(json.error || json.message || `HTTP ${res.status}`);
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

    const ba = document.getElementById('navBadgeAccounts');
    const bo = document.getElementById('navBadgeOrders');
    if (ba && s.available > 0) { ba.textContent = s.available; ba.classList.add('show'); }
    if (bo && s.total_orders > 0) { bo.textContent = s.total_orders; bo.classList.add('show'); }
  } catch (e) { showToast('⚠️ تعذّر تحميل الإحصائيات'); }
}
function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

// ── Accounts ──────────────────────────────────────────
async function loadAccounts() {
  try {
    accountsData = await api('/api/admin/accounts');
    renderAccounts(accountsData);
  } catch (e) { showToast('⚠️ تعذّر تحميل الحسابات'); }
}

function renderAccounts(list) {
  const tbody = document.getElementById('accountsTbody');
  const empty = document.getElementById('accountsEmpty');
  if (!list.length) {
    tbody.innerHTML = '';
    empty.classList.remove('hidden');
    return;
  }
  empty.classList.add('hidden');
  tbody.innerHTML = list.map(a => `
    <tr data-id="${a.id}">
      <td style="color:var(--text-3);font-size:.8rem">#${a.id}</td>
      <td style="font-weight:600;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(a.name)}</td>
      <td style="color:var(--text-2)">${a.creation_year || '—'}</td>
      <td style="font-weight:700;color:var(--blue)">$${Number(a.price).toFixed(2)}</td>
      <td><span class="spill sp-${a.status}">${statusLabel(a.status)}</span></td>
      <td style="color:var(--text-3);font-size:.8rem">${esc(a.category || 'twitter')}</td>
      <td>
        <div class="action-row">
          <button class="act-btn act-edit" onclick="openEdit(${a.id})">✏️ تعديل</button>
          <button class="act-btn act-sold" onclick="markSold(${a.id})">✅ بيع</button>
          <button class="act-btn act-del"  onclick="delAccount(${a.id})">🗑️</button>
        </div>
      </td>
    </tr>`).join('');
}

function statusLabel(s) {
  return { available: 'متاح', sold: 'مباع', reserved: 'محجوز' }[s] || s;
}

document.getElementById('accountSearch').addEventListener('input', function () {
  const q = this.value.trim().toLowerCase();
  renderAccounts(accountsData.filter(a =>
    a.name.toLowerCase().includes(q) ||
    String(a.creation_year || '').includes(q) ||
    (a.status || '').includes(q) ||
    (a.category || '').toLowerCase().includes(q)
  ));
});

async function markSold(id) {
  if (!confirm('تعيين هذا الحساب كمباع؟')) return;
  try {
    const fd = new FormData();
    fd.append('status', 'sold');
    fd.append('initData', initData());
    await api(`/api/admin/accounts/${id}`, { method: 'PUT', body: fd });
    showToast('✅ تم تعيينه مباعاً');
    await Promise.all([loadAccounts(), loadStats()]);
  } catch (e) { showToast('❌ ' + e.message); }
}

async function delAccount(id) {
  if (!confirm('حذف هذا الحساب نهائياً؟')) return;
  try {
    await api(`/api/admin/accounts/${id}`, { method: 'DELETE' });
    showToast('🗑️ تم الحذف');
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
function setVal(id, v) {
  const el = document.getElementById(id);
  if (el) el.value = v;
}

function closeEdit() {
  document.getElementById('editModal').classList.add('hidden');
}
document.getElementById('editClose').addEventListener('click', closeEdit);
document.getElementById('editCancel').addEventListener('click', closeEdit);
document.getElementById('editModal').addEventListener('click', e => {
  if (e.target.id === 'editModal') closeEdit();
});

document.getElementById('editForm').addEventListener('submit', async function (e) {
  e.preventDefault();
  const id  = document.getElementById('editId').value;
  const fd  = new FormData(this);
  fd.append('initData', initData());
  try {
    await api(`/api/admin/accounts/${id}`, { method: 'PUT', body: fd });
    showToast('💾 تم الحفظ بنجاح');
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

// Click to upload
dropContent.addEventListener('click', () => imageInput.click());

// Drag & drop
dropZone.addEventListener('dragover',  e => { e.preventDefault(); dropZone.classList.add('drag-over'); });
dropZone.addEventListener('dragleave', ()  => dropZone.classList.remove('drag-over'));
dropZone.addEventListener('drop', e => {
  e.preventDefault();
  dropZone.classList.remove('drag-over');
  const file = e.dataTransfer.files[0];
  if (file) { imageInput.files = e.dataTransfer.files; showPreview(file); }
});
imageInput.addEventListener('change', () => {
  if (imageInput.files[0]) showPreview(imageInput.files[0]);
});

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
  document.getElementById('addForm').reset();
  imageInput.value = '';
  previewImg.src   = '';
  imagePreview.classList.add('hidden');
  dropContent.classList.remove('hidden');
  addResult.classList.add('hidden');
});

document.getElementById('addForm').addEventListener('submit', async function (e) {
  e.preventDefault();
  const btn = document.getElementById('addSubmitBtn');
  btn.disabled = true;
  btn.innerHTML = '<span style="opacity:.6">⏳ جاري الإضافة…</span>';

  const fd = new FormData(this);
  fd.append('initData', initData());
  try {
    const data = await api('/api/admin/accounts', { method: 'POST', body: fd });
    addResult.textContent = `✅ تمت إضافة الحساب #${data.id} بنجاح!`;
    addResult.className   = 'form-feedback feedback-ok';
    addResult.classList.remove('hidden');
    this.reset();
    imagePreview.classList.add('hidden');
    dropContent.classList.remove('hidden');
    showToast('✅ تمت الإضافة بنجاح!');
    await Promise.all([loadAccounts(), loadStats()]);
  } catch (err) {
    addResult.textContent = '❌ ' + err.message;
    addResult.className   = 'form-feedback feedback-err';
    addResult.classList.remove('hidden');
    showToast('❌ ' + err.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/></svg> إضافة الحساب`;
  }
});

// ── Orders ────────────────────────────────────────────
async function loadOrders() {
  try {
    const orders = await api('/api/admin/orders');
    renderOrders(orders);
  } catch (e) { showToast('⚠️ تعذّر تحميل الطلبات'); }
}

function renderOrders(orders) {
  const tbody = document.getElementById('ordersTbody');
  const empty = document.getElementById('ordersEmpty');
  if (!orders.length) {
    tbody.innerHTML = '';
    empty.classList.remove('hidden');
    return;
  }
  empty.classList.add('hidden');

  const statuses = ['pending', 'paid', 'completed', 'cancelled'];
  const stLabel  = { pending: 'قيد الانتظار', paid: 'مدفوع', completed: 'مكتمل', cancelled: 'ملغي' };

  tbody.innerHTML = orders.map(o => `
    <tr>
      <td style="color:var(--text-3);font-size:.8rem">#${o.id}</td>
      <td style="font-weight:600;max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(o.account_name || '—')}</td>
      <td>
        <div style="font-weight:600">@${esc(o.buyer_username || 'unknown')}</div>
        <div style="font-size:.72rem;color:var(--text-3)">${o.buyer_id}</div>
      </td>
      <td><span class="spill sp-${o.status}">${stLabel[o.status] || o.status}</span></td>
      <td style="color:var(--text-3);font-size:.8rem">${fmtDate(o.created_at)}</td>
      <td>
        <select class="status-sel" onchange="updateOrder(${o.id}, this.value)">
          ${statuses.map(s =>
            `<option value="${s}"${s === o.status ? ' selected' : ''}>${stLabel[s]}</option>`
          ).join('')}
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
    showToast(`📋 الطلب #${id} → ${status}`);
    loadStats();
  } catch (e) { showToast('❌ ' + e.message); }
}

// ── Helpers ───────────────────────────────────────────
function esc(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function fmtDate(ts) {
  if (!ts) return '—';
  return new Date(ts).toLocaleDateString('ar-SA', {
    day: '2-digit', month: 'short', year: 'numeric'
  });
}

function showToast(msg, dur = 3500) {
  toast.textContent = msg;
  toast.classList.add('show');
  clearTimeout(toastT);
  toastT = setTimeout(() => toast.classList.remove('show'), dur);
}

// ── Auto-refresh every 60 s ───────────────────────────
setInterval(loadStats, 60_000);
