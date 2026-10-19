#!/usr/bin/env python3
import gzip,hashlib,json,pathlib,subprocess
OUT=pathlib.Path(__file__).resolve().parent
ROOT=OUT.parents[2]
def git(*a): return subprocess.check_output(['git','-C',str(ROOT),*a])
pins={
'0d4c9808f':['results/rtl/qwen_layer_tput_1018/compiled_L1/compute_programme/sys_face_events.json','rtl/qwen_split/qfd_sys_face.sv','rtl/qwen_split/qfd_native59_dv_service.sv','rtl/qwen_split/qfd_native59_command_context.sv','rtl/qwen_split/qfd_native59_q_export_control.sv','rtl/qwen_split/qfd_native59_static_service.sv','rtl/qwen_split/qfd_embedding_word_provider.sv','rtl/qwen_sys/static_embedding_20261014/qkd_embedding_static_preload_face.sv','rtl/qwen_sys/static_embedding_20261014/qkd_embedding_static_core_store.sv','rtl/qwen_sys/static_embedding_20261014/qkd_embedding_row_tx.sv','tools/qwen_split/d2d_link_calendar.py','rtl/test/qwen_split/sys_face_bench_events.json','rtl/test/qwen_split/run_sys_face_bench.sh'],
'3c51edcae':['rtl/qwen_split/qfd_native59_dv_service.sv','rtl/qwen_split/qfd_native59_qseat_sram.sv'],
'a29dda274':['results/rtl/sysface_lp_bank_native_join_1019/README.md','results/rtl/sysface_lp_bank_native_join_1019/source_receipt.json','rtl/test/qwen_split/tb_sysface_lp_bank_native_join.sv'],
'77fc3afbc':['results/rtl/sysface_physical_proof_1019/README.md','results/rtl/sysface_physical_proof_1019/receipts/matrix.log']}
manifest=[]
for rev,paths in pins.items():
 for p in paths:
  b=git('show',f'{rev}:{p}'); dest=OUT/'source'/rev/p;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(b)
  manifest.append(dict(commit=git('rev-parse',rev).decode().strip(),path=p,sha256=hashlib.sha256(b).hexdigest(),bytes=len(b),lines=len(b.splitlines())))
prior=ROOT/'results/arch/qwen_calr_sysface_binding_1019/source'
s=gzip.decompress((prior/'gen0__die.v.gz').read_bytes()).decode()
lines=s.splitlines()
selected=[l for l in lines if 'qfd_native59_dv_service native59' in l or 'qfd_embedding_word_provider embed_prov' in l or ('qfd_' in l and any(x in l for x in ['n_sf_q_slot','n_sf_emb_','n_dvw_dd_wo','n_dvw_native59_emb_']))]
(OUT/'actual_gen0_connections.txt').write_text('\n'.join(selected)+'\n')
import re
bindings={}
for instance in ['native59','embed_prov','sys_face','dvs_W5']:
 line=next(l for l in lines if re.search(r'\b'+instance+r'\s*\(',l))
 bindings[instance]=dict(re.findall(r'\.(\w+)\s*\(\s*([^()]*)\s*\)',line))
assert bindings['native59']['dd_i']=='n_dvw_dd_wo__r26'
assert bindings['native59']['dr_o']=='n_dvw_dr_wi'
assert bindings['native59']['ck']=='n_clk_r54'
assert bindings['native59']['rst_n']=='n_rst_seq__t80'
assert bindings['embed_prov']['core_token']=='n_dvw_tt_ctlm_emb_token'
assert bindings['embed_prov']['ck']=='n_clk_r54'
assert bindings['embed_prov']['rst_n']=='n_rst_seq__t25'
assert bindings['sys_face']['ck']=='n_clk_d2d'
assert bindings['sys_face']['rst_n']=='n_rst_d2d__fo2__r4__t24'
assert bindings['dvs_W5']['dd_wo']=='n_dvw_dd_wo'
assert bindings['dvs_W5']['dr_wi']=='n_dvw_dr_wi__r27'
assert bindings['dvs_W5']['ck']=='n_clk_r135'
assert bindings['dvs_W5']['rst_n']=='n_rst_field__t1774'
assert len([l for l in lines if re.search(r'\brly_dvw_dd_wo_\d+\s*\(',l)])==26
(OUT/'actual_gen0_bindings.json').write_text(json.dumps(bindings,indent=2)+'\n')

e=json.loads((prior/'results__rtl__qwen_layer_tput_1018__compiled_L1__compute_programme__sys_face_events.json').read_text())
provider=next(l for l in lines if 'qfd_embedding_word_provider embed_prov' in l)
a={'scope':'SOURCE_EXTRACTION_ONLY; dates and native timing unresolved','copied_7e515_events_sha256':hashlib.sha256((prior/'results__rtl__qwen_layer_tput_1018__compiled_L1__compute_programme__sys_face_events.json').read_bytes()).hexdigest(),'L_present':'L' in e,'E_present':'E' in e,'L_compiled':e['L_compiled'],'L_missing':e['L_missing'],'E_missing':e['E_missing'],'gen0_sha256':hashlib.sha256(s.encode()).hexdigest(),'embedding_core_token_bound':bool(__import__('re').search(r'\.core_token\s*\(',provider)),'actual_native_master':'qfd_native59_dv_service','native_ck':'n_clk_r54','native_rst':'n_rst_seq__t80','embedding_ck':'n_clk_r54','embedding_rst':'n_rst_seq__t25','sysface_ck':'n_clk_d2d','sysface_rst':'n_rst_d2d__fo2__r4__t24','native_phase':None,'first_use':None,'selected_QSLOT_dates':None,'selected_EMBW_dates':None,'selected_FILL_date':None,'build_admitted':False,'source_inventory':{'files':len(manifest),'bytes':sum(m['bytes'] for m in manifest),'lines':sum(m['lines'] for m in manifest)},'measured_prior_consumer_peak_GB':2.27,'new_compile_memory_GB':None}
(OUT/'sources.json').write_text(json.dumps(manifest,indent=2)+'\n');(OUT/'analysis.json').write_text(json.dumps(a,indent=2)+'\n')
a['metadata_pinned_0d4c_events_sha256']=hashlib.sha256((OUT/'source/0d4c9808f/results/rtl/qwen_layer_tput_1018/compiled_L1/compute_programme/sys_face_events.json').read_bytes()).hexdigest()
a['metadata_pinned_L_compiled']=json.loads((OUT/'source/0d4c9808f/results/rtl/qwen_layer_tput_1018/compiled_L1/compute_programme/sys_face_events.json').read_text())['L_compiled']
assert a['copied_7e515_events_sha256']=='b8e8121a75d0c12596f250596deb0ece1ef4d4b739d767611a2cb24f1266ad7f'
assert a['metadata_pinned_0d4c_events_sha256']=='787345b9fc1845e9897f6200eaa5fe0ffd31f08a454ef75911bafb1d8a632d23'
(OUT/'analysis.json').write_text(json.dumps(a,indent=2)+'\n')
assert not a['L_present'] and not a['E_present'] and a['embedding_core_token_bound']
assert {x[1] for x in a['L_compiled']}=={3,4}
assert a['gen0_sha256']=='7b1bdfc5fd26c2e6f17fe6aa5b1d68bd9e2fa05bc3ecf408b9f163eb600bbde7'
print('EXTRACTION_PASS: selected profile lacks L/E/QSLOT; GEN0 core_token bound; sources pinned')
print('FULL_CALENDAR_UNRESOLVED: no dates inferred, no compile admitted')

if '--full-graph' in __import__('sys').argv: raise SystemExit(2)
