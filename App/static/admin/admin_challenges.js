/* ─── Create-form event filter ─── */
function filterCreateEvents(seasonId) {
  const sid = String(seasonId || '').trim();
  const grid = document.getElementById('createEventsGrid');
  const placeholder = document.getElementById('createEventsPlaceholder');
  let visible = 0;
  grid.querySelectorAll('.ev-chk-label').forEach(label => {
    const match = String(label.dataset.season || '').trim() === sid;
    label.style.display = match ? '' : 'none';
    if (!match) label.querySelector('input').checked = false;
    if (match) visible++;
  });
  placeholder.style.display = visible === 0 ? 'block' : 'none';
  placeholder.textContent = visible === 0
    ? (sid ? 'No events for this season.' : 'Select a season to see events.')
    : '';
}

/* ─── Edit-modal event filter ─── */
function filterEditEvents(seasonId) {
  const sid = String(seasonId || '').trim();
  const grid = document.getElementById('editEventsGrid');
  const placeholder = document.getElementById('editEventsPlaceholder');
  let visible = 0;
  grid.querySelectorAll('.ev-chk-label').forEach(label => {
    const labelSeason = String(label.dataset.season || '').trim();
    const match = sid !== '' && labelSeason === sid;
    label.style.setProperty('display', match ? '' : 'none', 'important');
    if (!match) label.querySelector('input').checked = false;
    if (match) visible++;
  });
  placeholder.style.display = visible === 0 ? 'block' : 'none';
}

/* ─── Year stepper (challenges table) ─── */
var chYearIndex = (function () {
  var cur = new Date().getFullYear();
  var i = CH_VALID_YEARS.indexOf(cur);
  return i >= 0 ? i : Math.max(0, CH_VALID_YEARS.length - 1);
})();

function chActiveYear() { return CH_VALID_YEARS.length ? CH_VALID_YEARS[chYearIndex] : null; }

function updateChYearUI() {
  var y = chActiveYear();
  document.getElementById('chYearLabel').textContent = y !== null ? y : '—';
  document.getElementById('chYearPrev').style.opacity = chYearIndex <= 0 ? '0.3' : '1';
  document.getElementById('chYearNext').style.opacity = chYearIndex >= CH_VALID_YEARS.length - 1 ? '0.3' : '1';
  filterChTable();
}

/* ─── Table filter & sort (challenges) ─── */
function filterChTable() {
  var q     = (document.getElementById('chSearch').value || '').trim().toLowerCase();
  var sort  = document.getElementById('chSort').value;
  var y     = chActiveYear();
  var tbody = document.getElementById('chBody');
  if (!tbody) return;

  var rows = Array.from(tbody.querySelectorAll('tr.ch-row'));

  rows.sort(function (a, b) {
    var an = a.dataset.name || '', bn = b.dataset.name || '';
    if (sort === 'za') return an > bn ? -1 : an < bn ? 1 : 0;
    return an < bn ? -1 : an > bn ? 1 : 0;
  });
  rows.forEach(function (r) { tbody.appendChild(r); });

  var visible = 0;
  rows.forEach(function (row) {
    var show = (!q || row.dataset.name.includes(q))
            && (y === null || String(row.dataset.year) === String(y));
    row.style.display = show ? '' : 'none';
    if (show) visible++;
  });
  document.getElementById('chNoResults').style.display = visible === 0 ? 'block' : 'none';
}

/* Auto-trigger on page load */
document.addEventListener('DOMContentLoaded', () => {
  const sel = document.getElementById('createSeasonSelect');
  if (sel && sel.value) filterCreateEvents(sel.value);

  document.querySelectorAll('.toast').forEach(t => {
    setTimeout(() => { t.style.opacity = '0'; setTimeout(() => t.remove(), 400); }, 4000);
  });

  /* Year stepper buttons */
  document.getElementById('chYearPrev').addEventListener('click', function () {
    if (chYearIndex > 0) { chYearIndex--; updateChYearUI(); }
  });
  document.getElementById('chYearNext').addEventListener('click', function () {
    if (chYearIndex < CH_VALID_YEARS.length - 1) { chYearIndex++; updateChYearUI(); }
  });

  /* Filter listeners */
  document.getElementById('chSearch').addEventListener('input', filterChTable);
  document.getElementById('chSort').addEventListener('change', filterChTable);

  /* Kill Materialize on chSort if present */
  if (window.M && M.FormSelect) {
    try { const inst = M.FormSelect.getInstance(document.getElementById('chSort')); if (inst) inst.destroy(); } catch (e) {}
  }

  updateChYearUI();
});


/* ══════════════════════════════════════════
   CREATE FORM — Step 2 Placement Rules
══════════════════════════════════════════ */

let _createChRules = [];
let _createChRulesOpen = false;

function toggleCreateChRules() {
  _createChRulesOpen = !_createChRulesOpen;
  document.getElementById('createChRulesBody').style.display = _createChRulesOpen ? '' : 'none';
  document.getElementById('createChRulesChevron').style.transform =
    _createChRulesOpen ? 'rotate(180deg)' : 'rotate(0deg)';
}

function syncCreateChIndUI() {
  const wrap  = document.getElementById('createChIndTableWrap');
  const empty = document.getElementById('createChIndEmpty');
  const tbody = document.getElementById('createChIndBody');
  if (!_createChRules.length) {
    wrap.style.display  = 'none';
    empty.style.display = 'block';
    return;
  }
  wrap.style.display  = '';
  empty.style.display = 'none';
  const sorted = [..._createChRules].sort((a, b) => a.placement - b.placement);
  tbody.innerHTML = '';
  sorted.forEach(r => {
    const origIdx = _createChRules.indexOf(r);
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${ordinal(r.placement)}</td>
      <td>${escHtml(r.label)}</td>
      <td><strong>${r.points}</strong></td>
      <td style="text-align:center;">
        <button type="button" class="link danger"
                onclick="_createChRules.splice(${origIdx},1);syncCreateChIndUI()">Remove</button>
      </td>`;
    tbody.appendChild(tr);
  });
}

function openCreateChIndModal() {
  _chIndModalMode = 'createCh';
  document.getElementById('chIndIdx').value   = '';
  document.getElementById('chIndPlace').value = '';
  document.getElementById('chIndPts').value   = '';
  document.getElementById('chIndAward').value = '';
  openSubModal('chIndModal');
}

function serializeCreateChRules() {
  document.getElementById('createChPlacementJSON').value = JSON.stringify(_createChRules);
}


/* ══════════════════════════════════════════
   EDIT MODAL
══════════════════════════════════════════ */

let _chID = null;

function openEditChallenge(btn) {
  const row = btn.closest('tr');
  _chID = row.dataset.id;
  document.getElementById('editChallengeID').value = _chID;
  document.getElementById('chModalTitle').textContent = 'Edit: ' + row.dataset.cname;
  document.getElementById('editChName').value = row.dataset.cname;
  document.getElementById('editChDesc').value = row.dataset.desc;

  const seasonID = String(row.dataset.season || '').trim();
  document.getElementById('editChSeason').value = seasonID;

  filterEditEvents(seasonID);

  const attachedIDs = (row.dataset.eventIds || '').split(',').filter(Boolean);
  document.querySelectorAll('#editEventsGrid .ev-chk-label').forEach(label => {
    if (label.style.display === 'none') return;
    label.querySelector('input').checked =
      attachedIDs.includes(String(label.dataset.eventId).trim());
  });

  // Reset rules and pre-load so they're ready when the user switches to the Rules tab
  _chIndRules = [];
  renderChIndTable();
  loadChRules(_chID);

  chSwitchTab('details');
  openChModal();
}

function openChModal() {
  const m = document.getElementById('chModal');
  m.classList.add('open');
  m.setAttribute('aria-hidden', 'false');
}

function closeChModal() {
  document.getElementById('chModal').classList.remove('open');
  document.getElementById('chModal').setAttribute('aria-hidden', 'true');
  _chIndRules = [];
}

/* ─── Tab switching ─── */
function chSwitchTab(tab) {
  document.getElementById('chTabDetails').style.display = tab === 'details' ? '' : 'none';
  document.getElementById('chTabRules').style.display   = tab === 'rules'   ? '' : 'none';
  document.getElementById('chTabDetailsBtn').classList.toggle('active', tab === 'details');
  document.getElementById('chTabRulesBtn').classList.toggle('active',   tab === 'rules');
}

/* ─── Save details ─── */
async function saveChDetails() {
  const id   = document.getElementById('editChallengeID').value;
  const name = document.getElementById('editChName').value.trim();
  const desc = document.getElementById('editChDesc').value.trim();

  const checkedIDs = [...document.querySelectorAll('#editEventsGrid input:checked')]
    .map(cb => cb.value);

  const fd = new FormData();
  fd.append('challengeName', name);
  fd.append('description',   desc);
  checkedIDs.forEach(eid => fd.append('eventIDs', eid));

  const resp = await fetch(`/admin/challenges/${id}/update`, { method: 'POST', body: fd });
  const data = await resp.json();
  if (data.success) {
    closeChModal();
    location.reload();
  } else {
    alert('Error: ' + (data.error || 'Unknown error'));
  }
}


/* ══════════════════════════════════════════
   POINTS RULES
══════════════════════════════════════════ */

let _chIndRules = [];

async function loadChRules(challengeID) {
  try {
    const resp = await fetch(`/admin/challenges/${challengeID}/rules`);
    const data = await resp.json();
    _chIndRules = data.individual || [];
    renderChIndTable();
  } catch (e) {
    console.error('Failed to load challenge rules:', e);
  }
}

/* ── Individual / Placement rules table ── */
function renderChIndTable() {
  const tbody = document.getElementById('chIndBody');
  if (!tbody) return;
  tbody.innerHTML = '';
  const empty = document.getElementById('chIndEmpty');
  const wrap  = document.getElementById('chIndTableWrap');
  if (!_chIndRules.length) {
    empty.style.display = 'block';
    wrap.style.display  = 'none';
    return;
  }
  empty.style.display = 'none';
  wrap.style.display  = '';

  const sorted = [..._chIndRules].sort((a, b) => (a.placement || 0) - (b.placement || 0));

  sorted.forEach(r => {
    const origIdx = _chIndRules.indexOf(r);
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${ordinal(r.placement)}</td>
      <td>${escHtml(r.label)}</td>
      <td><strong>${r.points}</strong></td>
      <td style="text-align:center;white-space:nowrap;">
        <button class="link" onclick="openChIndModal(${origIdx})">Edit</button>
        <button class="link danger" onclick="deleteChIndRule(${origIdx})">Delete</button>
      </td>`;
    tbody.appendChild(tr);
  });
}

async function deleteChIndRule(idx) {
  const rule = _chIndRules[idx];
  if (!rule) return;
  if (!confirm('Remove this rule?')) return;

  if (rule.pointsID) {
    const resp = await fetch(
      `/admin/challenges/${_chID}/rules/${rule.pointsID}/delete`,
      { method: 'POST' }
    );
    const data = await resp.json();
    if (!data.success) { alert('Could not delete rule.'); return; }
  }

  _chIndRules.splice(idx, 1);
  renderChIndTable();
}

/* Tracks whether chIndModal is being used from create-form or edit modal */
let _chIndModalMode = 'edit'; // 'edit' | 'createCh'

function openChIndModal(idx) {
  _chIndModalMode = 'edit';
  document.getElementById('chIndIdx').value = idx === null ? '' : idx;
  if (idx !== null && _chIndRules[idx]) {
    const r = _chIndRules[idx];
    document.getElementById('chIndPlace').value = r.placement || '';
    document.getElementById('chIndPts').value   = r.points    || '';
    document.getElementById('chIndAward').value = r.label     || '';
  } else {
    document.getElementById('chIndPlace').value = '';
    document.getElementById('chIndPts').value   = '';
    document.getElementById('chIndAward').value = '';
  }
  openSubModal('chIndModal');
}

function closeChIndModal() { closeSubModal('chIndModal'); _chIndModalMode = 'edit'; }

function saveChIndRule() {
  const idx   = document.getElementById('chIndIdx').value;
  const place = parseInt(document.getElementById('chIndPlace').value);
  const pts   = parseFloat(document.getElementById('chIndPts').value);
  const award = document.getElementById('chIndAward').value.trim();
  if (!place || isNaN(pts) || !award) { alert('All fields are required.'); return; }

  /* ── Create-form mode (challenge) ── */
  if (_chIndModalMode === 'createCh') {
    if (_createChRules.some(r => r.placement === place)) {
      alert(`A rule for ${ordinal(place)} place already exists.`); return;
    }
    _createChRules.push({ placement: place, label: award, points: pts });
    syncCreateChIndUI();
    closeChIndModal();
    return;
  }

  /* ── Edit-modal mode ── */
  const rule = { placement: place, points: pts, label: award };
  if (idx !== '') {
    const duplicate = _chIndRules.some((r, i) =>
      i !== parseInt(idx) && r.placement === place
    );
    if (duplicate) { alert(`A rule for ${ordinal(place)} place already exists.`); return; }
    rule.pointsID = _chIndRules[parseInt(idx)]?.pointsID;
    _chIndRules[parseInt(idx)] = rule;
  } else {
    if (_chIndRules.some(r => r.placement === place)) {
      alert(`A rule for ${ordinal(place)} place already exists.`);
      return;
    }
    _chIndRules.push(rule);
  }
  renderChIndTable();
  closeChIndModal();
}

async function saveChRules() {
  const id = document.getElementById('editChallengeID').value;
  const resp = await fetch(`/admin/challenges/${id}/rules`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ individual: _chIndRules }),
  });
  const data = await resp.json();
  if (data.success) {
    closeChModal();
    location.reload();
  } else {
    alert('Error saving rules: ' + (data.error || 'unknown'));
  }
}

/* ─── Modal helpers ─── */
function openSubModal(id)  { const m = document.getElementById(id); m.style.display = 'flex'; m.setAttribute('aria-hidden', 'false'); }
function closeSubModal(id) { const m = document.getElementById(id); m.style.display = 'none'; m.setAttribute('aria-hidden', 'true'); }

function ordinal(n) {
  if (!n) return '—';
  const s = ['th', 'st', 'nd', 'rd'], v = n % 100;
  return n + (s[(v - 20) % 10] || s[v] || s[0]);
}

function escHtml(s) {
  return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}