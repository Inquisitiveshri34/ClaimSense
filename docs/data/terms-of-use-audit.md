# ClaimSense — Terms-of-Use Audit

> The filled PR 2 checklist from `04-data-sources.md` §2: what each publisher's terms say about copying, storing and republishing their decisions, what robots.txt allows, the attribution wording to use, and the usage decision that follows. **A collector may merge only when every box for its source is ticked** (NFR-09).

**Author:** Diya Shrivastava · **Owning PR:** 2 · **Status:** Terms read 2026-11-12 · robots.txt capture pending · permission requests to send

**Related:** `data-sources.md` (→ `04-data-sources.md`), `collection-runbook.md`, `../scope.md` §5, risk R2.

---

## 1. Result at a glance

| Source | Terms allow bulk local storage? | Terms allow publishing derived text? | Decision | PR unblocked? |
|---|---|---|---|---|
| **FSPO (Ireland)** | ✅ Yes, under PSI re-use | ✅ Yes, with conditions | **Proceed** (polite collection, attribute) | PR 4 (FSPO part) ✅ |
| **FOS (UK)** | ❌ Not without prior permission | ❌ Not without prior permission | **Request permission; do not collect yet** | PR 4 (FOS part) ⛔ |
| **CIOINS (India)** | ❌ Not without authorisation | ❌ Not without authorisation | **Request permission; do not collect yet** | PR 3 ⛔ |

**Consequence for the plan:** two of three sources, including the primary target domain, are blocked until permission arrives. This is risk **R2** firing in PR 2, earlier than the PR 3 data-volume checkpoint. See §6 for what happens while waiting.

### 1.1 Decision table

The record a collector depends on, one row per fact. `UNKNOWN — to verify` means nobody has checked it yet; it is never a guess. This table is the same as "Audit record per source" in [`DATA_SOURCES.md`](../../DATA_SOURCES.md); change both together. Its URL, licence, redistribution, `enabled` and audit-date rows are the same values as `collect.sources.<name>` in `config.yaml`, which `claimsense.collect.sources` reads.

| | CIOINS (India) | FOS (UK) | FSPO (Ireland) |
|---|---|---|---|
| **URL** | `https://cioins.co.in` | `https://www.financial-ombudsman.org.uk` | `https://www.fspo.ie` |
| **Terms of use** (page, date read) | *Terms & Conditions* PDF, `cioins.co.in/notification/Terms and Conditions.pdf`, read 2026-11-12 | *Legal information*, `financial-ombudsman.org.uk/legal-policy`, read 2026-11-12 | *Re-use of Public Sector Information*, `fspo.ie/governance/reuse.asp`, read 2026-11-12 |
| **robots.txt rules** for the paths used | UNKNOWN — to verify | UNKNOWN — to verify | UNKNOWN — to verify |
| **Crawl delay** stated in robots.txt | UNKNOWN — to verify | UNKNOWN — to verify | UNKNOWN — to verify |
| **Licence** | UNKNOWN — to verify | UNKNOWN — to verify | Re-use of Public Sector Information (PSI) Regulations; attribution required |
| **Redistribution** of derived, anonymised text | Not allowed | Not allowed | Allowed, with attribution |
| **`enabled`** in `config.yaml` | `false` | `false` | `true` |
| **Audit date** | 2026-11-12 | 2026-11-12 | 2026-11-12 |

- **Licence `UNKNOWN` for CIOINS and FOS.** Neither site offers a licence: CIOINS prohibits unauthorised copying and FOS requires prior permission for storage. A licence exists only once a permission reply states its terms (§7.2). Until that is recorded here and in `config.yaml`, the source registry refuses to load if either source is enabled (`SourceNotCleared`).
- **robots.txt and crawl delay** have not been captured for any source (§3 has the command). Until they are, `collect.min_interval_s` applies; a higher stated crawl delay replaces it.
- **FSPO is enabled on its terms alone.** Its robots.txt row must be verified before the first live collection run (PR 4).

---

## 2. What each source's terms say

Paraphrased from the pages read on 2026-11-12. Re-read before any collection run if more than 3 months have passed (§8).

### 2.1 CIOINS — Council for Insurance Ombudsmen

| Item | Finding |
|---|---|
| **Page read** | Website *Terms & Conditions* PDF (`cioins.co.in/notification/Terms and Conditions.pdf`), last updated 16.04.2026; *Privacy Policy* PDF |
| **Copyright owner** | CIO claims all content and information on the website as its property, protected by IP law |
| **Reuse** | Any unauthorised copying, distribution, modification or use of that content is stated to be prohibited. No open licence is offered |
| **Automated access** | Not addressed |
| **Decisions/awards specifically** | Not addressed separately; awards sit under the general IP clause |
| **Contact for queries** | `inscoun@cioins.co.in` (named in the T&C grievance section) |
| **Governing law** | India; courts in Mumbai |

**Reading:** downloading individual awards to read them is ordinary use of a public site, but systematically copying the archive into a dataset is "use" the clause reserves to CIO. **Authorisation needed before PR 3.**

### 2.2 FOS — Financial Ombudsman Service (UK)

| Item | Finding |
|---|---|
| **Page read** | *Legal information* (`financial-ombudsman.org.uk/legal-policy`) |
| **Copyright owner** | FOS owns copyright in site material unless stated otherwise |
| **Reuse** | Downloading and printing extracts for personal use is allowed; text must not be modified or used in a misleading context |
| **Storage** | Reproducing material, or storing any part of the site in another website or **any public or private electronic retrieval system**, needs prior permission unless the material itself says otherwise |
| **Automated access** | Not addressed directly, but a local SQLite/Parquet corpus and a vector index are both retrieval systems in plain terms |
| **Attribution** | Where reuse is permitted, the source must be quoted |
| **Governing law** | English law |

**Reading:** the precedent index and processed dataset both fall under the storage clause. **Permission needed before PR 4 (FOS).** Check first whether individual decision pages carry their own reuse statement (some FOS publications are under the Open Government Licence); if a decision page states OGL, record it here and the restriction lifts for those pages.

### 2.3 FSPO — Financial Services and Pensions Ombudsman (Ireland)

| Item | Finding |
|---|---|
| **Page read** | *Re-use of Public Sector Information* (`fspo.ie/governance/reuse.asp`) |
| **Copyright owner** | FSPO, unless otherwise indicated |
| **Reuse** | Free of charge, in any format; reuse expressly includes copying, publishing and non-commercial research and study |
| **Conditions** | Acknowledge the source and FSPO copyright when supplying to others; reproduce accurately; not misleading; not mainly for advertising a product; not for unlawful or dishonest purposes |
| **Automated access** | Not addressed; polite-crawler rules still apply (NFR-08) |
| **Liability** | FSPO gives no warranty that information is current or error-free |
| **Contact** | Contact form on fspo.ie |

**Reading:** collection, local processing and publishing anonymised derived text are all permitted with attribution. ClaimSense's anonymisation changes the text, so the published data card must say the text is **modified** from the original (the "accurately" condition).

---

## 3. robots.txt

Not yet captured: the audit environment could not fetch these files. Capture from your own machine and paste the relevant lines below before ticking the robots row.

```bash
for host in cioins.co.in www.financial-ombudsman.org.uk www.fspo.ie; do
  echo "=== $host  $(date -u +%FT%TZ)"
  curl -s -A "ClaimSense-audit/0.1 (+contact: <your email>)" "https://$host/robots.txt"
done | tee docs/data/robots-capture-$(date +%F).txt
```

| Source | Paths ClaimSense will request | Disallowed by robots.txt? | Crawl-delay stated? | Excerpt (paste) |
|---|---|---|---|---|
| CIOINS | `/AwardsHArchive`, `/AwardsMonthwise/…` | ☐ | ☐ | |
| FOS | `/decisions-case-studies/ombudsman-decisions/…`, decision pages | ☐ | ☐ | |
| FSPO | `/decisions/…`, decision PDFs | ☐ | ☐ | |

Rules: if a path is disallowed, that path is not collected even with permission unless the permission explicitly covers automated access. If `Crawl-delay` exceeds 3 s, the collector uses the stated delay (`collection-runbook.md` §4). A missing robots.txt (404) is recorded as "none published", not as permission.

---

## 4. Filled checklist (`04-data-sources.md` §2)

| Check | CIOINS | FOS | FSPO |
|---|---|---|---|
| Terms of use / copyright notice read and summarised | [x] §2.1 | [x] §2.2 | [x] §2.3 |
| robots.txt allows the paths used | [ ] §3 pending | [ ] §3 pending | [ ] §3 pending |
| Automated access permitted (or permission requested) | [ ] request not sent | [ ] request not sent | [x] reuse permitted; terms silent on automation |
| Redistribution of derived, anonymised text permitted? | [ ] **No** unless granted | [ ] **No** unless granted | [x] Yes, with attribution |
| Attribution wording recorded | [x] §5 | [x] §5 | [x] §5 |

A box for "permission requested" is ticked when the email is **sent**; collection still waits for a **yes**. Record replies in §7.

---

## 5. Attribution wording

Used in `DATA_CARD.md`, the README and the app's Data Explorer page.

| Source | Wording |
|---|---|
| FSPO | "Contains information from decisions of the Financial Services and Pensions Ombudsman (Ireland), © FSPO, re-used under the Re-use of Public Sector Information Regulations. Text has been anonymised and shortened by ClaimSense and is not reproduced in its original form." |
| FOS | "Contains material from Financial Ombudsman Service decisions, used with permission granted on ⟨date⟩. Source: financial-ombudsman.org.uk." *(only once permission is granted; use OGL wording instead if decision pages state OGL)* |
| CIOINS | "Contains material from Insurance Ombudsman awards published by the Council for Insurance Ombudsmen, used with permission granted on ⟨date⟩. Source: cioins.co.in." *(only once permission is granted)* |

The app also states, for every precedent, which ombudsman and country it comes from (gap G1).

---

## 6. Usage decision per source

| Source | Collect | Store locally | Train on | Index for retrieval | Publish processed text | Publish stats + weights |
|---|---|---|---|---|---|---|
| FSPO | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| FOS (no permission) | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| FOS (permission: research use only) | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| CIOINS (no permission) | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| CIOINS (permission: research use only) | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |

**While waiting:** build PR 3's collector and tests against a handful of **manually saved** sample pages (normal personal browsing, used only as test fixtures and never committed), and run the real FSPO collection in PR 4. If no CIOINS reply arrives within 4 weeks of sending, or the answer is no, record that here and apply the contingency in `../scope.md` §5 extended: FSPO (+ FOS if granted) for training, with India covered only by what CIOINS permits.

---

## 7. Permission requests

### 7.1 Request template

> **Subject:** Permission request: non-commercial research use of published ombudsman decisions
>
> Dear ⟨Council for Insurance Ombudsmen / Financial Ombudsman Service⟩,
>
> I am a B.Tech Computer Science student at Lovely Professional University building a non-commercial research project, ClaimSense, that studies how published ombudsman decisions on health-insurance claim disputes were decided.
>
> I would like permission to:
> 1. download the published ⟨health-insurance awards / insurance decisions⟩ from your website with an automated script limited to one request every 3 seconds, identified by a User-Agent with my contact email;
> 2. store them locally to build an anonymised research dataset (names, addresses, contact details and reference numbers removed);
> 3. publish code, aggregate statistics and a trained model, with your organisation credited as the source.
>
> I would **not** publish the original documents. ⟨Optional: I would also like to know whether publishing short, anonymised extracts would be acceptable.⟩
>
> The project does not give legal advice and states clearly that each case is decided on its own facts. I would be glad to share the results with you.
>
> Kind regards,
> Diya Shrivastava · ⟨email⟩ · ⟨GitHub link⟩

### 7.2 Log

| Source | Sent to | Date sent | Reply date | Scope granted | Conditions | Stored at |
|---|---|---|---|---|---|---|
| CIOINS | `inscoun@cioins.co.in` | | | | | `docs/data/permissions/` (local, not committed if it contains personal details) |
| FOS | contact route on the FOS site | | | | | |

---

## 8. Re-audit triggers

Re-read terms and recapture robots.txt when any of these happens:

- before each collection run that starts more than 3 months after the last audit;
- a collector test fails because the site structure changed (risk R14);
- a new source is proposed (v2 backlog V2-06);
- before publishing any processed dataset version.

Each re-audit adds a dated row here:

| Date | Source | What changed | Decision changed? |
|---|---|---|---|
| 2026-11-12 | All | First audit | — |

---

*This audit records the project's reading of each publisher's terms for planning purposes. It is not legal advice.*
