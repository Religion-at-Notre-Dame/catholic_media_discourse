# Unmatched-paragraph multilabel methodology

> **Provisional status:** These labels are exploratory, AI-assisted interpretations and are **NOT human-validated gold labels**. Percentages describe only this deliberately language-enriched review sample; they do not estimate prevalence in the 425 unmatched paragraphs or the corpus. Because coding is multilabel, percentages may overlap and membership counts may sum above 100.

## Sample and purpose

The source population is 425 paragraphs that matched none of the regex modes in `scripts/common/content_acts.py`. The review sample contains 100 paragraphs selected with seed `20261014` and deliberate language enrichment: 70 English, 15 Spanish, and 15 Portuguese. The unit coded is the extracted paragraph.

## Communicative-function taxonomy

Exactly eight allowed function labels were used:

- `news_event_report` — Narrates a discrete current, past, or planned event, institutional action, legal development, or measurable outcome.
- `background_exposition` — Supplies descriptive, explanatory, biographical, historical, scientific, or other contextual information.
- `attributed_statement` — Relays an actor's position, explanation, allegation, commitment, or quoted words.
- `opinion_analysis` — Offers authorial or quoted evaluation, interpretation, prediction, polemic, irony, or argument.
- `advocacy_appeal` — Requests, demands, exhorts, invites, or otherwise seeks action or change.
- `personal_testimony` — Presents first-person lived experience, witness, or self-reflection.
- `metadata_or_noise` — Consists substantially of a headline, caption, credit, citation, navigation, list fragment, malformed extraction, or off-topic contamination.
- `other_unclear` — Has insufficient recoverable evidence for a more specific communicative-function interpretation.

Every row has one `primary_function` and one or more semicolon-delimited `function_labels`. The primary label is the dominant communicative function and is always included in the full label set. Multiple labels were assigned only when the text genuinely performs multiple functions, such as reporting an event while quoting an appeal. Membership counts therefore overlap.

## Theological subject is a separate axis

Religious or theological content is not a communicative function. `theological_subject` records `yes`, `no`, or `unclear` independently of function, while `theological_topics` records concise semicolon-delimited subjects when identifiable. Thus a theological passage may function as exposition, attributed speech, opinion, advocacy, metadata, or another allowed function. There are 34 `yes` records and 8 `unclear` records.

## Results

- `news_event_report`: 34 memberships (34.0%)
- `background_exposition`: 33 memberships (33.0%)
- `attributed_statement`: 33 memberships (33.0%)
- `opinion_analysis`: 23 memberships (23.0%)
- `advocacy_appeal`: 14 memberships (14.0%)
- `personal_testimony`: 5 memberships (5.0%)
- `metadata_or_noise`: 22 memberships (22.0%)
- `other_unclear`: 5 memberships (5.0%)

There are 59 multilabel rows. The sum of function memberships is 169, exceeding 100 because overlap is allowed. `other_unclear` has 5 memberships and is reserved for records whose recoverable evidence is insufficient, rather than forcing a confident substantive label.

## Representative examples

The 10-example file includes 5 English, 3 Spanish, and 2 Portuguese records.

- **UM-007 (english)** — “[ORGANIZATION] — [PERSON] of [LOCATION], an immigrant from [LOCATION], pledged to push for a more welcoming immigration system after winning [DA…” Labels: `news_event_report;attributed_statement;advocacy_appeal`. Clear overlap of event reporting, attributed commitment, and policy advocacy.
- **UM-021 (english)** — ““These are essential, so that as the believer celebrates the Eucharist and reflects on the institution of that [ORGANIZATION], they have a sense…” Labels: `attributed_statement;background_exposition`. Shows theological subject matter separated from the quote's attributed/expository functions.
- **UM-026 (english)** — ““To work with this type of program takes courage because there is a lot of sadness that is part of the suicide crisis,” she told [ORGANIZATION]…” Labels: `personal_testimony;attributed_statement`. A compact English example of personal testimony embedded in attributed speech.
- **UM-033 (english)** — “[DATE] marks the 40th anniversary of the formation of [ORGANIZATION], and its PR handlers are in full spin mode. Over [DATE], they've dangled th…” Labels: `opinion_analysis;background_exposition`. Strong opinion/polemic that lacks the classifier's small fixed opinion phrase set.
- **UM-058 (english)** — “Catholic social teaching is grounded in a vision of the person as inherently sacred and made for community. All persons are created in the image…” Labels: `background_exposition;opinion_analysis`. Normative theological exposition illustrating that theology is a subject axis, not a function label.
- **UM-023 (spanish)** — “Solo espero que sea útil. Que ayude a cambiar lo que sea necesario para que el mundo sea un lugar que cuide, sane acompañe y no que maltrate. Y…” Labels: `advocacy_appeal;personal_testimony;opinion_analysis`. Spanish first-person reform appeal combining advocacy, testimony, and evaluation.
- **UM-049 (spanish)** — “El fenómeno que afectó hoy a la localidad de [LOCATION], [LOCATION], [LOCATION] y otros departamentos se lo denomina "haboob". Las corrientes de…” Labels: `background_exposition;news_event_report`. Spanish weather prose combining a current event with scientific explanation.
- **UM-039 (spanish)** — “1 of 16 — Virgen de Guadalupe-52.JPG 2 of 16 — Virgen de Guadalupe-4.JPG 3 of 16 — Virgen de Guadalupe-2.JPG 4 of 16 — Virgen de Guadalupe-10.JP…” Labels: `metadata_or_noise`. Spanish gallery metadata with a clearly religious subject but no prose discourse.
- **UM-068 (portuguese)** — ““Quando ele diz que é católico praticante, nós, bispos, temos a responsabilidade de corrigi-lo. Embora o povo lhe tenha conferido poder e autori…” Labels: `attributed_statement;opinion_analysis;advocacy_appeal`. Portuguese quotation combining attribution, normative analysis, and an appeal to correct.
- **UM-017 (portuguese)** — “[LOCATION]” Labels: `other_unclear;metadata_or_noise`. Portuguese placeholder-only record appropriately retained as Other/Unclear and metadata.

## Recurring misses in `content_acts.py`

- **Narrow reporting vocabulary:** ordinary event and attribution verbs such as *accused, filed, pleaded, released, responded, explained, tweeted, declarou, explicó,* and *escuchó* are absent from `REPORTING`.
- **Fixed opinion phrases:** adjective-led judgments, sarcasm, prediction, modality, and idiomatic Spanish/Portuguese evaluation often lack the small set in `OPINION`.
- **Incomplete advocacy constructions:** modal demands, hopes, reminders, bargaining requests, prayer invitations, and many inflections do not match `ADVOCACY`.
- **Theology conflated with devotional keywords:** `DEVOTIONAL` catches a few worship terms but misses doctrinal exposition about Eucharist, incarnation, grace, dignity, moral teaching, and ecclesiology. Theology should remain orthogonal to function.
- **No artifact-quality mode:** headlines, captions, credits, citations, gallery filenames, navigation, placeholders, and off-topic contamination fall into the generic fallback.
- **No positive expository mode:** coherent history, profiles, scientific explanation, and institutional description naturally contain none of the current question, reporting, opinion, advocacy, devotional, or numeric cues.
- **Limited numeric forms:** `FACTISH` misses several currencies, fractions, spelled quantities, placeholder dates, and facts expressed without its narrow units.

Expanding any regex should be tested conservatively: common verbs and religious keywords can create false positives by confusing topic with function, quotation with authorial stance, or ordinary narrative with news reporting.

## Limitations and next validation step

The sample is intentionally language-enriched, not representative. Paragraph extraction can remove attribution and surrounding context; placeholders obscure entities and dates; some records are headlines or metadata rather than body prose. Multilabel boundaries and theological-subject judgments are interpretive, and no intercoder reliability estimate is available.

The next step is blinded independent human coding by at least two multilingual reviewers using this codebook, followed by adjudication, per-label agreement and prevalence-adjusted reliability checks, and only then evaluation of candidate rule changes on a separate held-out sample that preserves the natural language distribution.
