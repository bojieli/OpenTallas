from pathlib import Path
import sys,json,hashlib
old=Path('/srv/opentallas-scratch2/claude/codex-kv-hhp-macro-trial-2340');src=Path('/srv/opentallas-scratch2/claude/codex-hhp-model-projection-0315/source/physical/die_plan/qwen_kvsys/cores/harden');sys.path.insert(0,str(src));import kv_core_rtl as K
out=Path('/srv/opentallas-scratch2/claude/codex-hhp-ft-roles-0435');out.mkdir(exist_ok=True)
typ='kv3_pc__cl5a95b461';plan=old/'source_r1/physical/die_plan/qwen_kvsys/plan_of_record/plan_c.json';t=json.loads(plan.read_text())['partition_types'][typ];meta=json.loads((old/'kit_rtl'/typ/'kit_rtl.json').read_text());ports={}
for name in meta['files']:
 p=old/'kit_rtl'/typ/Path(name).name
 for n,v in K._regex_ports(p).items():ports.setdefault(n,v)
B=K.Bound(old/'kit_rtl'/typ/(typ+'_bound.sv'),ports);hc=next(x for x in t['hard_cores'] if x['module']=='qkd_kvs_pc_h_head_p');M=K.build_core(B,t,hc,plan.parent/hc['pins_file'],straps=set());raw=K.emit_core(B,M)
assert 'module qkd_kvs_pc_h_head_p (' in raw and 'ft_ck_' not in raw
(out/'genuine_head_raw.sv').write_text(raw);(out/'genuine_head_pins.json').write_bytes((plan.parent/hc['pins_file']).read_bytes());(out/'RAW_HEAD_FIXTURE.json').write_text(json.dumps({'status':'RAW_IN_MEMORY_ONLY','qualified':False,'source_stage':'BEFORE_FULL_OVERLAY','module':hc['module'],'owner':hc['inst'],'raw_sha256':hashlib.sha256(raw.encode()).hexdigest(),'normal_api':'build_core+emit_core in memory only','GEN':False,'CAD':False,'source_plan':str(plan),'bound_source':str(B.path)},indent=2)+'\n');print('Actual genuine HEAD raw fixture emitted in memory only')
