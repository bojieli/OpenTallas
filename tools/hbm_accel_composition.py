"""HA0: the HBM accelerator's MEASURED composition (successor revisions, never overwritten).

Each rung row carries the modelled gain (from the frozen study ladder via
tools/uarch_model.py --hbm-accel), the measured gain, their difference and its cause, and the
area/route/timing status.  Only ADOPTED rungs (all six ordered gates passed) enter the composed
rate; every other rung is listed as excluded.  The composition base is the W19 ablation token
(442.14 us AR at 1M, itself a model composition of measured parts) and is labelled as such.

    python3 tools/hbm_accel_composition.py --rows ROWS.json [--note TEXT]

ROWS.json is a list of row dicts keyed by `rung`.  A new revision is appended to
results/rtl/hbm_accel_composition_20261004/measured_composition.json; earlier revisions are kept
byte-for-byte (the file is checked to be a prefix-extension).
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/rtl/hbm_accel_composition_20261004/measured_composition.json'
GATES = ['exact', 'latency', 'area', 'route', 'timing', 'gain']
GAIN_GATE_PCT = 1.0
REQUIRED = ['rung', 'workstream', 'modelled_gain_us', 'measured_gain_us', 'diff_cause',
            'gates', 'area', 'route', 'timing', 'verdict', 'evidence']


def modelled():
    sys.path.insert(0, str(ROOT / 'tools'))
    import uarch_model as u
    m = u.hbm_accel_rows()
    firm = m['hypotheses']['ds']['1M']['firm']
    cond = m['hypotheses']['ds']['1M']['with_R7a']
    lad = {r['rung']: r for r in firm['ladder'] + cond['ladder'][-1:]}
    base = next(r for r in firm['ladder'] if r['rung'].startswith('R1 ('))
    return m, lad, base


def compose(rows, lad, base):
    t_ar = base['ar_us']
    by = {}
    for r in rows:
        missing = [k for k in REQUIRED if k not in r]
        if missing:
            raise ValueError(f"{r.get('rung')}: missing {missing}")
        if list(r['gates']) != GATES:
            raise ValueError(f"{r['rung']}: gates must be ordered {GATES}")
        if r['rung'] in by:
            raise ValueError(f"duplicate rung {r['rung']}")
        by[r['rung']] = r
        price = lad.get(r['rung'])
        if price is not None and abs(price['saved_ar_us'] - r['modelled_gain_us']) > 0.01:
            raise ValueError(f"{r['rung']}: modelled gain {r['modelled_gain_us']} != ladder {price['saved_ar_us']}")
        mg = r['measured_gain_us']
        r['diff_us'] = None if mg is None else round(mg - r['modelled_gain_us'], 3)
        r['measured_gain_pct_of_rate'] = None if mg is None else round(100 * mg / (t_ar - mg), 3)
        all_pass = all(v == 'PASS' for v in r['gates'].values())
        r['adopted'] = bool(all_pass and mg is not None and r['measured_gain_pct_of_rate'] >= GAIN_GATE_PCT)
    adopted = [r for r in rows if r['adopted']]
    t = t_ar - sum(r['measured_gain_us'] for r in adopted)
    return dict(base=dict(row=base['rung'], ar_us=t_ar, ar_tok_s=base['ar_tok_s'],
                          label='W19 ablation token: model composition of measured parts, not an accelerator result'),
                adopted_rungs=[r['rung'] for r in adopted],
                excluded_rungs=[r['rung'] for r in rows if not r['adopted']],
                measured_composed_ar_us=round(t, 2) if adopted else None,
                measured_composed_ar_tok_s=round(1e6 / t, 1) if adopted else None,
                published_accelerator_rate=round(1e6 / t, 1) if adopted else None,
                modelled_hypothesis_ar_tok_s=lad['R6a']['ar_tok_s'],
                rule='only rungs with all six ordered gates PASS and measured gain >= 1% compose; '
                     'model numbers (3,015 AR / 6,001 MTP) are hypotheses and never published')


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--rows', required=True)
    ap.add_argument('--note', default='')
    ap.add_argument('--out', default=str(OUT))
    a = ap.parse_args(argv)
    m, lad, base = modelled()
    rows = json.loads(Path(a.rows).read_text())
    composed = compose(rows, lad, base)
    out = Path(a.out)
    rec = json.loads(out.read_text()) if out.exists() else dict(
        schema='opentallas.hbm_accel.measured_composition.v1', owner='HA0 (Claude)',
        model_record='results/uarch/hbm_accelerator_integration_20261004/model.json',
        gate_order=GATES, gain_gate_pct=GAIN_GATE_PCT, revisions=[])
    prev = [json.dumps(r, sort_keys=True) for r in rec['revisions']]
    rev = dict(revision=len(rec['revisions']) + 1,
               utc=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
               note=a.note, rows_input_sha256=hashlib.sha256(Path(a.rows).read_bytes()).hexdigest(),
               rows=rows, composed=composed)
    rec['revisions'].append(rev)
    if [json.dumps(r, sort_keys=True) for r in rec['revisions'][:-1]] != prev:
        raise ValueError('earlier revisions changed')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, indent=2) + '\n')
    print(json.dumps(composed, indent=2))


if __name__ == '__main__':
    main()
