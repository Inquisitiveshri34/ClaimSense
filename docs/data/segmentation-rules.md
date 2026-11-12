# ClaimSense — Segmentation Rules

> How each decision is cut into its four sections — **complaint, insurer position, findings, award** — with the markers used per source and per CIOINS office, the order rules are tried in, and what happens when nothing matches. This is the first and most important guard of the leakage contract (L1).

**Author:** Diya Shrivastava · **Owning PR:** 5 · **Status:** Planned (marker lists are starting points, extended as PR 5 finds new layouts)

**Related:** `leakage-contract.md` §2, `data-flow.md` Stage 3, `manual-audit-protocol.md` (50-document check), FR-05, risk R4.

---

## 1. Output

`data/interim/segments/<doc_id>.json`:

```json
{
  "doc_id": "cioins-2023-05-AHD-0056",
  "marker_rule": "cioins/ahmedabad/v2",
  "complaint": "…",
  "insurer_position": "…",
  "findings": "…",
  "award": "…",
  "spans": {"complaint": [412, 2210], "insurer_position": [2210, 3105], "findings": [3105, 6020], "award": [6020, 6488]}
}
```

`spans` are character offsets into `data/interim/text/<doc_id>.txt`, so the hand audit can highlight boundaries.

---

## 2. Algorithm

1. **Normalise** text: unify whitespace, straighten quotes, join hyphenated line breaks, drop repeated page headers/footers (lines appearing on ≥ 50% of pages).
2. **Strip front matter** before the first section marker: case caption, parties, policy and award numbers (these go to the anonymiser anyway, but never into `complaint`).
3. **Pick the rule set**: by `source`; for CIOINS also by `office` from the manifest; fall back to `cioins/default`.
4. **Find markers** as heading-like lines: a marker matches only if it starts a line, is ≤ 12 words, and is followed by a newline or colon. Case-insensitive; optional numbering (`1.`, `A.`, `(i)`) allowed before it.
5. **Order check**: sections must appear in the order complaint → insurer → findings → award. A marker found out of order is ignored; if that leaves a required section missing, the document is dropped.
6. **Assign text**: each section runs from its marker to the next found marker.
7. **Validate** (§5). Pass → write JSON. Fail → drop with a reason in `_segment_log.csv`.

No marker is ever inferred from content. If a boundary is not there, the document is dropped (FR-05).

---

## 3. Markers by source

Stored in `config.yaml` under `segment.markers.<rule>`. Regex-style; `\s+` between words implied.

### 3.1 FOS — `fos/v1`

| Section | Markers |
|---|---|
| Complaint | `The complaint`, `What happened` |
| Insurer position | *(usually inside "What happened"; see note)* `The insurer('s)? (said|says|response)`, `What [business] said` |
| Findings | `What I've decided( —|-| and)? why`, `My findings`, `Provisional decision` (quoted section) |
| Award | `My final decision`, `Putting things right` *(see note)* |

Notes:
- FOS rarely has a separate insurer heading. When missing, `insurer_position` is the **paragraphs inside "What happened" that report the insurer's reasons**, picked by sentence starters in `segment.fos.insurer_cues` (`"[Business] declined"`, `"It said"`, `"The insurer said"`). If no cue matches, `insurer_position` is empty and the document is **kept** (FOS only; complaint carries the insurer reason in its own words).
- "Putting things right" contains the remedy, which reveals the outcome: it belongs to **award**, even though it sits before "My final decision".
- Any quoted provisional decision inside "What happened" is cut out entirely (`leakage-contract.md` §2 edge cases).

### 3.2 FSPO — `fspo/v1`

| Section | Markers |
|---|---|
| Complaint | `Background`, `The Complainant'?s Case`, `The Complaint for Adjudication` *(the last is a one-paragraph summary, kept)* |
| Insurer position | `The Provider'?s Case` |
| Findings | `Analysis`, `Evidence` *(when followed by Analysis, Evidence belongs to findings)* |
| Award | `Decision`, `Conclusion`, `Directions` |

Notes:
- Skip the metadata page (outcome, conduct complained of) that precedes the decision text; detect it by the `Outcome:` field and cut to the first `Background` marker.
- FSPO decisions often include a section on post-preliminary-decision submissions (`Submissions`/`Preliminary Decision`) — treated as **findings**.

### 3.3 CIOINS — `cioins/default`

| Section | Markers |
|---|---|
| Complaint | `Brief facts( of the case)?`, `The complaint`, `Complainant'?s (argument|submission|contention)s?`, `Facts of the case` |
| Insurer position | `(The )?Insurer'?s (case|argument|submission|contention)s?`, `Respondent'?s (submission|reply|contention)s?`, `Insurer'?s SCN`, `Self[- ]contained note` |
| Findings | `Observations?( and conclusion)?`, `Findings`, `Reasons? for (the )?(decision|award)`, `Discussion`, `Analysis` |
| Award | `AWARD`, `Order`, `Decision`, `In the result` |

Notes:
- Many awards also have a block like *"The following documents were placed for perusal"* and *"Result of hearing with both parties"*. The documents list is dropped; the hearing result belongs to **findings**.
- Awards often restate the insurer's reason inside findings ("The insurer repudiated on grounds that…"). That text stays in findings; it does not move to insurer position.
- `Rule 17` / `Rule 13` statutory paragraphs after the award are dropped.

### 3.4 CIOINS per-office overrides

Offices differ in headings, numbering and whether facts and insurer case are merged. Each office gets an override that **extends** `cioins/default`; it never removes the default markers.

| Office | Rule ID | Known differences (to confirm in PR 5) |
|---|---|---|
| Ahmedabad | `cioins/ahmedabad/v1` | Numbered headings `1.`, `2.`…; facts may be headed `Brief Facts of the Complaint` |
| Bengaluru | `cioins/bengaluru/v1` | |
| Bhopal | `cioins/bhopal/v1` | Some awards partly in Hindi headings (`संक्षिप्त तथ्य`, `निर्णय`) |
| Bhubaneswar | `cioins/bhubaneswar/v1` | |
| Chandigarh | `cioins/chandigarh/v1` | |
| Chennai | `cioins/chennai/v1` | |
| Delhi | `cioins/delhi/v1` | |
| Ernakulam | `cioins/ernakulam/v1` | |
| Guwahati | `cioins/guwahati/v1` | |
| Hyderabad | `cioins/hyderabad/v1` | |
| Jaipur | `cioins/jaipur/v1` | Hindi headings possible |
| Kolkata | `cioins/kolkata/v1` | |
| Lucknow | `cioins/lucknow/v1` | Hindi headings possible |
| Mumbai | `cioins/mumbai/v1` | |
| Noida | `cioins/noida/v1` | |
| Patna | `cioins/patna/v1` | Hindi headings possible |
| Pune | `cioins/pune/v1` | |

The office list follows CIOINS's published ombudsman centres at the time of collection; re-check it in PR 3. Rows are filled as each office is first seen. A Hindi heading is only used as a **marker**; the body text must still be English (scope §2.4), otherwise the document is dropped as `non_english`.

---

## 4. Versioning rules

- A rule ID has a version suffix (`/v1`, `/v2`). Any change to a rule's markers bumps its version.
- `marker_rule` in each JSON records the version used, so audit results can be tied to a rule.
- After a rule change, re-run segmentation for **all** documents of that source/office and redo the hand check for that rule (`manual-audit-protocol.md` §3).
- Marker changes change segment text, so they change the dataset hash → new dataset version.

---

## 5. Validation (per document)

| Check | Fails when | Result |
|---|---|---|
| Required sections | `complaint` or `award` empty; `findings` empty | Drop: `missing_<section>` |
| Insurer position | Empty for CIOINS or FSPO | Drop: `missing_insurer_position` (FOS exempt, §3.1) |
| Minimum length | `complaint + insurer_position` < 200 chars | Drop: `facts_too_short` |
| Order | Spans overlap or out of order | Drop: `order_violation` |
| Leak markers | Any findings/award marker string appears inside `complaint` or `insurer_position` | Drop: `marker_in_facts` (L1 marker probe) |
| Language | English share of facts < 80% (word-level) | Drop: `non_english` |

`_segment_log.csv` columns: `doc_id, source, office, marker_rule, status, reason, facts_chars, findings_chars`.

---

## 6. Gate (PR 5)

- **≥ 95%** of 50 hand-checked documents correctly segmented, drawn per `manual-audit-protocol.md` §3 (stratified across sources and at least 5 CIOINS offices).
- Drop rate reported per source and per office; any office with > 30% drops gets a dedicated rule before PR 5 merges, or is listed as a known gap in the data card.
- Risk checkpoint: CIOINS documents surviving this stage are counted toward the ~800 threshold (scope §5).
