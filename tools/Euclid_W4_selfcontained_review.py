#!/usr/bin/env python3
"""Self-contained source/cost/stage integrity; no compilation or dependency imports."""
import pathlib,json,hashlib,gzip,math,re,argparse
ROOT=pathlib.Path(__file__).resolve().parents[1]
DEFAULT=ROOT/'results/uarch/Euclid_W4_RFACK_identity_contract_20261003/selfcontained-peer-r10'
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def review(p=DEFAULT):
 p=p.resolve();pins=json.loads((p/'artifact-pins-r10.json').read_text())
 for name,want in pins.items():
  f=(p/name).resolve()
  if not f.is_relative_to(p) or sha(f)!=want:raise ValueError('packet pin '+name)
 m=json.loads((p/'manifest-r10.json').read_text())
 for row in m['design']+m['benches']+m['original_bodies']+m['costs']:
  if sha(p/row['archive'])!=row['sha256']:raise ValueError('input pin '+row['original_path'])
 if len(m['design'])!=10 or len({r['archive'] for r in m['design']})!=10:raise ValueError('design inventory')
 if (p/'sources.f').read_text().splitlines()!=[r['archive'] for r in m['design']]:raise ValueError('selector drift')
 for name in ['ot_gpu_rf_service','ot_gpu_full_sm_service']:
  old=(p/'original-default-bodies'/f'{name}.sv').read_text();new=(p/'design'/f'{name}.sv').read_text()
  if not new.endswith(old.replace('module '+name+' ','module '+name+'_W4_original ')):raise ValueError('default branch not byteidentical')
 interface=json.loads((p/'interface-frozen-r7.json').read_text())
 for mod,head in interface['exact_module_headers'].items():
  body=(p/'design'/f'{mod}.sv').read_text()
  if body[:body.index(');')+2]!=head:raise ValueError('header changed')
 if {r['original_path']:r['sha256'] for r in m['design']}!=interface['source_pins']:raise ValueError('live source binding changed')
 cost=json.loads((p/'cost-inputs/component-price-r3.json').read_text());control=json.loads((p/'cost-inputs/ACK-match-control-pricing-r4.json').read_text())
 inv=cost['selected_inventory'];a=cost['area'];n=inv['SMs']
 if (n,inv['raw_identity_payload_bits_per_SM'],inv['protected_word_bits_per_SM'])!=(32,55,72):raise ValueError('canonical cost width')
 ff=n*(55+72+72);ffarea=ff*a['DFFHQN_geometric_basis_um2'];muxarea=(ff+n*55)*a['mux_bit_um2_ASSUMED']
 if not math.isclose(ffarea,a['FF_geometric_area_um2']) or not math.isclose(muxarea,a['mux_area_um2_ASSUMED']):raise ValueError('prospective cost ledger changed')
 subtotal=ffarea+muxarea+a['codec_area_um2_ASSUMED']
 if not math.isclose(subtotal,a['subtotal_cells_um2_ASSUMED']) or not math.isclose(control['cell_area_delta_um2_ASSUMED'],32*(109*.3+.2916)):raise ValueError('price mismatch')
 if cost['latency']['added_local_RF_edges_vs_existing_ACK']!=1 or control['actual_SSFF'] is not None:raise ValueError('clock scope changed')
 scope=json.loads((p/'cost-inputs/allocator-context-r6/once-only-join.json').read_text())
 if scope['once_only_ledger']['allocator_net_increment_area'] is not None or scope['qualification']['hardware_build_admission']:raise ValueError('allocator gross promoted to net/admission')
 s=p/'enabled-fullSM-stage';receipt=json.loads((s/'stage-receipt-r9.json').read_text());launch=json.loads((s/'launch.json').read_text())
 for job in receipt['completed_jobs']:
  if job['rc']!=0 or sha(s/job['log'])!=job['log_sha256']:raise ValueError('completed stage failure')
 if (s/'supervisor-stdout-new-stage.log').read_text()!='tb_W4_full_service-compile 0\ntb_W4_full_service-run 0\n':raise ValueError('supervisor evidence')
 if receipt['marker']!=(s/'tb_W4_full_service-run.log').read_text().strip() or '13cycle done;W4 accepted-owner46+slot9;mirrors;leases' not in receipt['marker']:raise ValueError('actual stage marker')
 if receipt['sourcefreeze']!=m['sourcefreeze'] or receipt['status']!='PASS_ENABLED_FULLSM_STAGE_ONLY_OVERALL_GATE_LIVE':raise ValueError('source/terminal scope')
 launchpins={r['original_path']:r['sha256'] for r in m['design']}
 for name,want in launch['source_sha256'].items():
  if launchpins[str(pathlib.Path(name).relative_to(pathlib.Path('/tmp/opentallas-W4-RFACK-identity-contract-20261003')))]!=want:raise ValueError('actual launch mismatch')
 h=hashlib.sha256();size=0
 with gzip.open(s/receipt['completed_executable']['compressed_archive'],'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b);size+=len(b)
 if h.hexdigest()!=receipt['completed_executable']['uncompressed_sha256'] or size!=receipt['completed_executable']['original_bytes']:raise ValueError('completed executable changed')
 for field in ['default_body_gate_qualified','validcode_mismatch_directed_qualified','production_C0_KV_caller_qualified','whole_connector_or_CDC_qualified','SSFF_or_rate_qualified','restart_or_duplicate']:
  if receipt[field]:raise ValueError('scope promotion '+field)
 if m['whole_gate_terminal'] or m['provider_or_caller_CDC_SSFF_or_rate']:raise ValueError('overall qualification claimed')
 return {'status':'PASS_SELFCONTAINED_SOURCE_AND_ENABLED_STAGE_ONLY','design_sources':10,'benches':len(m['benches']),'cost_inputs':len(m['costs']),'artifact_pins':len(pins),'sourcefreeze':m['sourcefreeze'],'fullSM_enabled_compile_rc':0,'fullSM_enabled_run_rc':0,'SIMD_done_cycles':13,'overall_gate_terminal':False,'new_compile_or_simulation':False,'original_body_identity':True,'production_caller_CDC_SSFF':False,'cost_full_component_complete':False}
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--packet',type=pathlib.Path,default=DEFAULT);a=parser.parse_args();print(json.dumps(review(a.packet),indent=2,sort_keys=True))
