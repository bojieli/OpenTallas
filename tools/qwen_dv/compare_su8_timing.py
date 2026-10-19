#!/usr/bin/env python3
"""Compare frozen baseline/landed g event traces after explicit boot offsets."""
import argparse
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path


def events(path,warm):
    return [(int(t)-warm,int(p),v) for t,p,v in (l.split() for l in path.read_text().splitlines()) if int(p)!=0]


def words(path,warm):
    result=defaultdict(list)
    for line in path.read_text().splitlines():
        t,p,v=line.split();result[p].append((int(t)-warm,v))
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('trace_dir');p.add_argument('--out',required=True);a=p.parse_args()
    d=Path(a.trace_dir)
    assert events(d/'base_g.ev',8)==events(d/'land_g.ev',10),'normalized input events differ'
    base,land=words(d/'base_g.log',8),words(d/'land_g.log',10)
    assert set(base)==set(land)
    rows={}
    for port,values in base.items():
        actual=land[port]
        assert [v for t,v in values]==[v for t,v in actual],f'{port}: word count/value/order changed'
        delta=Counter(b[0]-a[0] for a,b in zip(values,actual))
        expected=6 if port in ('S0DD','S1SD') else 0
        assert delta=={expected:len(values)},f'{port}: nonuniform/unexpected age {delta}'
        rows[port]=dict(words=len(values),delta_edges=expected,all_values_and_order_exact=True)
    assert rows['S0DD']['words']>=16 and rows['S1SD']['words']>=1
    result=dict(schema='opentallas.qwen.su8_landed_timing.v1',status='SOURCE_EXACT_W_FUNCTIONAL_TIMING_PASS_NOT_NATIVE_GATE',
                baseline_core='9b41881fe',landed_candidate='c4adbc1c3',
                fixture='dv_bench2 g SU_LT1 HD_W1301 MU_NU4 FACE1 SAFE_STORAGE SAFE_RESET',
                boot_offsets=dict(baseline=8,landed=10),input_events_normalized_exact=True,
                ports=rows,source_read_loop_edges=dict(old=8,new=12,head_inner_ML_old=7,head_inner_ML_new=11),
                edge_budget=dict(issue_control=1,read_roundtrip=4,result_return=1,total=6),
                native_clock_phase_reach_and_final_banked_source_qualified=False,
                traces_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(d.iterdir()) if p.suffix in ('.log','.ev')})
    Path(a.out).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(rows,sort_keys=True))


if __name__=='__main__':main()
