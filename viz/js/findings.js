/* Findings charts — uses window.FINDINGS (small JSON). No Leaflet required. */
(function () {
  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function prettyTheme(id, labels) {
    return (labels && labels[id]) || String(id).replaceAll("_", " ");
  }

  function barRow(label, value, max, unit) {
    const pct = max > 0 ? Math.max(2, Math.round((value / max) * 100)) : 0;
    return (
      '<div class="f-bar">' +
      '<div class="f-bar__meta"><span>' + esc(label) + "</span><b>" + esc(value) + (unit || "") + "</b></div>" +
      '<div class="f-bar__track"><i style="width:' + pct + '%"></i></div>' +
      "</div>"
    );
  }

  function renderSantiago(el, F) {
    const lifts = F.santiago.lifts || [];
    const max = Math.max(...lifts.map((d) => d.x), 1);
    el.innerHTML =
      '<p class="kicker">Place window · RISE host</p>' +
      "<h3>Santiago lifts vs. U.S. news</h3>" +
      '<p class="f-note">N ≈ ' + esc(F.santiago.n) + ". " + esc(F.santiago.note) + "</p>" +
      lifts.map((d) => barRow(d.theme, "~" + d.x + "×", max, "")).join("") +
      '<button type="button" class="cta f-cta" data-go="santiago">Open Santiago on the map</button>';
  }

  function renderSignatures(el, F) {
    el.innerHTML =
      '<p class="kicker">Regional signatures</p>' +
      "<h3>Where themes concentrate</h3>" +
      '<div class="f-sigs">' +
      (F.signatures || [])
        .map(
          (s) =>
            '<div class="f-sig"><span class="f-sig__place">' +
            esc(s.place) +
            '</span><span class="f-sig__theme">' +
            esc(s.theme) +
            "</span></div>"
        )
        .join("") +
      "</div>";
  }

  function renderHeat(el, F) {
    const themes = F.themes || [];
    const rows = F.matrix || [];
    const labels = F.themeLabels || {};
    let html =
      '<p class="kicker">Country rates</p>' +
      "<h3>Theme intensity per 1,000 stories</h3>" +
      '<p class="f-note">Darker gold = higher rate in that country’s geolocated news.</p>' +
      '<div class="f-heat-wrap"><table class="f-heat"><thead><tr><th>Country</th>';
    themes.forEach((t) => {
      html += "<th title='" + esc(t) + "'>" + esc(prettyTheme(t, labels).split(" ").slice(0, 2).join(" ")) + "</th>";
    });
    html += "</tr></thead><tbody>";
    const maxRate = Math.max(
      1,
      ...rows.flatMap((r) => themes.map((t) => r.rates[t] || 0))
    );
    rows.forEach((r) => {
      html +=
        "<tr><th>" +
        esc(r.name) +
        ' <span class="f-n">n=' +
        esc(r.n) +
        "</span></th>";
      themes.forEach((t) => {
        const v = r.rates[t] || 0;
        const a = Math.min(0.92, 0.08 + (v / maxRate) * 0.84);
        html +=
          '<td style="background:rgba(201,151,0,' +
          a.toFixed(3) +
          ')" title="' +
          esc(prettyTheme(t, labels)) +
          ": " +
          v +
          '/1k">' +
          (v ? v.toFixed(0) : "·") +
          "</td>";
      });
      html += "</tr>";
    });
    html += "</tbody></table></div>";
    el.innerHTML = html;
  }

  function renderLifts(el, F) {
    const rows = (F.matrix || []).filter((r) => r.fips !== "US");
    const labels = F.themeLabels || {};
    const focusTheme = "liberation_theology";
    const ranked = rows
      .map((r) => ({ name: r.name, fips: r.fips, x: r.lifts[focusTheme] || 0 }))
      .filter((d) => d.x > 0)
      .sort((a, b) => b.x - a.x);
    const max = Math.max(...ranked.map((d) => d.x), 1);
    el.innerHTML =
      '<p class="kicker">Lift vs. United States</p>' +
      "<h3>" +
      esc(prettyTheme(focusTheme, labels)) +
      "</h3>" +
      '<p class="f-note">Country rate ÷ U.S. rate. Gutiérrez’s preferential-option vocabulary is stronger across much of Latin America.</p>' +
      ranked.map((d) => barRow(d.name, d.x + "×", max)).join("") +
      '<button type="button" class="cta cta--ghost f-cta" data-go="topics" style="border-color:var(--nd-blue);color:var(--nd-blue)">Open Topics graph</button>';
  }

  function renderCooccur(el, F) {
    const rows = F.cooccur || [];
    const max = Math.max(...rows.map((d) => d.lift), 1);
    el.innerHTML =
      '<p class="kicker">Teaching co-occurrence</p>' +
      "<h3>Themes that travel together</h3>" +
      '<p class="f-note">Lift = P(a,b)/(P(a)P(b)). High lift means two teachings appear in the same stories more than chance.</p>' +
      rows
        .slice(0, 10)
        .map((d) =>
          barRow(d.a + " · " + d.b, d.lift + "×", max)
        )
        .join("");
  }

  function renderCompare(el, F) {
    const pair =
      (F.pairs || []).find((p) => p.a.fips === "US" && p.b.fips === "CI") ||
      (F.pairs || [])[0];
    if (!pair) {
      el.innerHTML = "<p class='f-note'>Compare pairs unavailable.</p>";
      return;
    }
    const max = Math.max(...pair.deltas.map((d) => Math.abs(d.delta)), 1);
    el.innerHTML =
      '<p class="kicker">Country compare</p>' +
      "<h3>" +
      esc(pair.a.name) +
      " vs " +
      esc(pair.b.name) +
      "</h3>" +
      '<p class="f-note">Δ per 1,000 stories (positive = higher in ' +
      esc(pair.b.name) +
      ").</p>" +
      pair.deltas
        .map((d) => {
          const pct = Math.max(4, Math.round((Math.abs(d.delta) / max) * 100));
          const pos = d.delta >= 0;
          return (
            '<div class="f-bar">' +
            '<div class="f-bar__meta"><span>' +
            esc(d.label) +
            "</span><b>" +
            (pos ? "+" : "") +
            d.delta.toFixed(1) +
            "</b></div>" +
            '<div class="f-bar__track"><i class="' +
            (pos ? "pos" : "neg") +
            '" style="width:' +
            pct +
            '%"></i></div></div>'
          );
        })
        .join("") +
      '<button type="button" class="cta f-cta" data-go="places">Explore Places</button>';
  }

  function renderMetros(el, F) {
    const rows = F.metros || [];
    const max = Math.max(...rows.map((d) => d.n), 1);
    el.innerHTML =
      '<p class="kicker">Writing desks</p>' +
      "<h3>Top ActionGeo metros</h3>" +
      '<p class="f-note">Counts reflect where stories were written into GDELT — D.C. leads because wire desks geocode there.</p>' +
      rows.map((d) => barRow(d.name + (d.fips === "CI" ? " · RISE" : ""), d.n.toLocaleString(), max)).join("");
  }

  function renderCorpus(el, F) {
    const c = F.corpus || {};
    el.innerHTML =
      '<p class="kicker">Corpus</p>' +
      "<h3>Scale of the collection</h3>" +
      '<p class="f-note">Multimodal harvest scored with a frozen EN/ES/PT lexicon — the substrate for geography and language questions.</p>' +
      '<div class="f-corpus">' +
      '<div><strong>' + esc(c.usNews) + "</strong><span>U.S. news paragraphs</span></div>" +
      '<div><strong>' + esc(c.americasNews) + "</strong><span>Americas news</span></div>" +
      '<div><strong>' + esc(c.tv) + "</strong><span>TV items</span></div>" +
      '<div><strong>' + esc(c.radioAAPB) + "</strong><span>AAPB radio</span></div>" +
      '<div><strong>EN·ES·PT</strong><span>parallel lexicons</span></div>' +
      '<div><strong>' + esc(c.period) + "</strong><span>coverage window</span></div>" +
      "</div>";
  }

  function renderEducation(el, F) {
    if (!el) return;
    const e = F.education || {};
    const topC = (e.top_content || [])
      .map((d) => "<li><strong>" + esc(d.label) + "</strong> · " + d.n + "</li>")
      .join("");
    const topD = (e.top_discourse || [])
      .map((d) => "<li><strong>" + esc(d.label) + "</strong> · " + d.n + "</li>")
      .join("");
    const cross = (e.cross_top || [])
      .map((d) => "<li><strong>" + esc(d.pair) + "</strong> · " + d.n + "</li>")
      .join("");
    const paths = (e.pathways || []).map((p) => "<li>" + esc(p) + "</li>").join("");
    const rate = e.misunderstanding_rate != null ? Math.round(100 * e.misunderstanding_rate) + "%" : "—";
    const acc =
      e.accuracy_mean != null
        ? typeof e.accuracy_mean === "number"
          ? e.accuracy_mean.toFixed(2)
          : String(e.accuracy_mean)
        : "—";
    el.innerHTML =
      '<p class="kicker">Education · informal learning</p>' +
      "<h3>Prior knowledge triage (fixture)</h3>" +
      '<p class="f-note">' +
      esc(e.note || "Dual taxonomy: content (what) + discourse (how) + accuracy triage.") +
      "</p>" +
      '<div class="f-corpus">' +
      "<div><strong>" +
      esc(String(e.n || "—")) +
      "</strong><span>fixture rows EN/ES/PT</span></div>" +
      "<div><strong>" +
      esc(rate) +
      "</strong><span>misunderstanding flags</span></div>" +
      "<div><strong>" +
      esc(String(e.needs_human_review != null ? e.needs_human_review : "—")) +
      "</strong><span>human-review flags</span></div>" +
      "<div><strong>" +
      esc(acc) +
      "</strong><span>mean accuracy (0–4)</span></div>" +
      "</div>" +
      '<div class="sig-list" style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-top:1rem">' +
      "<div><p class=\"f-note\">Top content</p><ul>" +
      topC +
      "</ul></div>" +
      "<div><p class=\"f-note\">Top discourse</p><ul>" +
      topD +
      "</ul></div>" +
      "</div>" +
      (cross
        ? '<p class="f-note" style="margin-top:1rem">Content × discourse</p><ul>' + cross + "</ul>"
        : "") +
      (paths
        ? '<p class="f-note" style="margin-top:1rem">Educator pathways</p><ul>' + paths + "</ul>"
        : "") +
      '<p class="f-note" style="margin-top:1rem">' +
      '<a href="triage.html">Open Triage lab</a> · ' +
      '<a href="methods.html#triage">Methods</a> · ' +
      '<a href="explore.html#/places">Places map</a>' +
      "</p>";
  }

  function bindCtas(root) {
    root.querySelectorAll("[data-go]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const go = btn.getAttribute("data-go");
        if (go === "santiago") location.href = "explore.html#/santiago";
        else if (go === "topics") location.href = "explore.html#/topics";
        else if (go === "places") location.href = "explore.html#/places";
      });
    });
  }

  window.renderFindings = function () {
    const F = window.FINDINGS;
    if (!F) return;
    const root = document.getElementById("findings");
    if (!root || root.dataset.ready === "1") {
      if (root) bindCtas(root);
      return;
    }
    renderCorpus(document.getElementById("f-corpus"), F);
    renderEducation(document.getElementById("f-education"), F);
    renderSignatures(document.getElementById("f-sigs"), F);
    renderSantiago(document.getElementById("f-santiago"), F);
    renderLifts(document.getElementById("f-lifts"), F);
    renderHeat(document.getElementById("f-heat"), F);
    renderCooccur(document.getElementById("f-cooccur"), F);
    renderCompare(document.getElementById("f-compare"), F);
    renderMetros(document.getElementById("f-metros"), F);
    root.dataset.ready = "1";
    bindCtas(root);
  };
})();
