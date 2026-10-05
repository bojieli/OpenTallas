#!/usr/bin/env python3
"""Cold source-pin/coverage replay; never loads checkpoints or executes engines."""
import argparse,ast,hashlib,json,re,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=Path(subprocess.check_output(['git','rev-parse','--show-toplevel'],text=True).strip())
def sha(b):return hashlib.sha256(b).hexdigest()
def data(p):return (HERE/'inputs'/p).read_bytes()
def j(p):return json.loads(data(p))
def derive():
 manifest=jlocal('input_manifest.json')
 for r in manifest:
  b=data(r['path']) if r['archive'] else subprocess.check_output(['git','show',r['source_commit']+':'+r['path']],cwd=ROOT)
  assert len(b)==r['bytes'] and sha(b)==r['sha256'],r['path']
  assert subprocess.check_output(['git','rev-parse',r['source_commit']+':'+r['path']],cwd=ROOT,text=True).strip()==r['git_blob']
 cfg=j('compiler/models/deepseek-v4.1-flash/inference_config.json')
 assert (cfg['n_mtp_layers'],cfg['dspark_block_size'],cfg['dspark_n_routed_experts'],cfg['dspark_n_activated_experts'])==(3,5,128,3)
 mtp=j('results/rtl/w19_hbm_tp96_isa_mtp_oreduce.json')
 run=mtp['runs']['mtp:oreduce:L0-39:head']['result']
 assert run['mode']=='mtp_verify' and len(run['positions'])==6 and len(run['layers'])==40
 assert all(r['verdict']=='pass' for r in run['layers'])
 assert run['head']['logits_bit_exact']==[True]*6 and run['head']['accepted']==1
 sm=j('results/rtl/w19_sm_real_ops_mtp.json')['cases']['mtp']
 assert len(sm)==197 and all(c['exact'] for c in sm)
 coverage=j('results/uarch/h3_deepseek_complete_native_20261002/coverage.json')
 assert coverage['coverage']['PCs']==2213 and len(coverage['coverage']['families'])==30
 assert sum(coverage['coverage']['families'].values())==2213
 audit=j('results/uarch/h3_complete_native_calendar_20261002/provider_v1_mtp_join_r4/final_physical/MTP_source_contract_audit.json')
 assert audit['source_verify_program']['actual_primitive_microprograms_and_version_home_calendar'] is None
 assert audit['reference_drafts']['actual_drafter_executed_by_reference'] is False
 assert audit['causal_KV_successor_contract']['implemented_native_commit_or_rollback_program'] is None
 assert audit['full_iteration_calibrated_us'] is None and audit['accepted_token_rate_qualified'] is False
 ref=j('results/uarch/h3_complete_native_calendar_20261002/authority_reconciliation_r4/inputs/w19_hbm_token_mtp_fused_wsel256.json')
 assert ref['result']['total_us']==715.82
 assert abs(sum(ref['result']['parts_us'].values())-715.82)<1e-8
 core=data('rtl/w17_runtime/hdc/v41x/ot_hdc_core_v41x.sv').decode()
 tile=data('rtl/w17_runtime/chip/ot_chip_v41x_tile.sv').decode()
 inst=tile.split('ot_hdc_core_v41x #',1)[1].split('u_core',1)[0]
 assert re.search(r'parameter integer NSLOT\s*=\s*1',core)
 assert '.NSLOT(' not in inst and '.MP(' not in inst
 wrapper=data('rtl/hdc/v41/ot_hdc_mtp_route_tops.sv').decode().split('module ot_mtp_accept8',1)[1]
 assert '.NW(16)' in wrapper and cfg['vocab_size']>65536
 isa=data('tools/hdc_isa_v41.py').decode();assert re.search(r'POS_RING\s*=\s*8',isa)
 reduced=j('results/rtl/hdc_v41_mtp_isa_evidence.json');assert 'HALTED' in reduced['claim_boundary']
 assert jlocal('findings.json')['buildable_component_prerequisites']['existing_accept_source_lower_bound']['unprotected_raw_sequential_bits']==366
 for p in ['results/rtl/hdc_v41_mtp_campaign.json','results/rtl/hdc_v41_mtp_performance.json']:
  assert not subprocess.check_output(['git','ls-tree',manifest[0]['source_commit'],'--',p],cwd=ROOT),p
 evidence={}
 for finding in jlocal('findings.json')['findings']:
  for s in finding['sources']:
   line=data(s['path']).decode().splitlines()[s['line']-1]
   assert s['anchor'] in line,(finding['id'],s)
  evidence[finding['id']]='PINNED_SOURCE_ANCHORS_VERIFIED'
 out={'schema':'DS_MTP_SOURCE_COVERAGE_DERIVED_R1','source_commit':manifest[0]['source_commit'],'pin_count':len(manifest),'archived_bytes':sum(r['bytes'] for r in manifest if r['archive']),
 'source_shape':{k:cfg[k] for k in ['n_layers','n_mtp_layers','dim','vocab_size','dspark_block_size','dspark_markov_rank','dspark_target_layer_ids','dspark_n_routed_experts','dspark_n_activated_experts','window_size']},
 'source_min_token_bits':(cfg['vocab_size']-1).bit_length(),'current_full_core_NW':21,'unchanged_route_accept_NW':16,
 'HBM_source_verify':{'positions':run['positions'],'input_tokens':run['tokens'],'layers':len(run['layers']),'head':run['head'],'mean_union_experts':run['mean_union_experts'],'actual_draft_executed':False,'native_iteration':False},
 'retained_SM_RTL':{'cases':len(sm),'layers':sorted({c['op'].split('.')[0] for c in sm}),'format_columns':sorted({(c['fmt'],c['cols'])for c in sm}),'all_case_outputs_exact':True,'whole_die_physical':False},
 'native_AR_coverage':coverage['coverage'],'ROM_runtime_core':{'NSLOT':1,'MP':1,'tile_override_present':False,'MTP_claim_qualified':False},
 'reference_HBM_fused_verify':{'total_us':ref['result']['total_us'],'parts_us':ref['result']['parts_us'],'artifact_source_commit':ref['source_commit'],'whole_iteration_calibrated':False},
 'reduced_evidence':{'status':reduced['status'],'claim_boundary':reduced['claim_boundary']},
 'finding_source_checks':evidence,'verdict':'PASS_BOUNDED_INVENTORY; FAIL_WHOLE_MTP_ADMISSION','qualified_rate':None,'hardware_admitted':False,'checkpoint_payload_read':False,'engine_or_acceptance_jobs':0}
 return (json.dumps(out,indent=2,sort_keys=True)+'\n').encode()
def jlocal(p):return json.loads((HERE/p).read_bytes())
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--verify',action='store_true');ap.add_argument('--out',type=Path);a=ap.parse_args();b=derive()
 if a.verify:
  assert (HERE/'inventory.json').read_bytes()==b,'cold derived receipt mismatch'
  print('PASS 47 source pins, 14 anchored findings, byte-exact inventory; whole MTP remains unqualified')
 else:
  target=a.out or HERE/'inventory.json';target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b);print(target)
if __name__=='__main__':main()
