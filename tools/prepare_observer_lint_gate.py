#!/usr/bin/env python3
"""Prepare exact commands and provenance only. Never invokes the compiler."""
import hashlib,json,re,subprocess,sys
from pathlib import Path
import plan_observer_hierarchy_gate as old

OUT='results/rtl/observer_lint_runner_4e383_20261002'
CKV_COPY='rtl/test/v41_runtime/ot_v41_rt_die_l20_sim_observe.sv'
CKV_ORIGINAL='rtl/test/v41_runtime/ot_v41_rt_die_l20.sv'
TOOLROOT=Path('/home/ubuntu/.local/opentallas-tools/verilator-5.050')
EXTRA=['rtl/hdc/ot_hdc_prefix.sv','rtl/hdc/ot_hdc_fp32_mul_lat.sv','rtl/link/ot_fifo_sram_fwft.sv',
'physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v',
'physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v',
*['rtl/hdc/v41x/'+n+'.sv' for n in ['ot_hdc_v41x_idx_kstream_ring','ot_hdc_v41x_idx_quarter_join','ot_hdc_v41x_idx_ring_port','ot_hdc_v41x_idx_ring_ranges','ot_hdc_v41x_idx_ring_kwr']]]
GUARDS={'ot_hdc_fp32_mul_lat_CUTS_must_match_LAT','ot_hdc_fp32_add_lat_CUTS_must_match_LAT','ot_hdc_v41x_vec_LV_must_be_1_to_7','ot_hdc_v41x_vec_lane_ALAT_must_be_3_or_4_and_at_most_MLAT'}

def instances(body):
    # Required whitespace before instance name prevents enc32() -> enc3 + 2.
    return [(m.group(1),m.group(2)) for m in re.finditer(r'\b(ot_\w+)(?:\s*#\s*\(.*?\))?\s+(\w+)\s*\(',body,re.S)]

def closure(inputs,top):
    defs={};dup={}
    for p,t in inputs.items():
        for m,b in old.module_bodies(t).items():
            if m in defs:dup.setdefault(m,[defs[m][0]]).append(p)
            defs[m]=(p,b)
    reached=set();unknown=set();edges=[];todo=[top]
    while todo:
        m=todo.pop()
        if m in reached:continue
        if m not in defs:unknown.add(m);continue
        reached.add(m)
        for child,i in instances(defs[m][1]):
            edges.append(dict(parent=m,instance=i,module=child));todo.append(child)
    support=sorted(p for p,t in inputs.items() if p.endswith('.svh') or re.search(r'\bpackage\s+',old.clean(t)))
    return dict(files=sorted({defs[m][0] for m in reached}),support=support,ownership={m:defs[m][0] for m in sorted(reached)},edges=edges,unresolved=sorted(unknown),ambiguous=dup)

def ckv_derivative(original,observer):
    marker='\n// BEGIN SIM OBSERVER'
    body=observer[observer.index(marker):observer.index('// END SIM OBSERVER')+len('// END SIM OBSERVER')]
    # Original L20 selects CKV by default; observation off must remain usable.
    body=body.replace('  if (SIM_OBS_CKV_SELECTED && !SIM_OBS_ENABLE) $fatal(1, "CKV observation requires opt-in");\n','')
    header=observer[observer.index('    input wire [63:0] sim_obs_epoch'):observer.index('    input  wire              clk,')]
    text=original.replace('module ot_v41_rt_die_l20 #(', 'module ot_v41_rt_die_l20_sim_observe #(\n    parameter bit SIM_OBS_ENABLE = 0,')
    text=text.replace('    input  wire              clk,',header+'    input  wire              clk,')
    return text.replace('endmodule','\nlocalparam bit SIM_OBS_CKV_SELECTED = CKV_SELECTED != 0;'+body+'\nendmodule')

def inverse_ckv(text,observer):
    marker='\nlocalparam bit SIM_OBS_CKV_SELECTED = CKV_SELECTED != 0;'
    start=text.index(marker);end=text.index('// END SIM OBSERVER')+len('// END SIM OBSERVER')
    text=text[:start]+text[end+1:]
    header=observer[observer.index('    input wire [63:0] sim_obs_epoch'):observer.index('    input  wire              clk,')]
    return text.replace(header,'').replace('module ot_v41_rt_die_l20_sim_observe #(\n    parameter bit SIM_OBS_ENABLE = 0,','module ot_v41_rt_die_l20 #(')

def proof(repo,path,anchors):
    data=old.blob(repo,path);text=data.decode();lines=text.splitlines();selected=[]
    for anchor in anchors:
        matches=[dict(line=i+1,text=l) for i,l in enumerate(lines) if anchor in l]
        if not matches:raise ValueError('missing provenance '+path+' '+anchor)
        selected.extend(matches)
    return dict(path=path,sha256=old.sha(data),excerpts=selected)

def prepare(repo):
    repo=Path(repo);out=repo/OUT
    observer=(repo/old.COPY).read_text();original=old.blob(repo,CKV_ORIGINAL).decode()
    ckv=ckv_derivative(original,observer);assert inverse_ckv(ckv,observer)==original
    (repo/CKV_COPY).write_text(ckv)
    previous=json.loads((repo/old.OUT/'plan.json').read_text())
    toolfiles=[TOOLROOT/'bin/verilator_bin',TOOLROOT/'bin/verilator',TOOLROOT/'share/verilator/include/verilated_config.h',TOOLROOT/'share/verilator/verilator-config-version.cmake']
    toolpins={str(p):old.sha(p.read_bytes()) for p in toolfiles}
    version=re.search(r'#define VERILATOR_VERSION "([^"]+)"',toolfiles[2].read_text()).group(1)
    assert version=='5.050 2026-07-01'
    provenance=[proof(repo,'tools/w17_current_fastpp_die_rt.py',['CL = dict','-GX_IDX=2','-fno-gate']),
        proof(repo,'rtl/w17_runtime/hdc/v41x/fastpp_pc21/l0/ot_hdc_core_v41x.sv',['SULV  = 7','.LV(SULV)']),
        proof(repo,'rtl/w17_runtime/hdc/v41x/fastpp_pc21/l20/ot_hdc_core_v41x.sv',['SULV  = 7','.LV(SULV)']),
        proof(repo,'rtl/hdc/v41x/ot_hdc_v41x_su_adapt.sv',['MLAT = 3','ALAT = 3','.LV(LV)','.MLAT(MLAT)']),
        proof(repo,'rtl/hdc/v41x/ot_hdc_v41x_vec.sv',['LV < 1 || LV > 7','.MLAT(MLAT)']),
        proof(repo,'rtl/hdc/v41x/ot_hdc_v41x_vec_lane.sv',['ALAT > MLAT || ALAT < 3 || ALAT > 4']),
        proof(repo,'rtl/hdc/ot_hdc_fp32_add_lat.sv',['parameter integer CUTS = -1','CUT_A + CUT_B + CUT_C + CUT_D + 3 != LAT','.LAT(4), .CUTS(1)']),
        proof(repo,'rtl/hdc/ot_hdc_fp32_mul_lat.sv',['parameter integer CUTS = -1','CUT1 + CUT2 + CUT3 + CUT4 + 3 != LAT','.LAT(5), .CUTS(5)']),
        proof(repo,CKV_ORIGINAL,['parameter integer CKV_SELECTED = 1','.X_IDX(X_IDX)','.CKV_SELECTED(CKV_SELECTED != 0)'])]
    # All guard modules retain real source branches; only their documented
    # unreachable parameter predicates are exempt from textual missing-name list.
    guardproof={
        'ot_hdc_fp32_mul_lat_CUTS_must_match_LAT':dict(predicate='CUTS>=0 && popcount(CUTS&15)+3 != LAT',instances='lat5i LAT5 CUTS5 -> 2+3=5; lat4/5/6/7 and parametric qmul_lat use default CUTS-1',false=True),
        'ot_hdc_v41x_vec_LV_must_be_1_to_7':dict(predicate='LV<1 || LV>7',value=7,false=True,chain='driver full SUN256 -> core SULV default7 -> u_su LV(SULV) -> u_vec LV(LV); neither real wrapper/tile overrides SULV'),
        'ot_hdc_v41x_vec_lane_ALAT_must_be_3_or_4_and_at_most_MLAT':dict(predicate='ALAT>MLAT || ALAT<3 || ALAT>4',ALAT=3,MLAT=3,false=True,chain='real u_su omits ALAT/MLAT, adapt defaults3 -> vec/lane pass through'),
        'ot_hdc_fp32_add_lat_CUTS_must_match_LAT':dict(predicate='CUTS>=0 && popcount(CUTS&15)+3 != LAT',instances='fixed wrappers: lat4i LAT4 CUTS1 -> 1+3=4; all other lat3/4/5/6/7 wrappers CUTS default-1',false=True)}
    modes=[]
    for prior in previous['modes']:
        isckv=prior['name']=='CKV_source_available'
        inputs={p:old.blob(repo,p).decode() for p in prior['source_sha256'] if p not in (old.COPY,old.L0_COPY)}
        for p in EXTRA:inputs[p]=old.blob(repo,p).decode()
        copy=CKV_COPY if isckv else old.L0_COPY;inputs[copy]=(repo/copy).read_text()
        top='ot_v41_rt_die_l20_sim_observe' if isckv else 'ot_v41_rt_die_sim_observe_l0'
        c=closure(inputs,top)
        missing=set(c['unresolved'])-GUARDS
        if missing or c['ambiguous']:raise ValueError('unresolved ownership '+str(missing)+str(c['ambiguous']))
        params=dict(prior['parameters']);params.pop('SIM_OBS_CKV_SELECTED')
        if isckv:params.update(CKV_SELECTED=1,X_IDX=2,X_SEL=1,IDX_RING=1)
        else:params['SIM_OBS_CKV_SELECTED']=0
        compilefiles=[p for p in c['support'] if not p.endswith('.svh')]+[p for p in c['files'] if p not in c['support']]
        pins={p:old.sha(inputs[p].encode()) for p in sorted(set(c['files']+c['support']))}
        # Literal relative paths resolve only in a fresh runner-materialized root.
        argv=[str(TOOLROOT/'bin/verilator_bin'),'--lint-only','--top-module',top,'-fno-gate','-DV41_ATT_CUT','-Irtl/hdc/v41','-Wno-fatal','-Wno-TIMESCALEMOD',*[f'-G{k}={v}' for k,v in params.items()],*compilefiles]
        mutants=[dict(name='wrong_signal_path',timeout_seconds=30,find='dut.step_user',replace='dut.observer_missing_step_user',expected_diagnostic='observer_missing_step_user'),dict(name='wrong_parameter',timeout_seconds=30,find='.FULL_SHAPE(1)',replace='.OBSERVER_NO_SUCH_PARAMETER(1)',expected_diagnostic='OBSERVER_NO_SUCH_PARAMETER')]
        for mutation in mutants:assert mutation['find'] in inputs[copy]
        modes.append(dict(name=prior['name'],top=top,copy=copy,parameters=params,argv=argv,source_sha256=pins,closure=c,guard_resolution=guardproof,mutants=mutants,source_bytes=sum(len(inputs[p].encode()) for p in pins),status='PREPARED_NO_COMPILER_EXECUTION'))
    result=dict(preparation_tools={path:old.sha((repo/path).read_bytes()) for path in ['tools/prepare_observer_lint_gate.py','tools/run_observer_capped_lint.py','tools/verify_observer_lint_caps.py']},source_commit=old.SOURCE,base_commit='d330b000b57c49f89f77a5672e15ac5fddafafd6',status='STATIC_OWNERSHIP_RESOLVED_AWAIT_PARENT_GO',tool=dict(executable=str(toolfiles[0]),pins=toolpins,metadata_version=version,version_command=[str(toolfiles[0]),'--version'],version_executed=False,environment=dict(VERILATOR_ROOT=str(TOOLROOT/'share/verilator')),options='direct compiler binary, lint-only, exact V41_ATT_CUT and full wrapper params; no bbox, stubs, ancestor pruning, timing relaxation or warning class globally hidden'),modes=modes,parameter_provenance=provenance,guard_resolution_limits='Source proof for named guard predicates; real compiler retains branches and must reject any actually reachable trap. Other inactive alternatives receive original source definitions, not stubs. No actual hook elaboration PASS yet.',scan_correction='Old function enc32 was falsely split into module enc3+instance2 by permissive regex; new scanner requires whitespace before instance identifier. Old record preserved.',caps=dict(memory_bytes=4*1024**3,cpu_count=2,mode_wall_seconds=60,mutant_wall_seconds=30,version_wall_seconds=5,log_bytes=16*1024**2,max_children=1,serial=True,total_compiler_wall_budget_seconds=245),ckv_scope='source-pinned L20 driver configuration now uses existing original CKV transport ports, but no host traffic, getter, service or causal association qualification',limits=['No compiler has run. GO authorization must match complete plan hash and owner review.','No live paths/source lists selected or altered; source blobs materialized only in new scratch directory by authorized runner.','No full model generation, C++ compilation, simulator, payload/checkpoint reads, engine/primitives or hardware admission.','Default observation off; L0 inverse and CKV inverse recover originals exactly.','BOUND_MISSING and native temporal/fence qualification remain.'])
    (out/'plan.json').write_text(json.dumps(result,indent=2)+'\n')
    digest=old.sha((out/'plan.json').read_bytes())
    template=dict(plan_sha256=digest,decision='PENDING',reviewer='',source_ownership_and_guard_provenance_reviewed=False,resource_caps_reviewed=False,lint_only_no_live_selection=True)
    (out/'GO.template.json').write_text(json.dumps(template,indent=2)+'\n')
    return result
if __name__=='__main__':
    ap=__import__('argparse').ArgumentParser();ap.add_argument('--repo',default='.');a=ap.parse_args();p=prepare(a.repo)
    print(json.dumps(dict(status=p['status'],version=p['tool']['metadata_version'],modes=[dict(name=m['name'],files=len(m['source_sha256']),bytes=m['source_bytes'],unresolved=m['closure']['unresolved'],ambiguous=m['closure']['ambiguous']) for m in p['modes']]),indent=2))
