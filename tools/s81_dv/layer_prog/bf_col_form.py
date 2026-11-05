#!/usr/bin/env python3
"""S81 BF column form -> compiler schedule constants (DIE-S81-51/RF-H 2026-11-03; TOK-VERIFY-1 20:41 ruling).

The BF pair column ot_v41_bf_col has competing conservative forms (first to sign off wins).  A form that adds cycles to
the BF partials moves two zero-slack compiler constants (TOK-VERIFY-1):
  (1) the BF -> BF go spacing floor (seg-label floor, xs_field_calendar.BF_SEG_LABEL_FLOOR and the attn.wo_a /
      ffn.router measured floors, P231 PASS / P230 FAIL at the base form): + bf_add;
  (2) the BF return calendar (xs_bf.bf_plan emission = the measured BF column partial edge of the shape): every BF
      partial edge + bf_add, unless the measurement record itself was taken on this form (record key bf_col_form).
BF pairs carry only BF16 ops in production (q-phase cfg rows zero), so fp_add (FP partials) moves no BF calendar; it
is reported for completeness.  The deltas are derived from the form's RTL parameters in its kit recipe, so the form
that signs off sets them:
  base   ot_v41_bf_col, BRNECUT 0                              bf_add 0, fp_add 0
  rfh1   ot_v41_bf_col, BRNECUT 1 (RNE encode cut, BF lane +1)   bf_add = BRNECUT, fp_add 0
  rfh3   ot_v41_bf_col3 (3 hard cores): 2 face registers + BRNECUT on the BF sums, FP partials delayed DEQ = 2 + BRNECUT
                                                               bf_add = fp_add = 2 + BRNECUT
FORM: OT_S81_BF_COL_FORM (base | rfh1 | rfh3), default DEFAULT_FORM below (the form branch sets it; the merge of the
signed form keeps it).  The rfh1 / rfh3 floor (231 + bf_add) is the predicted shift of the measured floor; a measured
floor on that form's frame replaces it (FLOOR_MEASURED)."""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_FORM = 'rfh3'
BASE_SEG_LABEL_FLOOR = 231            # S81-WQBP pipe3 / TOKSIM-S81C FSEQ: P231 PASS, P230 FAIL (base form)
RECIPES = {'rfh1': ('results/rfh_1103/bf_col/recipes_rfh_1103.json', 'ot_v41_bf_col'),
           'rfh3': ('results/rfh_1103/bf_col3/recipes_rfh3.json', 'ot_v41_bf_col3_c')}
FLOOR_MEASURED = {}                   # form -> measured seg-label floor on that form's frame (none yet)


def form():
    f = os.environ.get('OT_S81_BF_COL_FORM', DEFAULT_FORM)
    if f not in ('base',) + tuple(RECIPES):
        raise ValueError(f'unknown BF column form {f!r}')
    return f


def brnecut(f):
    if f == 'base':
        return 0
    path, key = RECIPES[f]
    return int(json.loads((ROOT / path).read_text())[key]['params'].get('BRNECUT', 0))


def deltas(f=None):
    """(bf_add, fp_add): edges added to the BF / FP column partials vs the base form"""
    f = f or form()
    b = brnecut(f)
    if f == 'rfh3':
        return 2 + b, 2 + b           # ot_v41_bf_col3_c: H out-face + C in-face + RNE cut; DEQ = 2 + BRNECUT
    return b, 0


def seg_label_floor(f=None):
    f = f or form()
    return FLOOR_MEASURED.get(f, BASE_SEG_LABEL_FLOOR + deltas(f)[0])


if __name__ == '__main__':
    for f in ('base',) + tuple(k for k, v in RECIPES.items() if (ROOT / v[0]).exists()):
        print(f, 'bf_add/fp_add', deltas(f), 'seg_label_floor', seg_label_floor(f))
