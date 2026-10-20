(function () {
  function esc(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function bar(label, value, max, detail, suffix) {
    var width = Math.max(2, Math.round((value / max) * 100));
    return (
      '<div class="src-row">' +
      '<div class="src-row__label"><strong>' + esc(label) + "</strong><span>" + esc(detail) + "</span></div>" +
      '<div class="src-row__track"><div class="src-row__fill" style="width:' + width + '%"></div></div>' +
      '<div class="src-row__pct">' + value.toFixed(2) + suffix + "</div>" +
      "</div>"
    );
  }

  function boot() {
    var T = window.TRIAGE;
    var host = document.getElementById("mis-source-bars");
    if (!host || !T || host.dataset.ready === "1") return;
    host.dataset.ready = "1";

    var fam = (T.family_contrast || []).filter(function (r) {
      return r.label === "misunderstanding";
    })[0];
    var n = T.n || 0;
    var hits = (T.content_counts && T.content_counts.misunderstanding) || 0;
    var overall = n ? (100 * hits) / n : 0;
    var names = { news: "News", tv: "Television", youtube: "YouTube", radio: "Radio" };
    var rates = T.outlet_rates || [];
    var max = overall;
    rates.forEach(function (r) { max = Math.max(max, r.misunderstanding || 0); });
    max = Math.max(max, 1);

    var html = bar("All excerpts", overall, max, hits.toLocaleString() + " of " + n.toLocaleString(), "%");
    rates.forEach(function (r) {
      html += bar(
        names[r.outlet] || r.outlet,
        r.misunderstanding || 0,
        max,
        Math.round((r.n || 0) * (r.misunderstanding || 0) / 100).toLocaleString() + " flags · n=" + (r.n || 0).toLocaleString(),
        "%"
      );
    });
    host.innerHTML = html;

    var OUTLETS = [
      ["news", "News", "GDELT news text. ActionGeo, the writing location, applies only here."],
      ["tv", "Television", "Television transcripts. No writing-location map."],
      ["youtube", "YouTube", "YouTube speech or description text. No writing-location map."],
      ["radio", "Radio", "Radio transcripts. The news-versus-radio tests on this page use this stream."]
    ];
    var outletHost = document.getElementById("mis-outlet-bars");
    var outlets = T.outlet_counts || {};
    if (outletHost && Object.keys(outlets).length) {
      var outletMax = OUTLETS.reduce(function (m, row) {
        return Math.max(m, outlets[row[0]] || 0);
      }, 1);
      outletHost.innerHTML = OUTLETS.map(function (row) {
        var count = outlets[row[0]] || 0;
        var pct = n ? (100 * count) / n : 0;
        return bar(row[1], pct, (100 * outletMax) / n, row[2] + " · " + count.toLocaleString() + " excerpts", "%");
      }).join("");
    }

    var TYPES = [
      ["institutional_news", "Institutional news", "A diocese, the Vatican, or a bishop’s office: appointments, events, statements, renovations. Little or no creed or moral teaching."],
      ["migration_politics", "Migration / politics", "Immigration, elections, church–state conflict, or a partisan frame around Catholicism."],
      ["moral_ethics", "Moral teaching", "A normative claim about life, dignity, honesty, or the option for the poor, without needing a named encyclical."],
      ["doctrine_sacrament", "Doctrine / sacrament", "Creed, sacraments, liturgy, or magisterial doctrine presented as teaching. The Mass, baptism, what the Church holds."],
      ["misunderstanding", "Misunderstanding", "A distorted, incomplete, or contradicted teaching. A flag for an educator, not a verdict of bad faith."],
      ["devotion_piety", "Devotion / popular piety", "Saints, Mary, rosary, pilgrimage, Guadalupe or Aparecida as devotion."],
      ["cst_papal", "Catholic social teaching / papal documents", "A named encyclical or an explicit CST theme: Laudato Si’, Fratelli Tutti, Aparecida, and the like."],
      ["evangelization_mission", "Evangelization / mission", "Mission, proclaiming the Gospel, or missionary discipleship as the main point."],
      ["other_unclear", "Other / unclear", "Too thin, or only a biography. Used when nothing else fits."]
    ];
    var typeHost = document.getElementById("mis-type-bars");
    if (typeHost && T.content_counts) {
      var typeMax = TYPES.reduce(function (m, row) {
        return Math.max(m, T.content_counts[row[0]] || 0);
      }, 1);
      var typeNote = document.getElementById("mis-type-note");
      if (typeNote) {
        typeNote.innerHTML =
          "Shares are of <strong>" + n.toLocaleString() + "</strong> labeled excerpts. They do not add to 100%, because one paragraph can carry two types. “Institutional news” is not a newspaper section. It means the excerpt is about a Church office, appointment, event, or schedule, and it does not teach a doctrine.";
      }
      typeHost.innerHTML = TYPES.map(function (row) {
        var count = T.content_counts[row[0]] || 0;
        var pct = n ? (100 * count) / n : 0;
        return bar(row[1], pct, (100 * typeMax) / n, row[2] + " · " + count.toLocaleString() + " excerpts", "%");
      }).join("");
    }

    var note = document.getElementById("mis-source-note");
    if (note && fam) {
      var spots = T.misunderstanding_hotspots || [];
      var placeBits = spots.map(function (r) {
        var dir = r.misunderstanding_pct > r.baseline_pct ? "above" : "below";
        return r.location + " " + r.misunderstanding_pct.toFixed(2) + "% (" + dir + " the news baseline)";
      });
      note.innerHTML =
        "The only outlet contrast that was hypothesis-tested is news versus radio: about <strong>" +
        fam.ratio_a_over_b.toFixed(1) +
        "×</strong> (Fisher exact, Holm-adjusted " + esc(fam.stars || "") +
        "). Television and YouTube sit near 2.6%, between news and radio, and were not in that test. Among news writing locations: " +
        esc(placeBits.join("; ")) +
        ". The flag marks a passage for educator review. It is not a theologian’s verdict.";
    }

    var company = document.getElementById("mis-company-bars");
    if (company) {
      var pairs = (T.types_together || []).filter(function (r) {
        return r.a === "misunderstanding" || r.b === "misunderstanding";
      });
      var cross = (T.content_x_discourse || []).filter(function (r) {
        return r.a === "misunderstanding" || r.b === "misunderstanding";
      });
      var rows = pairs.concat(cross).sort(function (a, b) {
        return b.lift - a.lift;
      }).slice(0, 5);
      var liftMax = rows.reduce(function (m, r) { return Math.max(m, r.lift); }, 1);
      company.innerHTML = rows.map(function (r) {
        var other = r.a === "misunderstanding" ? r.b : r.a;
        return bar(other, r.lift, liftMax, "n=" + r.n.toLocaleString() + " · " + (r.stars || ""), "×");
      }).join("");
    }

    document.querySelectorAll(".mis-legend button").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var sev = btn.getAttribute("data-sev");
        document.querySelectorAll(".mis-legend button").forEach(function (b) {
          b.classList.toggle("is-on", b === btn);
        });
        document.querySelectorAll(".mis-card").forEach(function (card) {
          var shown = 0;
          card.querySelectorAll(".mis-item").forEach(function (item) {
            var keep = sev === "all" || item.querySelector(".sev--" + sev);
            item.classList.toggle("is-hidden", !keep);
            if (keep) shown += 1;
          });
          card.classList.toggle("is-hidden", shown === 0);
        });
      });
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
  window.addEventListener("load", boot);
})();
