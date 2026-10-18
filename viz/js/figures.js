/* Interactive paper figures: charts + dual-taxonomy examples. */
(function () {
  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function pretty(id) {
    const map = {
      cst_papal: "CST / papal",
      doctrine_sacrament: "Doctrine / sacrament",
      institutional_news: "Institutional news",
      moral_ethics: "Moral / ethics",
      devotion_piety: "Devotion / piety",
      migration_politics: "Migration / politics",
      evangelization_mission: "Evangelization / mission",
      misunderstanding: "Misunderstanding",
      other_unclear: "Other / unclear",
      liberation_theology: "Liberation theology",
      doctrinal_claim: "Doctrinal claim",
      factual_claim: "Factual claim",
      news_report: "News report",
      opinion_editorial: "Opinion",
      advocacy: "Advocacy",
      homily_devotional: "Homily / devotion",
      question: "Question",
      interview_dialogue: "Interview",
      other_mixed: "Other / mixed",
      mission: "Mission",
      gospel: "Gospel",
      guadalupe: "Guadalupe",
    };
    if (!id) return "";
    if (map[id]) return map[id];
    return String(id).replace(/_/g, " ");
  }

  function chips(labels, kind) {
    return (labels || [])
      .map(function (x) {
        return (
          '<span class="figboard-chip figboard-chip--' +
          esc(kind) +
          '">' +
          esc(pretty(x)) +
          "</span>"
        );
      })
      .join("");
  }

  function panelFromHash(panels) {
    try {
      const h = (location.hash || "").replace(/^#/, "");
      const q = h.indexOf("?") >= 0 ? h.split("?")[1] : "";
      const params = new URLSearchParams(q || (location.search || "").replace(/^\?/, ""));
      const want = params.get("panel") || (h.match(/^fig-([a-z]+)/) || [])[1];
      if (want && panels.some(function (p) { return p.id === want; })) return want;
      // allow #chile etc. when on figures section pages
      if (h && panels.some(function (p) { return p.id === h; })) return h;
    } catch (e) { /* ignore */ }
    return null;
  }

  function stateFor(root) {
    if (!root._figState) {
      const panels = (window.FIGURES && window.FIGURES.panels) || [];
      root._figState = {
        panelId: panelFromHash(panels) || (panels[0] && panels[0].id) || null,
        filterKey: null,
        filterVal: null,
        filterLabel: null,
        exId: null,
      };
    }
    return root._figState;
  }

  function matchingExamples(G, panel, filterKey, filterVal) {
    const tags = (panel && panel.exampleTags) || [];
    let rows = (G.examples || []).filter(function (ex) {
      const et = ex.tags || [];
      return tags.some(function (t) {
        return et.indexOf(t) >= 0;
      });
    });
    if (!rows.length) rows = G.examples || [];
    if (filterKey === "content" && filterVal) {
      const hit = rows.filter(function (ex) {
        return (ex.content || []).indexOf(filterVal) >= 0;
      });
      if (hit.length) return hit;
    }
    if (filterKey === "theme" && filterVal) {
      const key = String(filterVal).toLowerCase();
      const hit = rows.filter(function (ex) {
        const blob = (
          (ex.content || []).join(" ") +
          " " +
          (ex.tags || []).join(" ") +
          " " +
          (ex.text || "")
        ).toLowerCase();
        return blob.indexOf(key.replace(/_/g, " ")) >= 0 || blob.indexOf(key) >= 0;
      });
      if (hit.length) return hit;
    }
    if (filterKey === "place" && filterVal) {
      const key = String(filterVal).toLowerCase();
      const hit = rows.filter(function (ex) {
        const blob = ((ex.tags || []).join(" ") + " " + (ex.text || "")).toLowerCase();
        return blob.indexOf(key) >= 0;
      });
      if (hit.length) return hit;
    }
    return rows;
  }

  function educatorCards(T) {
    const h = (T && T.hooks) || {};
    const cards = [
      {
        key: "news",
        big: (h.institutional_vs_doctrine || "~31.8% institutional vs ~3.1% doctrine").split(
          " vs "
        )[0],
        label: "Institutional news",
        body: "Headlines first",
        filterKey: "content",
        filterVal: "institutional_news",
        filterLabel: "Institutional news",
      },
      {
        key: "mis",
        big: "~" + (h.misunderstanding_pct != null ? h.misunderstanding_pct : "3") + "%",
        label: "Misunderstanding",
        body: "Gentle correction",
        filterKey: "content",
        filterVal: "misunderstanding",
        filterLabel: "Misunderstanding",
      },
      {
        key: "place",
        big: (h.place_hook || "El Salvador · Devotion").split("(")[0].trim(),
        label: "Place × type",
        body: "Distinctive lift",
        filterKey: "place",
        filterVal: "salvador",
        filterLabel: "El Salvador",
      },
      {
        key: "types",
        big: "OR " + (((h.types_together || "").match(/OR\s+([\d.]+)/) || [])[1] || "15.7"),
        label: "Types together",
        body: "CST × moral/ethics",
        filterKey: "content",
        filterVal: "cst_papal",
        filterLabel: "CST / papal",
      },
    ];
    return (
      '<div class="figboard-cards">' +
      cards
        .map(function (c) {
          return (
            '<button type="button" class="figboard-card" data-filter-key="' +
            esc(c.filterKey) +
            '" data-filter-val="' +
            esc(c.filterVal) +
            '" data-filter-label="' +
            esc(c.filterLabel) +
            '"><b>' +
            esc(c.big) +
            "</b><span>" +
            esc(c.label) +
            "</span><small>" +
            esc(c.body) +
            "</small></button>"
          );
        })
        .join("") +
      "</div>"
    );
  }

  function barChart(rows) {
    const max = Math.max.apply(
      null,
      rows
        .map(function (r) {
          return Number(r.v) || 0;
        })
        .concat([1])
    );
    return (
      '<div class="figboard-bars" role="list">' +
      rows
        .map(function (r) {
          const w = Math.max(6, Math.round((100 * (Number(r.v) || 0)) / max));
          return (
            '<button type="button" class="figboard-bar" role="listitem" data-filter-key="' +
            esc(r.filterKey || "content") +
            '" data-filter-val="' +
            esc(r.filterVal || r.id || "") +
            '" data-filter-label="' +
            esc(r.filterLabel || r.label || "") +
            '"><span class="figboard-bar__name">' +
            esc(r.label) +
            '</span><span class="figboard-bar__track"><i style="width:' +
            w +
            '%"></i></span><span class="figboard-bar__val">' +
            esc(r.display != null ? r.display : r.v) +
            "</span></button>"
          );
        })
        .join("") +
      "</div>"
    );
  }

  function chartHtml(panel, T, F) {
    const kind = panel.chart;
    if (kind === "educator") return educatorCards(T);

    if (kind === "taxonomy") {
      const counts = (T && T.content_counts) || {};
      const rows = Object.keys(counts)
        .map(function (k) {
          return {
            id: k,
            label: pretty(k),
            v: counts[k],
            display: Number(counts[k]).toLocaleString(),
            filterKey: "content",
            filterVal: k,
            filterLabel: pretty(k),
          };
        })
        .sort(function (a, b) {
          return b.v - a.v;
        })
        .slice(0, 8);
      return barChart(rows);
    }

    if (kind === "place") {
      const rows = ((T && T.place_lifts) || [])
        .filter(function (r) {
          return r.significant;
        })
        .slice(0, 10)
        .map(function (r) {
          const loc = r.location || "";
          let fv = String(loc).toLowerCase();
          if (/el salvador/i.test(loc)) fv = "salvador";
          if (/mexico/i.test(loc)) fv = "guadalupe";
          return {
            id: r.label,
            label: loc + " · " + pretty(r.label),
            v: Number(r.lift_vs_geo_news) || 0,
            display: (Number(r.lift_vs_geo_news) || 0).toFixed(2) + "×",
            filterKey: "place",
            filterVal: fv,
            filterLabel: loc + " · " + pretty(r.label),
          };
        });
      return barChart(rows.length ? rows : [{ label: "No lifts yet", v: 1, display: "n/a" }]);
    }

    if (kind === "types") {
      const rows = ((T && T.types_together) || []).slice(0, 8).map(function (r) {
        return {
          id: r.a,
          label: pretty(r.a) + " × " + pretty(r.b),
          v: Number(r.odds_ratio) || Number(r.lift) || 0,
          display: "OR " + (Number(r.odds_ratio) || 0).toFixed(1),
          filterKey: "content",
          filterVal: r.a,
          filterLabel: pretty(r.a) + " × " + pretty(r.b),
        };
      });
      return barChart(rows.length ? rows : [{ label: "No pairs yet", v: 1, display: "n/a" }]);
    }

    if (kind === "lang") {
      const rows = ((T && T.lang_contrast) || [])
        .filter(function (r) {
          return r.significant;
        })
        .slice(0, 8)
        .map(function (r) {
          const raw = r.label;
          const snake =
            typeof raw === "string" && raw.indexOf(" ") < 0
              ? raw
              : String(raw || "")
                  .toLowerCase()
                  .replace(/\s*\/\s*/g, "_")
                  .replace(/\s+/g, "_");
          return {
            id: raw,
            label: pretty(raw),
            v: Number(r.rate_ratio) || Number(r.odds_ratio) || 0,
            display:
              "EN " +
              (r.rate_a_pct != null ? r.rate_a_pct : "?") +
              "% / ES " +
              (r.rate_b_pct != null ? r.rate_b_pct : "?") +
              "%",
            filterKey: "content",
            filterVal: snake,
            filterLabel: pretty(raw),
          };
        });
      return barChart(rows.length ? rows : [{ label: "No contrasts yet", v: 1, display: "n/a" }]);
    }

    if (kind === "chile") {
      const lifts = ((F && F.santiago) || {}).lifts || [];
      const rows = lifts.map(function (d) {
        return {
          id: d.theme_id || d.theme,
          label: d.theme || pretty(d.theme_id),
          v: Number(d.x) || 0,
          display: "~" + d.x + "×",
          filterKey: "theme",
          filterVal: d.theme_id || d.theme,
          filterLabel: d.theme || pretty(d.theme_id),
        };
      });
      return barChart(rows.length ? rows : [{ label: "Chile lifts loading…", v: 1, display: "n/a" }]);
    }

    if (kind === "country") {
      const sigs = (F && F.signatures) || [];
      const rows = sigs.map(function (s) {
        let fv = String(s.place || "")
          .toLowerCase()
          .replace(/\s+/g, " ");
        if (/el salvador/i.test(fv)) fv = "salvador";
        if (/mexico/i.test(fv)) fv = "guadalupe";
        if (/brazil/i.test(fv)) fv = "aparecida";
        return {
          id: s.theme_id || s.theme,
          label: (s.place || "") + " · " + (s.theme || pretty(s.theme_id)),
          v: Number(s.lift) || 0,
          display: "~" + s.lift + "×",
          filterKey: "place",
          filterVal: fv,
          filterLabel: (s.place || "") + " · " + (s.theme || ""),
        };
      });
      return barChart(rows.length ? rows : [{ label: "Signatures loading…", v: 1, display: "n/a" }]);
    }

    return '<p class="f-note">Chart unavailable for this panel.</p>';
  }

  function renderExamples(el, examples, activeId) {
    if (!el) return;
    if (!examples.length) {
      el.innerHTML = '<p class="f-note">No matching examples for this filter.</p>';
      return;
    }
    el.innerHTML = examples
      .map(function (ex) {
        const active = ex.id === activeId ? " is-active" : "";
        return (
          '<article class="figboard-ex' +
          active +
          '" data-ex="' +
          esc(ex.id) +
          '" tabindex="0">' +
          '<p class="figboard-ex__lang">' +
          esc((ex.lang || "en").toUpperCase()) +
          "</p>" +
          "<blockquote>" +
          esc(ex.text) +
          "</blockquote>" +
          '<div class="figboard-ex__labels">' +
          chips(ex.content, "c") +
          chips(ex.discourse, "d") +
          "</div>" +
          '<p class="figboard-ex__why">' +
          esc(ex.why || "") +
          "</p>" +
          "</article>"
        );
      })
      .join("");
  }

  function linkLabel(panel) {
    if (!panel || !panel.href) return "Explore related view →";
    if (panel.href.indexOf("explore") >= 0) return "Open Santiago on the map →";
    if (panel.href.indexOf("findings") >= 0) return "Open Findings →";
    if (panel.href.indexOf("triage") >= 0) return "Open Triage →";
    return "Open related view →";
  }

  function paint(root) {
    const G = window.FIGURES;
    if (!G || !root) return;
    const T = window.TRIAGE || {};
    const F = window.FINDINGS || {};
    const st = stateFor(root);
    const panels = G.panels || [];
    if (!st.panelId && panels[0]) st.panelId = panels[0].id;
    const panel =
      panels.find(function (p) {
        return p.id === st.panelId;
      }) || panels[0];
    if (!panel) return;

    const tabs = root.querySelector("[data-fig-tabs]");
    const chart = root.querySelector("[data-fig-chart]");
    const img = root.querySelector("[data-fig-img]");
    const blurb = root.querySelector("[data-fig-blurb]");
    const filterEl = root.querySelector("[data-fig-filter]");
    const examples = root.querySelector("[data-fig-examples]");
    const link = root.querySelector("[data-fig-link]");
    const countEl = root.querySelector("[data-fig-count]");

    if (tabs) {
      tabs.innerHTML = panels
        .map(function (p) {
          return (
            '<button type="button" class="figboard-tab' +
            (p.id === panel.id ? " is-active" : "") +
            '" data-panel="' +
            esc(p.id) +
            '"><span>' +
            esc(p.kicker) +
            "</span><strong>" +
            esc(p.title) +
            "</strong></button>"
          );
        })
        .join("");
    }
    if (blurb) {
      blurb.innerHTML =
        '<p class="kicker">' +
        esc(panel.kicker) +
        "</p><h3>" +
        esc(panel.title) +
        '</h3><p class="f-note">' +
        esc(panel.blurb) +
        "</p>";
    }
    if (chart) chart.innerHTML = chartHtml(panel, T, F);
    if (img) {
      const src = (G.assetBase || "../assets/figures/") + panel.image;
      img.innerHTML =
        "<details class=\"figboard-slide\">" +
        "<summary>Paper slide companion</summary>" +
        '<img src="' +
        esc(src) +
        '" alt="' +
        esc(panel.title) +
        '" loading="lazy" />' +
        "</details>";
    }
    if (link) {
      link.href = panel.href || "triage.html";
      link.textContent = linkLabel(panel);
    }

    const exs = matchingExamples(G, panel, st.filterKey, st.filterVal);
    if (filterEl) {
      if (st.filterKey && st.filterVal) {
        filterEl.innerHTML =
          '<span class="figboard-filter__on">Showing · <strong>' +
          esc(st.filterLabel || pretty(st.filterVal) || st.filterVal) +
          '</strong></span> <button type="button" class="figboard-filter__clear" data-clear-filter>Clear</button>';
        filterEl.hidden = false;
      } else {
        filterEl.innerHTML =
          '<span class="figboard-filter__hint">Click a card or bar to filter examples</span>';
        filterEl.hidden = false;
      }
    }
    if (countEl) {
      countEl.textContent = exs.length + (exs.length === 1 ? " example" : " examples");
    }
    renderExamples(examples, exs, st.exId);

    root.querySelectorAll(".figboard-card, .figboard-bar").forEach(function (btn) {
      const fk = btn.getAttribute("data-filter-key");
      const fv = btn.getAttribute("data-filter-val");
      if (fk && fv && fk === st.filterKey && fv === st.filterVal) {
        btn.classList.add("is-active");
      }
    });
  }

  function bind(root) {
    if (root.dataset.bound === "1") return;
    root.dataset.bound = "1";
    root.addEventListener("click", function (e) {
      if (e.target.closest("[data-clear-filter]")) {
        const st = stateFor(root);
        st.filterKey = null;
        st.filterVal = null;
        st.filterLabel = null;
        st.exId = null;
        paint(root);
        return;
      }
      const tab = e.target.closest("[data-panel]");
      if (tab && root.contains(tab)) {
        const st = stateFor(root);
        st.panelId = tab.getAttribute("data-panel");
        st.filterKey = null;
        st.filterVal = null;
        st.filterLabel = null;
        st.exId = null;
        paint(root);
        return;
      }
      const filt = e.target.closest("[data-filter-key]");
      if (filt && root.contains(filt)) {
        const st = stateFor(root);
        st.filterKey = filt.getAttribute("data-filter-key");
        st.filterVal = filt.getAttribute("data-filter-val");
        st.filterLabel = filt.getAttribute("data-filter-label");
        st.exId = null;
        paint(root);
        return;
      }
      const ex = e.target.closest("[data-ex]");
      if (ex && root.contains(ex)) {
        const st = stateFor(root);
        st.exId = ex.getAttribute("data-ex");
        paint(root);
      }
    });
    root.addEventListener("keydown", function (e) {
      const ex = e.target.closest("[data-ex]");
      if (ex && (e.key === "Enter" || e.key === " ")) {
        e.preventDefault();
        ex.click();
      }
    });
  }

  function mount(sel) {
    const root = typeof sel === "string" ? document.querySelector(sel) : sel;
    if (!root || !window.FIGURES) return;
    if (!root.querySelector("[data-fig-tabs]")) {
      root.innerHTML =
        '<div class="figboard">' +
        '<div class="figboard-tabs" data-fig-tabs role="tablist" aria-label="Figure panels"></div>' +
        '<div class="figboard-body">' +
        '<div class="figboard-main">' +
        '<div data-fig-blurb></div>' +
        '<div class="figboard-chart" data-fig-chart></div>' +
        '<div class="figboard-filter" data-fig-filter></div>' +
        '<div class="figboard-img" data-fig-img></div>' +
        '<p class="figboard-cta"><a class="cta" data-fig-link href="triage.html">Open Triage →</a></p>' +
        "</div>" +
        '<aside class="figboard-side">' +
        '<div class="figboard-side__head">' +
        '<div><p class="kicker">Examples · dual taxonomy</p>' +
        "<h3>Media vignettes</h3></div>" +
        '<p class="figboard-count" data-fig-count></p>' +
        "</div>" +
        '<p class="f-note">EN / ES / PT excerpts with content and discourse labels. Not Theology gold.</p>' +
        '<div class="figboard-examples" data-fig-examples></div>' +
        "</aside>" +
        "</div></div>";
    }
    bind(root);
    paint(root);
  }

  window.renderFigures = function () {
    document.querySelectorAll("[data-figures]").forEach(mount);
  };

  function boot() {
    if (window.FIGURES) window.renderFigures();
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
  window.addEventListener("load", boot);
})();
