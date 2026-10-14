/* Story page mounts: fills from window.FINDINGS (corpus, signatures, Santiago, story). */
(function () {
  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function renderCorpus(el, F) {
    if (!el) return;
    const c = F.corpus || {};
    el.innerHTML =
      "<div><strong>" +
      esc(c.usNews || "…") +
      "</strong><span>U.S. news paragraphs</span></div>" +
      "<div><strong>" +
      esc(c.americasNews || "…") +
      "</strong><span>Americas news</span></div>" +
      "<div><strong>EN · ES · PT</strong><span>parallel lexicons</span></div>";
  }

  function renderSignatures(el, F) {
    if (!el) return;
    const rows = F.signatures || [];
    if (!rows.length) {
      el.innerHTML =
        '<div class="sig"><span class="sig__place">…</span><span class="sig__theme">no matrix lifts</span></div>';
      return;
    }
    el.innerHTML = rows
      .map(function (s) {
        const lift =
          s.lift != null ? ' <span class="sig__lift">~' + esc(String(s.lift)) + "×</span>" : "";
        return (
          '<div class="sig"><span class="sig__place">' +
          esc(s.place) +
          '</span><span class="sig__theme">' +
          esc(s.theme) +
          lift +
          "</span></div>"
        );
      })
      .join("");
  }

  function renderSantiago(el, F) {
    if (!el) return;
    const s = F.santiago || {};
    const lifts = s.lifts || [];
    const max = Math.max.apply(
      null,
      lifts.map(function (d) {
        return Number(d.x) || 0;
      }).concat([1])
    );
    const lead = document.getElementById("story-santiago-lead");
    if (lead && s.n) {
      const delay =
        (F && F.delayNote) ||
        "Papal documents such as Aparecida can reach Chile days after U.S. desks.";
      const top = lifts[0];
      const near = lifts.find(function (d) {
        const x = Number(d.x);
        return x >= 0.85 && x <= 1.15;
      });
      let middle =
        "shows Chile ActionGeo rates versus U.S. news; country shapes encounter in one city panel.";
      if (top) {
        middle =
          "shows Chile ActionGeo rates versus U.S. news; " +
          esc(top.theme) +
          " leads (~" +
          esc(String(top.x)) +
          "×)";
        if (near) {
          middle +=
            "; " +
            esc(near.theme).toLowerCase() +
            " sits near parity (~" +
            esc(String(near.x)) +
            "×)";
        }
        middle += ".";
      }
      lead.innerHTML =
        "Selecting Santiago (<em>N</em> ≈ " +
        esc(String(s.n)) +
        ") " +
        middle +
        " " +
        esc(delay);
    }
    let html = "<h3>Lifts vs. U.S. news</h3>";
    lifts.forEach(function (d, i) {
      const x = Number(d.x) || 0;
      const w = max > 0 ? Math.max(8, Math.round((x / max) * 100)) : 8;
      html +=
        '<div class="meter" style="--v:' +
        (i + 1) +
        '">' +
        '<div class="meter__top"><span>' +
        esc(d.theme) +
        "</span><b>~" +
        esc(String(d.x)) +
        "×</b></div>" +
        '<div class="meter__track"><i style="--w:' +
        w +
        '%;width:' +
        w +
        '%"></i></div>' +
        "</div>";
    });
    html +=
      '<p class="story-note">' +
      esc(s.note || "Chile country lifts vs. U.S. news; social-media layer forthcoming.") +
      "</p>";
    el.innerHTML = html;
  }

  function renderEducation(el, F) {
    if (!el) return;
    const st = F.story || {};
    const headline = document.getElementById("story-education-headline");
    const note = document.getElementById("story-education-note");
    const beats = document.getElementById("story-education-beats");
    if (headline) {
      headline.textContent = st.headline || "Education triage pending";
    }
    if (note) {
      const bits = [];
      if (st.n) bits.push("n=" + st.n);
      if (st.review_queue_n != null) bits.push("review flags " + st.review_queue_n);
      if (st.accuracy_mean != null) bits.push("mean accuracy " + Number(st.accuracy_mean).toFixed(2));
      note.textContent = (st.note || "") + (bits.length ? " · " + bits.join(" · ") : "");
    }
    if (beats) {
      const rows = st.beats || [];
      beats.innerHTML = rows
        .map(function (b) {
          return (
            '<a class="triage-hook triage-hook--link" href="' +
            esc(b.href || "triage.html") +
            '"><strong>' +
            esc(b.text) +
            "</strong><span>" +
            esc(b.id || "beat") +
            "</span></a>"
          );
        })
        .join("");
    }
  }

  window.renderStory = function () {
    const F = window.FINDINGS;
    if (!F) return;
    const root = document.getElementById("storyboard");
    if (!root || root.dataset.ready === "1") return;
    renderCorpus(document.getElementById("story-corpus"), F);
    renderSignatures(document.getElementById("story-signatures"), F);
    renderSantiago(document.getElementById("story-santiago"), F);
    renderEducation(document.getElementById("story-education"), F);
    root.dataset.ready = "1";
  };
})();
