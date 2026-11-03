from pathlib import Path
import sys,json,hashlib,copy
root=Path('/srv/opentallas-scratch2/claude/codex-hhp-model-projection-0315');h=root/'source/physical/die_plan/qwen_kvsys/cores/harden';sys.path.insert(0,str(h));import kv_core_rtl as K;import kvspc_model_projection as P
old=Path('/srv/opentallas-scratch2/claude/codex-kv-hhp-macro-trial-2340');typ='kv3_pc__cl5a95b461';plan=old/'source_r1/physical/die_plan/qwen_kvsys/plan_of_record/plan_c.json';t=json.load(open(plan))['partition_types'][typ];meta=json.load(open(old/'kit_rtl'/typ/'kit_rtl.json'));mods={};readset={}
for path in meta['files']:
 p=old/'kit_rtl'/typ/Path(path).name;assert p.is_file(),str(p);readset[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
 # Normal parser's ANSI-header fallback, no Yosys invocation or elaboration.
 for n,v in K._regex_ports(p).items():mods.setdefault(n,v)
bound=old/'kit_rtl'/typ/(typ+'_bound.sv');B=K.Bound(bound,mods);models=[]
for hc in t['hard_cores']:
 if hc['module']=='qkd_kvs_pc':models.append(K.build_core(B,t,hc,plan.parent/hc['pins_file'],straps=set()))
assert [m['hc']['inst'] for m in models]==['kvpc1','kvpc2','kvpc3'];before=copy.deepcopy(models)
g=P.verified_guard(root/'guard_inputs/event.json',root/'guard_inputs/rtl_overlay',root/'guard_inputs'/P.BASE_FILE,('kvpc1','kvpc2','kvpc3'))
r=P.prepare_split(B,models,g,enabled=True);assert models==before
for m in r['models']:
 owner=m['hc']['inst'];orig=next(z for z in models if z['hc']['inst']==owner)
 for bit in [259,260]:assert m['part_conn'][('pc__land_er_259',bit)]==orig['part_conn'][('pc__land_er',bit)]
for owner,txt in r['wrapped_cores'].items():(root/(owner+'_wrapper_only.sv')).write_text(txt)
(root/'split_wrapper_only.sv').write_text(r['split'])
heads={ri for ri,(mod,pm) in B.net.insts.items() if mod=='qkd_kvs_pc_h_head_p'};assert len(heads)==1;lines,spans=K.inst_blocks(B.text,heads);assert heads==set(spans)
for name,(a,z) in spans.items():assert '\n'.join(lines[a:z+1]) in r['split']
for owner,txt in r['functional_headers'].items():(root/(owner+'_functional_ports_only.sv')).write_text(txt)
assert r['split'].count('ft_ck_')==B.text.count('ft_ck_')
report=dict(status=r['status'],qualified=r['qualified'],fixture_source_stage='BEFORE_FULL_SOURCE_OVERLAY; public headers and parent topology preserved by ea246; NOT a current full-event GEN receipt',normal_API='Bound/build_core/emit_core(raw copies), wrapper ONLY, emit_split(projected copies)',port_direction_parser='normal ANSI-header fallback; no Yosys/GEN/elaboration',raw_models_unchanged=True,actual_head_instances=sorted(heads),head_original_block_exact=True,no_new_ft_bindings=True,holds=r['holds'],readset=readset,source_bound_sha256=hashlib.sha256(bound.read_bytes()).hexdigest(),source_plan_sha256=hashlib.sha256(plan.read_bytes()).hexdigest(),source_guard_event=g.event_sha256,helper_sha256={'model_projection':hashlib.sha256(Path(P.__file__).read_bytes()).hexdigest(),'normal_core':hashlib.sha256(Path(K.__file__).read_bytes()).hexdigest()},models={m['hc']['inst']:dict(raw_ports=len(raw['pdecl']),projected_ports=len(m['pdecl']),raw_bits=len(P.bitkeys(raw['pdecl'])),projected_bits=len(P.bitkeys(m['pdecl'])),land_high_raw={str(i):list(raw['part_conn'][('pc__land_er',i)]) for i in [259,260]},land_high_projected={str(i):list(m['part_conn'][('pc__land_er_259',i)]) for i in [259,260]}) for m,raw in zip(r['models'],models)})
(root/'ACTUAL_FIXTURE.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
