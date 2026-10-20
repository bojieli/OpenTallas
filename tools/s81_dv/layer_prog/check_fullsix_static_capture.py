#!/usr/bin/env python3
"""Compare frozen compiler return plans through the unchanged CAP cycle model.

This checks existing calibrated frame offsets explicitly. It does not claim a
new independently measured path or consumer retirement qualification.
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument('root',type=Path)
p.add_argument('model',type=Path)
p.add_argument('run',type=Path)
p.add_argument('out',type=Path)
a=p.parse_args()
sys.path[:0]=[str(a.root/'tools/s81_slice'),str(a.root/'tools/s81'),str(a.root/'tools/s81_dv/layer_prog/qf_producer')]
from cap_model import model
from head_local_contract import storage_offset
c=json.loads((a.model/'contract.json').read_text())
period=c['compiler_calendar']['period']
order=c['global_calendar']['frame_order']
offsets=c['global_calendar']['measured_frame_offsets']
shifts=c['global_calendar']['shifts']
lanes=[{} for _ in range(8)]
expected_frame=[]
for plan in c['plans']:
    phase=plan['epoch']
    frame=plan['frame'][-3:]
    lane=order.index(frame)
    for edge,tag,data,error in plan['return_model']:
        local=((tag >> 13)&65535)&0x3fff
        assert local<len(plan['rows']),(phase,frame,local)
        dim=plan['rows'][local]-3072
        row=(((phase+1)&3)<<14)+6144+storage_offset(dim)
        tag=(tag&~(65535<<13))|(row<<13)
        t=edge+offsets[frame]+phase*period
        expected_frame.append((t,lane,tag,data,error))
        # Exact original fullsix dr6 plus the selected CAP ED24/LD16.
        cap_t=t+6+shifts[frame]
        assert cap_t not in lanes[lane]
        lanes[lane][cap_t]=(tag,data,error,[(phase,frame,local)])
log=(a.run/'diagnostic.log').read_text()
actual_frame=[]
for t,lane,word in re.findall(r'^FRAME_RETURN t=(\d+) lane=(\d+) word=([0-9a-f]+)',log,re.M):
    word=int(word,16)
    actual_frame.append((int(t),int(lane),(word >> 3)&0xffffffff,(word >> 35)&0xffffffff,(word >> 67)&1))
expected_cfg=[]
for line in (a.run/'source_ctl.txt').read_text().splitlines():
    edge,payload=line.split()
    payload=int(payload,16)
    if ((payload >> 16)&31)==3:
        expected_cfg.append((int(edge)+3,payload >> 26))
actual_cfg=[(int(t),int(body,16)) for t,body in re.findall(r'^ACTUAL_CAP_CFG t=(\d+) body=([0-9a-f]+)',log,re.M)]
configs=[]
for t,body in expected_cfg:
        configs.append((t,dict(obase=body&4095,ops=(body>>12)&4095,np=(body>>24)&7,fmt=(body>>27)&3,rbase=(body>>29)&65535,rcnt=(body>>45)&2047,rsplit=(body>>56)&65535,lo32=(body>>72)&1,hi32=(body>>73)&1)))
pred=model(lanes,configs)
# cap_model and tb_s81sl_cap compare post-edge registered values at the
# following negedge. Fullsix ACTUAL_CW prints at posedge before NBA updates,
# so the same registered value is printed one edge later. No data latency
# or protocol edge is added by this observation convention.
expected_cw=Counter((t+1,leaf,address,data) for t,leaf,port,address,data,*_ in pred['writes'])
actual_cw=Counter()
for t,valid,addresses,values in re.findall(r'^ACTUAL_CW t=(\d+) valid=([0-9a-f]+) addr=([0-9a-f]+) data=([0-9a-f]+)',log,re.M):
    valid,addresses,values=map(lambda x:int(x,16),(valid,addresses,values))
    for port in range(10):
        if valid >> port & 1:actual_cw[int(t),port//2,(addresses >> (12*port))&4095,(values >> (32*port))&0xffffffff]+=1
ef,af=Counter(expected_frame),Counter(actual_frame)
result=dict(scope='Frozen compiler return plan + calibrated frame offsets + unchanged CAP model; consumer OPEN',
            source_plan_frame_PASS=ef==af,source_plan_frame_words=len(expected_frame),
            cfg_program_PIN_PASS=expected_cfg==actual_cfg,cfg_words=len(expected_cfg),
            model_capture_PASS=not pred['faults'] and expected_cw==actual_cw,model_faults=pred['faults'],
            expected_cw_words=sum(expected_cw.values()),actual_cw_words=sum(actual_cw.values()),
            frame_missing=list((ef-af).elements())[:12],frame_extra=list((af-ef).elements())[:12],
            cw_missing=list((expected_cw-actual_cw).elements())[:12],cw_extra=list((actual_cw-expected_cw).elements())[:12],
            full_stage_qualified=False)
a.out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
raise SystemExit(0 if result['source_plan_frame_PASS'] and result['cfg_program_PIN_PASS'] and result['model_capture_PASS'] else 1)
