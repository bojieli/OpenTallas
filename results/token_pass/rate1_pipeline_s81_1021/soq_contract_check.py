#!/usr/bin/env python3
"""TOK.DS.RATE.RTAG on the pipeline schedule (STEWARD-TOKb-RATE1 10-21): the RTAG/SOQ compiler contract is
"last partial of BF phase k < go_{k+1} + SWD (160)".  Inside one position the phase sequence is the compiler's
xs_field_calendar (P130, unchanged by the pipeline law).  The pipeline law only adds position boundaries: a stage runs
position p+1's items after position p's last item ends.  So the contract holds across positions iff every stage's
position windows are ordered and disjoint (go of p+1's first phase >= end of p >= p's last partial)."""
import json, sys
c = json.load(open(sys.argv[1] if len(sys.argv) > 1 else
                   'results/token_pass/calendar_pipeline_s81_1021/calendar_rel241_G4_mtp.json'))
g = c['pipeline_graph']; gaps = []
for s in g['stages']:
    w = s['position_windows']
    gaps += [(b[0] - a[1], s['stage']) for a, b in zip(w, w[1:])]
bad = [x for x in gaps if x[0] < -160]
print(json.dumps(dict(stages=len(g['stages']), boundaries=len(gaps), min_gap=min(gaps)[0], min_gap_stage=min(gaps)[1],
                      violations=len(bad), swd=160, result='PASS' if not bad else 'FAIL')))
sys.exit(1 if bad else 0)
