#!/usr/bin/env python3
"""Export actual recurring head-prepare transport from a source-complete GEN.
No estimated/missing lane age is substituted. Run with OT_QWEN_HEAD_PREP=1.
"""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import sys
os.environ['OT_QWEN_HEAD_PREP']='1'
sys.path.insert(0,str(Path(__file__).resolve().parent))
import record_bundles as RB

def face_boundaries(root, case, master):
    if master != 'qfd_sys_face_lctx3_wrapped':
        return None
    from qwen_split.sysface_lctx_source import wrapper_contract
    contract=wrapper_contract(root)
    params=Path(case)/'die.v.params.json'
    actual=json.loads(params.read_text())['masters'][master]
    expected=dict(L_CONTEXTS=1,MU=1,MU_HEAD=1,ROPE=1,MUT=0,GO_OFS=3,START_ADJ=0)
    if any(actual.get(k)!=v for k,v in expected.items()):
        raise ValueError('actual wrapped sysface GEN parameters differ from qualified boundary profile')
    contract['params_sha256']=hashlib.sha256(params.read_bytes()).hexdigest()
    return contract

def measure(case, tt_source_receipt=None):
    case=Path(case)
    die=case/'die.v'
    lanes=case/'fwd_lanes.json'
    text=die.read_text()
    tt_names=set(re.findall(r'\b(qfd_tt_ctlm\w*)\s+tt_ctlm\s*\(',text))
    if len(tt_names)!=1:
        raise ValueError('actual selected TT master required: '+str(sorted(tt_names)))
    tt_master=next(iter(tt_names))
    tt_local=1
    tt_source=dict(master=tt_master,calendar_sample_edges=1,output_offset_edges=0,
                   scope='raw qfd_tt_ctlm_dv source: existing c_emb bank capture at output')
    if tt_master!='qfd_tt_ctlm_dv':
        if tt_source_receipt is None:
            raise ValueError('selected LP/native TT requires its source-bound embedding output-offset receipt; raw-TT edge 1 is not inherited')
        receipt=Path(tt_source_receipt)
        row=json.loads(receipt.read_text())
        if row.get('schema') == 'opentallas.qwen.tt_source_local.v1':
            from tt_source_local import source_local_edges
            tt_local, tt_source = source_local_edges((case.parents[1]/'src').resolve(), tt_master, receipt)
        else:
            if row.get('schema')!='opentallas.qwen.tt_emb_source.v1' or row.get('status')!='QUALIFIED_SOURCE_LOCAL_EDGES' or row.get('master')!=tt_master or row.get('calendar_sample_edges')!=1:
                raise ValueError('TT embedding source receipt identity/sample edge mismatch')
            root=(case.parents[1]/'src').resolve()
            def bound_file(field, sha_field):
                path=(root/row[field]).resolve()
                if not path.is_relative_to(root) or hashlib.sha256(path.read_bytes()).hexdigest()!=row[sha_field]:
                    raise ValueError('TT embedding source receipt hash/path mismatch: '+field)
                return path
            rtl=bound_file('rtl','rtl_sha256')
            if not re.search(r'\bmodule\s+'+re.escape(tt_master)+r'\b',rtl.read_text()):
                raise ValueError('TT embedding RTL does not define selected master')
            lp=bound_file('lp_record','lp_record_sha256')
            record=json.loads(lp.read_text())
            offsets=record['compiler']['output_port_offset_edges']
            values=[offsets[p] for p in ('emb_start','emb_token','emb_position','emb_user')]
            producer=row['producer_instance']
            producer_offset=record['compiler']['child_offset_edges'][producer]
            if type(producer_offset)!=int or producer_offset<0 or producer!='u_gi':
                raise ValueError('TT embedding actual calendar producer offset missing/invalid')
            if record['audit']['ok'] is not True or any(type(n)!=int or n<0 for n in values) or len(set(values))!=1 or values[0]<producer_offset:
                raise ValueError('TT embedding LP output offsets are missing/unequal/unqualified')
            source_to_output=values[0]-producer_offset
            tt_local=1+source_to_output
            tt_source=dict(status=row['status'],master=tt_master,calendar_sample_edges=1,output_offset_edges=values[0],
                           producer_instance=producer,producer_offset_edges=producer_offset,
                           source_to_output_edges=source_to_output,
                           receipt_sha256=hashlib.sha256(receipt.read_bytes()).hexdigest(),
                           rtl_sha256=row['rtl_sha256'],lp_record_sha256=row['lp_record_sha256'])
    root=(case.parents[1]/'src').resolve()
    selected=[]
    for base in ('qfd_native59_dv_headprep','qfd_sys_face_ovl','qfd_d2d_static_ovl_sf7'):
        pattern=(r'(?:qfd_sys_face_ovl(?:_fault1|_lctx1)?|qfd_sys_face_lctx3_wrapped)' if base=='qfd_sys_face_ovl'
                 else base+r'(?:_obs1|_fault1|_lctx1)?')
        names=set(re.findall(r'\b'+pattern+r'\b',text))
        if len(names)!=1:
            raise ValueError('selected GEN must have one exact head-prepare master for '+base+': '+str(sorted(names)))
        selected.append(next(iter(names)))
    if not lanes.is_file(): raise ValueError('actual GEN fwd_lanes.json required; K-only reconstruction prohibited')
    audit=RB.audit_netlist(die,lanes)
    if audit['verdict']!='PASS': raise ValueError('record bundle audit fails: '+str(audit['fails']))
    ages={}
    for name,n in [('TT.head_prepare',4),('SF.head_descriptor',3)]:
        row=audit['bundles'].get(name)
        if row is None or len(row['members'])!=n or not row['consistent'] or len(row['cycles'])!=1:
            raise ValueError('incomplete or unequal actual bundle '+name)
        ages[name]=int(row['cycles'][0])
    face=face_boundaries(root,case,selected[1])
    face_input=face['input_capture_edges'] if face else 0
    total=tt_local+ages['TT.head_prepare']+3+ages['SF.head_descriptor']+face_input+1
    result=dict(schema='opentallas.qwen.head_prepare_age.v1',
      source='actual CTLM c_emb stored token/position/user; source epoch from per-user prepare or matching HOST',
      die_sha256=hashlib.sha256(die.read_bytes()).hexdigest(),
      selected_masters=selected,
      lanes_sha256=hashlib.sha256(lanes.read_bytes()).hexdigest(),
      source_intrinsic_edges=dict(ct_lm_sample=tt_local,native_prepare_descriptor=3,face_held_bank=1),
      tt_source=tt_source,
      actual_transport_edges=ages,head_prepare_edges=total,
      host_user0_contract='HOST O61 token/position/epoch must match actual prepare before publication; compiler must price actual HOST availability',
      scope='GEN-derived fixed schedule age; physical timing and final sole calendar qualification remain separate',
      bundles={k:audit['bundles'][k] for k in ages})
    if face:
        result['source_intrinsic_edges'].update(face_input_capture=face_input,face_output_capture=face['output_capture_edges'])
        result['sysface_wrapper']=face
        result['head_prepare_edges_scope']='internal held-bank availability; face output capture belongs to later published head-TX/codec-wire ledger'
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('case');p.add_argument('--out',required=True)
    p.add_argument('--tt-source-receipt',help='source/LP-record hash-bound local embedding output ages for a selected LP/native TT')
    a=p.parse_args()
    try: result=measure(a.case,a.tt_source_receipt)
    except (ValueError,OSError,KeyError) as e:
        result=dict(verdict='FAIL',reason=str(e));Path(a.out).write_text(json.dumps(result,indent=2)+'\n');print(result['reason']);return 1
    result['verdict']='PASS';Path(a.out).write_text(json.dumps(result,indent=2)+'\n');print('HEAD_PREPARE_EDGES='+str(result['head_prepare_edges']));return 0
if __name__=='__main__':sys.exit(main())
