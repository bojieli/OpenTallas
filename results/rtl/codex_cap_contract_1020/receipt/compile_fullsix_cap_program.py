#!/usr/bin/env python3
"""Private fullsix CAP lowering from frozen source plans, not observed logs.

Retains explicitly calibrated frame offsets and selected L16/E24 landing costs.
Checks the complete CAP calendar before emitting any descriptors. Consumer
retirement/deadline lowering is outside this component's qualification.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument('root',type=Path)
p.add_argument('model',type=Path)
p.add_argument('out',type=Path)
a=p.parse_args()
sys.path[:0]=[str(a.root/'tools/s81_slice'),str(a.root/'tools/s81'),str(a.root/'tools/s81_dv/layer_prog/qf_producer')]
from cap_model import C_NODE,model
from head_local_contract import storage_offset
c=json.loads((a.model/'contract.json').read_text())
assert c['compiler_calendar']['mode']=='pipeline'
assert c['actual_phases']==15 and c['semantic_rows']==512 and c['actual_frames']==6
period=c['compiler_calendar']['period']
gc=c['global_calendar']
assert gc['shifts']==dict(L01=0,L02=0,L03=0,R01=16,R02=24,R03=24)
lanes=[{} for _ in range(8)]
first={}
for plan in c['plans']:
    phase=plan['epoch'];frame=plan['frame'][-3:];lane=gc['frame_order'].index(frame)
    for edge,tag,data,error in plan['return_model']:
        local=((tag>>13)&65535)&0x3fff
        dim=plan['rows'][local]-3072
        row=(((phase+1)&3)<<14)+6144+storage_offset(dim)
        tag=(tag&~(65535<<13))|(row<<13)
        at=edge+gc['measured_frame_offsets'][frame]+phase*period+6+gc['shifts'][frame]
        first[phase]=min(first.get(phase,at),at)
        assert at not in lanes[lane]
        lanes[lane][at]=(tag,data,error,[(phase,frame,local)])
commands={int(line.split()[0]):int(line.split()[1],16) for line in (a.model/'source_ctl.txt').read_text().splitlines()}
configs=[];records=[]
for phase in range(15):
    # Three unchanged return-tree levels, each C_NODE, after the lane pin.
    # Configure at the first model FIN edge: the previous phase must already
    # be closed and this phase's first complete row is still ahead of DEC.
    pin_edge=first[phase]+1+3*C_NODE
    ctl_edge=pin_edge-3  # unchanged XR command input -> cfg output
    assert ctl_edge not in commands,('XR_CTL_COLLISION',phase,ctl_edge)
    cfg=dict(obase=0,ops=0,np=0,fmt=2,rbase=(((phase+1)&3)<<14)+6144,rcnt=828,rsplit=0,lo32=0,hi32=0)
    body=(cfg['fmt']<<27)|(cfg['rbase']<<29)|(cfg['rcnt']<<45)
    commands[ctl_edge]=(body<<26)|(3<<16)|(1<<6)
    configs.append((pin_edge,cfg))
    records.append(dict(phase=phase,earliest_CAP_pin_word=first[phase],first_FIN_edge=pin_edge,xr_ctl_pin_edge=ctl_edge,body=f'{body:040x}',cfg=cfg))
prediction=model(lanes,configs)
assert not prediction['faults'],prediction['faults']
assert len(prediction['writes'])==512
a.out.write_text(''.join(f'{edge} {payload:047x}\n' for edge,payload in sorted(commands.items())))
receipt=dict(scope='PRIVATE source-derived fullsix CAP lowering; consumer retirement/deadline OPEN',
             full_stage_qualified=False,model_faults=prediction['faults'],predicted_CW_words=len(prediction['writes']),
             calibrated_frame_offsets=gc['measured_frame_offsets'],selected_CAP_delays=gc['shifts'],
             actual_row_flags_rule='cfg7 per-frame launch counter (phase+1) mod4; distinct from XS tag0/2',
             descriptors=records,model_contract_sha256=hashlib.sha256((a.model/'contract.json').read_bytes()).hexdigest())
Path(str(a.out)+'.cap.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
