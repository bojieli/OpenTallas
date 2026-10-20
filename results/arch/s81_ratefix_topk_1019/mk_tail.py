#!/usr/bin/env python3
"""S81-RATEFIX: topk_final drain-window sweep.  The compiled bk_sel job opens its drain window TAIL_BUDGET edges after
the last ingress beat (lower_bk.py: w0 = t_last + TAIL_BUDGET; the drain CTL and every egress beat are placed relative
to w0).  A job compiled with TAIL = 640 - d is the committed job with the drain CTL (stim, vi_n) and every expected vo_s
beat from the forwarded drain CTL on moved d edges earlier; the ingress is unchanged.  (lower_bk's own 'early' mutant
is d = 400 on the stimulus only.)  usage: mk_tail.py SRC_CASE_DIR OUT_DIR TAIL"""
import sys,json
from pathlib import Path
src,out,tail=Path(sys.argv[1]),Path(sys.argv[2]),int(sys.argv[3])
m=json.loads((src/'meta.json').read_text());old=m['window'][0]-m['t_last_in'];d=old-tail
assert old==640 and 0<=d<640,(old,tail)
dr=m['drain']['vi_n_edge']
st=[l.split() for l in (src/'stim.txt').read_text().split('\n') if l.strip()]
ex=[l.split() for l in (src/'exp.txt').read_text().split('\n') if l.strip()]
assert int(st[-1][0])==dr and int(st[-1][1],16)==0, 'last stim line = the drain CTL alone on vi_n'
assert all(int(e)<dr for e,_,_ in st[:-1]), 'ingress precedes the drain'
assert min(int(e) for e,_ in ex)==m['drain']['vo_edge'], 'expectation starts at the forwarded drain CTL'
out.mkdir(parents=True,exist_ok=True)
st[-1][0]=str(dr-d)
(out/'stim.txt').write_text(''.join(' '.join(x)+'\n' for x in st))
(out/'exp.txt').write_text(''.join(f'{int(e)-d} {v}\n' for e,v in ex))
m['window']=[w-d for w in m['window']];m['drain']['vi_n_edge']-=d;m['drain']['vo_edge']-=d
m['tail_budget']=tail;m['derived_from']=str(src)
(out/'meta.json').write_text(json.dumps(m,indent=1)+'\n')
print('MK_TAIL',out,tail,'shift',d)
