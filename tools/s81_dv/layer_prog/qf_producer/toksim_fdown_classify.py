#!/usr/bin/env python3
"""TOKSIM-S81B/FDOWN 10-19: classify a fdown vehicle run (observational; reads diagnostic.log + rows.json).

Every FRAME_RETURN word (lane = frame, 70 b: valid 1, tag [34:3], data [66:35], e 67, fault 69) is decoded with the
return-tag ABI (static_return_calendar._f(norm(tag))): tag row = 8 epoch + r -> the placed row; its data / e must equal
the golden segment-tree node golden_node(vals, lo, k, n) of that row (frame_bench / lower_xs.check_words rule), every
row's segments [0, n) must be covered exactly once, and every row's golden accumulator rounds to the fixture BF16
(asserted at generation).  Timing: start = first ACTUAL_TAG_CAPTURE (operand capture at an element), retire = last
FRAME_RETURN word (frame root).  usage: toksim_fdown_classify.py RUN_DIR [ROOT]
"""
import collections, json, re, sys
from pathlib import Path
d = Path(sys.argv[1]); root = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).resolve().parents[4]
sys.path.insert(0, str(root / 'tools/s81')); sys.path.insert(0, str(root / 'tools/s81_dv'))
from static_return_calendar import _f, norm
from frame_bench import golden_node
s = (d / 'diagnostic.log').read_text()
rows = json.loads((d / 'rows.json').read_text())
lanes = ['u_f_3L01', 'u_f_3L02', 'u_f_3L03', 'u_f_3R01', 'u_f_3R02', 'u_f_3R03']
by = {(r['lane'], r['uid']): r for r in rows}
cov = collections.defaultdict(list); bad, unknown, words = [], [], []
ep_t = collections.defaultdict(list)
for t, l, w in re.findall(r'^FRAME_RETURN t=(-?\d+) lane=(\d+) word=([0-9a-f]+)', s, re.M):
    t, l, w = int(t), int(l), int(w, 16)
    tag, dat, e, ff = (w >> 3) & 0xFFFFFFFF, (w >> 35) & 0xFFFFFFFF, (w >> 67) & 1, (w >> 69) & 1
    row19, lo, k, n = _f(norm(tag)); uid = row19 & 0x3FFF
    r = by.get((l, uid))
    words.append(t)
    if r is None or (row19 >> 16):
        unknown.append(dict(t=t, lane=l, word=f'{w:018x}')); continue
    g, ge = golden_node(r['vals'], lo, k, n)
    if n != len(r['vals']) or dat != g or e != ge or ff:
        bad.append(dict(t=t, lane=l, uid=uid, lo=lo, k=k, n=n, got=f'{dat:08x}/{e}', want=f'{g:08x}/{ge}', fault=ff))
    cov[(l, uid)].extend(range(lo, min(lo + (1 << k), n)))
    ep_t[r['epoch']].append(t)
incomplete = [dict(lane=r['lane'], uid=r['uid'], segs=sorted(cov.get((r['lane'], r['uid']), [])))
              for r in rows if sorted(cov.get((r['lane'], r['uid']), [])) != list(range(len(r['vals'])))]
caps = [int(t) for t in re.findall(r'^ACTUAL_TAG_CAPTURE t=(-?\d+)', s, re.M)]
gos = [(int(t), int(e)) for t, e in re.findall(r'^ACTUAL_GO t=(-?\d+) epoch=(\d+)', s, re.M)]
src = re.findall(r'FULLSIX_SOURCE_CHECK errors=(\d+)', s)
ctlm = re.findall(r'^FDOWN_CONTROL .*$', s, re.M)
xsmm = len(re.findall(r'XS_MACRO_READ_MISMATCH|RETAINED_QOUTPUT_MISMATCH', s))
faults = re.findall(r'^FDOWN_FAULTS .*$', s, re.M)
rd = re.findall(r'EPOCH_READ_COUNTS epoch=(\d+) actual=(\d+) expected=(\d+)', s)
res = dict(rows=len(rows), returns=len(words), bad=len(bad), first_bad=bad[:5], unknown=len(unknown), first_unknown=unknown[:5],
           incomplete_rows=len(incomplete), first_incomplete=incomplete[:5], tb_errors=int(src[-1]) if src else None,
           control=ctlm[-1] if ctlm else None, xs_mismatch=xsmm, faults=faults, read_counts_bad=[x for x in rd if x[1] != x[2]],
           first_capture=min(caps) if caps else None, last_return=max(words) if words else None,
           first_go=gos[0][0] if gos else None,
           per_epoch={str(e): [min(v), max(v), len(v)] for e, v in sorted(ep_t.items())})
res['start_to_retire'] = (res['last_return'] - res['first_capture'] + 1) if caps and words else None
res['PASS'] = bool(words) and not bad and not unknown and not incomplete and res['tb_errors'] == 0 and not faults and not xsmm
(d / 'fdown_classification.json').write_text(json.dumps(res, indent=1) + '\n')
print('FDOWN_CLASSIFY', 'PASS' if res['PASS'] else 'FAIL', 'rows', len(rows), 'returns', len(words), 'bad', len(bad),
      'unknown', len(unknown), 'incomplete', len(incomplete), 'tb_err', res['tb_errors'], 'xs_mm', xsmm, 'faults', faults,
      'first_capture', res['first_capture'], 'last_return', res['last_return'], 'start_to_retire', res['start_to_retire'],
      'control', res['control'])
