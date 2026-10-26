#!/usr/bin/env python3
"""Check actual component outputs against checkpoint rows; record measured ages.

The single common return-plan shift is a measured component launch offset.
It does not qualify inherited absolute frame/model ages or a whole stage.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re


def check(v, log):
    m = json.loads((v/'meta.json').read_text())
    prog = json.loads((v/'dense_program.json').read_text())
    text = log.read_text()
    errors = []
    ret = []
    for e, w in re.findall(r'^RET (\d+) ([0-9a-f]+)$', text, re.M):
        w = int(w,16)
        ret.append([int(e), (w>>1)&0xffffffff, (w>>33)&0xffffffff, (w>>65)&1])
        if not w&1:
            errors.append('return word missing valid')
    want = m['plan']['ret']
    shift = ret[0][0]-want[0][0] if ret and want else None
    if len(ret) != len(want):
        errors.append(f'return count {len(ret)} != {len(want)}')
    if shift is not None:
        for n, (r, w) in enumerate(zip(ret, want)):
            if r != [w[0]+shift]+w[1:]:
                errors.append(f'return {n} differs: actual {r}, expected common shift {shift} + {w}')
    cap = [(f,int(e),int(p),int(a),int(d,16)) for f,e,p,a,d in
           re.findall(r'^CAP ([SN]) (\d+) (\d+) (\d+) ([0-9a-f]+)$',text,re.M)]
    cfg = int((v/'capture.hex').read_text(),16)
    rbase = (cfg>>29)&65535
    obase = cfg&4095
    expected = []
    for row, val in m['rows'].items():
        # Actual CAP native scalar placement: 64 scalars/column; five leaves.
        relative = ((1<<14)+int(row))-rbase
        column, elem = divmod(relative,64)
        leaf, block = column%5,column//5
        addr = obase+64*block+elem
        face = 'S' if leaf<3 else 'N'
        port = 2*(leaf if face=='S' else leaf-3)+((addr>>2)&1)
        expected.append((face,port,addr,int(val['bf16'])<<16))
    actual = [(f,p,a,d) for f,e,p,a,d in cap]
    if sorted(actual) != sorted(expected):
        errors.append(f'CAP words {actual} != checkpoint {expected}')
    end = re.search(r'^DENSE_SOURCE_END cycles=(\d+) events=(\d+) consumed=(\d+) xs_fault=(\d) frame_fault=(\d) cap_fault=(\d) mutant=(\d)',text,re.M)
    if not end:
        errors.append('missing terminal marker')
    elif end[2]!=end[3] or any(int(end[i]) for i in (4,5,6)):
        errors.append('unconsumed input or actual component fault: '+end[0])
    ctrl = [(int(e),int(c),int(g)) for e,c,g in re.findall(r'^XCTRL (\d+) cfg=(\d) go=(\d)',text,re.M)]
    return dict(schema='opentallas.s81.dense_source_component_receipt.v1',
                status='PASS' if not errors else 'FAIL', full_stage=False, full_token=False,
                qualification='actual XS4 -> single selected landed frame -> capc5r; gather input is fixture oracle',
                errors=errors, return_words=len(ret), capture_words=len(cap),
                measured_return_plan_shift=shift, measured_control_edges=ctrl,
                measured_last_return=ret[-1][0] if ret else None,
                measured_last_capture=max((r[1] for r in cap),default=None),
                immutable_program=prog, log_sha256=hashlib.sha256(log.read_bytes()).hexdigest())


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--vectors',type=Path,required=True)
    p.add_argument('--run',type=Path,required=True)
    a=p.parse_args()
    positive=check(a.vectors,a.run/'run_mut0.log')
    mutant=check(a.vectors,a.run/'run_mut1.log')
    d=dict(positive=positive,mutant=mutant,
           causal_negative_detected=positive['status']=='PASS' and mutant['status']=='FAIL',
           full_stage=False,full_token=False)
    (a.run/'check.json').write_text(json.dumps(d,indent=2)+'\n')
    print(json.dumps(d))
    return 0 if d['causal_negative_detected'] else 1


if __name__=='__main__':
    raise SystemExit(main())
