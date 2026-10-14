/* Shared classroom site helpers (multi-page). */
(function () {
  function boot(modeClass, fnName) {
    if (!document.body.classList.contains(modeClass)) return;
    function tryRender() {
      if (typeof window[fnName] === "function") window[fnName]();
    }
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", tryRender);
    } else {
      tryRender();
    }
    window.addEventListener("load", tryRender);
  }

  boot("mode-story", "renderStory");
  boot("mode-findings", "renderFindings");
  boot("mode-triage", "renderTriage");
  boot("mode-story", "renderFigures");
  boot("mode-findings", "renderFigures");
  boot("mode-triage", "renderFigures");

  document.querySelectorAll("a.cta, a.act").forEach(function (a) {
    a.addEventListener("keydown", function (e) {
      if (e.key === " ") {
        e.preventDefault();
        a.click();
      }
    });
  });
})();
