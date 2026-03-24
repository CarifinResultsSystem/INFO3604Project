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

/* Auto-trigger on page load if a season is already selected */
document.addEventListener('DOMContentLoaded', () => {
  const sel = document.getElementById('createSeasonSelect');
  if (sel && sel.value) filterCreateEvents(sel.value);

  document.querySelectorAll('.toast').forEach(t => {
    setTimeout(() => { t.style.opacity = '0'; setTimeout(() => t.remove(), 400); }, 4000);
  });
});

/* ─── Search filter for table ─── */
document.getElementById('chSearch')?.addEventListener('input', function () {
  const q = this.value.trim().toLowerCase();
  document.querySelectorAll('.ch-row').forEach(r => {
    r.style.display = (!q || r.dataset.name.includes(q)) ? '' : 'none';
  });
  document.getElementById('chNoResults').style.display =
    document.querySelectorAll('.ch-row:not([style*="none"])').length === 0 && q ? 'block' : 'none';
});

let _chID = null;

function openEditChallenge(btn) {
  const row = btn.closest('tr');
  _chID = row.dataset.id;
  document.getElementById('editChallengeID').value = _chID;
  document.getElementById('chModalTitle').textContent = 'Edit: ' + row.dataset.cname;
  document.getElementById('editChName').value  = row.dataset.cname;
  document.getElementById('editChDesc').value  = row.dataset.desc;
  document.getElementById('editChBonus').value = row.dataset.bonus;

  const seasonID = String(row.dataset.season || '').trim();
  document.getElementById('editChSeason').value = seasonID;

  filterEditEvents(seasonID);

  const attachedIDs = (row.dataset.eventIds || '').split(',').filter(Boolean);
  document.querySelectorAll('#editEventsGrid .ev-chk-label').forEach(label => {
    if (label.style.display === 'none') return;
    label.querySelector('input').checked =
      attachedIDs.includes(String(label.dataset.eventId).trim());
  });

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
  _chTeamRules = [];
}

function chSwitchTab(tab) {
  document.getElementById('chTabDetails').style.display = tab === 'details' ? '' : 'none';
  document.getElementById('chTabRules').style.display   = tab === 'rules'   ? '' : 'none';
  document.getElementById('chTabDetailsBtn').classList.toggle('active', tab === 'details');
  document.getElementById('chTabRulesBtn').classList.toggle('active',   tab === 'rules');
  if (tab === 'rules' && _chID) loadChRules(_chID);
}

async function saveChDetails() {
  const id    = document.getElementById('editChallengeID').value;
  const name  = document.getElementById('editChName').value.trim();
  const desc  = document.getElementById('editChDesc').value.trim();
  const bonus = document.getElementById('editChBonus').value;

  const checkedIDs = [...document.querySelectorAll('#editEventsGrid input:checked')]
    .map(cb => cb.value);

  const fd = new FormData();
  fd.append('challengeName', name);
  fd.append('description',   desc);
  fd.append('bonusPoints',   bonus);
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

let _chIndRules  = [];
let _chTeamRules = [];

async function loadChRules(challengeID) {
  const resp = await fetch(`/admin/challenges/${challengeID}/rules`);
  const data = await resp.json();
  _chIndRules  = data.individual || [];
  _chTeamRules = data.team       || [];
  renderChIndTable();
  renderChTeamTable();
}

function renderChIndTable() {
  const tbody = document.getElementById('chIndBody');
  tbody.innerHTML = '';
  document.getElementById('chIndEmpty').style.display     = _chIndRules.length ? 'none' : 'block';
  document.getElementById('chIndTableWrap').style.display = _chIndRules.length ? '' : 'none';
  _chIndRules.forEach((r, i) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${ordinal(r.placement)}</td>
      <td>${escHtml(r.label)}</td>
      <td><strong>${r.points}</strong></td>
      <td style="text-align:center;"><button class="link" onclick="openChIndModal(${i})">Edit</button></td>`;
    tbody.appendChild(tr);
  });
}

function openChIndModal(idx) {
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
function closeChIndModal() { closeSubModal('chIndModal'); }

function saveChIndRule() {
  const idx   = document.getElementById('chIndIdx').value;
  const place = parseInt(document.getElementById('chIndPlace').value);
  const pts   = parseFloat(document.getElementById('chIndPts').value);
  const award = document.getElementById('chIndAward').value.trim();
  if (!place || isNaN(pts) || !award) { alert('All fields required.'); return; }
  const rule = { placement: place, points: pts, label: award };
  if (idx !== '') {
    rule.pointsID = _chIndRules[idx]?.pointsID;
    _chIndRules[parseInt(idx)] = rule;
  } else {
    _chIndRules.push(rule);
  }
  renderChIndTable();
  closeChIndModal();
}

let _chTeamEditIdx = null;

function renderChTeamTable() {
  const tbody = document.getElementById('chTeamBody');
  tbody.innerHTML = '';
  const cats = {};
  _chTeamRules.forEach(r => { (cats[r.conditionType] = cats[r.conditionType] || []).push(r); });
  document.getElementById('chTeamEmpty').style.display     = Object.keys(cats).length ? 'none' : 'block';
  document.getElementById('chTeamTableWrap').style.display = Object.keys(cats).length ? '' : 'none';
  Object.entries(cats).forEach(([cat, rows]) => {
    const tr = document.createElement('tr');
    const conds = rows.map(r =>
      `<span style="font-size:12px;color:#555;">${escHtml(r.label)} <strong>(${r.points}pts)</strong></span>`
    ).join('<br>');
    tr.innerHTML = `
      <td><strong>${escHtml(cat)}</strong></td>
      <td>${conds}</td>
      <td style="text-align:center;"><button class="link" onclick="openChTeamModal(${JSON.stringify(cat)})">Edit</button></td>`;
    tbody.appendChild(tr);
  });
}

function openChTeamModal(cat) {
  _chTeamEditIdx = cat;
  document.getElementById('chTeamIdx').value = cat || '';
  if (cat) {
    document.getElementById('chTeamCat').value = cat;
    const rows = _chTeamRules.filter(r => r.conditionType === cat);
    document.getElementById('chAFBody').innerHTML = '';
    rows.forEach(r => addChAFRow(r.label, r.points, r.pointsID));
  } else {
    document.getElementById('chTeamCat').value = '';
    document.getElementById('chAFBody').innerHTML = '';
  }
  syncChAFEmpty();
  openSubModal('chTeamModal');
}
function closeChTeamModal() { closeSubModal('chTeamModal'); }

function addChAFRow(label = '', pts = '', pid = '') {
  const tbody = document.getElementById('chAFBody');
  const tr = document.createElement('tr');
  tr.innerHTML = `
    <td><input class="admin-input af-label" type="text" value="${escHtml(label)}"
               placeholder="e.g. Highest team turnout" style="width:100%;box-sizing:border-box;"></td>
    <td><input class="admin-input af-pts" type="number" step="0.01" min="0"
               value="${pts}" placeholder="0" style="width:100%;box-sizing:border-box;">
        <input type="hidden" class="af-pid" value="${pid}"></td>
    <td><button type="button" class="link danger"
                onclick="this.closest('tr').remove();syncChAFEmpty()">✕</button></td>`;
  tbody.appendChild(tr);
  syncChAFEmpty();
}
function syncChAFEmpty() {
  document.getElementById('chAFEmpty').style.display =
    document.getElementById('chAFBody').rows.length ? 'none' : 'block';
}

function saveChTeamRule() {
  const cat = document.getElementById('chTeamCat').value.trim();
  if (!cat) { alert('Category name is required.'); return; }
  const rows = [...document.getElementById('chAFBody').rows].map(tr => ({
    conditionType: cat,
    label:    tr.querySelector('.af-label').value.trim(),
    points:   parseFloat(tr.querySelector('.af-pts').value) || 0,
    pointsID: tr.querySelector('.af-pid').value || undefined,
  }));
  if (!rows.length) { alert('Add at least one condition.'); return; }
  if (_chTeamEditIdx) {
    _chTeamRules = _chTeamRules.filter(r => r.conditionType !== _chTeamEditIdx);
  }
  _chTeamRules.push(...rows);
  renderChTeamTable();
  closeChTeamModal();
}

async function saveChRules() {
  const id = document.getElementById('editChallengeID').value;
  const resp = await fetch(`/admin/challenges/${id}/rules`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ individual: _chIndRules, team: _chTeamRules }),
  });
  const data = await resp.json();
  if (data.success) {
    closeChModal();
    location.reload();
  } else {
    alert('Error saving rules: ' + (data.error || 'unknown'));
  }
}

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