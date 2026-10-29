#!/usr/bin/env python3
"""Conditional S2 exposure of d15's six +1 station chains; no new rate claim.

rr1 is a DMA-back response (one +1 return leg). The five NE Q7 outputs
are distinct pipelined bank->hub responses, NOT five serial nodes. status
is observability, not a production data leg. Without signal/call trace,
report conservative scenarios rather than pretending an exact op mapping.
"""
import argparse
import json
from pathlib import Path
import sys


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--model-root',required=True)
    ap.add_argument('--out',required=True)
    a=ap.parse_args()
    root=Path(a.model_root).resolve()
    sys.path.insert(0,str(root/'tools/throughput'))
    import accepted_cost as A
    cases=[('NW_rr1_all_DMA_upper_once','DMA.*',1),
           ('NE_each_VM_dependent_record_once','SM.*|ATT.*|DMA.*|SU.*|FUSED.*|SFU.*|IDX.*|COLL.*|HC.*|ARGMAX.*',1),
           ('pessimistic_six_serial_returns_each_record','*',6)]
    out=dict(schema='opentallas.hbm.six_chain_price.v1',
             status='CONDITIONAL: per-record exposure only; actual bound signal calendar still required',
             note='Six physical +1 chains, not six additive serial stages. No SOURCE timing adoption.',
             workloads={})
    for model in ('ds','qwen'):
        run,count=A.hbm_schedule(model)
        base=run()
        if model=='ds' and abs(base-576702.4)>0.1:
            raise SystemExit(f'wrong model input basis: DS {base}, expected576702.4')
        rows={name:A.hbm_loss(run,count,ops,None,base=base,delta=delta) for name,ops,delta in cases}
        out['workloads'][model]=dict(base_cycles=base,cases=rows)
    Path(a.out).write_text(json.dumps(out,indent=1)+'\n')
    print(json.dumps(out,indent=1))


if __name__=='__main__':main()
