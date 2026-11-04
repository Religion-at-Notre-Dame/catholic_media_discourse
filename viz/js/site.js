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

  const footer = document.getElementById("site-footer");
  if (footer && !footer.childElementCount) {
    fetch("../partials/footer.html")
      .then(function (res) {
        if (!res.ok) throw new Error(String(res.status));
        return res.text();
      })
      .then(function (html) {
        footer.innerHTML = html;
      })
      .catch(function () {});
  }

  var langKey = "viz-example-lang";
  try { window.__exampleLang = sessionStorage.getItem(langKey) || "all"; } catch (e) { window.__exampleLang = "all"; }
  function paintLang() {
    document.querySelectorAll("#lang-switch button").forEach(function (btn) {
      btn.classList.toggle("is-on", btn.getAttribute("data-lang") === window.__exampleLang);
    });
  }
  paintLang();
  var langSwitch = document.getElementById("lang-switch");
  if (langSwitch) {
    langSwitch.addEventListener("click", function (e) {
      var btn = e.target.closest("button[data-lang]");
      if (!btn) return;
      window.__exampleLang = btn.getAttribute("data-lang") || "all";
      sessionStorage.setItem(langKey, window.__exampleLang);
      paintLang();
      document.querySelectorAll("[data-figures]").forEach(function (root) {
        if (typeof window.renderFigures === "function") window.renderFigures(root);
      });
    });
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
