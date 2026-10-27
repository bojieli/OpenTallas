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


XS4_PATH_EDGES = 1   # measured XS4 path edge over the calibrated model (s81_dense_source_1021 positive: 322 = 321 + 1)


def check(v, log, pin=None):
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
    if pin is not None and shift != pin:
        errors.append(f'return calendar shift {shift} != pinned {pin} (calibrated model + measured XS4 edge)')
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
                measured_first_return=ret[0][0] if ret else None,
                measured_first_capture=min((r[1] for r in cap),default=None),
                pinned_return_shift=pin, element_go_edges=len(re.findall(r'^ELEMENT_GO ', text, re.M)),
                immutable_program=prog, log_sha256=hashlib.sha256(log.read_bytes()).hexdigest())


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--vectors',type=Path,required=True)
    p.add_argument('--run',type=Path,required=True)
    p.add_argument('--gb',action='store_true',help='TOK-ALL-15 GB successor: pinned shift + old-Q and wrong-image controls')
    p.add_argument('--oldq-vectors',type=Path)
    p.add_argument('--wrongimg-vectors',type=Path)
    a=p.parse_args()
    if a.gb:
        return main_gb(a)
    positive=check(a.vectors,a.run/'run_mut0.log')
    mutant=check(a.vectors,a.run/'run_mut1.log')
    d=dict(positive=positive,mutant=mutant,
           causal_negative_detected=positive['status']=='PASS' and mutant['status']=='FAIL',
           full_stage=False,full_token=False)
    (a.run/'check.json').write_text(json.dumps(d,indent=2)+'\n')
    print(json.dumps(d))
    return 0 if d['causal_negative_detected'] else 1


def main_gb(a):
    prog=json.loads((a.vectors/'dense_program.json').read_text())
    assert prog['q_issue_advance_edges']==1 and prog['gb_provider_under_test'], 'GB positive needs the native Q advance1'
    pin=prog['calibrated_common_shift_model']+XS4_PATH_EDGES
    positive=check(a.vectors,a.run/'run_mut0.log',pin)
    runs=dict(input_corruption=check(a.vectors,a.run/'run_mut1.log',pin))
    if a.oldq_vectors:
        q=json.loads((a.oldq_vectors/'dense_program.json').read_text())
        assert q['q_issue_advance_edges']==0, 'old-Q control must use the legacy Q launch'
        # the old calendar is judged against the SAME pinned schedule as the positive
        runs['old_q_calendar']=check(a.oldq_vectors,a.run/'run_oldq.log',pin)
    if a.wrongimg_vectors:
        runs['wrong_loaded_image']=check(a.wrongimg_vectors,a.run/'run_wrongimg.log',pin)
    caught={k:r['status']=='FAIL' for k,r in runs.items()}
    d=dict(schema='opentallas.s81.dense_gb_composition_receipt.v1',positive=positive,controls=runs,controls_caught=caught,
           pass_and_all_controls_caught=positive['status']=='PASS' and all(caught.values()),
           uniform_clock_phase=True,native_provider_qualified=False,full_stage=False,full_token=False)
    (a.run/'check.json').write_text(json.dumps(d,indent=2)+'\n')
    print(json.dumps(dict(positive=positive['status'],errors=positive['errors'][:4],caught=caught,
                          shift=positive['measured_return_plan_shift'],pin=pin)))
    return 0 if d['pass_and_all_controls_caught'] else 1


if __name__=='__main__':
    raise SystemExit(main())
