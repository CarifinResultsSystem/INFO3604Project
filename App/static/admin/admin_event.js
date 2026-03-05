// UTILITIES
function esc(s) {
  return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function ordinal(n) {
  n = Number(n);
  if (n === 1) return '1st';
  if (n === 2) return '2nd';
  if (n === 3) return '3rd';
  return n + 'th';
}
function openOverlay(id)  { var el = document.getElementById(id); el.classList.add('open'); el.setAttribute('aria-hidden','false'); }
function closeOverlay(id) { var el = document.getElementById(id); el.classList.remove('open'); el.setAttribute('aria-hidden','true'); }

// SEASON MODAL
function openSeasonModal()  { openOverlay('seasonModal'); }
function closeSeasonModal() { closeOverlay('seasonModal'); }

// YEAR FILTER
var yearIndex = (function () {
  var cur = new Date().getFullYear();
  var i = VALID_YEARS.indexOf(cur);
  return i >= 0 ? i : Math.max(0, VALID_YEARS.length - 1);
})();

function activeYear() { return VALID_YEARS.length ? VALID_YEARS[yearIndex] : null; }

function updateYearUI() {
  var y = activeYear();
  document.getElementById('yearLabel').textContent = y !== null ? y : '—';
  document.getElementById('yearPrev').style.opacity = yearIndex <= 0 ? '0.3' : '1';
  document.getElementById('yearNext').style.opacity = yearIndex >= VALID_YEARS.length - 1 ? '0.3' : '1';
  filterTable();
}

// TABLE FILTER / SORT
function filterTable() {
  var q    = (document.getElementById('eventSearch').value || '').trim().toLowerCase();
  var loc  = (document.getElementById('locationFilter').value || '').trim().toLowerCase();
  var sort = document.getElementById('eventSort').value;
  var y    = activeYear();
  var tbody = document.getElementById('eventTbody');
  if (!tbody) return;

  var rows = Array.from(tbody.querySelectorAll('tr.event-row'));

  rows.sort(function (a, b) {
    if (sort === 'date') {
      var ad = a.dataset.date || '', bd = b.dataset.date || '';
      return ad < bd ? -1 : ad > bd ? 1 : 0;
    }
    var an = a.dataset.name || '', bn = b.dataset.name || '';
    return an < bn ? -1 : an > bn ? 1 : 0;
  });
  rows.forEach(function (r) { tbody.appendChild(r); });

  var visible = 0;
  rows.forEach(function (row) {
    var show = (!q   || row.dataset.name.includes(q))
            && (!loc || row.dataset.location === loc)
            && row.dataset.hasSeason === 'true'
            && (y === null || String(row.dataset.year) === String(y));
    row.style.display = show ? '' : 'none';
    if (show) visible++;
  });
  document.getElementById('noResultsMsg').style.display = visible === 0 ? 'block' : 'none';
}

// DOM READY
document.addEventListener('DOMContentLoaded', function () {

  // Auto-dismiss toasts
  document.querySelectorAll('.toast').forEach(function (t) {
    setTimeout(function () {
      t.style.transition = 'opacity 0.4s'; t.style.opacity = '0';
      setTimeout(function () { t.remove(); }, 400);
    }, 4000);
  });

  // Date → season auto-select
  var di = document.getElementById('eventDateInput');
  var ss = document.getElementById('seasonSelect');
  if (di && ss) {
    di.addEventListener('change', function () {
      var yr = this.value ? String(new Date(this.value).getUTCFullYear()) : null;
      if (!yr) return;
      Array.from(ss.options).forEach(function (o) { if (o.text.trim() === yr) o.selected = true; });
    });
  }

  // Year stepper
  document.getElementById('yearPrev').addEventListener('click', function () {
    if (yearIndex > 0) { yearIndex--; updateYearUI(); }
  });
  document.getElementById('yearNext').addEventListener('click', function () {
    if (yearIndex < VALID_YEARS.length - 1) { yearIndex++; updateYearUI(); }
  });

  // Filter listeners
  document.getElementById('eventSearch').addEventListener('input', filterTable);
  document.getElementById('locationFilter').addEventListener('change', filterTable);
  document.getElementById('eventSort').addEventListener('change', filterTable);

  // Kill Materialize on our selects
  if (window.M && M.FormSelect) {
    ['locationFilter','eventSort'].forEach(function (id) {
      var el = document.getElementById(id);
      if (!el) return;
      try { var inst = M.FormSelect.getInstance(el); if (inst) inst.destroy(); } catch (e) {}
    });
    M.FormSelect.init(document.querySelectorAll(
      'select:not(#seasonSelect):not(#eventSort):not(#locationFilter)'
    ));
  }

  // Escape key
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    if (document.getElementById('indModal').classList.contains('open'))  { closeIndividualModal(); return; }
    if (document.getElementById('teamModal').classList.contains('open')) { closeTeamModal(); return; }
    closeModal();
    closeSeasonModal();
  });

  updateYearUI();
});


// STATE
var _eventId  = null;
var _indRules = [];   // [{pointsID, placement, award, points}]
var _teamGroups = []; // [{category, rows:[{pointsID, label, points}]}]

// MAIN MODAL
function openModal()  { openOverlay('eventModal');  document.body.classList.add('modal-open'); }
function closeModal() {
  closeOverlay('eventModal');
  document.body.classList.remove('modal-open');
  _eventId = null; _indRules = []; _teamGroups = [];
  document.getElementById('indTableBody').innerHTML  = '';
  document.getElementById('teamTableBody').innerHTML = '';
  switchTab('details');
}

function switchTab(tab) {
  var isD = tab === 'details';
  document.getElementById('tabDetails').style.display = isD ? 'block' : 'none';
  document.getElementById('tabRules').style.display   = isD ? 'none'  : 'block';
  document.getElementById('tabDetailsBtn').classList.toggle('active',  isD);
  document.getElementById('tabRulesBtn').classList.toggle('active', !isD);
}

// Read data attributes from the row — NO inline onclick quoting issues
function openEditFromRow(btn) {
  var row = btn.closest('tr');
  openEdit(
    parseInt(row.dataset.id, 10),
    row.dataset.ename,
    row.dataset.edate,
    row.dataset.etime,
    row.dataset.eloc
  );
}

async function openEdit(eventId, eventName, eventDate, eventTime, eventLocation) {
  _eventId = eventId;
  document.getElementById('modalHeaderName').textContent = eventName || 'Edit Event';
  document.getElementById('detailName').value     = eventName     || '';
  document.getElementById('detailDate').value     = eventDate     || '';
  document.getElementById('detailTime').value     = eventTime     || '';
  document.getElementById('detailLocation').value = eventLocation || '';

  _indRules   = [];
  _teamGroups = [];

  try {
    var res = await fetch('/admin/events/' + eventId + '/rules', { credentials: 'same-origin' });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    var data = await res.json();

    _indRules = (data.individual || []).map(function (r) {
      return { pointsID: r.pointsID, placement: r.placement, award: r.label || '', points: r.points };
    });

    var gMap = {}, gOrder = [];
    (data.team || []).forEach(function (r) {
      var cat = r.conditionType || 'Uncategorised';
      if (!gMap[cat]) { gMap[cat] = []; gOrder.push(cat); }
      gMap[cat].push({ pointsID: r.pointsID, label: r.label || '', points: r.points });
    });
    _teamGroups = gOrder.map(function (cat) { return { category: cat, rows: gMap[cat] }; });

  } catch (err) {
    console.error('Rules fetch failed:', err);
    // Still open modal — rules just start empty
  }

  renderRules();
  switchTab('details');
  openModal();
}

// SAVE DETAILS
async function saveDetails() {
  if (!_eventId) return;
  var name = document.getElementById('detailName').value.trim();
  var date = document.getElementById('detailDate').value;
  var time = document.getElementById('detailTime').value;
  var loc  = document.getElementById('detailLocation').value.trim();
  if (!name || !date || !time || !loc) { alert('All fields are required.'); return; }

  var fd = new FormData();
  fd.append('eventName', name); fd.append('eventDate', date);
  fd.append('eventTime', time); fd.append('eventLocation', loc);

  try {
    var res = await fetch('/admin/events/' + _eventId + '/update', {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Accept': 'application/json' }, body: fd
    });
    var data = await res.json().catch(function () { return {}; });
    if (!res.ok || data.success === false) throw new Error(data.error || 'Unknown error');
    window.location.reload();
  } catch (err) {
    alert('Failed to save: ' + err.message);
  }
}

// SAVE RULES
async function saveRules() {
  if (!_eventId) return;

  var teamFlat = [];
  _teamGroups.forEach(function (g) {
    g.rows.forEach(function (r) {
      teamFlat.push({
        pointsID: r.pointsID || null,
        conditionType: g.category,
        label: r.label.trim(),
        points: Number(r.points || 0),
        lowerLimit: 0, upperLimit: 0
      });
    });
  });

  var payload = {
    individual: _indRules.map(function (r) {
      return { pointsID: r.pointsID || null, placement: Number(r.placement),
               label: r.award.trim(), points: Number(r.points || 0) };
    }),
    team: teamFlat
  };

  try {
    var res = await fetch('/admin/events/' + _eventId + '/rules', {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    window.location.reload();
  } catch (err) {
    alert('Failed to save rules: ' + err.message);
  }
}

// RENDER RULES TABLES
function renderRules() {
  // Individual
  var iBody = document.getElementById('indTableBody');
  var iWrap = document.getElementById('indTableWrap');
  var iMpty = document.getElementById('indEmpty');
  iBody.innerHTML = '';
  if (!_indRules.length) {
    iWrap.style.display = 'none'; iMpty.style.display = 'block';
  } else {
    iWrap.style.display = ''; iMpty.style.display = 'none';
    _indRules.forEach(function (r, i) {
      var tr = document.createElement('tr');
      tr.innerHTML =
        '<td><strong>' + ordinal(r.placement) + ' Place</strong></td>' +
        '<td>' + esc(r.award || '—') + '</td>' +
        '<td>' + Number(r.points || 0) + ' pts</td>' +
        '<td style="text-align:center;">' +
          '<button type="button" class="rule-action-btn edit" onclick="openIndividualModal(' + i + ')" title="Edit">' +
            '<i class="material-icons" style="font-size:15px;">edit</i></button>' +
          '<button type="button" class="rule-action-btn del" onclick="deleteIndRule(' + i + ')" title="Delete">' +
            '<i class="material-icons" style="font-size:15px;">delete</i></button>' +
        '</td>';
      iBody.appendChild(tr);
    });
  }

  // Team
  var tBody = document.getElementById('teamTableBody');
  var tWrap = document.getElementById('teamTableWrap');
  var tMpty = document.getElementById('teamEmpty');
  tBody.innerHTML = '';
  if (!_teamGroups.length) {
    tWrap.style.display = 'none'; tMpty.style.display = 'block';
  } else {
    tWrap.style.display = ''; tMpty.style.display = 'none';
    _teamGroups.forEach(function (g, gi) {
      var catRow = document.createElement('tr');
      catRow.className = 'team-category-row';
      catRow.innerHTML =
        '<td>' + esc(g.category) + '</td>' +
        '<td><span style="color:#888;font-size:12px;">' + g.rows.length +
          ' condition' + (g.rows.length !== 1 ? 's' : '') + '</span></td>' +
        '<td style="text-align:center;">' +
          '<button type="button" class="rule-action-btn edit" onclick="openTeamModal(' + gi + ')" title="Edit">' +
            '<i class="material-icons" style="font-size:15px;">edit</i></button>' +
          '<button type="button" class="rule-action-btn del" onclick="deleteTeamGroup(' + gi + ')" title="Delete">' +
            '<i class="material-icons" style="font-size:15px;">delete</i></button>' +
        '</td>';
      tBody.appendChild(catRow);
      g.rows.forEach(function (row) {
        var sub = document.createElement('tr');
        sub.className = 'team-subrow';
        sub.innerHTML =
          '<td style="padding-left:28px;"><span style="color:#ccc;margin-right:6px;">↳</span>' + esc(row.label || '—') + '</td>' +
          '<td>' + Number(row.points || 0) + ' pts</td><td></td>';
        tBody.appendChild(sub);
      });
    });
  }
}

// INDIVIDUAL RULE SUB-MODAL
function openIndividualModal(idx) {
  document.getElementById('indModalTitle').textContent =
    idx === null ? 'Add Individual Rule' : 'Edit Individual Rule';
  document.getElementById('indIdx').value = idx !== null ? idx : '';
  if (idx !== null) {
    var r = _indRules[idx];
    document.getElementById('indPlace').value = r.placement || '';
    document.getElementById('indAward').value = r.award || '';
    document.getElementById('indPts').value   = r.points  || '';
  } else {
    document.getElementById('indPlace').value = '';
    document.getElementById('indAward').value = '';
    document.getElementById('indPts').value   = '';
  }
  openOverlay('indModal');
  setTimeout(function () { document.getElementById('indPlace').focus(); }, 60);
}
function closeIndividualModal() { closeOverlay('indModal'); }

function saveIndividualRule() {
  var place = parseInt(document.getElementById('indPlace').value, 10);
  var award = document.getElementById('indAward').value.trim();
  var pts   = parseFloat(document.getElementById('indPts').value);
  var idxS  = document.getElementById('indIdx').value;

  if (!place || place < 1) { alert('Please enter a valid placement (1, 2, 3…)'); return; }
  if (!award)               { alert('Please enter an award name.'); return; }
  if (isNaN(pts) || pts < 0){ alert('Please enter a valid points value.'); return; }

  var idx = idxS !== '' ? parseInt(idxS, 10) : null;
  if (idx === null) {
    if (_indRules.some(function (r) { return Number(r.placement) === place; })) {
      alert('A rule for ' + ordinal(place) + ' place already exists.'); return;
    }
    _indRules.push({ pointsID: null, placement: place, award: award, points: pts });
  } else {
    _indRules[idx] = { pointsID: _indRules[idx].pointsID, placement: place, award: award, points: pts };
  }
  _indRules.sort(function (a, b) { return Number(a.placement) - Number(b.placement); });
  closeIndividualModal();
  renderRules();
}

function deleteIndRule(idx) {
  if (!confirm('Remove this individual point rule?')) return;
  _indRules.splice(idx, 1);
  renderRules();
}

// TEAM RULE SUB-MODAL
var _afRows = []; // [{pointsID, label, points}]

function openTeamModal(groupIdx) {
  document.getElementById('teamModalTitle').textContent =
    groupIdx === null ? 'Add Team Category' : 'Edit Team Category';
  document.getElementById('teamIdx').value = groupIdx !== null ? groupIdx : '';
  if (groupIdx !== null) {
    var g = _teamGroups[groupIdx];
    document.getElementById('teamCat').value = g.category || '';
    _afRows = g.rows.map(function (r) {
      return { pointsID: r.pointsID || null, label: r.label || '', points: r.points || '' };
    });
  } else {
    document.getElementById('teamCat').value = '';
    _afRows = [{ pointsID: null, label: '', points: '' }];
  }
  renderAFRows();
  openOverlay('teamModal');
  setTimeout(function () { document.getElementById('teamCat').focus(); }, 60);
}
function closeTeamModal() { closeOverlay('teamModal'); _afRows = []; }

function renderAFRows() {
  var tbody = document.getElementById('afBody');
  var empty = document.getElementById('afEmpty');
  var wrap  = document.querySelector('.af-table-wrap');
  tbody.innerHTML = '';
  if (!_afRows.length) {
    wrap.style.display = 'none'; empty.style.display = 'block'; return;
  }
  wrap.style.display = ''; empty.style.display = 'none';
  _afRows.forEach(function (row, i) {
    var tr = document.createElement('tr');
    tr.innerHTML =
      '<td><input class="admin-input" type="text" value="' + esc(row.label) + '" ' +
        'placeholder="e.g. 5 or more Snr Managers present" ' +
        'oninput="_afRows[' + i + '].label=this.value" ' +
        'style="width:100%;box-sizing:border-box;height:34px;font-size:13px;"></td>' +
      '<td><input class="admin-input" type="number" step="0.01" min="0" ' +
        'value="' + (row.points !== '' ? Number(row.points) : '') + '" placeholder="pts" ' +
        'oninput="_afRows[' + i + '].points=this.value" ' +
        'style="width:100%;box-sizing:border-box;height:34px;font-size:13px;"></td>' +
      '<td style="text-align:center;">' +
        '<button type="button" class="af-remove-btn" onclick="removeAFRow(' + i + ')">' +
          '<i class="material-icons" style="font-size:16px;">remove_circle_outline</i></button>' +
      '</td>';
    tbody.appendChild(tr);
  });
}

function addAFRow() {
  _afRows.push({ pointsID: null, label: '', points: '' });
  renderAFRows();
  var inputs = document.querySelectorAll('#afBody input[type="text"]');
  if (inputs.length) inputs[inputs.length - 1].focus();
}
function removeAFRow(idx) { _afRows.splice(idx, 1); renderAFRows(); }

function saveTeamRule() {
  var cat  = document.getElementById('teamCat').value.trim();
  var idxS = document.getElementById('teamIdx').value;
  if (!cat) { alert('Please enter a category name.'); return; }
  if (!_afRows.length) { alert('Please add at least one condition.'); return; }
  for (var i = 0; i < _afRows.length; i++) {
    if (!_afRows[i].label.trim()) { alert('Row ' + (i+1) + ': description is required.'); return; }
    if (isNaN(parseFloat(_afRows[i].points)) || parseFloat(_afRows[i].points) < 0) {
      alert('Row ' + (i+1) + ': enter a valid points value.'); return;
    }
  }
  var rows = _afRows.map(function (r) {
    return { pointsID: r.pointsID || null, label: r.label.trim(), points: parseFloat(r.points) };
  });
  var idx = idxS !== '' ? parseInt(idxS, 10) : null;
  if (idx === null) {
    if (_teamGroups.some(function (g) { return g.category.toLowerCase() === cat.toLowerCase(); })) {
      alert('A category named "' + cat + '" already exists.'); return;
    }
    _teamGroups.push({ category: cat, rows: rows });
  } else {
    if (_teamGroups.some(function (g, gi) { return gi !== idx && g.category.toLowerCase() === cat.toLowerCase(); })) {
      alert('Another category named "' + cat + '" already exists.'); return;
    }
    _teamGroups[idx].category = cat;
    _teamGroups[idx].rows     = rows;
  }
  closeTeamModal();
  renderRules();
}

function deleteTeamGroup(gi) {
  if (!confirm('Remove the "' + (_teamGroups[gi].category || 'this') + '" category?')) return;
  _teamGroups.splice(gi, 1);
  renderRules();
}