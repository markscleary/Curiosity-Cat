"""curiosity_cat.card — the Clean Bill share card (APP_SPEC.md Shell
section: "Clean Bill viewer with PNG share-card export").

Renders a PNG from any clean-bill.json: a cat glyph, the adventure level,
how many escape attempts it survived, the date, and curiositycat.online.
Pure engine-side rendering (no Tauri, no browser canvas) so the exact same
code path serves the CLI (`curiosity-cat card`), the sidecar
(`ccat-engine serve`'s `render_share_card` method, called from the app's
Clean Bill viewer), and this module's own fixture-driven tests.

Honesty rule (APP_SPEC.md Layer 1): the headline claim is built only from
`observed_trials` — the live, proof-of-enforcement trials `prove()` actually
ran — never from `self_consistency_trials`, which only confirm the compiled
file says what the compiler intended. The card states the self-check count
on its own line, labelled as a self-check, so the two are never read as one
number.
"""

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

CARD_SIZE = (1200, 630)
CARD_FILENAME = "share-card.png"

_BACKGROUND = (250, 244, 231)
_INK = (43, 36, 30)
_MUTED = (120, 108, 96)
_ACCENT = (196, 108, 66)


def _font(size):
    # Pillow >=9.2 accepts a size kwarg on the bundled default font; older
    # Pillow ignores it and always returns the same fixed small size —
    # still renders a valid card, just not at the intended proportions.
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _draw_cat_glyph(draw, cx, cy, r):
    """A simple drawn cat-face glyph: head, two ears, two eyes. Vector
    shapes rather than the 🐱 emoji character, so the card renders
    identically regardless of whether the host has a colour-emoji font.
    """
    draw.polygon([(cx - r, cy - r * 0.2), (cx - r * 0.35, cy - r * 0.2), (cx - r * 0.7, cy - r * 1.35)],
                 fill=_ACCENT)
    draw.polygon([(cx + r, cy - r * 0.2), (cx + r * 0.35, cy - r * 0.2), (cx + r * 0.7, cy - r * 1.35)],
                 fill=_ACCENT)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=_ACCENT)
    eye_r = r * 0.12
    for dx in (-r * 0.35, r * 0.35):
        draw.ellipse([cx + dx - eye_r, cy - eye_r, cx + dx + eye_r, cy + eye_r], fill=_BACKGROUND)


def observed_survived_count(clean_bill):
    """How many observed (live) trials held — the only number this card is
    allowed to call "escape attempts survived" (see module docstring).
    """
    return sum(1 for t in (clean_bill.get("observed_trials") or []) if t.get("held") is True)


def self_check_held_count(clean_bill):
    """How many self-consistency checks held — reported separately, never
    added to observed_survived_count().
    """
    return sum(1 for t in (clean_bill.get("self_consistency_trials") or []) if t.get("held") is True)


def _headline(clean_bill):
    observed = clean_bill.get("observed_trials") or []
    if not observed:
        return "No live escape attempts run yet"
    n = observed_survived_count(clean_bill)
    return f"{n} escape attempt{'' if n == 1 else 's'} survived"


def _self_check_line(clean_bill):
    total = len(clean_bill.get("self_consistency_trials") or [])
    held = self_check_held_count(clean_bill)
    return f"{held}/{total} self-checks held (compiled rules replayed, not independently enforced)"


def render_share_card(clean_bill):
    """Render a Clean Bill dict (the parsed contents of clean-bill.json)
    into a PIL Image. Never raises on a thin/partial dict — every field is
    read defensively, same discipline as the rest of this codebase's
    honesty-sensitive rendering (curiosity_cat.meow).
    """
    level = (clean_bill.get("level") or "unknown").capitalize()
    date = clean_bill.get("date") or ""

    image = Image.new("RGB", CARD_SIZE, _BACKGROUND)
    draw = ImageDraw.Draw(image)

    _draw_cat_glyph(draw, cx=130, cy=150, r=70)

    draw.text((230, 90), "Curiosity Cat", font=_font(28), fill=_MUTED)
    draw.text((230, 125), f"{level} — Clean Bill of Health", font=_font(40), fill=_INK)

    draw.text((80, 300), _headline(clean_bill), font=_font(64), fill=_ACCENT)
    draw.text((80, 400), _self_check_line(clean_bill), font=_font(26), fill=_MUTED)

    if date:
        draw.text((80, 460), date, font=_font(26), fill=_MUTED)

    draw.text((80, 560), "curiositycat.online", font=_font(30), fill=_INK)

    return image


def render_share_card_to_file(clean_bill, out_path):
    """render_share_card() plus writing the PNG to `out_path`. Returns
    `out_path` (as a str) for callers (the CLI, the sidecar) that just want
    the written location back.
    """
    image = render_share_card(clean_bill)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(out_path, format="PNG")
    return str(out_path)


def render_share_card_from_file(clean_bill_path, out_path=None):
    """Load a clean-bill.json from disk and render its share card,
    defaulting `out_path` to share-card.png alongside it — the natural
    location, since clean-bill.json already lives in the dated
    <profile>/proof/proof-<date>/ directory the card is describing.
    """
    clean_bill_path = Path(clean_bill_path)
    clean_bill = json.loads(clean_bill_path.read_text())
    if out_path is None:
        out_path = clean_bill_path.parent / CARD_FILENAME
    return render_share_card_to_file(clean_bill, out_path)
