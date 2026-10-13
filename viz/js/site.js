/* Shared classroom site helpers (multi-page). */
(function () {
  if (document.body.classList.contains("mode-findings")) {
    function tryRender() {
      if (typeof window.renderFindings === "function") window.renderFindings();
    }
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", tryRender);
    } else {
      tryRender();
    }
    window.addEventListener("load", tryRender);
  }

  if (document.body.classList.contains("mode-triage")) {
    function tryTriage() {
      if (typeof window.renderTriage === "function") window.renderTriage();
    }
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", tryTriage);
    } else {
      tryTriage();
    }
    window.addEventListener("load", tryTriage);
  }

  document.querySelectorAll("a.cta, a.act").forEach(function (a) {
    a.addEventListener("keydown", function (e) {
      if (e.key === " ") {
        e.preventDefault();
        a.click();
      }
    });
  });
})();
