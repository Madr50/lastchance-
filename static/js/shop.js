/* ═══════════════════════════════════════════════════
   𝕏 Account Shop — Premium Mini App JS
   ═══════════════════════════════════════════════════ */

const tg = window.Telegram?.WebApp;
if (tg) { tg.ready(); tg.expand(); tg.enableClosingConfirmation(); }

// ── State ─────────────────────────────────────────────
let allAccounts  = [];
let activeYear   = 'all';
let searchOpen   = false;

// ── DOM ───────────────────────────────────────────────
const grid          = document.getElementById('accountsGrid');
const loadingState  = document.getElementById('loadingState');
const emptyState    = document.getElementById('emptyState');
const statsBar      = document.getElementById('statsBar');
const searchInput   = document.getElementById('searchInput');
const searchBar     = document.getElementById('searchBar');
const searchClear   = document.getElementById('searchClear');
const searchToggle  = document.getElementById('searchToggle');
const modal         = document.getElementById('modal');
const successModal  = document.getElementById('successModal');
const toast         = document.getElementById('toast');

// ── Load ──────────────────────────────────────────────
async function loadAccounts() {
  try {
    const res   = await fetch('/api/accounts');
    allAccounts = await res.json();
    render();
  } catch (e) {
    loadingState.innerHTML =
      '<p style="color:var(--red);text-align:center;padding:40px">Failed to load. Please try again.</p>';
    console.error(e);
  }
}

// ── Render ────────────────────────────────────────────
function render() {
  const q = searchInput.value.trim().toLowerCase();

  const list = allAccounts.filter(a => {
    const yearOk = activeYear === 'all' || String(a.creation_year) === activeYear;
    const queryOk = !q ||
      a.name.toLowerCase().includes(q) ||
      (a.description || '').toLowerCase().includes(q) ||
      String(a.creation_year || '').includes(q) ||
      (a.category || '').toLowerCase().includes(q);
    return yearOk && queryOk;
  });

  loadingState.classList.add('hidden');

  // Stats bar
  if (allAccounts.length) {
    const avail = allAccounts.filter(a => a.status === 'available').length;
    statsBar.textContent = `${avail} AVAILABLE  ·  ${allAccounts.length} TOTAL ACCOUNTS`;
  }

  if (!list.length) {
    emptyState.classList.remove('hidden');
    grid.innerHTML = '';
    return;
  }
  emptyState.classList.add('hidden');

  grid.innerHTML = list.map((a, i) => buildCard(a, i)).join('');

  grid.querySelectorAll('.card').forEach(el => {
    el.addEventListener('click', () => {
      haptic('light');
      openModal(Number(el.dataset.id));
    });
  });
}

function buildCard(a, idx) {
  const thumb = a.image
    ? `<img src="${esc(a.image)}" alt="${esc(a.name)}" loading="lazy"/>`
    : `<div class="card-thumb-placeholder">𝕏</div>`;

  const badgeClass = `badge-${a.status}`;
  const delay      = Math.min(idx * 50, 400);

  return `<div class="card" data-id="${a.id}" role="button" tabindex="0"
               style="animation-delay:${delay}ms">
    <div class="card-thumb">
      ${thumb}
      <span class="card-badge ${badgeClass}">${a.status}</span>
    </div>
    <div class="card-body">
      ${a.creation_year ? `<div class="card-year">📅 ${a.creation_year}</div>` : ''}
      <div class="card-name">${esc(a.name)}</div>
      <div class="card-price">$${Number(a.price).toFixed(2)}</div>
    </div>
  </div>`;
}

// ── Modal ─────────────────────────────────────────────
let currentAccount = null;

function openModal(id) {
  const a = allAccounts.find(x => x.id === id);
  if (!a) return;
  currentAccount = a;

  // Hero image
  const heroWrap = document.getElementById('modalImageWrap');
  heroWrap.innerHTML = a.image
    ? `<img src="${esc(a.image)}" alt="${esc(a.name)}"/>`
    : `<div class="sheet-hero-placeholder">𝕏</div>`;

  // Meta tags
  const meta = document.getElementById('sheetMeta');
  meta.innerHTML = '';
  if (a.creation_year) meta.innerHTML += `<span class="tag tag-year">📅 ${a.creation_year}</span>`;
  if (a.category)      meta.innerHTML += `<span class="tag tag-cat">${esc(a.category)}</span>`;
  const stCls = { available: 'tag-avail', sold: 'tag-sold', reserved: 'tag-reserved' }[a.status] || '';
  const stLbl = { available: '✅ Available', sold: '❌ Sold', reserved: '🕐 Reserved' }[a.status] || a.status;
  meta.innerHTML += `<span class="tag ${stCls}">${stLbl}</span>`;

  document.getElementById('modalName').textContent  = a.name;
  document.getElementById('modalDesc').textContent  = a.description || 'No description provided.';
  document.getElementById('modalPrice').textContent = `$${Number(a.price).toFixed(2)}`;

  const btn = document.getElementById('modalBuyBtn');
  btn.onclick   = null;
  btn.disabled  = a.status !== 'available';

  if (a.status === 'available') {
    btn.querySelector('.buy-btn-inner').innerHTML = `
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 0 1-8 0"/></svg>
      Buy Now`;
    btn.onclick = () => doBuy(a.id);
  } else if (a.status === 'sold') {
    btn.querySelector('.buy-btn-inner').textContent = '❌ Sold Out';
  } else {
    btn.querySelector('.buy-btn-inner').textContent = '🕐 Reserved';
  }

  modal.classList.remove('hidden');
  document.body.style.overflow = 'hidden';
}

function closeModal() {
  modal.classList.add('hidden');
  document.body.style.overflow = '';
  currentAccount = null;
}

modal.addEventListener('click', e => { if (e.target === modal) { haptic('light'); closeModal(); } });

// ── Buy ───────────────────────────────────────────────
async function doBuy(accId) {
  haptic('medium');
  const btn   = document.getElementById('modalBuyBtn');
  const inner = btn.querySelector('.buy-btn-inner');
  btn.disabled = true;
  inner.innerHTML = `<span class="spin-ring"></span> Processing…`;

  const fd = new FormData();
  fd.append('account_id', accId);
  fd.append('initData', tg?.initData || '');

  try {
    const res  = await fetch('/api/buy', { method: 'POST', body: fd });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Purchase failed');

    closeModal();
    showSuccess(data);
    haptic('success');

    // Optimistically update local data
    const idx = allAccounts.findIndex(x => x.id === accId);
    if (idx !== -1) allAccounts[idx].status = 'reserved';
    render();

  } catch (err) {
    showToast('❌ ' + err.message);
    btn.disabled = false;
    inner.innerHTML = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 0 1-8 0"/></svg>Buy Now`;
    haptic('error');
  }
}

function showSuccess(data) {
  document.getElementById('successDetails').innerHTML = `
    <div style="text-align:center;margin-bottom:12px">
      <div style="font-size:.75rem;color:var(--text-3);margin-bottom:4px">ORDER ID</div>
      <div class="order-id-badge">#${data.order_id}</div>
    </div>
    <div style="border-top:1px solid var(--border);padding-top:12px;display:flex;flex-direction:column;gap:6px">
      <div>Account: <strong>${esc(data.account_name)}</strong></div>
      <div>Price: <strong>$${Number(data.price).toFixed(2)} USD</strong></div>
      <div style="margin-top:4px;font-size:.75rem;color:var(--text-3)">
        Contact <strong style="color:var(--text-2)">@l825h</strong> on Telegram with your Order ID to complete payment.
      </div>
    </div>`;

  successModal.classList.remove('hidden');
  document.body.style.overflow = 'hidden';
}

document.getElementById('successClose').addEventListener('click', () => {
  haptic('light');
  successModal.classList.add('hidden');
  document.body.style.overflow = '';
});
successModal.addEventListener('click', e => {
  if (e.target === successModal) { successModal.classList.add('hidden'); document.body.style.overflow = ''; }
});

// ── Search ────────────────────────────────────────────
searchToggle.addEventListener('click', () => {
  haptic('light');
  searchOpen = !searchOpen;
  searchBar.classList.toggle('open', searchOpen);
  if (searchOpen) setTimeout(() => searchInput.focus(), 100);
  else { searchInput.value = ''; render(); }
});

searchInput.addEventListener('input', () => {
  searchClear.classList.toggle('hidden', !searchInput.value);
  clearTimeout(searchInput._t);
  searchInput._t = setTimeout(render, 200);
});

searchClear.addEventListener('click', () => {
  searchInput.value = '';
  searchClear.classList.add('hidden');
  searchInput.focus();
  render();
});

// ── Filters ───────────────────────────────────────────
document.querySelectorAll('.pill').forEach(btn => {
  btn.addEventListener('click', () => {
    haptic('light');
    document.querySelectorAll('.pill').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    activeYear = btn.dataset.year;
    render();
  });
});

// ── Helpers ───────────────────────────────────────────
function haptic(type) {
  if (!tg?.HapticFeedback) return;
  const hf = tg.HapticFeedback;
  if (type === 'light')   hf.impactOccurred('light');
  if (type === 'medium')  hf.impactOccurred('medium');
  if (type === 'success') hf.notificationOccurred('success');
  if (type === 'error')   hf.notificationOccurred('error');
}

let toastTimer;
function showToast(msg, dur = 3200) {
  toast.textContent = msg;
  toast.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove('show'), dur);
}

function esc(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// Deep link: ?account=ID
function checkDeepLink() {
  const id = new URLSearchParams(location.search).get('account');
  if (id) { const a = allAccounts.find(x => x.id === Number(id)); if (a) openModal(a.id); }
}

// ── Inject spin-ring style ─────────────────────────────
const spinStyle = document.createElement('style');
spinStyle.textContent = `.spin-ring{display:inline-block;width:16px;height:16px;border:2.5px solid rgba(255,255,255,.3);border-top-color:#fff;border-radius:50%;animation:spin .6s linear infinite;vertical-align:middle}@keyframes spin{to{transform:rotate(360deg)}}`;
document.head.appendChild(spinStyle);

// ── Init ──────────────────────────────────────────────
loadAccounts().then(checkDeepLink);
