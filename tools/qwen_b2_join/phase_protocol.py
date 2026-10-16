#!/usr/bin/env python3
"""Fail-closed consumer contract for source-specific b2 phase calibration.

Current local component proof cannot authorize production emission. The producer
must supply actual path ledgers and a route-composed temporal gate, including the
calibrated parameter-free controller and issuer sources. No generic PASS+SHA is
accepted as a substitute for these named source/path obligations.
"""
import hashlib,json,sys
from pathlib import Path
PATH_GROUPS=('tc_to_port','am_to_controller','rq_to_train','tag_copy_to_issuer','issuer_to_train','lc_to_halfband','selector_to_upper','upper_to_halfband','rb_to_vm')

def validate_calibration(manifest,root):
 root=Path(root).resolve();a=json.loads(Path(manifest).read_text())
 if a.get('protocol')!='qwen-b2-native-phase-v1':raise ValueError('wrong phase protocol')
 if a.get('status')!='CALIBRATED_SOURCE_AND_ROUTE_TEMPORAL_PASS':raise ValueError('b2 production phase OPEN: '+', '.join(a.get('open_fields',[])))
 # Hash actual available files, rather than accepting an opaque success label.
 def checked_file(rec):
  p=root/rec['path']
  if not p.is_file()or hashlib.sha256(p.read_bytes()).hexdigest()!=rec['sha256']:raise ValueError('phase evidence missing or changed: '+str(p))
  return p
 for n in ('allocator_graph','allocator_stage_of','allocated_path_ledger','route_bench_runner','route_bench_source','route_bench_source_manifest','route_bench_log'):
  checked_file(a['evidence'][n])
 # Parameter-free production successors must be distinct actual sources.
 for n in ('controller','issuer'):
  r=a['calibrated_sources'][n];p=checked_file(r)
  import re
  text=p.read_text()
  m=re.search(r'\bmodule\s+'+re.escape(r['module'])+r'\s*([#(])',text)
  if not m or m[1]=='#':raise ValueError('calibrated '+n+' must have actual parameter-free source identity')
  if r['module']in('qfd_tt_ctlm_b2','qfd_res_train_issue_b2'):raise ValueError('uncalibrated generic source selected')
 halves=a['halves']
 if sorted(halves)!=list('012345'):raise ValueError('six actual half paths required')
 tes=[]
 for h in '012345':
  r=halves[h]
  for g in PATH_GROUPS:
   p=r[g]
   if type(p.get('edges'))is not int or p['edges']<0 or not p.get('source_pin')or not p.get('sink_pin')or not p.get('stage_record_ids'):raise ValueError('missing actual source-bound path '+h+'/'+g)
  if (r['tc_to_port']['edges']+r['am_to_controller']['edges'])!=2*r['controller_lnk']:raise ValueError('TC/AM F+R != 2L on half'+h)
  te=14+r['tc_to_port']['edges']+r['rq_to_train']['edges']-1-r['tag_copy_to_issuer']['edges']-r['issuer_to_train']['edges']
  if te!=r['train_edges']or te<2:raise ValueError('issuer phase mismatch half'+h)
  tes.append(te)
 if len(set(tes))!=1:raise ValueError('six issuer paths require explicit equal-age padding')
 # These must come from a source-pinned real DUT run, and cover every consumer.
 g=a['temporal_gate']
 for key in ('all_six_exact_rq_and_am','all_six_exact_rb_cycles_and_payload','real_e3_readbacks','native_head_scalar_exact','actual_prefetch_mutant_rejected','actual_train_phase_mutant_rejected','selector_and_upper_returns_exact'):
  if g.get(key)is not True:raise ValueError('missing actual route temporal gate '+key)
 if g.get('source_manifest_sha256')!=a['evidence']['route_bench_source_manifest']['sha256']:raise ValueError('bench source snapshot not bound')
 # Run artifacts must bind to this exact allocation, not an older local smoke.
 if g.get('allocator_graph_sha256')!=a['evidence']['allocator_graph']['sha256']or g.get('allocated_path_ledger_sha256')!=a['evidence']['allocated_path_ledger']['sha256']:raise ValueError('route gate allocation mismatch')
 return a
if __name__=='__main__':
 try:validate_calibration(sys.argv[1],sys.argv[2]if len(sys.argv)>2 else'.')
 except (ValueError,KeyError,FileNotFoundError)as e:print('REFUSED:',e);sys.exit(1)
 print('CALIBRATED_SOURCE_AND_ROUTE_TEMPORAL_PASS')
