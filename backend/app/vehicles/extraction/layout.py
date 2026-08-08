"""Layout-aware label detection and label->value resolution.

Works on a list of positioned Words (from native PDF or OCR word boxes). RTL
Hebrew PDFs return unreliable reading order, so we NEVER trust flat text order —
everything here is geometry-based.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.vehicles.extraction.anchors import best_field_for_phrase
from app.vehicles.extraction.schemas import Word


@dataclass
class LabelHit:
    field: str
    text: str
    score: float
    x0: float
    y0: float
    x1: float
    y1: float
    page: int

    @property
    def cx(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2

    @property
    def h(self) -> float:
        return max(1.0, self.y1 - self.y0)


def group_rows(words: list[Word], tol_ratio: float = 0.6) -> list[list[Word]]:
    """Group words into visual rows by vertical overlap. Each row sorted by x."""
    rows: list[list[Word]] = []
    for w in sorted(words, key=lambda w: w.cy):
        placed = False
        for row in rows:
            ref = row[0]
            if abs(w.cy - ref.cy) <= tol_ratio * ref.h:
                row.append(w)
                placed = True
                break
        if not placed:
            rows.append([w])
    for row in rows:
        row.sort(key=lambda w: w.x0)
    return rows


def _median_height(words: list[Word]) -> float:
    hs = sorted(w.h for w in words) or [12.0]
    return hs[len(hs) // 2]


def find_label_hits(words: list[Word], max_span: int = 4) -> list[LabelHit]:
    """Detect field labels, matching phrases across up to ``max_span`` CONTIGUOUS
    words in the same row (labels like מס' + רישוי are separate but adjacent
    tokens). A large horizontal gap ends a run, so tokens from two different
    labels sharing a row are never joined into a false phrase."""
    hits: list[LabelHit] = []
    max_gap = max(20.0, 2.5 * _median_height(words))
    for row in group_rows(words):
        n = len(row)
        for i in range(n):
            for span in range(1, max_span + 1):
                if i + span > n:
                    break
                chunk = row[i : i + span]
                # Enforce contiguity: bail if any adjacent gap in the chunk is wide.
                if any(chunk[k + 1].x0 - chunk[k].x1 > max_gap for k in range(len(chunk) - 1)):
                    break
                # RTL: native PDF words are in visual (LTR) order, so a label like
                # "מס' רישוי" appears as [רישוי][מס']. Try both directions.
                lr = " ".join(w.text for w in chunk)
                rl = " ".join(w.text for w in reversed(chunk))
                f_lr, s_lr = best_field_for_phrase(lr)
                f_rl, s_rl = best_field_for_phrase(rl)
                use_rl = s_rl > s_lr
                field, score = (f_rl, s_rl) if use_rl else (f_lr, s_lr)
                phrase = rl if use_rl else lr
                if field:
                    hits.append(LabelHit(
                        field=field, text=phrase, score=score,
                        x0=min(w.x0 for w in chunk), y0=min(w.y0 for w in chunk),
                        x1=max(w.x1 for w in chunk), y1=max(w.y1 for w in chunk),
                        page=chunk[0].page,
                    ))
    # Keep the best (highest score, then longest) hit per (field, approx position).
    hits.sort(key=lambda h: (h.field, round(h.cy), -h.score, -(h.x1 - h.x0)))
    deduped: list[LabelHit] = []
    seen: set[tuple[str, int, int]] = set()
    for h in hits:
        key = (h.field, round(h.cy / 6), round(h.cx / 40))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(h)
    return deduped


def _overlap(a0: float, a1: float, b0: float, b1: float) -> float:
    return max(0.0, min(a1, b1) - max(a0, b0))


def relation_score(label: LabelHit, cand: Word) -> tuple[float, str]:
    """Geometric association score between a label and a candidate value token.

    Higher = more likely to be that label's value. Considers (in priority order):
    directly below in the same column, same row (either side — RTL puts the value
    to the left), then general proximity. Returns (score, relation)."""
    if cand.page != label.page:
        return 0.0, "other_page"

    col_overlap = _overlap(label.x0, label.x1, cand.x0, cand.x1)
    row_overlap = _overlap(label.y0, label.y1, cand.cy - 1, cand.cy + 1)
    unit = label.y1 - label.y0 or 10.0

    # Below, column-aligned (classic table label-over-value).
    if cand.y0 >= label.y1 - unit * 0.3 and col_overlap > 0:
        vdist = cand.cy - label.cy
        if 0 < vdist <= unit * 6:
            return 100.0 - (vdist / unit) * 6.0, "below"

    # Same row (value beside the label; RTL usually to the left).
    if row_overlap > 0 or abs(cand.cy - label.cy) <= unit * 0.6:
        hdist = abs(cand.cx - label.cx)
        return 90.0 - (hdist / unit) * 4.0, "same_row"

    # General proximity fallback.
    dist = ((cand.cx - label.cx) ** 2 + (cand.cy - label.cy) ** 2) ** 0.5
    return max(0.0, 40.0 - (dist / unit) * 3.0), "near"


def resolve_value(label: LabelHit, words: list[Word], *, numeric_only: bool = False,
                  exclude: set[int] | None = None) -> tuple[Word | None, float, str]:
    """Find the word that is the value for ``label``. Returns (word, score, relation)."""
    exclude = exclude or set()
    best: tuple[Word | None, float, str] = (None, 0.0, "")
    for w in words:
        if id(w) in exclude:
            continue
        if not w.text.strip():
            continue
        if numeric_only and not any(ch.isdigit() for ch in w.text):
            continue
        # Skip words that are themselves the label span.
        if (abs(w.cx - label.cx) < 1 and abs(w.cy - label.cy) < 1):
            continue
        score, rel = relation_score(label, w)
        if score > best[1]:
            best = (w, score, rel)
    return best
