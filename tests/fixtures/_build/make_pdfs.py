"""Build the synthetic PDF fixtures deterministically (test-fixtures.md §2, §10).

Run from the repo root::

    uv run python tests/fixtures/_build/make_pdfs.py           # rebuild the committed PDFs
    uv run python tests/fixtures/_build/make_pdfs.py --check   # fail if a rebuild would differ

Two kinds of PDF, both byte-identical on every run and every platform:

* ``text_pdf``: a PDF with a text layer, written by reportlab in invariant mode
  (fixed dates and document ID) and without stream compression.
* ``scan_pdf``: an image-only page, like a scanned award: the text is rendered
  with Pillow's built-in bitmap font, speckled with seeded noise, and stored as
  an uncompressed 1-bit image in a PDF written by hand. Nothing here depends on
  the zlib or FreeType build.

The e2e corpus (``tests/e2e/corpus.py``) uses the same two functions.
"""

from __future__ import annotations

import argparse
import hashlib
import random
import sys
import tempfile
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas

BUILD_DIR = Path(__file__).resolve().parent
FIXTURES_DIR = BUILD_DIR.parent
SOURCES_DIR = BUILD_DIR / "sources"
AUTHOR = "ClaimSense synthetic fixture"

# (source text, output path relative to tests/fixtures/, kind)
BUILDS: tuple[tuple[str, str, str], ...] = (
    ("cioins_award_text.txt", "collect/cioins/award_text.pdf", "text"),
    ("cioins_award_scan.txt", "collect/cioins/award_scan.pdf", "scan"),
    ("cioins_award_nonhealth.txt", "collect/cioins/award_nonhealth.pdf", "text"),
)

# Text layout (points).
FONT_NAME = "Helvetica"
FONT_SIZE = 10
LEADING = 14
MARGIN = 54
WRAP_COLUMNS = 96

# Scan layout (pixels). 600 x 848 keeps the A4 ratio and the file under 100 KB.
SCAN_WIDTH = 600
SCAN_HEIGHT = 848
SCAN_SCALE = 2
SCAN_MARGIN = 20
SCAN_LINE_HEIGHT = 12
SCAN_WRAP_COLUMNS = 44
SCAN_NOISE_PIXELS = 1500
SCAN_SEED = 13


def _wrap(text: str, columns: int) -> list[str]:
    lines: list[str] = []
    for line in text.splitlines():
        lines.extend(textwrap.wrap(line, columns) or [""])
    return lines


def text_pdf(text: str, path: Path, title: str = "Synthetic document") -> None:
    """Write ``text`` as a PDF with a text layer. Same text, same bytes."""
    _, height = A4
    canvas = Canvas(str(path), pagesize=A4, invariant=1, pageCompression=0)
    canvas.setAuthor(AUTHOR)
    canvas.setTitle(title)
    canvas.setFont(FONT_NAME, FONT_SIZE)
    y = height - MARGIN
    for line in _wrap(text, WRAP_COLUMNS):
        if y < MARGIN:
            canvas.showPage()
            canvas.setFont(FONT_NAME, FONT_SIZE)
            y = height - MARGIN
        canvas.drawString(MARGIN, y, line)
        y -= LEADING
    canvas.save()


def _scan_bitmap(text: str, seed: int) -> Image.Image:
    """Render ``text`` as a noisy 1-bit page image."""
    small = Image.new("1", (SCAN_WIDTH // SCAN_SCALE, SCAN_HEIGHT // SCAN_SCALE), 1)
    draw = ImageDraw.Draw(small)
    font = ImageFont.load_default_imagefont()
    y = SCAN_MARGIN // SCAN_SCALE
    for line in _wrap(text, SCAN_WRAP_COLUMNS):
        draw.text((SCAN_MARGIN // SCAN_SCALE, y), line, font=font, fill=0)
        y += SCAN_LINE_HEIGHT
    page = small.resize((SCAN_WIDTH, SCAN_HEIGHT), Image.Resampling.NEAREST)
    rng = random.Random(seed)
    for _ in range(SCAN_NOISE_PIXELS):
        page.putpixel((rng.randrange(SCAN_WIDTH), rng.randrange(SCAN_HEIGHT)), 0)
    return page


def scan_pdf(text: str, path: Path, seed: int = SCAN_SEED) -> None:
    """Write ``text`` as an image-only, one-page PDF (no text layer). Same input, same bytes."""
    width_pt, height_pt = (int(side) for side in A4)
    pixels = _scan_bitmap(text, seed).tobytes()
    content = f"q {width_pt} 0 0 {height_pt} 0 0 cm /Im0 Do Q".encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {width_pt} {height_pt}] "
            "/Resources << /XObject << /Im0 4 0 R >> >> /Contents 5 0 R >>"
        ).encode("ascii"),
        (
            f"<< /Type /XObject /Subtype /Image /Width {SCAN_WIDTH} /Height {SCAN_HEIGHT} "
            f"/ColorSpace /DeviceGray /BitsPerComponent 1 /Length {len(pixels)} >>\n"
        ).encode("ascii")
        + b"stream\n"
        + pixels
        + b"\nendstream",
        f"<< /Length {len(content)} >>\n".encode("ascii") + b"stream\n" + content + b"\nendstream",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets: list[int] = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode("ascii") + body + b"\nendobj\n"
    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode("ascii")
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode("ascii")
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n".encode("ascii")
    out += f"startxref\n{xref_at}\n%%EOF\n".encode("ascii")
    path.write_bytes(bytes(out))


def build_all(out_dir: Path) -> list[Path]:
    """Build every PDF in ``BUILDS`` under ``out_dir``; return the paths written."""
    written: list[Path] = []
    for source_name, relative, kind in BUILDS:
        text = (SOURCES_DIR / source_name).read_text(encoding="utf-8")
        path = out_dir / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if kind == "scan":
            scan_pdf(text, path)
        else:
            text_pdf(text, path, title=Path(relative).stem)
        written.append(path)
    return written


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    """Rebuild the committed PDFs, or with ``--check`` compare a rebuild with them."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="compare a rebuild; write nothing")
    args = parser.parse_args()
    if not args.check:
        for path in build_all(FIXTURES_DIR):
            print(f"wrote {path.relative_to(FIXTURES_DIR)}  {_sha256(path)}")
        return 0
    different = 0
    with tempfile.TemporaryDirectory() as tmp:
        for path in build_all(Path(tmp)):
            relative = path.relative_to(tmp)
            committed = FIXTURES_DIR / relative
            same = committed.is_file() and _sha256(committed) == _sha256(path)
            print(f"{'same     ' if same else 'DIFFERENT'} {relative}")
            different += not same
    return 1 if different else 0


if __name__ == "__main__":
    sys.exit(main())
