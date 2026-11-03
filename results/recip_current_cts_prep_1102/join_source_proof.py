from pathlib import Path
import hashlib,json,re,shutil
old=Path('/srv/opentallas-scratch2/claude/codex-kv-ahub-1131/kits/recip_native216');root=Path('/srv/opentallas-scratch2/claude/codex-recip-place-canary-prep-0810');cur=root/'kit';out=root/'cts_prep';out.mkdir(exist_ok=True);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();receipt=old/'lec/lec.json';d=json.loads(receipt.read_text());reuse=json.loads((cur/'source_eq_reuse.json').read_text());prov=json.loads((old/'PROVENANCE.json').read_text());assert sha(receipt)==reuse['receipt_sha256']=='2930cf8f6bfd793b98d5864fb044e341a2c5ae7471ef063b9a46a2cd1f28fa49';assert d['verdict']=='EQUIVALENT' and d['counts']=={'compare_points':11074,'proved':11074,'differs':0,'undecided':0};assert not d['black_boxes'] and not d['failing'] and not d['unproven_points'];assert d['reset_contract']['used']==4 and not d['reset_contract']['debug_overrides'];inputs={}
for rel,want in prov['files'].items():
 if rel.startswith('rtl/') or rel=='lec.py':
  assert sha(old/rel)==sha(cur/rel)==want,rel;inputs[rel]=want
keys=['DESIGN_NAME','VERILOG_FILES','VERILOG_DEFINES','VERILOG_INCLUDE_DIRS','SYNTH_HDL_FRONTEND','ADDITIONAL_LIBS']
def cfg(p):return dict(re.findall(r'^(?:override )?export (\w+)\s*[:?+]?=\s*(.*?)\s*$',p.read_text(),re.M))
a,b=cfg(old/'config.mk'),cfg(cur/'config.mk');assert all(a.get(k)==b.get(k) for k in keys)
net='run/results/asap7/hc_ot_qkh_recip_leaf__216x216/base/1_2_yosys.v';assert sha(old/net)==sha(cur/net)=='ebaffaeff0de02cd19b36ce216f644f43a319171467760e258f9042fd86815c6';inputs[net]=sha(cur/net)
gold=(old/'lec/gold.ys').read_text();gate=(old/'lec/gate.ys').read_text();assert '-DSYNTHESIS' in gold and '--top ot_qkh_recip_leaf' in gold and '/work/'+net in gate
keep=['lec.json','gold.ys','gate.ys','gold.aig','gate.aig','gold.map','gate.map','gold.aliases.json','hyp.json','wrap_gold.v','wrap_gate.v','lecff.v','stubs.v','noreset_constants.tsv']
p=out/'source_proof_native';p.mkdir(exist_ok=True)
for n in keep:shutil.copy2(old/'lec'/n,p/n)
shutil.copy2(old/'PROVENANCE.json',p/'ORIGINAL_PROVENANCE.json');shutil.copy2(cur/'source_eq_reuse.json',p/'source_eq_reuse.json');shutil.copy2(old/'config.mk',p/'original_config.mk');shutil.copy2(cur/'config.mk',p/'current_config.mk')
result={'status':'PASS_CURRENT_CASE_SOURCE_TO_RETAINED_SYNTH_EQ_JOIN','original_proof':str(receipt),'receipt_sha256':sha(receipt),'counts':d['counts'],'top':d['top'],'reset_contract':d['reset_contract'],'reset_ports':d['kit_reset_ports'],'implicit_nets':d['implicit_nets'],'black_boxes':d['black_boxes'],'source_frontend':'slang','gate_frontend':'verilog','source_config_fields':{k:a.get(k) for k in keys},'exact_current_inputs':inputs,'retained_native_proof_files':{n:sha(p/n) for n in keep},'no_solver_rerun':True,'scope':'Existing actual original proof of exact current case RTL/config/defines/checker/mapped SYNTH; not proof of optimized PLACE or old selected AHUB models','normal_final_netlist_EQ':'NOT_RUN_STILL_REQUIRED_LATER'};(out/'SOURCE_PROOF_JOIN.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'],d['counts'])
