/* ═══════════════════════════════════════════════════
   ريبر X — Premium Mini App JS
   ═══════════════════════════════════════════════════ */
'use strict';

const tg = window.Telegram?.WebApp;
if (tg) { tg.ready(); tg.expand(); tg.enableClosingConfirmation(); }

// ── State ─────────────────────────────────────────────
let allAccounts  = [];
let filteredList = [];
let activeYear   = 'all';
let searchQ      = '';
let currentAcc   = null;

// ── DOM refs ──────────────────────────────────────────
const grid         = document.getElementById('accountsGrid');
const loadingBox   = document.getElementById('loadingBox');
const emptyBox     = document.getElementById('emptyBox');
const statsBar     = document.getElementById('statsBar');
const statsText    = document.getElementById('statsText');
const searchToggle = document.getElementById('searchToggle');
const searchBar    = document.getElementById('searchBar');
const searchInput  = document.getElementById('searchInput');
const searchClear  = document.getElementById('searchClear');
const overlay      = document.getElementById('overlay');
const sheet        = document.getElementById('sheet');
const toast        = document.getElementById('toast');

// ── Boot ──────────────────────────────────────────────
(async function boot() {
  // Animate ambient orbs in after page loads
  setTimeout(() => document.querySelectorAll('.orb').forEach(o => o.classList.add('loaded')), 300);
  await loadAccounts();
  checkDeepLink();
})();

// ── API: Load accounts ────────────────────────────────
async function loadAccounts() {
  showSkeleton();
  try {
    const headers = {};
    if (tg?.initData) headers['X-Init-Data'] = tg.initData;
    const res = await fetch('/api/accounts', { headers });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    allAccounts = await res.json();
    buildFilters();
    renderGrid();
  } catch (e) {
    console.error('Load failed:', e);
    loadingBox.innerHTML = `
      <div style="padding:40px;text-align:center;color:var(--text-3)">
        <div style="font-size:2rem;margin-bottom:12px">⚠️</div>
        <div style="font-size:.85rem">تعذّر تحميل الحسابات.<br>تحقق من الاتصال وحاول مجدداً.</div>
      </div>`;
  }
}

// ── Filters ───────────────────────────────────────────
function buildFilters() {
  // Collect unique years
  const years = [...new Set(
    allAccounts.map(a => a.creation_year).filter(Boolean)
  )].sort();

  const track = document.getElementById('pillsTrack');
  if (!track) return;

  // Keep "الكل" pill, remove old year pills
  const existing = Array.from(track.querySelectorAll('.pill[data-year]'));
  existing.forEach(p => { if (p.dataset.year !== 'all') p.remove(); });

  // Update "الكل" count
  const allPill = track.querySelector('.pill[data-year="all"]');
  if (allPill) {
    const cnt = allPill.querySelector('.pill-count');
    if (cnt) cnt.textContent = allAccounts.filter(a => a.status === 'available').length;
  }

  // Add year pills in reverse order (newest first)
  years.reverse().forEach(y => {
    const count = allAccounts.filter(a => a.creation_year === y && a.status === 'available').length;
    const p = document.createElement('button');
    p.className = 'pill'; p.dataset.year = String(y);
    p.innerHTML = `${y} <span class="pill-count">${count}</span>`;
    p.addEventListener('click', () => setFilter(String(y), p));
    track.appendChild(p);
  });
}

function setFilter(year, btn) {
  haptic('light');
  document.querySelectorAll('.pill').forEach(p => p.classList.remove('active'));
  btn.classList.add('active');
  activeYear = year;
  renderGrid();
}

// ── Grid render ───────────────────────────────────────
function renderGrid() {
  filteredList = allAccounts.filter(a => {
    const yearOk = activeYear === 'all' || String(a.creation_year) === activeYear;
    const queryOk = !searchQ ||
      a.name.toLowerCase().includes(searchQ) ||
      (a.description || '').toLowerCase().includes(searchQ) ||
      String(a.creation_year || '').includes(searchQ);
    return yearOk && queryOk;
  });

  // Stats bar
  if (allAccounts.length) {
    const avail = allAccounts.filter(a => a.status === 'available').length;
    statsBar.classList.remove('hidden');
    statsText.textContent = `${avail} متاح · ${allAccounts.length} إجمالي`;
  }

  loadingBox.classList.add('hidden');

  if (!filteredList.length) {
    emptyBox.classList.remove('hidden');
    grid.classList.add('hidden');
    grid.innerHTML = '';
    return;
  }

  emptyBox.classList.add('hidden');
  grid.classList.remove('hidden');

  grid.innerHTML = filteredList.map((a, i) => buildCardHTML(a, i)).join('');

  // Attach click handlers
  grid.querySelectorAll('.card').forEach(el => {
    el.addEventListener('click', () => {
      haptic('light');
      openSheet(Number(el.dataset.id));
    });
  });
}

// ── Card HTML ─────────────────────────────────────────
function buildCardHTML(a, idx) {
  const delay  = Math.min(idx * 55, 450);
  const thumb  = a.image
    ? `<img src="${esc(a.image)}" alt="${esc(a.name)}" loading="lazy"/>`
    : `<div class="card-thumb-placeholder">𝕏</div>`;

  const badgeLabel = { available: 'متاح', reserved: 'محجوز', sold: 'مباع' }[a.status] || a.status;
  const followers  = a.followers ? fmtNum(a.followers) : null;

  return `
    <div class="card" data-id="${a.id}" style="animation-delay:${delay}ms" role="button" tabindex="0"
         aria-label="${esc(a.name)}">
      <div class="card-thumb">
        ${thumb}
        <span class="card-badge badge-${a.status}">${badgeLabel}</span>
        ${a.creation_year ? `<span class="card-year-badge">${a.creation_year}</span>` : ''}
      </div>
      <div class="card-body">
        <div class="card-name">${esc(a.name)}</div>
        <div class="card-meta">
          <span class="card-followers">${followers ? '👥 ' + followers : ''}</span>
          <span class="card-price">$${Number(a.price).toFixed(0)}</span>
        </div>
      </div>
    </div>`;
}

// ── Sheet: open / close ───────────────────────────────
function openSheet(id) {
  const a = allAccounts.find(x => x.id === id);
  if (!a) return;
  currentAcc = a;

  renderSheetContent(a);

  overlay.classList.add('open');
  sheet.classList.add('open');
  document.body.style.overflow = 'hidden';

  if (tg) tg.BackButton.show();
}

function closeSheet() {
  overlay.classList.remove('open');
  sheet.classList.remove('open');
  document.body.style.overflow = '';
  currentAcc = null;
  if (tg) tg.BackButton.hide();
}

overlay.addEventListener('click', closeSheet);
if (tg) tg.BackButton.onClick(closeSheet);

// ── Sheet: render content ─────────────────────────────
function renderSheetContent(a) {
  const badgeLabel = { available: 'متاح', reserved: 'محجوز', sold: 'مباع' }[a.status] || a.status;
  const followers  = a.followers ? fmtNum(a.followers) : null;
  const tweets     = a.tweets_count ? fmtNum(a.tweets_count) : null;

  let heroHTML;
  if (a.image) {
    heroHTML = `<img src="${esc(a.image)}" alt="${esc(a.name)}"/>`;
  } else {
    heroHTML = `<div class="sheet-hero-placeholder">𝕏</div>`;
  }

  let metaChips = '';
  if (a.creation_year)    metaChips += `<div class="meta-chip gold"><span class="chip-icon">📅</span>${a.creation_year}</div>`;
  if (followers)          metaChips += `<div class="meta-chip"><span class="chip-icon">👥</span>${followers} متابع</div>`;
  if (tweets)             metaChips += `<div class="meta-chip"><span class="chip-icon">🐦</span>${tweets} تغريدة</div>`;
  if (a.category)         metaChips += `<div class="meta-chip"><span class="chip-icon">🏷️</span>${esc(a.category)}</div>`;

  let featuresHTML = '';
  if (a.features) {
    const tags = a.features.split(/[،,\n]/).map(f => f.trim()).filter(Boolean);
    if (tags.length) {
      featuresHTML = `
        <div class="sheet-features">
          <div class="features-title">المميزات</div>
          <div class="features-list">
            ${tags.map(t => `<span class="feature-tag">✓ ${esc(t)}</span>`).join('')}
          </div>
        </div>`;
    }
  }

  const isSold = a.status === 'sold';
  const isReserved = a.status === 'reserved';
  let actionsHTML;
  if (isSold) {
    actionsHTML = `<div class="btn-secondary" style="pointer-events:none;opacity:.5">❌ الحساب مباع</div>`;
  } else if (isReserved) {
    actionsHTML = `<div class="btn-secondary" style="pointer-events:none;opacity:.5">⏳ محجوز حالياً</div>`;
  } else {
    actionsHTML = `
      <button class="btn-primary" onclick="showPaymentOptions(${a.id})">
        <span>🛒</span> شراء الآن
      </button>`;
  }

  sheet.innerHTML = `
    <div class="sheet-handle"></div>
    <div class="sheet-hero">
      ${heroHTML}
      <span class="sheet-hero-badge badge-${a.status}">${badgeLabel}</span>
    </div>
    <div class="sheet-content">
      <div class="sheet-title-row">
        <div class="sheet-title">${esc(a.name)}</div>
        <div class="sheet-price">$${Number(a.price).toFixed(0)}</div>
      </div>
      ${metaChips ? `<div class="sheet-meta">${metaChips}</div>` : ''}
      ${a.description ? `<div class="sheet-desc">${esc(a.description)}</div>` : ''}
      ${featuresHTML}
      <div class="buy-section">
        ${actionsHTML}
        <button class="btn-back" onclick="closeSheet()">← رجوع للقائمة</button>
      </div>
    </div>`;
}

// ── Payment options ───────────────────────────────────
function showPaymentOptions(accId) {
  const a = allAccounts.find(x => x.id === accId);
  if (!a) return;
  haptic('medium');

  sheet.innerHTML = `
    <div class="sheet-handle"></div>
    <div class="sheet-content" style="padding-top:20px">
      <div style="text-align:center;margin-bottom:20px">
        <div style="font-size:1.5rem;font-weight:900;margin-bottom:4px">اختر طريقة الدفع</div>
        <div style="font-size:.85rem;color:var(--text-3)">${esc(a.name)} · <strong style="color:var(--gold)">$${Number(a.price).toFixed(2)}</strong></div>
      </div>
      <div class="buy-section">
        <button class="btn-primary" onclick="payWithStars(${a.id})">
          <span>⭐</span> دفع بنجوم تيليجرام
        </button>
        <button class="btn-secondary btn-usdt" onclick="payWithUSDT(${a.id})">
          <span>💎</span> دفع بـ USDT (TRC20)
        </button>
        <button class="btn-back" onclick="openSheet(${a.id})">← رجوع لتفاصيل الحساب</button>
      </div>
      <div style="margin-top:16px;padding:12px;background:var(--surface);border:1px solid var(--border);border-radius:var(--r-sm);font-size:.75rem;color:var(--text-3);line-height:1.7;text-align:center">
        💡 بعد إتمام الدفع ستصلك بيانات الحساب مباشرة في التيليجرام
      </div>
    </div>`;
}

async function payWithStars(accId) {
  haptic('medium');
  // Stars payment is handled via Telegram bot — close mini app to let bot handle it
  showToast('⭐ افتح البوت للدفع بالنجوم');
  if (tg) {
    tg.sendData(JSON.stringify({ action: 'pay_stars', account_id: accId }));
  }
}

async function payWithUSDT(accId) {
  haptic('medium');
  const a = allAccounts.find(x => x.id === accId);
  if (!a) return;

  try {
    const headers = { 'Content-Type': 'application/json' };
    if (tg?.initData) headers['X-Init-Data'] = tg.initData;

    const res = await fetch('/api/orders', {
      method: 'POST',
      headers,
      body: JSON.stringify({ account_id: accId }),
    });
    const data = await res.json();

    if (!res.ok) throw new Error(data.error || 'Order failed');

    const orderId = data.order_id;
    const usdtAddress = data.usdt_address || '';

    sheet.innerHTML = `
      <div class="sheet-handle"></div>
      <div class="sheet-content" style="padding-top:20px">
        <div style="text-align:center;margin-bottom:20px">
          <div style="font-size:1.5rem;font-weight:900;margin-bottom:4px">الدفع بـ USDT</div>
          <div style="font-size:.85rem;color:var(--text-3)">${esc(a.name)}</div>
        </div>
        <div style="text-align:center;margin-bottom:16px">
          <div style="font-size:2rem;font-weight:900;background:var(--grad);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text">$${Number(a.price).toFixed(2)}</div>
          <div style="font-size:.75rem;color:var(--text-3);margin-top:2px">TRC20 — Tron Network</div>
        </div>
        <div class="usdt-info">
          <div class="usdt-label">عنوان المحفظة (TRC20)</div>
          <div class="usdt-address" onclick="copyAddress(this)" title="اضغط للنسخ">
            ${esc(usdtAddress || 'سيتم توفيره من الأدمن')}
          </div>
          ${usdtAddress ? '<div class="usdt-copy-hint">👆 اضغط لنسخ العنوان</div>' : ''}
        </div>
        <div class="buy-section">
          <button class="btn-primary" onclick="confirmUSDTSent(${orderId})">
            ✅ أرسلت المبلغ — إشعار الأدمن
          </button>
          <button class="btn-back" onclick="showPaymentOptions(${accId})">← رجوع</button>
        </div>
        <div style="margin-top:14px;padding:12px;background:rgba(239,68,68,0.06);border:1px solid rgba(239,68,68,0.15);border-radius:var(--r-sm);font-size:.75rem;color:#F87171;line-height:1.7;text-align:center">
          ⚠️ أرسل المبلغ بالضبط عبر شبكة TRC20 فقط.<br>بعد الإرسال اضغط الزر أعلاه لإشعار الأدمن.
        </div>
      </div>`;
  } catch (e) {
    showToast('❌ ' + (e.message || 'حدث خطأ'));
  }
}

function copyAddress(el) {
  const addr = el.textContent.trim();
  if (!addr || addr.includes('سيتم')) return;
  navigator.clipboard.writeText(addr).then(() => {
    haptic('success');
    showToast('✅ تم نسخ العنوان');
  }).catch(() => showToast('❌ تعذّر النسخ'));
}

async function confirmUSDTSent(orderId) {
  haptic('medium');
  try {
    const headers = { 'Content-Type': 'application/json' };
    if (tg?.initData) headers['X-Init-Data'] = tg.initData;

    await fetch(`/api/orders/${orderId}/confirm`, { method: 'POST', headers });
    showSuccessSheet(orderId);
  } catch (e) {
    showToast('❌ تعذّر الإرسال، تواصل مع الأدمن مباشرة');
  }
}

function showSuccessSheet(orderId) {
  haptic('success');
  sheet.innerHTML = `
    <div class="sheet-content">
      <div class="success-sheet">
        <div class="success-anim">✅</div>
        <div class="success-title">تم الإرسال!</div>
        <div class="success-sub">تم إشعار الأدمن بطلبك. سيراجع الدفع ويرسل لك بيانات الحساب خلال دقائق.</div>
        <div class="success-order">
          <div class="success-order-label">رقم الطلب</div>
          <div class="success-order-id">#${orderId}</div>
        </div>
        <button class="btn-primary" onclick="closeSheet()" style="width:100%">العودة للمتجر</button>
      </div>
    </div>`;
}

// ── Search ────────────────────────────────────────────
searchToggle.addEventListener('click', () => {
  const isOpen = searchBar.classList.toggle('open');
  if (isOpen) {
    setTimeout(() => searchInput.focus(), 100);
    searchToggle.textContent = '✕';
  } else {
    searchToggle.textContent = '🔍';
    searchInput.value = '';
    searchQ = '';
    searchClear.classList.add('hidden');
    renderGrid();
  }
});

searchInput.addEventListener('input', e => {
  searchQ = e.target.value.toLowerCase().trim();
  searchClear.classList.toggle('hidden', !searchQ);
  renderGrid();
});

searchClear.addEventListener('click', () => {
  searchInput.value = ''; searchQ = '';
  searchClear.classList.add('hidden');
  searchInput.focus();
  renderGrid();
});

// ── Skeleton ──────────────────────────────────────────
function showSkeleton() {
  loadingBox.classList.remove('hidden');
  loadingBox.innerHTML = `
    <div class="skeleton-grid">
      ${Array(4).fill(0).map(() => `
        <div class="skeleton-card">
          <div class="skeleton-thumb shine"></div>
          <div class="skeleton-body">
            <div class="skeleton-line w100 shine"></div>
            <div class="skeleton-line w60 shine"></div>
            <div class="skeleton-line w40 shine"></div>
          </div>
        </div>`).join('')}
    </div>`;
}

// ── Deep link ─────────────────────────────────────────
function checkDeepLink() {
  const id = new URLSearchParams(location.search).get('account');
  if (id) {
    const a = allAccounts.find(x => x.id === Number(id));
    if (a) setTimeout(() => openSheet(a.id), 300);
  }
}

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

function fmtNum(n) {
  if (!n) return '';
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1).replace(/\.0$/, '') + 'M';
  if (n >= 1_000)     return (n / 1_000).toFixed(1).replace(/\.0$/, '') + 'K';
  return String(n);
}
