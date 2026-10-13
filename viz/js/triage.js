/* Informal-learning triage lab: significant contrasts + Jev networks. */
(function () {
  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function pct(n) {
    if (n == null || Number.isNaN(n)) return "—";
    return (Math.round(10 * n) / 10).toFixed(1).replace(/\.0$/, "") + "%";
  }

  function badge(r) {
    const st = r && r.stars ? String(r.stars) : "";
    if (!st || st === "ns") {
      return '<span class="triage-badge triage-badge--ns">ns</span>';
    }
    return '<span class="triage-badge triage-badge--sig">' + esc(st) + "</span>";
  }

  function pTxt(r) {
    if (r == null || r.p_holm == null) return "";
    const p = Number(r.p_holm);
    if (Number.isNaN(p)) return "";
    if (p < 0.001) return "p_holm&lt;0.001";
    return "p_holm=" + p.toFixed(3);
  }

  function preferSig(rows) {
    const all = rows || [];
    const sig = all.filter(function (r) {
      return r.significant;
    });
    return sig.length ? sig : all;
  }

  function renderHooks(el, T) {
    if (!el) return;
    const h = T.hooks || {};
    const st = T.stats || {};
    el.innerHTML =
      '<p class="kicker">Education · priors from media</p>' +
      "<h3>What learners may already “know”</h3>" +
      '<p class="f-note">' +
      esc(T.note || "") +
      (h.stats_note ? " · " + esc(h.stats_note) : "") +
      "</p>" +
      '<div class="triage-hooks">' +
      '<div class="triage-hook"><strong>' +
      esc(h.institutional_vs_doctrine || "—") +
      "</strong><span>content mix</span></div>" +
      '<div class="triage-hook"><strong>~' +
      esc(String(h.misunderstanding_pct != null ? h.misunderstanding_pct : "—")) +
      "%</strong><span>misunderstanding queue</span></div>" +
      '<div class="triage-hook"><strong>' +
      esc(h.place_hook || "—") +
      "</strong><span>place × type (Fisher+Holm)</span></div>" +
      '<div class="triage-hook"><strong>' +
      esc(h.types_together || "—") +
      "</strong><span>types together (sig)</span></div>" +
      "</div>" +
      '<p class="f-note triage-stats-line">' +
      "Test: " +
      esc(st.test || "Fisher exact") +
      " · " +
      esc(st.multiple_testing || "Holm–Bonferroni") +
      " · α=" +
      esc(st.alpha != null ? st.alpha : 0.05) +
      " · sig pairs " +
      esc(st.n_sig_content_pairs != null ? st.n_sig_content_pairs : "—") +
      " · sig place edges " +
      esc(st.n_sig_place_lifts != null ? st.n_sig_place_lifts : "—") +
      "</p>";
  }

  function renderContrast(el, title, rows, fmt) {
    if (!el) return;
    const body = preferSig(rows)
      .slice(0, 8)
      .map(fmt)
      .join("");
    el.innerHTML =
      '<p class="kicker">Difference</p><h3>' +
      esc(title) +
      "</h3>" +
      (body
        ? '<ul class="triage-list">' + body + "</ul>"
        : '<p class="f-note">No contrasts yet — rebuild correlations.</p>');
  }

  function renderHotspots(el, rows) {
    renderContrast(el, "Misunderstanding hotspots (vs rest of geo news)", rows, function (r) {
      return (
        "<li>" +
        badge(r) +
        " <strong>" +
        esc(r.location) +
        "</strong> · " +
        pct(r.misunderstanding_pct) +
        " <span class=\"f-note\">vs " +
        pct(r.baseline_pct) +
        " · OR " +
        esc(r.odds_ratio != null ? r.odds_ratio : "—") +
        " · " +
        pTxt(r) +
        "</span></li>"
      );
    });
  }

  function renderPlaces(el, rows) {
    renderContrast(el, "Place × teaching type (country vs rest)", rows, function (r) {
      return (
        "<li>" +
        badge(r) +
        " <strong>" +
        esc(r.location) +
        "</strong> · " +
        esc(String(r.label).replace(/_/g, " ")) +
        " · <b>" +
        esc(r.lift_vs_geo_news) +
        "×</b> <span class=\"f-note\">OR " +
        esc(r.odds_ratio != null ? r.odds_ratio : "—") +
        " · " +
        pct(r.rate_pct) +
        " vs " +
        pct(r.baseline_pct) +
        " · " +
        pTxt(r) +
        "</span></li>"
      );
    });
  }

  function renderPairs(el, title, rows) {
    renderContrast(el, title, rows, function (r) {
      return (
        "<li>" +
        badge(r) +
        " <strong>" +
        esc(String(r.a).replace(/_/g, " ")) +
        " × " +
        esc(String(r.b).replace(/_/g, " ")) +
        "</strong> · lift " +
        esc(r.lift) +
        " <span class=\"f-note\">OR " +
        esc(r.odds_ratio != null ? r.odds_ratio : "—") +
        " · n=" +
        esc(r.n) +
        " · " +
        pTxt(r) +
        "</span></li>"
      );
    });
  }

  function renderLang(el, rows) {
    renderContrast(el, "English vs Spanish (Fisher+Holm)", rows, function (r) {
      const lean =
        r.ratio_a_over_b >= 1
          ? "EN heavier"
          : "ES heavier";
      return (
        "<li>" +
        badge(r) +
        " <strong>" +
        esc(String(r.label).replace(/_/g, " ")) +
        "</strong> · EN " +
        pct(r.rate_a_pct) +
        " / ES " +
        pct(r.rate_b_pct) +
        " · " +
        esc(lean) +
        " <span class=\"f-note\">OR " +
        esc(r.odds_ratio != null ? r.odds_ratio : "—") +
        " · " +
        pTxt(r) +
        "</span></li>"
      );
    });
  }

  function networkBundle(T, mode) {
    const nets = (T.networks || {})[mode] || { nodes: [], edges: [] };
    const edges = (nets.edges || []).filter(function (e) {
      return e.significant !== false;
    });
    const useEdges = edges.length ? edges : nets.edges || [];
    const keep = {};
    useEdges.forEach(function (e) {
      keep[e.source] = true;
      keep[e.target] = true;
    });
    return {
      nodes: (nets.nodes || [])
        .filter(function (n) {
          return keep[n.id];
        })
        .map(function (n) {
          return Object.assign({}, n);
        }),
      edges: useEdges.map(function (e) {
        return Object.assign({}, e);
      }),
    };
  }

  function drawNetwork(svgEl, T, mode) {
    if (!svgEl || typeof d3 === "undefined") return;
    const data = networkBundle(T, mode);
    const wrap = svgEl.parentElement;
    const w = (wrap && wrap.clientWidth) || 720;
    const h = 440;
    const svg = d3.select(svgEl);
    svg.selectAll("*").remove();
    svg.attr("viewBox", "0 0 " + w + " " + h).attr("width", "100%").attr("height", h);

    if (!data.nodes.length) {
      svg
        .append("text")
        .attr("x", w / 2)
        .attr("y", h / 2)
        .attr("text-anchor", "middle")
        .attr("fill", "#5a6a7a")
        .text("No significant network edges — rebuild analyze_jev_correlations.py");
      return;
    }

    const byId = {};
    data.nodes.forEach(function (n) {
      byId[n.id] = n;
    });
    const links = data.edges
      .filter(function (e) {
        return byId[e.source] && byId[e.target];
      })
      .map(function (e) {
        return {
          source: e.source,
          target: e.target,
          lift: e.lift || 1,
          n: e.n || 1,
          type: e.type,
          significant: e.significant !== false,
          stars: e.stars || "",
          p_holm: e.p_holm,
          odds_ratio: e.odds_ratio,
        };
      });

    const color = {
      content: "#0a843d",
      discourse: "#1c4f8f",
      place: "#c99700",
    };

    const sim = d3
      .forceSimulation(data.nodes)
      .force(
        "link",
        d3
          .forceLink(links)
          .id(function (d) {
            return d.id;
          })
          .distance(function (d) {
            return 95 / Math.sqrt(d.lift || 1);
          })
          .strength(0.5)
      )
      .force("charge", d3.forceManyBody().strength(-210))
      .force("center", d3.forceCenter(w / 2, h / 2))
      .force("collide", d3.forceCollide(20));

    const g = svg.append("g");
    const link = g
      .append("g")
      .selectAll("line")
      .data(links)
      .join("line")
      .attr("stroke", function (d) {
        return d.significant ? "rgba(12,35,64,.42)" : "rgba(12,35,64,.18)";
      })
      .attr("stroke-width", function (d) {
        return Math.min(7, 0.9 + Math.log1p(d.lift));
      });

    const node = g
      .append("g")
      .selectAll("g")
      .data(data.nodes)
      .join("g")
      .call(
        d3
          .drag()
          .on("start", function (event, d) {
            if (!event.active) sim.alphaTarget(0.25).restart();
            d.fx = d.x;
            d.fy = d.y;
          })
          .on("drag", function (event, d) {
            d.fx = event.x;
            d.fy = event.y;
          })
          .on("end", function (event, d) {
            if (!event.active) sim.alphaTarget(0);
            d.fx = null;
            d.fy = null;
          })
      );

    node
      .append("circle")
      .attr("r", function (d) {
        return 6 + Math.min(14, Math.sqrt(d.n || 1) / 8);
      })
      .attr("fill", function (d) {
        return color[d.type] || "#0c2340";
      })
      .attr("stroke", "#fff")
      .attr("stroke-width", 1.2);

    node.append("title").text(function (d) {
      return d.label + " · n=" + d.n + " · " + d.type;
    });

    link.append("title").text(function (d) {
      return (
        "lift " +
        d.lift +
        (d.odds_ratio != null ? " · OR " + d.odds_ratio : "") +
        (d.p_holm != null ? " · p_holm " + d.p_holm : "") +
        " " +
        (d.stars || "")
      );
    });

    node
      .append("text")
      .text(function (d) {
        return d.label;
      })
      .attr("x", 10)
      .attr("y", 3)
      .attr("font-size", 10)
      .attr("fill", "#0c2340");

    sim.on("tick", function () {
      link
        .attr("x1", function (d) {
          return d.source.x;
        })
        .attr("y1", function (d) {
          return d.source.y;
        })
        .attr("x2", function (d) {
          return d.target.x;
        })
        .attr("y2", function (d) {
          return d.target.y;
        });
      node.attr("transform", function (d) {
        return "translate(" + d.x + "," + d.y + ")";
      });
    });
  }

  window.renderTriage = function () {
    const T = window.TRIAGE;
    if (!T) return;
    const root = document.getElementById("triage");
    if (!root || root.dataset.ready === "1") return;
    renderHooks(document.getElementById("t-hooks"), T);
    renderPlaces(document.getElementById("t-places"), T.place_lifts);
    renderHotspots(document.getElementById("t-mis"), T.misunderstanding_hotspots);
    renderLang(document.getElementById("t-lang"), T.lang_contrast);
    renderPairs(document.getElementById("t-pairs"), "Types that travel together", T.types_together);
    renderPairs(
      document.getElementById("t-cross"),
      "Content × discourse",
      T.content_x_discourse
    );

    const svg = document.getElementById("t-network");
    const modeSel = document.getElementById("t-network-mode");
    function redraw() {
      drawNetwork(svg, T, (modeSel && modeSel.value) || "place_x_type");
    }
    if (modeSel) modeSel.addEventListener("change", redraw);
    redraw();
    root.dataset.ready = "1";
  };
})();
