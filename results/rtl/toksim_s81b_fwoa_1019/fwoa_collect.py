#!/usr/bin/env python3
"""TOKSIM-S81B/FWOA: collect per-phase start->retire from the frame bench (fb) and xs-slice bench (xb) runs of
run_frame_ops.sh.  start = the first valid x word at the frame input (GO_EDGE 67 = spine go 63 + 4, XSL_LOCKSTEP first_ref),
retire = the last frame-root return word (RET edge).  usage: fwoa_collect.py OUTDIR... > summary.json"""
import json, re, sys
from pathlib import Path

GO_EDGE = 67   # first valid x word at the frame input (XSL_LOCKSTEP first_ref; spine go is edge 63)
res = {}
for od in map(Path, sys.argv[1:]):
    fr = json.loads((od / 'frame/frame.json').read_text())
    tag = od.name
    ph = []
    for p in fr['phases']:
        k = p['phase']
        if p['op'] not in ('attn.wo_a', 'attn.wo_b') or p['rows'] == 0:
            continue
        r = dict(phase=k, op=p['op'], rows=p['rows'])
        for b in ('fb', 'xb'):
            log = od / b / f'run_p{k}.log'
            chk = od / b / f'check_p{k}.out'
            if not log.exists():
                r[b] = None
                continue
            t = log.read_text()
            rets = [int(m.group(1)) for m in re.finditer(r'^RET (\d+) ', t, re.M)]
            c = chk.read_text().strip().splitlines() if chk.exists() else []
            last = c[-1] if c else ''
            r[b] = dict(words=len(rets), first_ret=min(rets) if rets else None, last_ret=max(rets) if rets else None,
                        pass_=(' PASS ' in last) or last.startswith(('XS_PLACE_CHECK PASS', 'XSL_CHECK PASS', 'XS_CAL_CHECK PASS'))
                        or ('PASS' in last and 'FAIL' not in last),
                        check=last[:300], end=(re.findall(r'^END .*$', t, re.M) or [''])[0])
            if b == 'fb' and rets:
                r['start_retire'] = max(rets) - GO_EDGE
        ph.append(r)
    res[tag] = dict(frame=fr.get('frame'), master=fr['master'], lk=fr['lk'], phases=ph)
    for op in ('attn.wo_b', 'attn.wo_a'):
        pp = [x for x in ph if x['op'] == op]
        if pp:
            res[tag][op] = dict(nphases=len(pp), rows=sum(x['rows'] for x in pp),
                                serial_sum=sum(x.get('start_retire') or 0 for x in pp),
                                per_phase=[x.get('start_retire') for x in pp],
                                all_fb_pass=all(x['fb'] and x['fb']['pass_'] for x in pp),
                                all_xb_pass=all(x['xb'] and x['xb']['pass_'] for x in pp))
print(json.dumps(res, indent=1))
