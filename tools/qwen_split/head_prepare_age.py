#!/usr/bin/env python3
"""Export actual recurring head-prepare transport from a source-complete GEN.
No estimated/missing lane age is substituted. Run with OT_QWEN_HEAD_PREP=1.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
os.environ['OT_QWEN_HEAD_PREP']='1'
sys.path.insert(0,str(Path(__file__).resolve().parent))
import record_bundles as RB

def measure(case):
    case=Path(case)
    die=case/'die.v'
    lanes=case/'fwd_lanes.json'
    text=die.read_text()
    required=('qfd_native59_dv_headprep','qfd_sys_face_ovl','qfd_d2d_static_ovl_sf7')
    missing=[m for m in required if m not in text]
    if missing: raise ValueError('selected GEN lacks actual head-prepare masters: '+str(missing))
    if not lanes.is_file(): raise ValueError('actual GEN fwd_lanes.json required; K-only reconstruction prohibited')
    audit=RB.audit_netlist(die,lanes)
    if audit['verdict']!='PASS': raise ValueError('record bundle audit fails: '+str(audit['fails']))
    ages={}
    for name,n in [('TT.head_prepare',4),('SF.head_descriptor',3)]:
        row=audit['bundles'].get(name)
        if row is None or len(row['members'])!=n or not row['consistent'] or len(row['cycles'])!=1:
            raise ValueError('incomplete or unequal actual bundle '+name)
        ages[name]=int(row['cycles'][0])
    total=1+ages['TT.head_prepare']+3+ages['SF.head_descriptor']+1
    return dict(schema='opentallas.qwen.head_prepare_age.v1',
      source='actual CTLM c_emb stored token/position/user; source epoch from per-user prepare or matching HOST',
      die_sha256=hashlib.sha256(die.read_bytes()).hexdigest(),
      lanes_sha256=hashlib.sha256(lanes.read_bytes()).hexdigest(),
      source_intrinsic_edges=dict(ct_lm_sample=1,native_prepare_descriptor=3,face_held_bank=1),
      actual_transport_edges=ages,head_prepare_edges=total,
      host_user0_contract='HOST O61 token/position/epoch must match actual prepare before publication; compiler must price actual HOST availability',
      scope='GEN-derived fixed schedule age; physical timing and final sole calendar qualification remain separate',
      bundles={k:audit['bundles'][k] for k in ages})

def main():
    p=argparse.ArgumentParser();p.add_argument('case');p.add_argument('--out',required=True);a=p.parse_args()
    try: result=measure(a.case)
    except (ValueError,OSError,KeyError) as e:
        result=dict(verdict='FAIL',reason=str(e));Path(a.out).write_text(json.dumps(result,indent=2)+'\n');print(result['reason']);return 1
    result['verdict']='PASS';Path(a.out).write_text(json.dumps(result,indent=2)+'\n');print('HEAD_PREPARE_EDGES='+str(result['head_prepare_edges']));return 0
if __name__=='__main__':sys.exit(main())
