import json,sys,hashlib,subprocess
from pathlib import Path
p=Path('/srv/opentallas-scratch2/claude/codex-kv-pvj-load-1029');src=p/'source'
sys.path[:0]=[str(src/'tools/die_plan'),str(src/'physical/die_plan/qwen_kvsys/cores/harden')]
import core_infra as CI,gen_core_kit_kv as GK,kit_contract as KC,lec as L
commit='850fa6e8a'
# Commit is the exact archive input, expanded on the hub before final kit provenance.
commit=Path(p/'SOURCE_SHA').read_text().strip()
plan=p/'current24/event/plan_sites_astk.json';records=[]
for n,pf in [('ot_qwen_tp8_pv_join_t__172.8x172.8','pv_join_pins_r26q5c_de688492fadf.json'),('ot_qwen_tp8_pv_join_t__172.8x172.8_fR180','pv_join_pins_fR180_r26q5c_5ebb1b850396.json')]:
 k=p/'kits'/n;pin=p/'current24/cores'/pf
 doc=json.load(open(pin));f=json.load(open(k/'freeze.json'))
 assert KC._canon(KC.placed_pins(k),[172.8,172.8])==KC._canon(doc,[172.8,172.8]),'current plan ABI differs physically'
 (k/'plan_pins.json').write_bytes(pin.read_bytes())
 c=json.load(open(k/'pv_clock_census.json'));old=len(c['sinks'])
 add=[f'u_leaf.g_output_load_local.g_word\\[{i}\\].load_q$_DFF_PN0_/CLK'for i in range(32)]
 present=set(add)&set(c['sinks']);assert not present or present==set(add)
 if present:old-=32
 else:c['sinks']+=add
 c['output_load_local']=dict(added_predicted=32,rule='actual synth census must replace predicted names before CTS')
 (k/'pv_clock_census.json').write_text(json.dumps(c,indent=1)+'\n')
 sl=json.load(open(k/'pv_trunk_slice.json'));sl['core_tree']['leaves'][0]['sinks']=c['sinks'];sl['core_tree']['leaves'][0]['domain_sinks']=len(c['sinks']);CI.install(k,sl)
 (k/'pv_trunk_slice.json').write_text(json.dumps(sl,indent=1)+'\n')
 t=(k/'pv_trunk_install.tcl').read_text();(k/'pv_trunk_install.tcl').write_text(t.replace(f'sinks{old}',f'sinks{len(c["sinks"])}'))
 f.update(source_commit=commit,plan=str(plan),plan_sha256=hashlib.sha256(plan.read_bytes()).hexdigest(),pins_file='plan_pins.json',pins_sha256=hashlib.sha256(pin.read_bytes()).hexdigest(),pins_canon_sha256=KC._canon(doc,[172.8,172.8]),regen=dict(base_kit='codex-kv-kits-1028/pvj/'+n,base_source_commit=f.get('source_commit'),rtl_delta='actual one-hot source + opt-in lookahead output-load32FF/0cycles',census_added_predicted=32))
 f['kit_hash']=GK.kit_hash(k);(k/'freeze.json').write_text(json.dumps(f,indent=1)+'\n');L.write_kit_provenance(k,src,provenance=dict(commit=commit,dirty=False,source='git recipe + pinned current native kit source'))
 records.append(dict(kit=n,kit_hash=f['kit_hash'],sinks=len(c['sinks']),current_plan_pins=pf,source_commit=commit))
print('PVJ_KITS_PREPARED',records)
(p/'kits_prepared.json').write_text(json.dumps(records,indent=1)+'\n')
