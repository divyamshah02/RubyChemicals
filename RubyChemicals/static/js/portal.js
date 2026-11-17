/* Portal-wide helpers. Page scripts never need to call anything here.
 *
 * Table labels: on phones, list tables inside .table-container / .data-table are shown as
 * stacked cards (see portal.css). Each cell needs a data-label taken from its column header.
 * Pages render rows dynamically, so labels are applied now and again whenever rows change.
 */
(function () {
  'use strict';

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
          if (!cells[c].hasAttribute('data-label')) {
            cells[c].setAttribute('data-label', labels[c]);
          }
        }
      }
    }
  }

  function labelAll(root) {
    var scope = root && root.querySelectorAll ? root : document;
    var tables = scope.querySelectorAll(TABLE_SELECTOR);
    for (var i = 0; i < tables.length; i++) labelTable(tables[i]);
    if (scope.matches && scope.matches(TABLE_SELECTOR)) labelTable(scope);
  }

  var scheduled = false;
  function scheduleLabelling() {
    if (scheduled) return;
    scheduled = true;
    var run = function () {
      scheduled = false;
      labelAll(document);
    };
    if (window.requestAnimationFrame) window.requestAnimationFrame(run);
    else setTimeout(run, 16);
  }

  function start() {
    labelAll(document);
    if (!window.MutationObserver) return;
    // Only child-list changes: setting data-label attributes does not re-trigger this
    new MutationObserver(scheduleLabelling).observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();
})();
