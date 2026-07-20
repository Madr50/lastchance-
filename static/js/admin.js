/* ═══════════════════════════════════════════════════
   𝕏 Admin Panel — v3 Pro
   ═══════════════════════════════════════════════════ */
'use strict';

const tg    = window.Telegram?.WebApp;
const ADMIN = 8989271393;
const toast = document.getElementById('toast');
let toastT  = null;
let accountsData = [];
let currentFilter = 'all';

if (tg) { tg.ready(); tg.expand(); }

// ── Auth Flow ─────────────────────────────────────────
(async function initAuth() {
  // 1) Telegram WebApp with real initData (actually inside Telegram)
  if (tg && tg.initData) {
    const user = tg.initDataUnsafe?.user;
    if (!user || Number(user.id) !== ADMIN) {
      document.getElementById('accessDenied').classList.remove('hidden');
      return;
    }
    reveal();
    return;
  }

  // 2) Browser — check existing session first
  try {
    const res = await fetch('/api/admin/check');
    if (res.ok) {
      reveal();
      return;
    }
  } catch (_) {}

  // 3) Show login screen
  showLogin();
})();

function showLogin() {
  document.getElementById('loginScreen').classList.remove('hidden');
  setTimeout(() => document.getElementById('loginPass').focus(), 100);
}

function reveal() {
  document.getElementById('loginScreen').classList.add('hidden');
  document.getElementById('adminApp').classList.remove('hidden');
  loadStats();
  loadAccounts();
  loadOrders();
}

// Login form
document.getElementById('loginForm').addEventListener('submit', async function(e) {
  e.preventDefault();
  const btn     = document.getElementById('loginBtn');
  const btnText = document.getElementById('loginBtnText');
  const btnLoad = document.getElementById('loginBtnLoad');
  const err     = document.getElementById('loginErr');
  const pass    = document.getElementById('loginPass').value;

  btn.disabled  = true;
  btnText.classList.add('hidden');
  btnLoad.classList.remove('hidden');
  err.classList.add('hidden');

  try {
    const res  = await fetch('/api/admin/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password: pass })
    });
    if (res.ok) {
      reveal();
    } else {
      err.classList.remove('hidden');
      document.getElementById('loginPass').value = '';
      document.getElementById('loginPass').focus();
    }
  } catch (_) {
    err.textContent = '❌ خطأ في الاتصال بالخادم';
    err.classList.remove('hidden');
  } finally {
    btn.disabled = false;
    btnText.classList.remove('hidden');
    btnLoad.classList.add('hidden');
  }
});

// Toggle password visibility
document.getElementById('togglePass').addEventListener('click', function() {
  const inp = document.getElementById('loginPass');
  const open = document.getElementById('eyeOpen');
  const closed = document.getElementById('eyeClosed');
  if (inp.type === 'password') {
    inp.type = 'text';
    open.classList.add('hidden');
    closed.classList.remove('hidden');
  } else {
    inp.type = 'password';
    open.classList.remove('hidden');
    closed.classList.add('hidden');
  }
});

// Logout
async function logout() {
  try { await fetch('/api/admin/logout', { method: 'POST' }); } catch (_) {}
  location.reload();
}
document.getElementById('logoutBtn').addEventListener('click', logout);
document.getElementById('logoutBtnMobile').addEventListener('click', logout);

// ── Mobile Sidebar ────────────────────────────────────
const sidebar        = document.getElementById('sidebar');
const sidebarOverlay = document.getElementById('sidebarOverlay');
const menuBtn        = document.getElementById('menuBtn');

menuBtn.addEventListener('click', () => {
  sidebar.classList.toggle('open');
  sidebarOverlay.classList.toggle('hidden');
});
sidebarOverlay.addEventListener('click', closeSidebar);
function closeSidebar() {
  sidebar.classList.remove('open');
  sidebarOverlay.classList.add('hidden');
}

// ── Tab Navigation ────────────────────────────────────
document.querySelectorAll('.nav-link').forEach(link => {
  link.addEventListener('click', () => {
    switchTab(link.dataset.tab);
    closeSidebar();
  });
});

function switchTab(name) {
  document.querySelectorAll('.nav-link').forEach(l =>
    l.classList.toggle('active', l.dataset.tab === name)
  );
  document.querySelectorAll('.tab').forEach(t =>
    t.classList.toggle('active', t.id === `tab-${name}`)
  );
}

// ── API helper ────────────────────────────────────────
function initData() { return tg?.initData || ''; }

async function api(url, opts = {}) {
  if (!opts.headers) opts.headers = {};
  const iData = initData();
  if (iData) opts.headers['X-Init-Data'] = iData;
  const res  = await fetch(url, opts);
  const json = await res.json().catch(() => ({}));
  if (!res.ok) {
    if (res.status === 403) {
      showLogin();
      document.getElementById('adminApp').classList.add('hidden');
      throw new Error('يرجى تسجيل الدخول مجدداً');
    }
    throw new Error(json.error || json.message || `HTTP ${res.status}`);
  }
  return json;
}

// ── Refresh all ────────────────────────────────────────
function refreshAll() {
  loadStats();
  loadAccounts();
  loadOrders();
  showToast('🔄 تم التحديث', 2000);
}

// ── Stats ─────────────────────────────────────────────
async function loadStats() {
  try {
    const s = await api('/api/admin/stats');
    animateNumber('statTotal',    s.total);
    animateNumber('statAvail',    s.available);
    animateNumber('statSold',     s.sold);
    animateNumber('statReserved', s.reserved);
    setText('statRev', '$' + Number(s.revenue).toFixed(2));
    animateNumber('statOrders',   s.total_orders);

    const ba = document.getElementById('navBadgeAccounts');
    const bo = document.getElementById('navBadgeOrders');
    if (ba) {
      if (s.available > 0) { ba.textContent = s.available; ba.classList.add('show'); }
      else ba.classList.remove('show');
    }
    if (bo) {
      if (s.total_orders > 0) { bo.textContent = s.total_orders; bo.classList.add('show'); }
      else bo.classList.remove('show');
    }
  } catch (e) {
    if (!e.message.includes('تسجيل')) showToast('⚠️ تعذّر تحميل الإحصائيات');
  }
}

function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

function animateNumber(id, target) {
  const el = document.getElementById(id);
  if (!el) return;
  const start   = parseInt(el.textContent) || 0;
  const end     = Number(target) || 0;
  const dur     = 600;
  const startTs = performance.now();
  function step(ts) {
    const progress = Math.min((ts - startTs) / dur, 1);
    const ease     = 1 - Math.pow(1 - progress, 3);
    el.textContent = Math.round(start + (end - start) * ease);
    if (progress < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

// ── Accounts ──────────────────────────────────────────
async function loadAccounts() {
  try {
    accountsData = await api('/api/admin/accounts');
    renderAccounts(getFilteredAccounts());
  } catch (e) {
    if (!e.message.includes('تسجيل')) showToast('⚠️ تعذّر تحميل الحسابات');
  }
}

function getFilteredAccounts() {
  const q = (document.getElementById('accountSearch')?.value || '').trim().toLowerCase();
  return accountsData.filter(a => {
    const matchFilter = currentFilter === 'all' || a.status === currentFilter;
    const matchSearch = !q ||
      a.name.toLowerCase().includes(q) ||
      String(a.creation_year || '').includes(q) ||
      (a.status || '').includes(q) ||
      (a.category || '').toLowerCase().includes(q);
    return matchFilter && matchSearch;
  });
}

function renderAccounts(list) {
  const grid  = document.getElementById('accountsGrid');
  const empty = document.getElementById('accountsEmpty');
  if (!list.length) {
    grid.innerHTML = '';
    empty.classList.remove('hidden');
    return;
  }
  empty.classList.add('hidden');
  grid.innerHTML = list.map(a => `
    <div class="acc-card sp-border-${a.status}" data-id="${a.id}">
      <div class="acc-card-img">
        ${a.image
          ? `<img src="${esc(a.image)}" alt="${esc(a.name)}" loading="lazy"/>`
          : `<div class="acc-img-placeholder">𝕏</div>`}
        <span class="acc-status-pill sp-${a.status}">${statusLabel(a.status)}</span>
      </div>
      <div class="acc-card-body">
        <div class="acc-card-name">${esc(a.name)}</div>
        <div class="acc-card-meta">
          <span class="acc-year">${a.creation_year ? '📅 ' + a.creation_year : ''}</span>
          <span class="acc-cat">${catIcon(a.category)} ${catLabel(a.category)}</span>
        </div>
        ${a.description ? `<div class="acc-desc">${esc(a.description.substring(0,80))}${a.description.length>80?'…':''}</div>` : ''}
        <div class="acc-price">${Number(a.price).toFixed(2)}</div>
      </div>
      <div class="acc-card-actions">
        <button class="acc-act-btn acc-act-edit" onclick="openEdit(${a.id})">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
          تعديل
        </button>
        <button class="acc-act-btn acc-act-sell" onclick="markSold(${a.id})" ${a.status==='sold'?'disabled':''}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
          ${a.status==='sold' ? 'مباع' : 'تعيين مباع'}
        </button>
        <button class="acc-act-btn acc-act-del" onclick="confirmDelete(${a.id})">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>
          حذف
        </button>
      </div>
    </div>`).join('');
}

function catIcon(c) {
  return { twitter:'🐦', aged:'🕰️', verified:'✅', other:'📌' }[c] || '📌';
}
function catLabel(c) {
  return { twitter:'Twitter/X', aged:'Aged', verified:'Verified', other:'أخرى' }[c] || c || 'Twitter/X';
}
function statusLabel(s) {
  return { available:'متاح', sold:'مباع', reserved:'محجوز' }[s] || s;
}

// Search + Filter chips
document.getElementById('accountSearch').addEventListener('input', () => renderAccounts(getFilteredAccounts()));

document.querySelectorAll('.chip').forEach(chip => {
  chip.addEventListener('click', () => {
    document.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
    chip.classList.add('active');
    currentFilter = chip.dataset.filter;
    renderAccounts(getFilteredAccounts());
  });
});

async function markSold(id) {
  confirmAction({
    title: 'تعيين مباعاً؟',
    msg: 'سيتم تغيير حالة الحساب إلى "مباع" — هذا الإجراء قابل للتعديل.',
    icon: '✅',
    okText: 'نعم، بيع',
    onOk: async () => {
      try {
        const fd = new FormData();
        fd.append('status', 'sold');
        await api(`/api/admin/accounts/${id}`, { method: 'PUT', body: fd });
        showToast('✅ تم تعيينه مباعاً بنجاح');
        await Promise.all([loadAccounts(), loadStats()]);
      } catch (e) { showToast('❌ ' + e.message); }
    }
  });
}

function confirmDelete(id) {
  confirmAction({
    title: 'حذف الحساب؟',
    msg: 'سيتم حذف الحساب نهائياً ولا يمكن التراجع عن هذا الإجراء.',
    icon: '🗑️',
    okText: 'حذف نهائي',
    danger: true,
    onOk: async () => {
      try {
        await api(`/api/admin/accounts/${id}`, { method: 'DELETE' });
        showToast('🗑️ تم الحذف بنجاح');
        await Promise.all([loadAccounts(), loadStats()]);
      } catch (e) { showToast('❌ ' + e.message); }
    }
  });
}

// ── Confirm Dialog ────────────────────────────────────
let _confirmOkCallback = null;
function confirmAction({ title, msg, icon, okText, danger, onOk }) {
  document.getElementById('confirmIcon').textContent  = icon  || '❓';
  document.getElementById('confirmTitle').textContent = title || 'تأكيد';
  document.getElementById('confirmMsg').textContent   = msg   || '';
  const okBtn = document.getElementById('confirmOk');
  okBtn.textContent = okText || 'تأكيد';
  okBtn.className   = 'btn ' + (danger ? 'btn-danger' : 'btn-primary');
  _confirmOkCallback = onOk;
  document.getElementById('confirmModal').classList.remove('hidden');
}
document.getElementById('confirmOk').addEventListener('click', async () => {
  document.getElementById('confirmModal').classList.add('hidden');
  if (_confirmOkCallback) { await _confirmOkCallback(); _confirmOkCallback = null; }
});
document.getElementById('confirmCancel').addEventListener('click', () => {
  document.getElementById('confirmModal').classList.add('hidden');
  _confirmOkCallback = null;
});
document.getElementById('confirmModal').addEventListener('click', e => {
  if (e.target.id === 'confirmModal') {
    document.getElementById('confirmModal').classList.add('hidden');
    _confirmOkCallback = null;
  }
});

// ── Edit Modal ────────────────────────────────────────
function openEdit(id) {
  const a = accountsData.find(x => x.id === id);
  if (!a) return;
  setVal('editId',       a.id);
  setVal('editName',     a.name);
  setVal('editPrice',    a.price);
  setVal('editYear',     a.creation_year || '');
  setVal('editStatus',   a.status);
  setVal('editCategory', a.category || 'twitter');
  setVal('editDesc',     a.description || '');

  // Image preview in edit modal
  const thumbImg   = document.getElementById('editThumbImg');
  const thumbPh    = document.getElementById('editThumbPlaceholder');
  const imgInput   = document.getElementById('editImageInput');
  const imgName    = document.getElementById('editImgName');
  const imgHint    = document.getElementById('editImgHint');
  imgInput.value   = '';
  imgName.classList.add('hidden');
  imgHint.classList.remove('hidden');
  if (a.image) {
    thumbImg.src = a.image;
    thumbImg.classList.remove('hidden');
    thumbPh.classList.add('hidden');
  } else {
    thumbImg.src = '';
    thumbImg.classList.add('hidden');
    thumbPh.classList.remove('hidden');
  }

  document.getElementById('editModal').classList.remove('hidden');
  document.getElementById('editName').focus();
}

// Show chosen file name when user picks image in edit modal
document.getElementById('editImageInput').addEventListener('change', function() {
  const imgName = document.getElementById('editImgName');
  const imgHint = document.getElementById('editImgHint');
  const thumbImg = document.getElementById('editThumbImg');
  const thumbPh  = document.getElementById('editThumbPlaceholder');
  if (this.files[0]) {
    imgName.textContent = '📎 ' + this.files[0].name;
    imgName.classList.remove('hidden');
    imgHint.classList.add('hidden');
    // Live preview
    const r = new FileReader();
    r.onload = ev => {
      thumbImg.src = ev.target.result;
      thumbImg.classList.remove('hidden');
      thumbPh.classList.add('hidden');
    };
    r.readAsDataURL(this.files[0]);
  }
});

function setVal(id, v) {
  const el = document.getElementById(id);
  if (el) el.value = v;
}

function closeEdit() { document.getElementById('editModal').classList.add('hidden'); }

document.getElementById('editClose').addEventListener('click',  closeEdit);
document.getElementById('editCancel').addEventListener('click', closeEdit);
document.getElementById('editModal').addEventListener('click', e => {
  if (e.target.id === 'editModal') closeEdit();
});

document.getElementById('editForm').addEventListener('submit', async function(e) {
  e.preventDefault();
  const id  = document.getElementById('editId').value;
  const btn = this.querySelector('[type=submit]');
  btn.disabled = true;
  const fd = new FormData(this);
  try {
    await api(`/api/admin/accounts/${id}`, { method: 'PUT', body: fd });
    showToast('💾 تم الحفظ بنجاح');
    closeEdit();
    await Promise.all([loadAccounts(), loadStats()]);
  } catch (err) {
    showToast('❌ ' + err.message);
  } finally {
    btn.disabled = false;
  }
});

// ── Add Form ──────────────────────────────────────────
const dropZone     = document.getElementById('dropZone');
const imageInput   = document.getElementById('imageInput');
const dropContent  = document.getElementById('dropContent');
const imagePreview = document.getElementById('imagePreview');
const previewImg   = document.getElementById('previewImg');
const removePreview= document.getElementById('removePreview');
const addResult    = document.getElementById('addResult');

dropContent.addEventListener('click', () => imageInput.click());

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

document.getElementById('addForm').addEventListener('submit', async function(e) {
  e.preventDefault();
  const btn = document.getElementById('addSubmitBtn');
  btn.disabled = true;
  btn.innerHTML = '<svg class="spin" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0"/></svg> جاري الإضافة…';

  const fd = new FormData(this);
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
    setTimeout(() => switchTab('accounts'), 1500);
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
  } catch (e) {
    if (!e.message.includes('تسجيل')) showToast('⚠️ تعذّر تحميل الطلبات');
  }
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
  const stLabel  = { pending:'قيد الانتظار', paid:'مدفوع', completed:'مكتمل', cancelled:'ملغي' };

  tbody.innerHTML = orders.map(o => `
    <tr>
      <td class="td-id">#${o.id}</td>
      <td>
        <div class="order-account">
          <span class="order-name">${esc(o.account_name || '—')}</span>
        </div>
      </td>
      <td>
        <div class="buyer-cell">
          <div class="buyer-name">@${esc(o.buyer_username || 'unknown')}</div>
          <div class="buyer-id">${o.buyer_id}</div>
        </div>
      </td>
      <td class="td-price">$${Number(o.account_price || 0).toFixed(2)}</td>
      <td><span class="spill sp-${o.status}">${stLabel[o.status] || o.status}</span></td>
      <td class="td-date">${fmtDate(o.created_at)}</td>
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
      headers: { 'Content-Type': 'application/json' },
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
setInterval(() => {
  if (!document.getElementById('adminApp').classList.contains('hidden')) {
    loadStats();
  }
}, 60_000);
