#!/usr/bin/env python3
"""Check source reads against frozen ROM requests, rather than latest GO.

The pipelined issuer accepts the next phase before prior reads finish. Runtime
retire-mask and downstream consumer observation remain separate obligations.
"""
import argparse
import json
import re
from collections import Counter
from pathlib import Path


def words(path):
    physical = [int(v,16) for v in Path(path).read_text().split()]
    return [sum(((physical[a//8] >> (bit*8+a%8)) & 1) << bit for bit in range(72)) for a in range(4096)]


def check(run, model):
    contract = json.loads((model/'contract.json').read_text())
    stream = sum((words(model/f'pq_stream{bank}.viamap.hex') for bank in range(4)),[])
    # XR input -> output3; issuer TS300, GO_LAT3, OFF37, XS_LAG3.
    # Controller stream request -> stream head6 + registered R1/monitor2.
    ctl_origin = 1100+3+300+3+37+3
    read_origin = ctl_origin+8
    expected, expected_go, attributed = [], [], {}
    for phase in contract['compiler_calendar']['phases']:
        p = phase['phase']
        plan = next(x for x in contract['plans'] if x['epoch']==p)
        sbase = plan['phase']['sbase']
        data_reads = 0
        expected_go.append((ctl_origin+phase['abs_accept'],p))
        for i in range(phase['nb']):
            w=stream[sbase+i]
            if w & 1 and (w >> 12) & 3:
                u,b,gate=(w >> 1)&255,(w >> 9)&7,(w >> 12)&3
                expected.append((read_origin+phase['abs_stream'][0]+i,gate,16*u+b,16*u+b+8,0))
                data_reads+=1
        attributed[str(p)]=data_reads
    log=(run/'diagnostic.log').read_text()
    actual=[]
    for m in re.finditer(r'ACTUAL_QREAD t=(\d+) epoch=-?\d+ gates=([01]+) blocks=(\d+),(\d+) parity=([01]) source=(\d+),(\d+) valid=([01]+)',log):
        t,gate,a,b,parity,s0,s1,valid=m.groups()
        gate=int(gate,2)
        actual.append((int(t),gate,int(a),int(b),int(parity)))
        # Bench prints valid as q_v0 followed by q_v1, opposite binary
        # significance of gates[1:0]. Check each live half explicitly.
        if ((gate&1 and (int(s0) or valid[0]!='1')) or
                (gate&2 and (int(s1) or valid[1]!='1'))):
            actual.append(('INVALID_SOURCE',m.group(0)))
    observed_go=[tuple(map(int,m)) for m in re.findall(r'ACTUAL_GO t=(\d+) epoch=(\d+)',log)]
    data_failures = re.findall(r'^.*(?:RETAINED_QOUTPUT_MISMATCH|QNORM_SOURCE_MISMATCH|QNORM_SOURCE_AGE_MISMATCH|XS_MACRO_MISMATCH|QNORM_SOURCE_COUNTS|QNORM_SOURCE_MISSING_XS_JOIN).*$' ,log,re.M)
    ec,ac=Counter(expected),Counter(actual)
    result=dict(scope='Frozen source ROM/read schedule proof; retire masks and consumer deadlines OPEN',
                source_schedule_PASS=ec==ac and expected_go==observed_go,
                expected_reads=len(expected),actual_reads=len(actual),per_phase_reads=attributed,
                missing=list((ec-ac).elements()),extra=list((ac-ec).elements()),
                expected_go=expected_go,observed_go=observed_go,
                data_failures=data_failures,
                expected_pipeline_end_markers=1,observed_end_markers=log.count('ACTUAL_END '),
                full_stage_qualified=False)
    result['source_schedule_PASS'] &= result['observed_end_markers']==1
    result['source_schedule_PASS'] &= not data_failures
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('run',type=Path)
    parser.add_argument('model',type=Path)
    parser.add_argument('out',type=Path)
    args=parser.parse_args()
    result=check(args.run,args.model)
    args.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    raise SystemExit(0 if result['source_schedule_PASS'] else 1)
