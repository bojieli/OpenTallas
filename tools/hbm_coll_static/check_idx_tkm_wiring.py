#!/usr/bin/env python3
"""Typed native child/API and cycle-contract binding audit, not elaboration."""
import hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
P=ROOT/'rtl/hbm_accel/generic/collective/p2p'
def norm(s):return re.sub(r'\s+','',s)
def check(inputs):
 inputs=Path(inputs);manifest=json.loads((P/'idx_tkm_native_sources.json').read_text())
 for name,want in manifest['input_SHA256'].items():
  assert hashlib.sha256((inputs/name).read_bytes()).hexdigest()==want,'Native dependency changed:'+name
 src=(P/'ot_hgi_coll_idx_tkm_join.sv').read_text()
 required={
 'selector_actual':'ot_hbm_idx_selector_static u_selector',
 'staging_actual':'ot_hbm_idx_topk_link_static u_staging',
 'selector_result_port':'.selected_line(selected_line)',
 'actual_ingest_check':'.actual(selected_v)',
 'fixed_ingest_reservation':'.ingest_v(staging_ingest)',
 'group_base':'.rank(rank),.gbase(gbase)',
 'typed_native_IDX':'.idx_v(idx_launch_v),.idx_d(idx_launch_data)',
 'typed_native_VM':'.vm_v(vm_v),.vm_d(vm_d)',
 'reserved_mode':'.mode_idx(ingress_mode_idx)',
 'native_transport':'ot_hgi_coll_qslots #(.NS(4),.ND(4),.SELW(2)) u_transport',
 'actual_TKM':'ot_hgi_coll_tkm_static #(.KMAX(2048)) u_tkm',
 'native_n512':'.cfg_n(12\'d512)',
 'native_pf64':'.cfg_pf(16\'d64)',
 'real_consumer_data':'.del_valid(tkm_input_v),.del_flit(tkm_input_data)',
 'compiler_consumer_slot':'.del_slot(tkm_del_slot)',
 }
 for name,fragment in required.items():assert norm(fragment) in norm(src),name
 assert src.count('.selected_line(selected_line)')==2,'Selector output must directly drive real staging input'
 prod=(inputs/'ot_hbm_idx_topk_link_static.sv').read_text()
 assert 'rank,gbase' in prod and "read_gbase" in prod,'group-relative index source required'
 tkm=(ROOT/'rtl/hbm_accel/generic/collective/tkm/ot_hgi_coll_tkm_static.sv').read_text()
 for x in ['ingress_end','rel[2:0]==0','fl_=32\'(cfg_g)*32\'(cfg_pf)','i_=8+((fl_+3)/4)*8']:
  assert norm(x) in norm(tkm),'Actual TKM timing changed:'+x
 assert "KMAX=2048" in norm(tkm)
 return {'status':'PASS_TYPED_SOURCE_BINDING_ONLY','checked_wires':list(required),'actual_child_modules':['ot_hbm_idx_selector_static','ot_hbm_idx_topk_link_static','ot_hgi_coll_vm_idx_ingress','ot_hgi_coll_qslots','ot_hgi_coll_tkm_static'],
 'parent_sha256':hashlib.sha256(src.encode()).hexdigest(),'full_TKM_runtime':'PENDING existing publisher build; not replaced by a model','actual_index_inputs':manifest['input_SHA256']}
if __name__=='__main__':print(json.dumps(check(sys.argv[1]),indent=2))
