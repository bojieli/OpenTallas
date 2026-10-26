#!/usr/bin/env python3
"""Sub-tap latency PADDING sizer for the multi-root shallow clock (PATH-QC-N59-PAD 2026-10-25).

After the closed-loop trunk + ONE global CTS every density sub-tap has a measured natural port-referred mean sink
insertion below its budget (P4: reg 167..222 vs 250 TT).  Padding is ONE structural mechanism: a series chain of
identical delay buffers on each sub-tap's root branch (between the trunk leaf net and the sub-tap buffer input),
sized from the measured natural latency.  No per-flop hold buffers, no trunk change, no sink movement.

Sizing (per tap, integer stages n >= 0):
  stage_ps = (mean_now - natural) / n_now   when n_now > 0 and that is positive  (measured, per tap)
           = default stage estimate          otherwise
  n_new    = clamp(round((target - natural) / stage_ps), 0, max_stages)
A tap is converged when |mean_now - target| <= tol.  A tap above target gets n = 0 (padding never removes delay:
an over-target tap is a trunk/geometry problem and is reported, not hidden).

TSV in : tap kind target_ps natural_ps mean_ps n_now
TSV out: tap n_new stage_ps err_ps  ; summary line on stdout as JSON.
"""
import argparse
import json
import math


def size(rows, default_stage=15.0, tol=6.0, max_stages=16):
    out, changed, over = [], 0, 0
    for r in rows:
        tgt, nat, mean, n = float(r['target_ps']), float(r['natural_ps']), float(r['mean_ps']), int(r['n_now'])
        if not all(math.isfinite(v) for v in (tgt, nat, mean)):
            raise ValueError(f"non-finite measurement for {r['tap']}")
        stage = default_stage
        if n > 0 and mean - nat > 0:
            stage = (mean - nat) / n
        err = mean - tgt
        if abs(err) <= tol:
            nn = n
        else:
            nn = int(round((tgt - nat) / stage)) if tgt > nat else 0
            nn = max(0, min(max_stages, nn))
        if nat > tgt + tol:
            over += 1
        changed += nn != n
        out.append(dict(tap=r['tap'], n_new=nn, stage_ps=round(stage, 2), err_ps=round(err, 2)))
    return out, dict(taps=len(rows), changed=changed, natural_over_target=over,
                     max_abs_err=round(max((abs(o['err_ps']) for o in out), default=0.0), 2),
                     stages=sum(o['n_new'] for o in out))


def read_tsv(path):
    with open(path) as f:
        lines = [l.rstrip('\n').split('\t') for l in f if l.strip()]
    head = lines[0]
    need = ['tap', 'kind', 'target_ps', 'natural_ps', 'mean_ps', 'n_now']
    if head != need:
        raise ValueError(f'bad header {head}')
    return [dict(zip(head, l)) for l in lines[1:]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('meas'); ap.add_argument('--out', required=True)
    ap.add_argument('--default-stage-ps', type=float, default=15.0)
    ap.add_argument('--tol-ps', type=float, default=6.0)
    ap.add_argument('--max-stages', type=int, default=16)
    a = ap.parse_args()
    out, summ = size(read_tsv(a.meas), a.default_stage_ps, a.tol_ps, a.max_stages)
    with open(a.out, 'w') as f:
        f.write('tap\tn_new\tstage_ps\terr_ps\n')
        for o in out:
            f.write(f"{o['tap']}\t{o['n_new']}\t{o['stage_ps']}\t{o['err_ps']}\n")
    print(json.dumps(summ))


if __name__ == '__main__':
    main()
