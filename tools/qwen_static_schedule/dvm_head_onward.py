"""DVM head-row ONWARD_REG=2 schedule contract for the static compiler / b2 phase calibration (Q-B2r 2026-10-16).

Source of truth: Q-LINK-D2D's receipt results/rtl/qwen_link_recovery_0253/head_onward2_receipt.json (schema
opentallas.qwen.dvm.head_onward2_receipt.v1; branch codex/qwen-link-recovery-0253 ce5590b4e; RTL 7e4bb8103).
Fail-closed: a missing / foreign / internally inconsistent receipt is an error, never a silent zero.

Model (HEAD_CHAIN 1): two roots (W, E), 24 heads a side chained; every column's corridor outputs are equalised to the
farthest head, so each column's arrival + equalise is the SAME constant (2 x 23 = 46 edges at ONWARD 2, 23 at ONWARD 1).
Consequence for the compiler: every ME op's x/go broadcast and fill reach all tile columns `extra_edges_per_ME_op` (+23)
edges later than at ONWARD 1, uniformly.  For the b2 path calibration this is a common-mode shift of every tile word
relative to the ME command.  The actual-age b2 temporal gate must apply `word_shift` as a tile-word delay on top of the
allocator ages; which calibrated constants (issuer TE, controller tag ages) move is decided by that gate, never by
re-using an ONWARD 1 calibration.
"""
import json
from pathlib import Path

from .calendar import ScheduleError

ROOT = Path(__file__).resolve().parents[2]
RECEIPT = 'results/rtl/qwen_link_recovery_0253/head_onward2_receipt.json'
SCHEMA = 'opentallas.qwen.dvm.head_onward2_receipt.v1'
NCOL = 48


def load(root=ROOT, onward=2):
    """per-column arrival/equalise edges and the uniform per-op shift of the chosen ONWARD_REG"""
    if onward not in (1, 2):
        raise ScheduleError('DVM head ONWARD_REG must be 1 or 2')
    f = Path(root) / RECEIPT
    if not f.is_file():
        raise ScheduleError(f'DVM head-row receipt missing: {RECEIPT} (codex/qwen-link-recovery-0253)')
    d = json.loads(f.read_text())
    if d.get('schema') != SCHEMA:
        raise ScheduleError(f'{RECEIPT}: unknown schema')
    s = d.get('schedule') or {}
    cols = s.get('per_column') or []
    if len(cols) != NCOL or sorted(c.get('column') for c in cols) != list(range(NCOL)):
        raise ScheduleError(f'{RECEIPT}: per_column must list all {NCOL} columns once')
    row = s.get(f'head_row_edges_onward{onward}')
    if type(row) is not int:
        raise ScheduleError(f'{RECEIPT}: head_row_edges_onward{onward} missing')
    k = f'onward{onward}'
    out = {}
    for c in cols:
        a, e, hops = c.get(f'arrival_edges_{k}'), c.get(f'equalise_edges_{k}'), c.get('hops_from_root')
        if not all(type(x) is int and x >= 0 for x in (a, e, hops)) or c.get('side') not in ('W', 'E'):
            raise ScheduleError(f'{RECEIPT}: column {c.get("column")} incomplete')
        if a != onward * hops or a + e != row:
            raise ScheduleError(f'{RECEIPT}: column {c["column"]} arrival {a} + equalise {e} != head row {row} '
                                f'(or arrival != {onward} x hops)')
        out[c['column']] = dict(side=c['side'], hops=hops, arrival=a, equalise=e)
    extra = s.get('extra_edges_per_ME_op')
    if onward == 2 and extra != s['head_row_edges_onward2'] - s['head_row_edges_onward1']:
        raise ScheduleError(f'{RECEIPT}: extra_edges_per_ME_op inconsistent with the head-row edges')
    return dict(onward=onward, head_row_edges=row, columns=out,
                word_shift=(extra if onward == 2 else 0), basis=RECEIPT)


def column_offset(contract, column):
    """edges from the head-row root to the equalised corridor output of a tile column (same for every column)"""
    c = contract['columns'].get(column)
    if c is None:
        raise ScheduleError(f'no DVM head column {column}')
    return c['arrival'] + c['equalise']

