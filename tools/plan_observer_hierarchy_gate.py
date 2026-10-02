#!/usr/bin/env python3
"""Static, read-only source planning. Contains no compiler launch or model build.

The text dependency closure is conservative: generate/ifdef alternatives are kept.
It is not a proven minimum elaborated netlist or a hook elaboration PASS.
"""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

SOURCE='4e38326d6f361bc85e660f48c59c355e2bb95274'
OUT='results/rtl/observer_hierarchy_source_plan_4e383_20261002'
COPY='rtl/test/v41_runtime/ot_v41_rt_die_sim_observe.sv'
L0_COPY='rtl/test/v41_runtime/ot_v41_rt_die_sim_observe_l0.sv'
L0_PARENT='rtl/w17_runtime/chip/ot_chip_v41x_die.sv'
CKV_PARENT='rtl/chip/ckvsel/ot_chip_v41x_die.sv'
L20_LIST='tools/w17_current_fastpp_l20_sources.txt'

def sha(data): return hashlib.sha256(data).hexdigest()
def blob(repo,path):
    # Git source blobs only. Never use local live source or image/checkpoint files.
    return subprocess.check_output(['git','show',SOURCE+':'+path],cwd=repo)
def clean(text):
    return re.sub(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"',' ',text,flags=re.S)
def module_bodies(text):
    return {m.group(1):m.group(2) for m in re.finditer(r'\bmodule\s+(\w+)\b(.*?)\bendmodule\b',clean(text),re.S)}
def instantiations(body):
    return [(m.group(1),m.group(2)) for m in re.finditer(r'\b(ot_\w+)\s*(?:#\s*\(.*?\)\s*)?(\w+)\s*\(',body,re.S)]
def closure(inputs,top):
    definitions={}; duplicates={}
    for path,text in inputs.items():
        for module,body in module_bodies(text).items():
            if module in definitions: duplicates.setdefault(module,[definitions[module][0]]).append(path)
            definitions[module]=(path,body)
    reached=set(); unresolved=set(); edges=[]; stack=[top]
    while stack:
        module=stack.pop()
        if module in reached: continue
        if module not in definitions: unresolved.add(module);continue
        reached.add(module)
        for child,instance in instantiations(definitions[module][1]):
            edges.append(dict(parent=module,child=child,instance=instance))
            stack.append(child)
    paths=sorted({definitions[m][0] for m in reached})
    # Includes/imports are separately conservatively retained from supplied universe.
    support=sorted(path for path in inputs if path.endswith('.svh') or re.search(r'\bpackage\s+\w+',clean(inputs[path])))
    return dict(root=top,files=paths,support_files=support,modules=sorted(reached),edges=edges,unresolved_modules=sorted(unresolved),duplicate_definitions=duplicates,method='conservative textual dependency closure; unresolved conditionals retained, not compiler elaboration')

def l0_derivative(text):
    assert text.count('module ot_v41_rt_die_sim_observe #(')==1
    assert text.count('.CKV_SELECTED(SIM_OBS_CKV_SELECTED),')==1
    return text.replace('module ot_v41_rt_die_sim_observe #(', 'module ot_v41_rt_die_sim_observe_l0 #(').replace(' .CKV_SELECTED(SIM_OBS_CKV_SELECTED),','')

def inverse_l0(text):
    return text.replace('module ot_v41_rt_die_sim_observe_l0 #(', 'module ot_v41_rt_die_sim_observe #(').replace('.WINDOW_HBM_ATTENTION(1),', '.WINDOW_HBM_ATTENTION(1), .CKV_SELECTED(SIM_OBS_CKV_SELECTED),')

def plan(repo):
    repo=Path(repo);out=repo/OUT
    authority=json.loads((out/'retained_manifest_authority.json').read_text())
    entries={e['path']:e for e in authority['audit'] if e['path'].endswith(('.sv','.v','.svh'))}
    inputs={}
    for path,e in entries.items():
        data=blob(repo,path);assert sha(data)==e['sha256'];inputs[path]=data.decode()
    observer=(repo/COPY).read_bytes()
    import sys
    sys.path.insert(0,str(repo/'tools'))
    import prepare_simulation_observation_wrapper as original_tool
    assert original_tool.inverse(observer.decode())==original_tool.original(repo)
    # A manifest universe pins the exact L0 source selections; no old tools executed.
    inputs.pop(original_tool.ORIGINAL)
    derivative=l0_derivative(observer.decode())
    assert inverse_l0(derivative)==observer.decode()
    assert original_tool.inverse(inverse_l0(derivative))==original_tool.original(repo)
    (repo/L0_COPY).write_text(derivative)
    inputs[L0_COPY]=derivative
    l0=closure(inputs,'ot_v41_rt_die_sim_observe_l0')
    l20_paths=blob(repo,L20_LIST).decode().split()
    ck_inputs={p:blob(repo,p).decode() for p in l20_paths if p.endswith(('.sv','.v','.svh')) and p!='rtl/test/v41_runtime/ot_v41_rt_die_l20.sv'}
    ck_inputs['rtl/hdc/v41/ot_hdc_isa_v41_profiles.svh']=blob(repo,'rtl/hdc/v41/ot_hdc_isa_v41_profiles.svh').decode()
    ck_inputs[COPY]=observer.decode()
    ckv=closure(ck_inputs,'ot_v41_rt_die_sim_observe')
    def cost(c, universe):
        paths=set(c['files']+c['support_files'])
        return dict(text_files=len(paths),source_bytes=sum(len(universe[p].encode()) for p in paths),modules=len(c['modules']),instances_text=len(c['edges']),minimum_elaborated_instances='UNAVAILABLE_BEFORE_COMPILER',frontend_rss_seconds='UNMEASURED; source bytes are not a memory/time predictor')
    service_roots={root:closure(ck_inputs,root) for root in ['ot_chip_v41x_window_attn_source','ot_chip_v41x_ckv_die_service']}
    base=dict(RANK=0,K_MEM=1<<24,ROM_R=128,ROM_PHW=6,ROM_SAW=16,ROM_BST=17,SUN=256,SUM=64,CL_LANES=16,CL_DEPTH=512,CL_RELAY=0,SIM_OBS_ENABLE=1,SIM_OBS_CKV_SELECTED=0)
    # Command specification only. No subprocess call to this executable exists.
    flags=['--lint-only','--top-module','ot_v41_rt_die_sim_observe','-fno-gate','-DV41_ATT_CUT','-I@SOURCE_ROOT@/rtl/hdc/v41','-Wno-fatal','-Wno-TIMESCALEMOD']
    modes=[]
    for name,c,universe,ck in [('WINDOW_actual_L0',l0,inputs,0),('CKV_source_available',ckv,ck_inputs,1)]:
        params=dict(base,SIM_OBS_CKV_SELECTED=ck)
        files=sorted(set(c['files']+c['support_files']))
        root=c['root']
        mode_flags=list(flags);mode_flags[mode_flags.index('ot_v41_rt_die_sim_observe')]=root
        compile_files=sorted(p for p in c['support_files'] if p.endswith(('.sv','.v'))) + sorted(p for p in c['files'] if p not in c['support_files'])
        filelist_name=name+'.f'
        (out/filelist_name).write_text('\n'.join(compile_files)+'\n')
        modes.append(dict(name=name,filelist=filelist_name,compile_files=compile_files,closure=c,cost=cost(c,universe),source_sha256={p:sha(universe[p].encode()) for p in files},parameters=params,command_spec=['@PINNED_VERILATOR_5_050@',*mode_flags,*[f'-G{k}={v}' for k,v in params.items()],'-f','@PLAN_EVIDENCE@/'+filelist_name],defines_scope='V41_ATT_CUT matches die frontend; FAST1/PP1/CUT379/LAT8 apply separate field models, not new field source compilation here',status='NOT_EXECUTED',branch_params=dict(FULL_SHAPE=1,WINDOW_HBM_ATTENTION=1,WINDOW_REFILL_CREDITS=1,WIN_STACK=0,WINDOW_STREAM_II1=0,WINDOW_RETAIN_L0=0,CKV_NSLOT=64,CLK_PS=1000)))
    l0txt=inputs[L0_PARENT]; cktxt=ck_inputs[CKV_PARENT]
    assert 'parameter bit CKV_SELECTED' not in l0txt
    assert 'parameter bit CKV_SELECTED = 0' in cktxt
    receipt=dict(verdict='STATIC_BINDING_BLOCKER_NOT_COMPILER_VERDICT',source_commit=SOURCE,source_excerpt=[line for line in observer.decode().splitlines() if '.WINDOW_HBM_ATTENTION(1)' in line],l0_parameter_names=re.findall(r'parameter\s+(?:integer|bit)\s+(\w+)',l0txt),observer_commit='2c867b19139de1086b522cb15213dec80435af33',observer_sha256=sha(observer),actual_parent=L0_PARENT,actual_parent_sha256=sha(l0txt.encode()),separate_ckv_parent=CKV_PARENT,separate_ckv_parent_sha256=sha(cktxt.encode()),trigger='.CKV_SELECTED(SIM_OBS_CKV_SELECTED) is supplied unconditionally by copied wrapper',reason='actual L0 parent has no CKV_SELECTED formal, including at SIM_OBS_CKV_SELECTED0',old_copy_changed=False,compiler_run=False,additive_derivative=L0_COPY,additive_derivative_sha256=sha(derivative.encode()),additive_derivative_status='PREPARED_STATIC_ONLY_NOT_ELABORATED',proposed_future_correction='New L0-specific wrapper derivative omits only the unsupported CKV parameter actual; no existing file edits. Its inverse must recover original ot_v41_rt_die.sv exactly. Independently retain CKV derivative with real CKV parent; no L0/CKV source-list mixing.',limits='Does not retract fake packet tests; prevents treating them as actual-parent hierarchy closure. No historical record overwritten.')
    result=dict(status='SOURCE_PLAN_PENDING_PARENT_REVIEW_NO_COMPILER_EXECUTION',source_commit=SOURCE,intake_base='879c3a50359b7ed160dd4d1b6052ea8f13fecbf2',observer_commit=receipt['observer_commit'],observer_sha256=sha(observer),census_commit='9696a5b920013eaa176f8ffe9995bef54da5d50f',manifest_sha256=authority['manifest_sha256'],retained_manifest_authority_sha256=sha((out/'retained_manifest_authority.json').read_bytes()),manifest_entries=authority['source_count'],modes=modes,necessary_service_closures=service_roots,static_blocker=receipt,real_ancestor_chain=['ot_v41_rt_die_sim_observe.dut','dut.g_packed_kv','dut.g_packed_kv.g_window_hbm_attention','...u_source.u_window','...u_source.u_schedule','...g_ckv.u_ckv (CKV parent only)'],resource_budget=dict(memory_max_bytes=4*1024**3,cpu_affinity_count=2,compiler_instances_parallel=1,per_mode_wall_seconds=60,total_base_wall_seconds=120,mutant_wall_seconds_each=30,max_diagnostic_output_bytes=16*1024**2,build_kind='Verilator lint-only frontend; no --cc, --build, make, linking, simulator or generated getter attach',estimate='Guarded budget only, not measured feasibility. Stop on cap and retain failure; no parameter reduction or retries that relax cap.'),unresolved_scope='Text closure includes guard-error modules and absent inactive alternative implementations; these are not all unconditional missing dependencies. No branch pruning or stub is admitted here. Each must be resolved by reviewed parameter/define provenance or additional original source pins before a compiler verdict.',minimum_scope='Faithful wrapper root requires real die/tile/core and unrelated instantiated sibling source closure. Leaf-only or pruned/reconstructed ancestor shells cannot qualify copied observer hierarchy. Static lists are conservative branch supersets, not claimed mathematically minimum.',future_gate_verdict=['Review prepared NEW L0 derivative removing unsupported parameter actual; original observer remains byte-identical. Its CKV flag must remain zero; CKV mode uses the separate real parent and observer copy.','Use pinned exact source blobs in clean scratch namespace, never live source paths; verify each SHA before lint.','Lint both real-parent modes separately, preserving all parameters and existing clock/reset logic. Errors or unresolved/ambiguous definitions block execution.','No .svh compile inputs: pinned headers served only through include directory. Do not waive hierarchical reference/parameter/width errors. Retain all warnings, specifically CKV PINMISSING due original L0 wrapper transport omission; a hierarchy-only PASS does not admit CKV functionality.','After review, deliberate wrong real signal path and wrong parent parameter mutants must produce compiler rejection; separate logs, no prior receipt overwritten.','Disabled observer defaultoff exact-inverse check remains mandatory; no source-list or binary selected.','Lint success only closes name/type/elaboration prerequisites. Native cycle association, reset fences, causal bounds, CKV transport/producer bindings and hardware qualification remain separate gates.'],missing_prerequisites=['Parent source-plan review before any lint invocation.','Prepared new L0 derivative and conservative closure require review; no elaboration result yet.','CKV source availability is indexed-layer companion scope, not actual current L0 elaboration. Existing copy omits ag_tx_ready/ag_rx ports; no CKV traffic or current-live deadlock conclusion.','No finite causal service bound admitted; BOUND_MISSING.'])
    receipt_text=json.dumps(receipt,indent=2)+'\n'
    negative_path=out/'static_binding_negative_r2.json'
    if negative_path.exists():
        assert negative_path.read_text()==receipt_text, 'retain old negative; use new version for changed evidence'
    else: negative_path.write_text(receipt_text)
    (out/'plan.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--repo',default='.');args=ap.parse_args()
    p=plan(args.repo)
    print(json.dumps({'status':p['status'],'modes':[{k:m[k] for k in ('name','cost')} for m in p['modes']],'blocker':p['static_blocker']['reason']},indent=2))
