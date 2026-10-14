/* Informal-learning triage: plain-language contrasts + readable connection maps. */
(function () {
  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function pretty(id) {
    return String(id == null ? "" : id).replace(/_/g, " ");
  }

  function pct(n) {
    if (n == null || Number.isNaN(n)) return "n/a";
    return (Math.round(10 * n) / 10).toFixed(1).replace(/\.0$/, "") + "%";
  }

  function signalBadge(r) {
    const st = r && r.stars ? String(r.stars) : "";
    if (!st || st === "ns" || r.significant === false) {
      return '<span class="triage-badge triage-badge--ns" title="Not clearly stronger than chance">Unclear</span>';
    }
    if (st.indexOf("***") >= 0) {
      return '<span class="triage-badge triage-badge--strong" title="Very clear pattern after multiple-testing check">Strong signal</span>';
    }
    if (st.indexOf("**") >= 0) {
      return '<span class="triage-badge triage-badge--clear" title="Clear pattern after multiple-testing check">Clear signal</span>';
    }
    return '<span class="triage-badge triage-badge--modest" title="Modest pattern after multiple-testing check">Modest signal</span>';
  }

  function preferSig(rows) {
    const all = rows || [];
    const sig = all.filter(function (r) {
      return r.significant;
    });
    return sig.length ? sig : all;
  }

  function plainHook(s, fallback) {
    let t = String(s || fallback || "").trim();
    if (!t) return fallback || "";
    // Drop stats jargon meant for Methods, keep the human phrase.
    t = t.replace(/\s*\([^)]*(?:lift|OR|Holm|\*\*\*)[^)]*\)/gi, "");
    t = t.replace(/\s*·\s*[^·]*(?:lift|OR|Holm|\*\*\*)[^·]*/gi, "");
    t = t.replace(/\s*[×x]\s*/g, " with ");
    t = t.replace(/\s{2,}/g, " ").trim();
    return t || fallback || "";
  }

  function renderHooks(el, T) {
    if (!el) return;
    const h = T.hooks || {};
    const n = T.n != null ? Number(T.n).toLocaleString() : "many";
    const place = plainHook(h.place_hook, "Place accents vary");
    const together = plainHook(h.types_together, "Themes travel together");
    el.innerHTML =
      '<p class="kicker">1 · Headlines</p>' +
      "<h3>What stands out in the labeled sample</h3>" +
      '<p class="f-note">About ' +
      esc(n) +
      " media excerpts, dual-labeled for what is taught and how it is said. " +
      "Use these as Week-0 listening cues, not as a census of all Catholic media.</p>" +
      '<div class="triage-hooks">' +
      '<div class="triage-hook"><strong>' +
      esc(plainHook(h.institutional_vs_doctrine, "Institutional news dominates")) +
      "</strong><span>Learners meet headlines first</span></div>" +
      '<div class="triage-hook"><strong>~' +
      esc(String(h.misunderstanding_pct != null ? h.misunderstanding_pct : "3")) +
      "%</strong><span>Gentle-correction queue</span></div>" +
      '<div class="triage-hook"><strong>' +
      esc(place) +
      "</strong><span>Country accents a teaching type</span></div>" +
      '<div class="triage-hook"><strong>' +
      esc(together) +
      "</strong><span>Themes that travel together</span></div>" +
      "</div>" +
      '<p class="f-note triage-stats-line">' +
      "Signal badges below mean “clearer than chance” after a careful check. " +
      "They are not Theology gold grades.</p>";
  }

  function renderContrast(el, step, title, blurb, rows, fmt) {
    if (!el) return;
    const body = preferSig(rows)
      .slice(0, 8)
      .map(fmt)
      .join("");
    el.innerHTML =
      '<p class="kicker">' +
      esc(step) +
      "</p><h3>" +
      esc(title) +
      "</h3>" +
      (blurb ? '<p class="f-note">' + esc(blurb) + "</p>" : "") +
      (body
        ? '<ul class="triage-list">' + body + "</ul>"
        : '<p class="f-note">No clear contrasts in this sample yet.</p>');
  }

  function renderPlaces(el, rows) {
    renderContrast(
      el,
      "2 · Where",
      "Places that elevate a teaching type",
      "Compared with the rest of geolocated news in the sample.",
      rows,
      function (r) {
        const lift = r.lift_vs_geo_news != null ? Number(r.lift_vs_geo_news).toFixed(1) : "?";
        return (
          "<li>" +
          signalBadge(r) +
          " <strong>" +
          esc(r.location) +
          "</strong> elevates <em>" +
          esc(pretty(r.label)) +
          "</em> about <b>" +
          esc(lift) +
          "×</b> more often" +
          ' <span class="f-note">(' +
          pct(r.rate_pct) +
          " there vs " +
          pct(r.baseline_pct) +
          " elsewhere)</span></li>"
        );
      }
    );
  }

  function renderHotspots(el, rows) {
    renderContrast(
      el,
      "2 · Correction queue",
      "Where misunderstanding labels cluster",
      "Places where the model more often flagged a possible misunderstanding for educator review.",
      rows,
      function (r) {
        return (
          "<li>" +
          signalBadge(r) +
          " <strong>" +
          esc(r.location) +
          "</strong>: " +
          pct(r.misunderstanding_pct) +
          " of local rows in the queue" +
          ' <span class="f-note">(vs ' +
          pct(r.baseline_pct) +
          " elsewhere)</span></li>"
        );
      }
    );
  }

  function renderPairs(el, step, title, blurb, rows) {
    renderContrast(el, step, title, blurb, rows, function (r) {
      const lift = r.lift != null ? Number(r.lift).toFixed(1) : "?";
      return (
        "<li>" +
        signalBadge(r) +
        " <strong>" +
        esc(pretty(r.a)) +
        "</strong> often travels with <strong>" +
        esc(pretty(r.b)) +
        "</strong>" +
        ' <span class="f-note">(about ' +
        esc(lift) +
        "× more than chance · " +
        esc(r.n) +
        " co-labeled rows)</span></li>"
      );
    });
  }

  function renderLang(el, rows) {
    renderContrast(
      el,
      "2 · Language",
      "English vs Spanish mix",
      "Which teaching types are denser in English-labeled rows than Spanish ones (and the reverse).",
      rows,
      function (r) {
        const lean = Number(r.ratio_a_over_b) >= 1 ? "more common in English" : "more common in Spanish";
        return (
          "<li>" +
          signalBadge(r) +
          " <strong>" +
          esc(pretty(r.label)) +
          "</strong> is " +
          esc(lean) +
          ' <span class="f-note">(EN ' +
          pct(r.rate_a_pct) +
          " · ES " +
          pct(r.rate_b_pct) +
          ")</span></li>"
        );
      }
    );
  }

  function renderFamily(el, rows) {
    renderContrast(
      el,
      "2 · Modality",
      "News vs radio",
      "Doctrine and papal social teaching often show up denser in news than in radio in this sample.",
      rows,
      function (r) {
        const lean = Number(r.ratio_a_over_b) >= 1 ? "denser in news" : "denser on radio";
        return (
          "<li>" +
          signalBadge(r) +
          " <strong>" +
          esc(pretty(r.label)) +
          "</strong> is " +
          esc(lean) +
          ' <span class="f-note">(news ' +
          pct(r.rate_a_pct) +
          " · radio " +
          pct(r.rate_b_pct) +
          ")</span></li>"
        );
      }
    );
  }

  function networkBundle(T, mode) {
    const nets = (T.networks || {})[mode] || { nodes: [], edges: [] };
    let edges = (nets.edges || []).filter(function (e) {
      return e.significant !== false;
    });
    if (!edges.length) edges = nets.edges || [];
    edges = edges
      .slice()
      .sort(function (a, b) {
        return (Number(b.lift) || 0) - (Number(a.lift) || 0);
      })
      .slice(0, mode === "place_x_type" ? 18 : 14);
    const keep = {};
    edges.forEach(function (e) {
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
      edges: edges.map(function (e) {
        return Object.assign({}, e);
      }),
    };
  }

  function setReadout(html) {
    const el = document.getElementById("t-network-readout");
    if (el) el.innerHTML = html;
  }

  function edgePlain(d, byId) {
    const a = byId[typeof d.source === "object" ? d.source.id : d.source];
    const b = byId[typeof d.target === "object" ? d.target.id : d.target];
    const left = a ? a.label : "Theme";
    const right = b ? b.label : "Theme";
    const lift = d.lift != null ? Number(d.lift).toFixed(1) : "?";
    if (d.type === "place_teaches" || (a && a.type === "place")) {
      return (
        "<strong>" +
        esc(left) +
        "</strong> elevates <strong>" +
        esc(right) +
        "</strong> about <b>" +
        esc(lift) +
        "×</b> vs the rest of geolocated news in this sample."
      );
    }
    return (
      "<strong>" +
      esc(left) +
      "</strong> and <strong>" +
      esc(right) +
      "</strong> appear together about <b>" +
      esc(lift) +
      "×</b> more than chance."
    );
  }

  function drawNetwork(svgEl, T, mode) {
    if (!svgEl || typeof d3 === "undefined") return;
    const data = networkBundle(T, mode);
    const wrap = svgEl.parentElement;
    const w = Math.max(320, (wrap && wrap.clientWidth) || 720);
    const h = mode === "place_x_type" ? 480 : 440;
    const svg = d3.select(svgEl);
    svg.selectAll("*").remove();
    svg.attr("viewBox", "0 0 " + w + " " + h).attr("width", "100%").attr("height", h);

    const blurb = document.getElementById("t-network-blurb");
    if (blurb) {
      blurb.textContent =
        mode === "place_x_type"
          ? "Left: places. Right: teaching types. A line means that theme shows up more often there than elsewhere in the sample. Click a circle or line to read it in words."
          : "Circles are teaching types. A line means two types often appear in the same excerpt. Click a circle or line to read it in words.";
    }

    if (!data.nodes.length) {
      svg
        .append("text")
        .attr("x", w / 2)
        .attr("y", h / 2)
        .attr("text-anchor", "middle")
        .attr("fill", "#5a6a7a")
        .text("No clear connections in this sample yet.");
      setReadout("No clear connections to show yet.");
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
        };
      });

    const color = { content: "#0a843d", discourse: "#1c4f8f", place: "#c99700" };

    // Bipartite layout for place × type (far clearer than spaghetti)
    if (mode === "place_x_type") {
      const places = data.nodes.filter(function (n) {
        return n.type === "place";
      });
      const themes = data.nodes.filter(function (n) {
        return n.type !== "place";
      });
      places.forEach(function (n, i) {
        n.x = w * 0.22;
        n.y = ((i + 1) / (places.length + 1)) * (h - 24) + 12;
        n.fx = n.x;
        n.fy = n.y;
      });
      themes.forEach(function (n, i) {
        n.x = w * 0.78;
        n.y = ((i + 1) / (themes.length + 1)) * (h - 24) + 12;
        n.fx = n.x;
        n.fy = n.y;
      });
    }

    const sim = d3
      .forceSimulation(data.nodes)
      .force(
        "link",
        d3
          .forceLink(links)
          .id(function (d) {
            return d.id;
          })
          .distance(mode === "place_x_type" ? 180 : 90)
          .strength(mode === "place_x_type" ? 0.15 : 0.55)
      )
      .force("charge", d3.forceManyBody().strength(mode === "place_x_type" ? -40 : -240))
      .force("center", d3.forceCenter(w / 2, h / 2))
      .force("collide", d3.forceCollide(mode === "place_x_type" ? 14 : 22));

    if (mode === "place_x_type") {
      sim.force("x", null).force("y", null);
      sim.alpha(0.2);
    }

    const g = svg.append("g");
    const link = g
      .append("g")
      .selectAll("line")
      .data(links)
      .join("line")
      .attr("stroke", "rgba(12,35,64,.35)")
      .attr("stroke-width", function (d) {
        return Math.min(6, 1 + Math.log1p(d.lift));
      })
      .style("cursor", "pointer")
      .on("click", function (event, d) {
        event.stopPropagation();
        setReadout(edgePlain(d, byId));
        link.attr("stroke", "rgba(12,35,64,.2)");
        d3.select(this).attr("stroke", "#c99700").attr("stroke-width", 4);
      });

    const node = g
      .append("g")
      .selectAll("g")
      .data(data.nodes)
      .join("g")
      .style("cursor", "pointer")
      .call(
        d3
          .drag()
          .on("start", function (event, d) {
            if (mode === "place_x_type") return;
            if (!event.active) sim.alphaTarget(0.25).restart();
            d.fx = d.x;
            d.fy = d.y;
          })
          .on("drag", function (event, d) {
            if (mode === "place_x_type") return;
            d.fx = event.x;
            d.fy = event.y;
          })
          .on("end", function (event, d) {
            if (mode === "place_x_type") return;
            if (!event.active) sim.alphaTarget(0);
            d.fx = null;
            d.fy = null;
          })
      )
      .on("click", function (event, d) {
        event.stopPropagation();
        const related = links.filter(function (e) {
          const s = typeof e.source === "object" ? e.source.id : e.source;
          const t = typeof e.target === "object" ? e.target.id : e.target;
          return s === d.id || t === d.id;
        });
        if (!related.length) {
          setReadout("<strong>" + esc(d.label) + "</strong> · no strong links in this view.");
          return;
        }
        related.sort(function (a, b) {
          return (b.lift || 0) - (a.lift || 0);
        });
        setReadout(
          "<strong>" +
            esc(d.label) +
            "</strong> · top link: " +
            edgePlain(related[0], byId)
        );
        link.attr("stroke", function (e) {
          const s = typeof e.source === "object" ? e.source.id : e.source;
          const t = typeof e.target === "object" ? e.target.id : e.target;
          return s === d.id || t === d.id ? "#c99700" : "rgba(12,35,64,.12)";
        });
      });

    node
      .append("circle")
      .attr("r", function (d) {
        return 7 + Math.min(12, Math.sqrt(d.n || 1) / 10);
      })
      .attr("fill", function (d) {
        return color[d.type] || "#0c2340";
      })
      .attr("stroke", "#fff")
      .attr("stroke-width", 1.5);

    node
      .append("text")
      .text(function (d) {
        const lab = d.label || "";
        return lab.length > 22 ? lab.slice(0, 20) + "…" : lab;
      })
      .attr("x", function (d) {
        if (mode !== "place_x_type") return 11;
        return d.type === "place" ? -10 : 10;
      })
      .attr("y", 4)
      .attr("text-anchor", function (d) {
        if (mode !== "place_x_type") return "start";
        return d.type === "place" ? "end" : "start";
      })
      .attr("font-size", 11)
      .attr("font-weight", 600)
      .attr("fill", "#0c2340");

    svg.on("click", function () {
      link.attr("stroke", "rgba(12,35,64,.35)");
      setReadout("Click a circle or line for a plain-language readout.");
    });

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

    if (mode === "place_x_type") {
      // Freeze after a short settle so bipartite stays readable
      setTimeout(function () {
        sim.stop();
      }, 400);
    }
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
    renderFamily(document.getElementById("t-family"), T.family_contrast);
    renderPairs(
      document.getElementById("t-pairs"),
      "2 · Together",
      "Themes that travel together",
      "Teaching types that often appear in the same excerpt.",
      T.types_together
    );
    renderPairs(
      document.getElementById("t-cross"),
      "2 · How it is said",
      "Content paired with speech-act",
      "What is taught, and how the excerpt says it.",
      T.content_x_discourse
    );

    const svg = document.getElementById("t-network");
    const modeSel = document.getElementById("t-network-mode");
    function redraw() {
      drawNetwork(svg, T, (modeSel && modeSel.value) || "place_x_type");
    }
    if (modeSel) modeSel.addEventListener("change", redraw);
    window.addEventListener("resize", function () {
      if (root.dataset.ready === "1") redraw();
    });
    redraw();
    root.dataset.ready = "1";
  };
})();
