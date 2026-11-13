"""The synthetic world: made-up decisions and the fake sites that serve them (CONVENTIONS §7).

``build_corpus(root, seed)`` writes, under ``root``, everything the collectors
need to run exactly as they would against the real sites, and returns the
ground truth later stages are checked against. This PR implements CIOINS
(30 health awards plus non-health distractors); PR 4 adds FOS and FSPO behind
the same function, to 90 decisions.

What every decision has:

* all four sections (complaint, insurer position, findings, award) under the
  headings the source uses (``docs/data/segmentation-rules.md`` §3.3);
* fictional personal data (name, address, PIN, phone, policy number, hospital),
  so the anonymiser in PR 6 has work to do and its output can be searched for leaks;
* a **weak** signal in the facts and a **strong** one in the findings: the
  complaint carries a cue that matches the label about 70% of the time, while
  the findings state the reasoning outright. Models trained on facts can beat
  the majority class; a model that sees findings does much better, which is
  how a leak would show up.

Everything is generated at run time into the session's temp folder; nothing
here is committed. All people, insurers, hospitals and numbers are invented.
The listing layout matches the assumption documented in ``claimsense.collect.cioins``.
"""

from __future__ import annotations

import calendar
import random
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml

from claimsense import config
from claimsense.config import Config
from claimsense.schema import COUNTRY_OF_SOURCE, LABELS
from tests.fixtures._build.make_pdfs import text_pdf

DECISIONS_PER_SOURCE = 30
FIRST_MONTH = (2019, 1)
LAST_MONTH = (2025, 12)
# How often the cue in the complaint agrees with the label (the "weak signal").
CUE_AGREEMENT = 0.7

# Placeholder strings until PR 4 defines the RejectionReason enum (data-schema.md §1).
REJECTION_REASONS = (
    "non_disclosure",
    "waiting_period",
    "exclusion",
    "not_medically_necessary",
    "documentation",
    "other",
)

CIOINS_OFFICES = ("Ahmedabad", "Bengaluru", "Bhopal", "Chennai", "Delhi", "Mumbai")
CIOINS_PRODUCTS = (
    ("Individual Mediclaim", "individual_mediclaim"),
    ("Group Mediclaim", "group_mediclaim"),
    ("Overseas Mediclaim", "overseas_mediclaim"),
)
CIOINS_DISTRACTOR_POLICIES = (
    "Motor (Private Car Package)",
    "Life (Endowment)",
    "Fire and Burglary",
    "Marine Cargo",
    "Personal Accident",
)

INSURERS = (
    "Fictional General Insurance Co. Ltd.",
    "Madeup Health Insurance Ltd.",
    "Placeholder Assurance Co. Ltd.",
    "Specimen Standalone Health Insurance Ltd.",
)
HONORIFICS = ("Shri", "Smt")
FIRST_NAMES = (
    "Aarav", "Meera", "Kabir", "Ananya", "Rohan", "Ishita", "Vikram", "Neha", "Arjun", "Pooja",
)  # fmt: skip
SURNAMES = (
    "Testwala", "Samplekar", "Demopatel", "Mockerjee", "Fixturewala",
    "Exampleton", "Specimenwal", "Nobodykar", "Placeholderan", "Dummyanathan",
)  # fmt: skip
HOSPITALS = (
    "Lakeside Demo Nursing Home",
    "Hilltop Sample Hospital",
    "Riverside Mock Clinic",
    "Greenfield Specimen Hospital",
)
CONDITIONS = (
    "a kidney stone", "cataract in the left eye", "a fractured wrist", "dengue fever",
    "gall bladder stones", "a slipped disc", "appendicitis", "a hernia",
)  # fmt: skip

# The cue in the complaint: weakly tied to the label.
CUES = {
    "upheld": (
        "The complainant states that the condition was diagnosed for the first time during "
        "this admission, after the policy began."
    ),
    "partially_upheld": (
        "The complainant accepts part of the deduction made from the hospital bill but "
        "disputes the rest."
    ),
    "rejected": (
        "The complainant accepts that an earlier consultation for the same complaint was "
        "not mentioned in the proposal form."
    ),
}

# What the insurer says, by rejection reason.
INSURER_POSITIONS = {
    "non_disclosure": (
        "The insurer repudiated the claim on the ground of non-disclosure of material facts "
        "in the proposal form."
    ),
    "waiting_period": (
        "The insurer rejected the claim because the treatment fell within the two-year "
        "waiting period for the stated condition."
    ),
    "exclusion": "The insurer relied on a permanent exclusion clause of the policy.",
    "not_medically_necessary": (
        "The insurer submitted that hospitalisation was not medically necessary and the "
        "treatment could have been taken as an out-patient."
    ),
    "documentation": (
        "The insurer closed the claim because the documents it had called for were not "
        "submitted within the time allowed."
    ),
    "other": (
        "The insurer settled the claim after deducting amounts it considers above reasonable "
        "and customary charges."
    ),
}

# The reasoning: strongly tied to the label. This must never reach the model input.
FINDINGS = {
    "upheld": (
        "The insurer has not produced any record of earlier diagnosis or treatment. Its "
        "ground for refusing the claim is not supported by the documents on file, and the "
        "refusal cannot be sustained."
    ),
    "partially_upheld": (
        "The insurer was right to apply the policy limit, but part of the deduction has no "
        "basis in the policy terms. The complainant is entitled to that part only."
    ),
    "rejected": (
        "The documents on file support the insurer's ground. The policy terms were applied "
        "correctly and there is no reason to interfere with the insurer's decision."
    ),
}
AWARDS = {
    "upheld": (
        "The complaint is allowed. The insurer is directed to pay Rs. {amount} to the "
        "complainant within 30 days."
    ),
    "partially_upheld": (
        "The complaint is partly allowed. The insurer is directed to pay Rs. {part} to the "
        "complainant within 30 days."
    ),
    "rejected": "The complaint is dismissed. No relief is granted.",
}

SECTION_HEADINGS = {
    "cioins": {
        "complaint": "Brief facts of the case",
        "insurer_position": "Insurer's submission",
        "findings": "Observations and conclusion",
        "award": "AWARD",
    }
}


@dataclass(frozen=True)
class Decision:
    """One synthetic decision and everything later stages need to check against it.

    ``label``, ``rejection_reason`` and ``product`` are ``None`` for a non-health
    distractor, which the collector must filter and never download.
    """

    doc_id: str
    source: str
    country: str
    decision_date: date
    office: str | None
    insurer: str
    product_listed: str
    product: str | None
    label: str | None
    rejection_reason: str | None
    cue_label: str | None
    sections: dict[str, str]
    pii: dict[str, str]
    text: str
    url: str

    @property
    def is_health(self) -> bool:
        """Whether this is a health decision (not a distractor)."""
        return self.product is not None


@dataclass(frozen=True)
class Corpus:
    """The generated world: where the fake sites are and what is true about each decision."""

    root: Path
    seed: int
    decisions: tuple[Decision, ...]
    urlmaps: dict[str, Path]

    def health(self, source: str | None = None) -> list[Decision]:
        """The health decisions, in listing order; optionally one source only."""
        return [d for d in self.decisions if d.is_health and (source is None or d.source == source)]

    def distractors(self, source: str | None = None) -> list[Decision]:
        """The non-health decisions that must be filtered; optionally one source only."""
        return [
            d for d in self.decisions if not d.is_health and (source is None or d.source == source)
        ]

    def truth(self, doc_id: str) -> Decision:
        """The ground truth for one ``doc_id``."""
        for decision in self.decisions:
            if decision.doc_id == doc_id:
                return decision
        raise KeyError(doc_id)


def _spread_dates(count: int, rng: random.Random) -> list[date]:
    """``count`` dates spread evenly from ``FIRST_MONTH`` to ``LAST_MONTH``, in order."""
    first = FIRST_MONTH[0] * 12 + FIRST_MONTH[1] - 1
    last = LAST_MONTH[0] * 12 + LAST_MONTH[1] - 1
    dates = []
    for index in range(count):
        month_index = first + round(index * (last - first) / (count - 1))
        dates.append(date(month_index // 12, month_index % 12 + 1, rng.randint(1, 28)))
    return dates


def _person(index: int, rng: random.Random) -> dict[str, str]:
    """Fictional personal data, unique per decision, in the formats real awards use."""
    name = (
        f"{HONORIFICS[index % 2]} {FIRST_NAMES[index % len(FIRST_NAMES)]} "
        f"{SURNAMES[(index * 3 + index // len(FIRST_NAMES)) % len(SURNAMES)]}"
    )
    pin = f"9999{index:02d}"
    return {
        "name": name,
        "address": f"{index + 1} Placeholder Lane, Samplepur {index + 1}",
        "pin": pin,
        "phone": f"90000 00{index:03d}",
        "policy_number": f"DEMO/POL/{2000 + index}/{rng.randint(10000, 99999)}",
        "hospital": HOSPITALS[index % len(HOSPITALS)],
    }


def _cue_label(label: str, rng: random.Random) -> str:
    """The label whose cue appears in the complaint: the true one most of the time."""
    if rng.random() < CUE_AGREEMENT:
        return label
    return rng.choice([other for other in LABELS if other != label])


def _cioins_text(
    decision_date: date,
    office: str,
    award_no: str,
    insurer: str,
    product_listed: str,
    sections: dict[str, str],
    pii: dict[str, str],
) -> str:
    """The full text of one award, laid out like a CIOINS award order."""
    year = decision_date.year if decision_date.month >= 4 else decision_date.year - 1
    headings = SECTION_HEADINGS["cioins"]
    lines = [
        "SYNTHETIC TEST DOCUMENT - NOT A REAL AWARD - ALL NAMES AND NUMBERS ARE FICTIONAL",
        "",
        f"PROCEEDINGS BEFORE THE INSURANCE OMBUDSMAN, {office.upper()}",
        "(Under Rule 17 of the Insurance Ombudsman Rules, 2017)",
        "",
        f"Award No: IO/{office[:3].upper()}/A/HI/{award_no}/{year}-{(year + 1) % 100:02d}",
        f"Complainant: {pii['name']}, {pii['address']}, PIN {pii['pin']}",
        f"Contact: {pii['phone']}",
        f"Respondent: {insurer}",
        f"Policy No: {pii['policy_number']}",
        f"Type of policy: {product_listed}",
        f"Date of Award: {decision_date:%d.%m.%Y}",
    ]
    for key in ("complaint", "insurer_position", "findings", "award"):
        lines += ["", headings[key], sections[key]]
    lines += ["", f"Dated at {office} on {decision_date:%d.%m.%Y}", "INSURANCE OMBUDSMAN"]
    return "\n".join(lines) + "\n"


def _cioins_decisions(base_url: str, rng: random.Random) -> list[Decision]:
    """30 health awards and one non-health distractor per distractor policy type."""
    decisions: list[Decision] = []
    dates = _spread_dates(DECISIONS_PER_SOURCE, rng)
    for index, decision_date in enumerate(dates):
        label = LABELS[index % len(LABELS)]
        reason = REJECTION_REASONS[index % len(REJECTION_REASONS)]
        office = CIOINS_OFFICES[index % len(CIOINS_OFFICES)]
        product_listed, product = CIOINS_PRODUCTS[index % len(CIOINS_PRODUCTS)]
        insurer = INSURERS[index % len(INSURERS)]
        pii = _person(index, rng)
        cue_label = _cue_label(label, rng)
        amount = rng.randrange(40, 400) * 1000
        condition = CONDITIONS[index % len(CONDITIONS)]
        sections = {
            "complaint": (
                f"The complainant, {pii['name']}, was admitted to {pii['hospital']} for "
                f"treatment of {condition} and lodged a claim for Rs. {amount} under the "
                f"policy. {CUES[cue_label]}"
            ),
            "insurer_position": INSURER_POSITIONS[reason],
            "findings": FINDINGS[label],
            "award": AWARDS[label].format(amount=amount, part=amount // 2),
        }
        # Award numbers repeat across offices: each number is used by two offices.
        award_no = f"{index // 2 + 1:04d}"
        decisions.append(
            _cioins_decision(
                base_url, decision_date, office, award_no, insurer, product_listed, product,
                label, reason, cue_label, sections, pii,
            )  # fmt: skip
        )

    for index, policy in enumerate(CIOINS_DISTRACTOR_POLICIES):
        decision_date = dates[(index * 7) % len(dates)]
        office = CIOINS_OFFICES[(index + 1) % len(CIOINS_OFFICES)]
        pii = _person(DECISIONS_PER_SOURCE + index, rng)
        sections = {
            "complaint": f"The complainant, {pii['name']}, made a claim unrelated to health.",
            "insurer_position": "The insurer rejected the claim under the policy terms.",
            "findings": "The matter does not concern a health insurance policy.",
            "award": "The complaint is dismissed. No relief is granted.",
        }
        decisions.append(
            _cioins_decision(
                base_url, decision_date, office, f"9{index:03d}", INSURERS[index % len(INSURERS)],
                policy, None, None, None, None, sections, pii,
            )  # fmt: skip
        )
    return decisions


def _cioins_decision(
    base_url: str,
    decision_date: date,
    office: str,
    award_no: str,
    insurer: str,
    product_listed: str,
    product: str | None,
    label: str | None,
    reason: str | None,
    cue_label: str | None,
    sections: dict[str, str],
    pii: dict[str, str],
) -> Decision:
    slug = office.lower()
    return Decision(
        doc_id=f"cioins-{decision_date:%Y-%m}-{slug}-{award_no}",
        source="cioins",
        country=COUNTRY_OF_SOURCE["cioins"],
        decision_date=decision_date,
        office=office,
        insurer=insurer,
        product_listed=product_listed,
        product=product,
        label=label,
        rejection_reason=reason,
        cue_label=cue_label,
        sections=sections,
        pii=pii,
        text=_cioins_text(decision_date, office, award_no, insurer, product_listed, sections, pii),
        url=f"{base_url}/AwardsMonthwise/{decision_date:%Y/%m}/{slug}/{award_no}.pdf",
    )


def _page(title: str, body: str) -> str:
    return (
        '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        f"<title>{title}</title>\n</head>\n<body>\n"
        "<!-- SYNTHETIC PAGE generated by tests/e2e/corpus.py -->\n"
        f"<h1>{title}</h1>\n{body}</body>\n</html>\n"
    )


def _write_cioins_site(site: Path, cfg: Config, decisions: list[Decision]) -> Path:
    """Write the fake CIOINS site (PDFs, listing pages, robots.txt); return its urlmap."""
    section = cfg.collect.sources.cioins
    base_url = section.audit.base_url
    site.mkdir(parents=True, exist_ok=True)
    urlmap: dict[str, str] = {section.audit.robots_url: "robots.txt", section.start: "index.html"}
    (site / "robots.txt").write_text("User-agent: *\nDisallow: /admin/\n", encoding="utf-8")

    months = sorted({(d.decision_date.year, d.decision_date.month) for d in decisions})
    # One month in the archive has no awards at all: 0 rows, not an error.
    empty_month = (LAST_MONTH[0] + 1, 1)
    month_rows = []
    for year, month in [*months, empty_month]:
        name = f"month_{year}-{month:02d}.html"
        path = f"/AwardsMonthwise/{year}/{month:02d}"
        urlmap[base_url + path] = name
        label = f"{calendar.month_name[month]} {year}"
        month_rows.append(
            f'    <tr><td><a class="month-link" href="{path}">{label}</a></td></tr>\n'
        )
        listed = [
            d for d in decisions if (d.decision_date.year, d.decision_date.month) == (year, month)
        ]
        (site / name).write_text(_month_page(label, listed, base_url), encoding="utf-8")

    index_body = (
        '<table id="awards-archive">\n  <thead><tr><th>Month</th></tr></thead>\n  <tbody>\n'
        + "".join(month_rows)
        + "  </tbody>\n</table>\n"
    )
    (site / "index.html").write_text(
        _page("Health Insurance Awards - Archive", index_body), encoding="utf-8"
    )
    for decision in decisions:
        name = f"{decision.doc_id}.pdf"
        text_pdf(decision.text, site / name, title=decision.doc_id)
        urlmap[decision.url] = name

    urlmap_path = site / "urlmap.yaml"
    urlmap_path.write_text(yaml.safe_dump(urlmap, sort_keys=True), encoding="utf-8")
    return urlmap_path


def _month_page(label: str, listed: list[Decision], base_url: str) -> str:
    if not listed:
        body = '<p class="no-awards">No awards were published for this month.</p>\n'
        return _page(f"Health Insurance Awards - {label}", body)
    blocks = []
    for office in sorted({d.office for d in listed if d.office}):
        rows = []
        for d in (d for d in listed if d.office == office):
            award_no = d.doc_id.rsplit("-", 1)[1]
            rows.append(
                "      <tr>"
                f'<td class="award-no">{award_no}</td>'
                f'<td class="award-date">{d.decision_date:%d.%m.%Y}</td>'
                f'<td class="insurer">{d.insurer}</td>'
                f'<td class="policy-type">{d.product_listed}</td>'
                f'<td><a class="award-pdf" href="{d.url.removeprefix(base_url)}">PDF</a></td>'
                "</tr>\n"
            )
        blocks.append(
            f'<div class="office" id="office-{office.lower()}">\n'
            f'  <h2 class="office-name">{office}</h2>\n'
            '  <table class="awards">\n'
            "    <thead><tr><th>Award No</th><th>Date of Award</th><th>Insurer</th>"
            "<th>Type of Policy</th><th>Award</th></tr></thead>\n"
            "    <tbody>\n" + "".join(rows) + "    </tbody>\n  </table>\n</div>\n"
        )
    return _page(f"Health Insurance Awards - {label}", "".join(blocks))


def build_corpus(root: Path, seed: int, cfg: Config | None = None) -> Corpus:
    """Generate the synthetic world under ``root``. Same seed and config, same world.

    Args:
        root: Folder to write the fake sites into (one sub-folder per source).
        seed: Seed for every random choice.
        cfg: Config that gives each source's URLs. Defaults to the current resolved config.
    """
    cfg = cfg if cfg is not None else config.load()
    rng = random.Random(seed)
    cioins = _cioins_decisions(cfg.collect.sources.cioins.audit.base_url, rng)
    urlmaps = {"cioins": _write_cioins_site(Path(root) / "cioins", cfg, cioins)}
    return Corpus(root=Path(root), seed=seed, decisions=tuple(cioins), urlmaps=urlmaps)
