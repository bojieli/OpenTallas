#!/usr/bin/env python3
"""Admitted W6 local implementation refinement, before additive RTL."""
import argparse,hashlib,importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def model():
    path=ROOT/'tools/hbm_w6_fullwidth_model.py'
    spec=importlib.util.spec_from_file_location('w6_admitted_base',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    old=m.price();new=json.loads(json.dumps(old))
    g=new['gate_proxy'];g['identity_XNOR']=7*55;g['identity_reduce']=7*54;g['state_control']=256;g['drain_scope_compare']=2
    new['fanout']['identity_comparison_loads_per_bit']=7
    logic=144*.2916+sum(g.values())*.2
    new['area'].update(prospective_logic_um2_per_SM=logic,full32SM_logic_um2=logic*32,
        reserved_slot_um2_per_SM=logic/.5,full32SM_slot_mm2=logic*32/.5/1e6)
    new['completion_input_ports'].update(request_identity_origin_valid_ready_bits=58,
        drain_request_control_bits=59,allcopies_response_control_bits=68,
        scope_bits='has_owner and reset_scope; represented by retained valid/phase, no added FF',
        alldrain_status_kind='current source-owned levels under coordinated admission-stop, not old queued certificates')
    new['implementation_refinement']=dict(preceding_model_commit='9b8ae395d4a1999962c8818cbece490c1bb31efe',
        preceding_proxy_slot_mm2=old['area']['full32SM_slot_mm2'],
        additional_full32SM_slot_mm2=new['area']['full32SM_slot_mm2']-old['area']['full32SM_slot_mm2'],
        seven_match_ports=['host_ACK','internal_SIMD_ACK_retire','consumer','child_reverse_done','parent_reverse_done','reverse_CDC_done','drain_response'],
        source_ADMISSION='parent explicit prospective component admission; no full bridge adoption or P&R',
        state_bits_unchanged=71,protected_state_bits_unchanged=144,
        clock_note='age guards enforce positive protocol edges; they do not physically retime ECC logic or prove1.2GHz closure',
        reset='por_n is cold global initialization only; rst_n is synchronous runtime reset held across clock edges with synchronized release; outputs gate while rst_n low; retained identity not cleared',
        external_source_contract='drain request/response owner55 +has_owner/reset scope. alldrain_live[8:0] must be current scoped source levels under admission-stop, including pending certificate and bothCDC copies; not delayed historical flags',
        boot='cold boot quarantines has_owner0; requires coordinated global source drain before any request',
        ECC='2 SECDED72/64 chunks; single-bit correction and scrub, double-bit failclosed. Uncorrectable state needs coordinated global cold recovery, no guessed owner release',
        payload_and_global_source_mapping_unchanged=True)
    new['base_model_source_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
    return new
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    with a.out.open('x') as f:json.dump(model(),f,indent=2,sort_keys=True);f.write('\n')
