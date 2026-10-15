#!/usr/bin/env python3
"""Measure every signal contract bit of the current HOST-north KV die.

These are source-assigned physical rectangles, including placeholders.  This
cannot establish native timing or real-view closure.  Missing bus mappings are
reported as unmeasured and must never silently count as qualified.
"""
from collections import Counter
import argparse
import hashlib
import json
from pathlib import Path
import kv_die as K

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args()
    model=K.build(kv_wq_mirror=True,split=True,host_v14=True,host_north=True)
    masters=K.masters(model,1)
    report=K.assigned_pin_reach(model,masters,classes=None)
    baseline=json.loads((K.ROOT/'results/arch/qwen_split_1014/kvsys_v1_4_2/plan.json').read_text())
    old=baseline['relay_stages'];new=model['relay_stages']
    report['relay_stage_changes_from_pre_fault_contract']={b:dict(before=old.get(b,0),after=new.get(b,0))
        for b in sorted(set(old)|set(new)) if old.get(b,0)!=new.get(b,0)}
    report['fault_stage_counts_by_pc']={b:n for b,n in new.items() if b.startswith('wcf_')}
    report['actual_master_counts']=dict(Counter(i.master for i in model['insts']))
    report['die_geometry']=K.check(model)
    report['instances']=len(model['insts'])
    report['fault_calendar']='Actual inserted stage count perPC; fault observation delay only. End/drain fences require these actual counts before adoption.'
    report.update(schema='opentallas.qwen.kv.all-signal-pin-contract-reach.v1',
        generator_sha256=hashlib.sha256(Path(K.__file__).read_bytes()).hexdigest(),
        source_views='Generated assigned pin contracts; native real-view and timing qualification remain separate.',
        status='PASS_PIN_CONTRACT' if not report['violations'] and not report['unmeasured'] else 'OPEN_PIN_CONTRACT')
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(report,indent=1)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('worst','missing')}))
