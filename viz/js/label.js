(function () {
  var ITEMS = [
    {
      kicker: "1 of 3 · news · score 1.77",
      text: "Pope [PERSON] says that just because [ORGANIZATION] bans artificial contraceptives, it does not mean Catholics have to \"breed like rabbits.\"",
      content: ["moral_ethics", "misunderstanding"],
      discourse: ["factual_claim", "news_report"],
      accuracy: "2",
      accuracyName: "partial or misleading (nearest to 1.77)"
    },
    {
      kicker: "2 of 3 · news · score 3.28",
      text: "In his encyclical, \"Laudato Si', on Care for Our Common Home,\" the pope said that human life depends on the well-being of the planet.",
      content: ["cst_papal"],
      discourse: ["factual_claim", "news_report"],
      accuracy: "3",
      accuracyName: "broadly accurate (nearest to 3.28)"
    },
    {
      kicker: "3 of 3 · news · score 0.35",
      text: "She said the archdiocese assured her that the priest, [PERSON], would never be a pastor or counsel women again.",
      content: ["institutional_news"],
      discourse: ["factual_claim", "news_report"],
      accuracy: "0",
      accuracyName: "cannot assess (nearest to 0.35)"
    }
  ];
  var itemIndex = 0;

  var CONTENT = [
    ["doctrine_sacrament", "Doctrine / sacramental teaching", "Creed, sacraments, liturgy, or magisterial doctrine presented as teaching."],
    ["cst_papal", "Catholic social teaching / papal documents", "Named encyclicals or explicit CST themes."],
    ["devotion_piety", "Devotion / popular piety", "Saints, Mary, pilgrimages, rosary, popular religiosity."],
    ["moral_ethics", "Moral teaching / ethics", "Normative claims about personal or social morality."],
    ["migration_politics", "Migration / politics", "Immigration, elections, church–state conflict, or partisan framing."],
    ["institutional_news", "Institutional news", "Appointments, events, or logistics with little teaching content."],
    ["evangelization_mission", "Evangelization / mission", "Mission, proclaiming the Gospel, missionary discipleship."],
    ["misunderstanding", "Misunderstanding / partial truth", "Distorted or contradicted Catholic teaching. Not a verdict of malice."],
    ["other_unclear", "Other / unclear", "Too thin or not classifiable. Use sparingly."]
  ];
  var DISCOURSE = [
    ["factual_claim", "Factual claim", "A checkable fact about events, numbers, or institutions."],
    ["doctrinal_claim", "Doctrinal claim", "Asserts what the Church or believers hold as true."],
    ["question", "Question", "A real question directed at the audience."],
    ["news_report", "News reporting", "Recounts that someone said or announced something."],
    ["opinion_editorial", "Opinion", "A writer’s evaluation or commentary."],
    ["advocacy", "Advocacy", "A call to action."],
    ["homily_devotional", "Homily / devotion", "Prayer or preaching addressed to a faith audience."],
    ["interview_dialogue", "Interview", "Quoted question and answer."],
    ["other_mixed", "Other / mixed", "Does not fit cleanly."]
  ];
  var ACCURACY = [
    ["0", "Cannot assess", "No clear religious claim."],
    ["1", "Clearly inaccurate", "Contradicts standard Catholic teaching."],
    ["2", "Partial or misleading", "Partly true, incomplete, or easy to misread."],
    ["3", "Broadly accurate", "Mostly consistent; minor imprecision is fine."],
    ["4", "Accurate and clear", "Clear enough for formation without a major correction."]
  ];

  function gold() {
    return ITEMS[itemIndex];
  }

  var picked = { content: {}, discourse: {}, accuracy: "" };
  var revealed = false;

  function chip(id, name, tip, group) {
    var li = document.createElement("li");
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "chip";
    btn.setAttribute("data-group", group);
    btn.setAttribute("data-id", id);
    btn.setAttribute("aria-pressed", "false");
    btn.textContent = name;
    var span = document.createElement("span");
    span.className = "chip-tip";
    span.setAttribute("role", "tooltip");
    span.textContent = tip;
    btn.appendChild(span);
    btn.addEventListener("click", function () {
      if (revealed) return;
      if (group === "accuracy") {
        picked.accuracy = picked.accuracy === id ? "" : id;
      } else if (picked[group][id]) {
        delete picked[group][id];
      } else {
        picked[group][id] = true;
      }
      paint();
    });
    li.appendChild(btn);
    return li;
  }

  function fill(ul, rows, group) {
    rows.forEach(function (row) {
      ul.appendChild(chip(row[0], row[1], row[2], group));
    });
  }

  function stateFor(group, id) {
    var on = group === "accuracy" ? picked.accuracy === id : !!picked[group][id];
    var g = gold();
    var goldOn =
      group === "accuracy"
        ? id === g.accuracy
        : (group === "content" ? g.content : g.discourse).indexOf(id) >= 0;
    if (!revealed) return on ? "is-on" : "";
    if (on && goldOn) return "is-hit";
    if (on && !goldOn) return "is-miss";
    if (!on && goldOn) return "is-missed";
    return "";
  }

  function paint() {
    document.querySelectorAll(".chip").forEach(function (btn) {
      var group = btn.getAttribute("data-group");
      var id = btn.getAttribute("data-id");
      var on = group === "accuracy" ? picked.accuracy === id : !!picked[group][id];
      btn.className = "chip " + stateFor(group, id);
      btn.setAttribute("aria-pressed", on ? "true" : "false");
      btn.disabled = revealed;
    });
    var g = gold();
    var check = document.getElementById("label-check");
    var reset = document.getElementById("label-reset");
    var next = document.getElementById("label-next");
    var result = document.getElementById("label-result");
    var kicker = document.querySelector(".post-card__kicker");
    var post = document.getElementById("label-post");
    if (kicker) kicker.textContent = g.kicker;
    if (post) post.textContent = g.text;
    var any = picked.accuracy || Object.keys(picked.content).length || Object.keys(picked.discourse).length;
    check.hidden = revealed;
    check.disabled = !any;
    reset.hidden = !revealed;
    next.hidden = !revealed;
    result.hidden = !revealed;
    if (!revealed) return;
    var contentHits = g.content.filter(function (id) { return picked.content[id]; }).length;
    var discourseHits = g.discourse.filter(function (id) { return picked.discourse[id]; }).length;
    var contentExtra = Object.keys(picked.content).filter(function (id) {
      return g.content.indexOf(id) < 0;
    }).length;
    var discourseExtra = Object.keys(picked.discourse).filter(function (id) {
      return g.discourse.indexOf(id) < 0;
    }).length;
    var accOk = picked.accuracy === g.accuracy;
    var names = []
      .concat(g.content.map(function (id) {
        var row = CONTENT.filter(function (r) { return r[0] === id; })[0];
        return row ? row[1] : id;
      }))
      .concat(g.discourse.map(function (id) {
        var row = DISCOURSE.filter(function (r) { return r[0] === id; })[0];
        return row ? row[1] : id;
      }));
    result.innerHTML =
      "<p>Content: <strong>" + contentHits + "</strong> of " + g.content.length +
      (contentExtra ? " · <strong>" + contentExtra + "</strong> extra" : "") + ".</p>" +
      "<p>Discourse: <strong>" + discourseHits + "</strong> of " + g.discourse.length +
      (discourseExtra ? " · <strong>" + discourseExtra + "</strong> extra" : "") + ".</p>" +
      "<p>Accuracy: <strong>" + (accOk ? "matched" : "not matched") +
      "</strong>. Answer key is " + g.accuracyName + ".</p>" +
      "<p>Answer key: " + names.join(" · ") + ".</p>";
  }

  function boot() {
    var post = document.getElementById("label-post");
    if (!post || post.dataset.ready === "1") return;
    post.dataset.ready = "1";
    fill(document.getElementById("chips-content"), CONTENT, "content");
    fill(document.getElementById("chips-discourse"), DISCOURSE, "discourse");
    fill(document.getElementById("chips-accuracy"), ACCURACY, "accuracy");
    document.getElementById("label-check").addEventListener("click", function () {
      revealed = true;
      paint();
    });
    document.getElementById("label-reset").addEventListener("click", function () {
      picked = { content: {}, discourse: {}, accuracy: "" };
      revealed = false;
      paint();
    });
    document.getElementById("label-next").addEventListener("click", function () {
      itemIndex = (itemIndex + 1) % ITEMS.length;
      picked = { content: {}, discourse: {}, accuracy: "" };
      revealed = false;
      paint();
    });
    paint();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
