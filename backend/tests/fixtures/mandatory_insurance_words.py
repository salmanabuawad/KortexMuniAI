"""Reconstructed word layout of the mandatory-insurance certificate.

Coordinates in PDF points (top-left origin). Native Hebrew PDF words come out in
VISUAL (left-to-right) order, so multi-word labels are stored with the left token
first (e.g. רישוי then מס'). This exercises the RTL-aware matcher.

Values mirror the real document:
  vehicle_number  7046676        (מס' רישוי)
  id_number       37005618       (מס' זהות / ח"פ)  -- must NOT become vehicle_number
  policy_number   201-502525667826-00
  policy_holder   אבו עואד נדא
  engine_capacity 1197
  production_year 2012
  insurance_start 02/08/2026
  insurance_end   15/08/2026
  premium         234.00
"""

from __future__ import annotations

from app.vehicles.extraction.schemas import Word


def _w(text: str, x0: float, y: float, w: float = 34, source: str = "pdf_text") -> Word:
    return Word(text, x0, y, x0 + w, y + 12, page=1, conf=1.0, source=source)


def build_words() -> dict[int, list[Word]]:
    words: list[Word] = []

    # --- Title (classification) — reading order right-to-left in the list ---
    words += [
        _w("תעודת", 380, 40), _w("ביטוח", 335, 40), _w("חובה", 300, 40),
        _w("פקודת", 470, 40), _w("ביטוח", 430, 40), _w("רכב", 400, 40), _w("מנועי", 360, 40),
        _w("הראל", 720, 40),  # insurer
    ]

    # --- Label row (y=140) + value row (y=160): vehicle / id / policy ---
    # מס' רישוי  (visual: רישוי then מס')
    words += [_w("רישוי", 465, 140, 33), _w("מס'", 500, 140, 20)]
    words += [_w("7046676", 470, 160, 55)]

    # מס' זהות / ח"פ
    words += [_w("זהות", 350, 140, 30), _w("מס'", 382, 140, 20)]
    words += [_w("37005618", 352, 160, 50)]

    # מס' פוליסה
    words += [_w("פוליסה", 600, 140, 40), _w("מס'", 642, 140, 20)]
    words += [_w("201-502525667826-00", 595, 160, 70)]

    # --- Policy holder (name to the LEFT of the label, same row; RTL: אבו is
    # rightmost so it reads אבו עואד נדא) ---
    words += [
        _w("נדא", 560, 220, 30), _w("עואד", 600, 220, 38), _w("אבו", 640, 220, 38),
        _w("הפוליסה", 700, 220, 40), _w("בעל", 742, 220, 20),
    ]

    # --- Details row (labels y=300, values y=320) ---
    words += [_w("מנוע", 300, 300, 30), _w("נפח", 332, 300, 20), _w("1197", 305, 320, 40)]
    words += [_w("ייצור", 400, 300, 35), _w("שנת", 437, 300, 25), _w("2012", 405, 320, 35)]
    words += [_w("מתאריך", 500, 300, 60), _w("02/08/2026", 505, 320, 70)]
    words += [_w("תאריך", 622, 300, 38), _w("עד", 600, 300, 20), _w("15/08/2026", 600, 320, 70)]
    words += [_w("פרמיה", 700, 300, 50), _w("234.00", 705, 320, 50)]

    return {1: words}
