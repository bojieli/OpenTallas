#!/usr/bin/env python3
"""DIE-S81-51/RF-H 11-03: the BF column form drives the BF seg-label floor and the BF emission shift.
python3 tools/s81_dv/layer_prog/test_bf_col_form.py   (exit 0 = PASS)"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bf_col_form as F  # noqa: E402


def test_forms():
    assert F.deltas('base') == (0, 0) and F.seg_label_floor('base') == 231
    for f in F.RECIPES:
        if not (F.ROOT / F.RECIPES[f][0]).exists():
            continue
        b, p = F.deltas(f)
        assert F.seg_label_floor(f) == 231 + b
        if f == 'rfh1':
            assert (b, p) == (F.brnecut(f), 0)
        if f == 'rfh3':
            assert b == p == 2 + F.brnecut(f)


def test_calendar_constants():
    import importlib
    f = F.form()
    import xs_field_calendar as XF
    importlib.reload(XF)
    b = F.deltas(f)[0]
    assert XF.BF_SEG_LABEL_FLOOR == 231 + b
    for op in ('attn.wo_a', 'ffn.router'):
        assert XF.FLOORS[op][1] == 231 + b and XF.FLOORS[op][2] == 230 + b, (op, XF.FLOORS[op])


if __name__ == '__main__':
    test_forms()
    test_calendar_constants()
    print('test_bf_col_form PASS form', F.form(), 'deltas', F.deltas())
