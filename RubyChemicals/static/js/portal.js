/* Portal-wide behaviour. Page scripts never need to call anything here.
 *
 *  - theme toggle (light / dark), persisted in localStorage
 *  - mobile drawer, topbar title and date, active navigation link
 *  - attendance banner (check in / check out) shown on every page
 *  - table cell labels, so list tables can be shown as stacked cards on phones
 */
(function () {
  'use strict';

  var body = document.body;
  var root = document.documentElement;
  var shell = document.querySelector('.app-shell');

  /* ---------------------------------------------------------------- theme */
  var themeBtn = document.getElementById('themeToggle');

  function currentTheme() {
    return root.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
  }

  function applyTheme(theme, persist) {
    root.setAttribute('data-theme', theme);
    root.setAttribute('data-bs-theme', theme);
    if (persist) {
      try { localStorage.setItem('portal-theme', theme); } catch (e) { /* ignore */ }
    }
    if (themeBtn) {
      var next = theme === 'dark' ? 'light' : 'dark';
      themeBtn.setAttribute('aria-label', 'Switch to ' + next + ' mode');
      themeBtn.setAttribute('title', 'Switch to ' + next + ' mode');
    }
  }

  if (themeBtn) {
    applyTheme(currentTheme(), false);
    themeBtn.addEventListener('click', function () {
      applyTheme(currentTheme() === 'dark' ? 'light' : 'dark', true);
    });
  }

  if (!shell) return; // pages without the shell (login) only need the theme

  /* --------------------------------------------------------------- drawer */
  var sidebar = document.getElementById('appSidebar');
  var menuBtn = document.getElementById('appMenuToggle');
  var closeBtn = document.getElementById('appSidebarClose');
  var backdrop = document.getElementById('appBackdrop');

  function setDrawer(open) {
    body.classList.toggle('sidebar-open', open);
    if (menuBtn) menuBtn.setAttribute('aria-expanded', String(open));
    if (open && closeBtn) closeBtn.focus();
    if (!open && menuBtn && window.innerWidth < 992) menuBtn.focus();
  }

  if (menuBtn) menuBtn.addEventListener('click', function () { setDrawer(true); });
  if (closeBtn) closeBtn.addEventListener('click', function () { setDrawer(false); });
  if (backdrop) backdrop.addEventListener('click', function () { setDrawer(false); });
  if (sidebar) {
    sidebar.addEventListener('click', function (e) {
      if (e.target.closest && e.target.closest('a.sb-link')) body.classList.remove('sidebar-open');
    });
  }
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && body.classList.contains('sidebar-open')) setDrawer(false);
  });
  window.addEventListener('resize', function () {
    if (window.innerWidth >= 992 && body.classList.contains('sidebar-open')) {
      body.classList.remove('sidebar-open');
      if (menuBtn) menuBtn.setAttribute('aria-expanded', 'false');
    }
  });

  /* ------------------------------------------------- topbar and identity */
  function normalisePath(p) {
    return (p || '/').replace(/\/+$/, '') || '/';
  }

  (function markActiveLink() {
    var here = normalisePath(location.pathname);
    var best = null;
    var bestLen = -1;
    var links = document.querySelectorAll('.sb-link[href]');
    for (var i = 0; i < links.length; i++) {
      var target = normalisePath(links[i].getAttribute('href'));
      var matches = here === target || (target !== '/' && here.indexOf(target + '/') === 0);
      if (matches && target.length > bestLen) { best = links[i]; bestLen = target.length; }
    }
    if (best) {
      best.classList.add('active');
      best.setAttribute('aria-current', 'page');
    }
  })();

  var titleEl = document.getElementById('tbTitle');
  if (titleEl) titleEl.textContent = (document.title || '').split(' - ')[0].trim();

  var dateEl = document.getElementById('tbDate');
  if (dateEl) {
    var now = new Date();
    dateEl.textContent = now.toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long' });
    dateEl.setAttribute('datetime', now.toISOString());
  }

  var userName = (shell.getAttribute('data-user-name') || '').trim();
  var avatar = document.getElementById('sbAvatar');
  if (avatar && userName) {
    var parts = userName.split(/\s+/);
    avatar.textContent = ((parts[0] || '').charAt(0) + (parts.length > 1 ? parts[parts.length - 1].charAt(0) : '')).toUpperCase();
  }

  var monthEls = document.querySelectorAll('[data-month-year]');
  for (var mi = 0; mi < monthEls.length; mi++) {
    monthEls[mi].textContent = new Date().toLocaleDateString('en-IN', { month: 'long', year: 'numeric' });
  }

  var greetEls = document.querySelectorAll('[data-greeting]');
  if (greetEls.length) {
    var hour = new Date().getHours();
    var part = hour < 12 ? 'morning' : hour < 17 ? 'afternoon' : 'evening';
    var first = userName.split(/\s+/)[0];
    for (var g = 0; g < greetEls.length; g++) {
      greetEls[g].textContent = 'Good ' + part + (first ? ', ' + first : '');
    }
  }

  /* ----------------------------------------------------------- attendance */
  var banner = document.getElementById('attBanner');
  var titleText = document.getElementById('attendance-status-text');
  var subText = document.getElementById('attSub');
  var icon = document.getElementById('attIcon');
  var inBtn = document.getElementById('btn-check-in');
  var outBtn = document.getElementById('btn-check-out');
  var csrf = shell.getAttribute('data-csrf') || '';

  function clock(iso) {
    if (!iso) return '';
    return new Date(iso).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
  }

  function stamp(iso) {
    if (!iso) return '';
    return new Date(iso).toLocaleString('en-IN', {
      day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit'
    });
  }

  function renderAttendance(state, title, sub, iconClass) {
    if (!banner) return;
    banner.setAttribute('data-state', state);
    banner.className = 'att-banner' + (state === 'loading' ? '' : ' is-' + state);
    titleText.textContent = title;
    subText.textContent = sub;
    subText.hidden = !sub;
    icon.className = 'fas ' + iconClass;
    inBtn.hidden = state !== 'pending';
    inBtn.disabled = state !== 'pending';
    outBtn.hidden = state !== 'active';
    outBtn.disabled = state !== 'active';
  }

  function loadAttendance() {
    if (!banner) return;
    fetch('/user-api/attendance-api/', { credentials: 'same-origin' })
      .then(function (res) { return res.json(); })
      .then(function (result) {
        if (!result || !result.success) throw new Error('status unavailable');
        var info = result.data || {};
        var today = info.today || {};
        if (info.has_checked_out_today) {
          renderAttendance('done',
            'Checked out at ' + clock(today.check_out_time),
            'Checked in at ' + clock(today.check_in_time) + '. Have a good evening.',
            'fa-circle-check');
        } else if (info.has_checked_in_today) {
          renderAttendance('active',
            'Checked in at ' + clock(today.check_in_time),
            'Remember to check out when you finish for the day.',
            'fa-clock');
        } else {
          renderAttendance('pending',
            'You have not checked in today',
            info.last_check_out_time
              ? 'Last check-out ' + stamp(info.last_check_out_time) + '. Mark your attendance to start the day.'
              : 'Mark your attendance to start the day.',
            'fa-clock');
        }
      })
      .catch(function () {
        renderAttendance('error', 'Attendance unavailable', 'Could not load your status. Refresh to try again.', 'fa-triangle-exclamation');
      });
  }

  function sendAttendance(url, button, busyLabel) {
    var original = button.innerHTML;
    button.disabled = true;
    button.innerHTML = '<span class="spinner-border spinner-border-sm" aria-hidden="true"></span> ' + busyLabel;
    fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'X-CSRFToken': csrf, 'Content-Type': 'application/json' }
    })
      .then(function (res) { return res.json(); })
      .then(function (result) {
        button.innerHTML = original;
        if (!result.success) {
          subText.textContent = result.error || 'Something went wrong. Please try again.';
          subText.hidden = false;
          button.disabled = false;
          return;
        }
        loadAttendance();
      })
      .catch(function () {
        button.innerHTML = original;
        button.disabled = false;
        subText.textContent = 'Network error. Please try again.';
        subText.hidden = false;
      });
  }

  if (inBtn) inBtn.addEventListener('click', function () { sendAttendance('/user-api/attendance-api/check-in/', inBtn, 'Checking in'); });
  if (outBtn) outBtn.addEventListener('click', function () { sendAttendance('/user-api/attendance-api/check-out/', outBtn, 'Checking out'); });
  loadAttendance();

  /* ---------------------------------------------------------- table labels */
  var TABLE_SELECTOR = '.table-container table, .data-table table';
  var ACTION_HEADER = /^actions?$/i;

  function clean(text) {
    return (text || '').replace(/\s+/g, ' ').trim();
  }

  function headerLabels(table) {
    var head = table.tHead;
    if (!head || !head.rows.length) return null;
    var row = head.rows[head.rows.length - 1];
    var labels = [];
    for (var i = 0; i < row.cells.length; i++) {
      if (row.cells[i].colSpan > 1) return null;
      var text = clean(row.cells[i].textContent);
      labels.push(ACTION_HEADER.test(text) ? 'Actions' : text);
    }
    return labels;
  }

  function labelTable(table) {
    // Item-entry tables inside modals contain inputs: they scroll sideways instead of stacking
    if (table.closest('.modal')) table.classList.add('no-stack');
    if (table.classList.contains('no-stack')) return;
    var labels = headerLabels(table);
    if (!labels) return;

    for (var b = 0; b < table.tBodies.length; b++) {
      var rows = table.tBodies[b].rows;
      for (var r = 0; r < rows.length; r++) {
        var cells = rows[r].cells;
        if (cells.length !== labels.length) continue;
        for (var c = 0; c < cells.length; c++) {
          if (!cells[c].hasAttribute('data-label')) cells[c].setAttribute('data-label', labels[c]);
        }
      }
    }
  }

  function labelAll() {
    var tables = document.querySelectorAll(TABLE_SELECTOR);
    for (var i = 0; i < tables.length; i++) labelTable(tables[i]);
  }

  var scheduled = false;
  function scheduleLabelling() {
    if (scheduled) return;
    scheduled = true;
    var run = function () { scheduled = false; labelAll(); };
    if (window.requestAnimationFrame) window.requestAnimationFrame(run);
    else setTimeout(run, 16);
  }

  labelAll();
  if (window.MutationObserver) {
    // Child-list only: setting data-label attributes does not re-trigger this
    new MutationObserver(scheduleLabelling).observe(document.body, { childList: true, subtree: true });
  }
})();
