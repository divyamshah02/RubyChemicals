/* Runs synchronously in <head> so the saved theme is applied before first paint (no flash).
 * Light is the default; dark is used only after the user switches to it with the theme toggle. */
(function () {
  var theme = 'light';
  try {
    if (localStorage.getItem('portal-theme') === 'dark') theme = 'dark';
  } catch (e) {
    /* storage can be blocked; light is a safe default */
  }
  var root = document.documentElement;
  root.setAttribute('data-theme', theme);
  root.setAttribute('data-bs-theme', theme);
})();
