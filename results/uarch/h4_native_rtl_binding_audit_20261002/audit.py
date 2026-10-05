#!/usr/bin/env python3
"""Replay H4 immutable-source audit; no simulation, builds or calendar generation."""
import ast, collections, concurrent.futures, gzip, hashlib, json, pathlib, subprocess
NATIVE='fd7220c1e55397dec90222e1f99a8bd95ae02e03'
H1='992c14a70f812028f9de5e46eb79d5688db9482b'
OUT=pathlib.Path(__file__).resolve().parent
pins={}
def blob(path,commit=NATIVE):
    return subprocess.check_output(['git','show',commit+':'+path])
def read(path,commit=NATIVE):
    b=blob(path,commit); pins[commit+':'+path]=hashlib.sha256(b).hexdigest()
    return json.loads(gzip.decompress(b) if path.endswith('.gz') else b)
def put(name,obj):
    b=(json.dumps(obj,indent=2,sort_keys=True)+'\n').encode()
    if name.endswith('.gz'):(OUT/name).write_bytes(gzip.compress(b,mtime=0))
    else:(OUT/name).write_bytes(b)
def source(path,commit=H1):
    b=blob(path,commit); h=hashlib.sha256(b).hexdigest();pins[commit+':'+path]=h
    text=b.decode();return {'commit':commit,'path':path,'sha256':h,'lines':len(text.splitlines())},text
QPATH='results/uarch/h3_qwen_complete_native_20261002/bounded_r2/Qwen_tiled.json.gz'
DPATH='results/uarch/h3_deepseek_complete_native_20261002/program_final.json.gz'
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    fq=pool.submit(read,QPATH);fd=pool.submit(read,DPATH);q,d=fq.result(),fd.result()
residence=read(d['residence_archive'])
dispatch=read('results/uarch/h3_deepseek_bounded_tiles_20261002/forward_dispatch_milestone.json.gz')
assert dispatch['coverage']['PCs']==2213 and len(dispatch['coverage']['families'])==30
counts=read('results/uarch/h3_deepseek_bounded_tiles_20261002/full_shape_family_counts.json')
read('results/uarch/native_software_parent_intake_20261002/deepseek_full_driver_review.json')
read('results/uarch/native_software_parent_intake_20261002/deepseek_bounded_native_review.json')
contract=read('results/uarch/h3_native_command_cost_contract_20261002/model.json')
model_pin,model=source('tools/uarch_model.py',NATIVE)
model_node=next(n.value for n in ast.parse(model).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SM_ELEM' for t in n.targets))
sm_model={ast.literal_eval(k):{w.arg:ast.literal_eval(w.value) for w in v.keywords} for k,v in zip(model_node.keys,model_node.values)}
paths=['rtl/test/hbm_rf_visibility/tb_connected_rf_visibility.sv','rtl/test/hbm_rf_visibility/ot_gpu_matrix_capture_audit.sv','rtl/gpu/ot_gpu_sm_q.sv','rtl/gpu/ot_gpu_sm_v.sv','rtl/gpu/ot_gpu_full_sm_service.sv','rtl/gpu/ot_gpu_rf_service.sv','rtl/gpu/ot_gpu_scratch_service.sv','rtl/gpu/ot_gpu_rf_visibility_fence.sv','rtl/gpu/ot_gpu_issue.sv','rtl/gpu/ot_gpu_tc_col.sv','rtl/gpu/ot_gpu_bd_col.sv']
rtl={};texts={}
for p in paths: rtl[p],texts[p]=source(p)
prepared={}
for p in ['results/uarch/hbm_qwen_cxx_r10_20261002/prepared_gate.json','results/uarch/hbm_qwen_runtime_r11_20261002/prepared_gate.json','results/uarch/hbm_runtime_calibration_r8_20261002/DS_prepared_gate.json']:
    prepared[p]=read(p,H1)
# Record the complete prepared compilation closure; compiled does not imply reachable.
compiled_closure={}
for gate in prepared.values():
    for path in gate['source_sha256']:
        if path.startswith('rtl/') and path not in compiled_closure:
            rec,txt=source(path);compiled_closure[path]=rec
            if path not in rtl:rtl[path]=rec;texts[path]=txt
checks=[]
for p,gate in prepared.items():
    for f,r in rtl.items():
        if f in gate['source_sha256']:
            checks.append({'prepared':p,'path':f,'match':r['sha256']==gate['source_sha256'][f]})
assert checks and all(c['match'] for c in checks),'H1 source differs from prepared RTL'

def loc(path,needle):
    return {'path':path,'line':next(i for i,l in enumerate(texts[path].splitlines(),1) if needle in l),'commit':H1,'sha256':rtl[path]['sha256']}
S='rtl/gpu/ot_gpu_full_sm_service.sv';B=paths[0]
bindings={
 'vector':{'module':'ot_gpu_full_sm_service','instance':'service','entry':'simd_valid/ready, simd_mul, simd_a/b/dst; simd_done/ready after mirrored RF ACK','source':loc(S,'input wire simd_valid'),'config':{'ENABLE':1,'lanes':128,'word_bits':32,'RF_vectors':512,'ALU_LAT':7},'implemented':['FADD','FMUL'],'H1_exercised':['FADD'],'unexercised':['FMUL'],'limitation':'H1 ties simd_mul=0. No native opcode decoder, predicate, lane mask or generic scalar broadcast.'},
 'RF':{'module':'ot_gpu_rf_service','instance':'service.g_enabled.u_rf','entry':'host_rd_valid/ready -> host_rsp_valid/ready; host_wr_valid/ready -> host_ack_valid/ready','source':loc(S,'ot_gpu_rf_service u_rf'),'config':{'logical_bytes':262144,'mirrors':2,'physical_bytes':524288,'read_ports':2,'write_ports':1,'vector_bits':4096,'address_bits':9},'limitation':'512*128*4=256KiB logical RF. Service serializes accepted SIMD transaction through write ACK; does not implement native version/home allocator.'},
 'scratch':{'module':'ot_gpu_scratch_service','instance':'service.g_enabled.u_scratch','entry':'scratch_valid/write/addr; scratch_done/ready','source':loc(S,'input wire scratch_valid'),'config':{'bytes':65536,'beat_bytes':64,'address_bits':10},'limitation':'One addressed beat transaction; no TAKE/SCATTER controller or native tensor view.'},
 'visibility':{'module':'ot_gpu_rf_visibility_fence','instance':'RF_fence','entry':'producer start/row completion, mirrored RF ACK, consumer accept','source':loc(B,'ot_gpu_rf_visibility_fence'),'config':{'ENABLE':1,'epoch_bits':8,'max_vectors':512},'limitation':'Matrix-to-RF visibility; not persistent KV publication, distributed version retirement or provider reverse-credit lifecycle.'},
 'capture':{'module':'ot_gpu_matrix_capture_audit','instance':'capture_fence','entry':'rv/rrow/rdata -> full 128-lane RF write -> ACK','source':loc(B,'ot_gpu_matrix_capture_audit'),'config':{'ENABLE':1,'RMAX':4096,'Qwen_NC':16,'DS_NC':8},'limitation':'Test/audit full-operation register capture; not hardened SRAM abstract or arbitrary version output adapter.'},
 'Qwen_matrix':{'module':'ot_gpu_sm_q','instance':'g_q.u_sm (generate branch; see source)','entry':'start,op_rows,op_c,op_g; d_* bulk copy, xw_* fragment; rv/rrow/rdata; arrive/release','source':loc(B,'ot_gpu_sm_q u_sm'),'config':{'SUB':4,'LS':32,'NC':16,'IL':8,'RMAX':4096,'LEV':5,'NXM':16,'MAX_OUT':512,'op_scale':0,'sw_en':0},'limitation':'INT8/BF16 matrix arithmetic exists; row-scale multiplier exists but H1 disables it. Host supplies fragments and synthetic weight response, not full native program/provider dispatch.'},
 'DS_matrix':{'module':'ot_gpu_sm_v','instance':'g_v.u_sm (generate branch; see source)','entry':'start,op_rows,op_c,op_g,op_gs,op_fmt; d_*,xw_*; rv/rrow/rdata; arrive/release','source':loc(B,'ot_gpu_sm_v u_sm'),'config':{'SUB':4,'LBS':2,'LSB':16,'NC':8,'IL':8,'RMAX':4096,'LEV':4,'XD':128,'MAX_OUT':512,'op_gs':0,'op_fmt':0},'limitation':'BF16 H1 path; FP4/FP8 and group-slot hardware exists but H1 does not exercise those configurations.'},
 'issue':{'module':'ot_gpu_issue','entry':'matrix row/group issue; barrier arrive/release','source':loc('rtl/gpu/ot_gpu_issue.sv','module ot_gpu_issue'),'limitation':'Matrix sequencer, not a1737/2213-PC native program or vector micro-op controller.'}}
# Derive branch labels from actual bench rather than assumed names.
import re
branches=re.findall(r'begin\s*:\s*(\w+)',texts[B])
for key in ('Qwen_matrix','DS_matrix'): bindings[key]['instance']='u_sm in QWEN-select generate branch; labels='+','.join(branches)
put('hardware_inventory.json',{'sources':rtl,'prepared_compilation_closure':compiled_closure,'compilation_note':'A source in a Verilator compile list may contain uninstantiated modules; presence is not a connected opcode endpoint. SRAM behavioral models are simulation substitutions, not timing qualification.','prepared_RTL_hash_checks':checks,'bindings':bindings,'unified_model':{'source':model_pin,'SM_ELEM':sm_model},'differences':['Qwen calendar shared beat128B versus H1 scratch64B: reprice command count; weight ingest128B is a distinct port.','DS model stack_levels3/group_slot true versus H1 RTL LEV4/op_gs0: source contract/config reconciliation required.','H1 is one SM service, not32SM/rank or2Qwen/96DS ranks.','Matrix capture is test storage; clocked functional evidence is not SS/FF closure.']})
work={
 'C0':{'priority':0,'work':'Native PC/micro-op dispatch and operand/version scoreboard','deliverable':'Source-pinned command decode for all PCs, loop/template calls, predicates, dynamic EID/index and rank/SM assignment; map declared versions to RF/scratch/spill; accept/completion/ACK/reverse-release distinction.','validation':'Replay all native PCs and source order; no host opcode results injected. Price fetch, issue, RF arbitration, broadcasts and32SM replication in unified model before RTL.'},
 'V1':{'priority':1,'work':'Missing vector integer/predicate/format datapaths','deliverable':'128-lane integer arithmetic, shifts/logic, I64 paired32-bit lanes, conversions, comparison/select and native pack/unpack/ldexp; register/mask wiring for constants, bitcasts and views.','validation':'Exact signedness, NaN/tie and rounding contracts per pinned CPU primitive; ADD/MUL reuse still needs opcode mapping and masking.'},
 'R1':{'priority':1,'work':'Ordered reductions and scalar result broadcast','deliverable':'General chunk8/adjacent-carry golden trees and padding, RSTD/head norm/softmax sums, argmax tie-break and top-k merge; arriving-stream reduction and scalar broadcast.','validation':'Bit-exact source trees, including source +0 leaves. Matrix stack/tree is not a generic reduction endpoint; model serial clock and broadcast latency.'},
 'S1':{'priority':1,'work':'Source-exact SFU chains','deliverable':'exp/reciprocal/rsqrt plus DS DIV/SQRT contracts, separately rounded Newton steps and source saturation; lane-local composed chains.','validation':'CPU golden approximate DIV is not IEEE division; Qwen reciprocal seed0x7ef311c7 and3Newton steps; RSTD FMUL(1/4096), not substitution by DIV. Existing RTL candidates require exact-contract proof.'},
 'M1':{'priority':1,'work':'Addressed vector movement and format boundaries','deliverable':'TAKE/SCATTER/transpose/slice/concat/reshape, typed index addressing, fragment pack/unpack, finite RF/scratch spill and64B physical scratch transactions.','validation':'Golden index order and I64 ABI; no implied zero-cost view, broadcast or gather. Reuse provider-owner interface rather than create competing providers.'},
 'T1':{'priority':1,'work':'Full-shape matrix descriptor and output adapter','deliverable':'Bind all native matrix/dot shapes, tiled long-K/row loops, compressed formats and Qwen row scales; real consumer rounding, fragment ingress and ACK output address/version; replace audit capture with model-priced macro storage.','validation':'Each shape/config and source reduction exact; test FP4/FP8/group-slot and enabled row scale separately; reconcile DS model/RTL configuration. Directed H1 matrix fixture alone is insufficient.'},
 'N1':{'priority':1,'work':'Distributed collectives and persistent state boundaries','deliverable':'2Qwen/96DS ranks,32SM each; all-reduce/all-gather/top-k rendezvous, version visibility, KV/state read-write-fence and exact-once retire/reverse grants.','validation':'Finite common-fabric credits, accept versus completion, selected expert identity and full-context leases; link existing provider-owner work, do not claim it from CPU PACKET_COMMIT.'},
 'G1':{'priority':2,'work':'Full connected token composition and physical qualification','deliverable':'Compose actual checkpoint/program/providers and all family implementations through hardware command paths; token verdict plus model latency and actual context SS setup/FF hold.','validation':'No host numerical replacement, no dead PCs or unbounded workspace; source-pinned complete token and stalls/reset/alias retirement; no SS/FF credit from10ns bench.'}}
put('remaining_work.json',{'scope':'H4 consumers/control/data paths, independent of current provider implementations; no engine/P&R performed','items':work})
integer={'AND','OR','XOR','SHL','SHR','IADD','ISUB','IMUL','IMOD','IOTA','I2F','F2I','FCMP_EQ','FCMP_NE','FCMP_LT','FCMP_GT','FMIN','FMAX','SELECT','FP8_PACK','FP8_UNPACK','LDEXP'}
move={'LOAD','STORE','TAKE','SCATTER','TRANSPOSE','SLICE','CONCAT','RESHAPE','BROADCAST','CONST','COPY','BITCAST_F','BITCAST_U'}
def gaps(f,ops,model):
    out={'C0','G1'}
    if f=='QKV_SPLIT':out.add('M1')
    if integer&ops:out.add('V1')
    if move&ops:out.add('M1')
    if {'DIV','SQRT'}&ops:out.add('S1')
    lo=f.lower()
    if any(x in lo for x in ('norm','rstd','sum','argmax','topk','hc_','scores','attend','route')):out.add('R1')
    if any(x in lo for x in ('exp','silu','swiglu','router_act','hc_','rstd','norm','normalize')):out.add('S1')
    if lo in {'matrix','mv','linear_bf16','linear_q','expert_fetch','wo_a_part','pv','scores','attend','index_scores','hc_mixes','engram_mix'}:out.add('T1')
    if any(x in lo for x in ('all_','kv_','fence','fetch','topk_merge')) or 'PACKET_COMMIT' in ops:out.add('N1')
    return sorted(out)
rows=[]
operand={x['version']:x for x in q['operands']}
for name,program in [('Qwen',q['operations']),('DeepSeek',d['instructions'])]:
    groups=collections.defaultdict(list)
    for op in program:groups[op.get('opcode',op.get('family'))].append(op)
    for family,ops in sorted(groups.items()):
        primitives=collections.Counter();pcbindings=[];shapes=set();templates=set()
        for op in ops:
            if name=='Qwen':
                commands=op['calendar_export']['physical_primitives']['native_primitive_commands'];primitives.update(commands)
                ports={}
                for side in ('reads','writes'):
                    ports[side]=[{'version':v,'shape':operand[v]['shape'],'elements_per_rank':operand[v]['elements_per_rank'],'home_partition':operand[v]['home_partition'],'exact_homes_ref':QPATH+'#/operands/version='+v} for v in op[side]]
                    shapes.update(json.dumps(x['shape']) for x in ports[side])
                pcbindings.append({'pc':op['pc'],'operands':ports,'attributes':op['attributes'],'loop_program':op['loop_program'],'native_primitive_commands':commands})
            else:
                ids=sorted({x['template'] for x in op['rank_bindings'] if 'template' in x}|{b['template'] for x in op['rank_bindings'] for b in x.get('buffer_programs',[])});templates.update(ids)
                parameters=[]
                for tid in ids:
                    t=d['templates'][tid];parameters.append({'template':tid,'shape_parameters':t['shape_parameters'],'source_attributes':t['source_attributes'],'primitive_shapes':sorted({json.dumps(x['shape']) for x in t['code']})})
                    primitives.update(x['op'] for x in t['code']);shapes.update(json.dumps(x['shape']) for x in t['code'])
                pcbindings.append({'pc':op['pc'],'bounded_dispatch_ref':'results/uarch/h3_deepseek_bounded_tiles_20261002/forward_dispatch_milestone.json.gz#/PC_dispatch/'+str(op['pc']),'template_bindings':parameters,'rank_template_map':[{'rank':x['rank'],'template':x.get('template'),'row_interval':x.get('row_interval'),'empty_owned_extent':x.get('empty_owned_extent',False),'buffer_programs':x.get('buffer_programs',[])} for x in op['rank_bindings']],'reads':[{'version':x['version'],'external':x.get('external')} for x in op['reads']],'writes':[{'version':x['version']} for x in op['writes']],'native_outer_loops':op['native_outer_loops'],'home_binding_archive':d['residence_archive'],'home_indices':{side:[{'version':x['version'],'home_index_count':len(x['home_indices']),'home_indices_sha256':hashlib.sha256(json.dumps(x['home_indices'],separators=(',',':')).encode()).hexdigest(),'exact_home_indices_ref':DPATH+'#/instructions/'+str(op['pc'])+'/'+side+'/'+str(j) } for j,x in enumerate(op[side])] for side in ('reads','writes')}})
        assert all(t in d['templates'] for t in templates)
        required=set(primitives)
        if name=='DeepSeek':required.update(counts['families'][family]['forward_primitive_scalars'])
        keys=['RF','scratch','visibility','issue','vector']
        if 'T1' in gaps(family,required,name):keys+=['capture',name+'_matrix' if name=='Qwen' else 'DS_matrix']
        rows.append({'model':name,'family':family,'PC_count':len(ops),'PCs':[x['pc'] for x in ops],'program_source':QPATH if name=='Qwen' else DPATH,'native_commit':NATIVE,'CPU_execution':{'entry':'TiledMachine.execute -> NativePrimitiveVM.primitive' if name=='Qwen' else 'execute_bound_ds_operation / bounded_tiles._primitive','source':'tools/h3_qwen_bounded_native.py' if name=='Qwen' else 'tools/h3_native_microop_adapter.py -> tools/h3_deepseek_bounded_tiles.py','evidence':'CPU/native primitive program; does not establish RTL opcode or connected-token capability'},'shape_set':[json.loads(x) for x in sorted(shapes)],'empty_primitive_reason':('visibility/retirement fence, requires hardware N1 control' if family=='KV_FENCE' else 'source view/version split, requires hardware C0/M1 address binding' if family=='QKV_SPLIT' else None),'required_primitives':sorted(required),'primitive_counts':dict(primitives),'primitive_count_units':'native128-lane command totals' if name=='Qwen' else 'template code occurrences summed per PC over unique rank templates; NOT runtime command counts','existing_Dewey_cost_counts':None if name=='Qwen' else counts['families'][family],'actual_H1_binding':{k:bindings[k] for k in keys},'H1_arithmetic_candidates':sorted(required&{'FADD','FMUL'}),'H1_unexposed_native_primitives':sorted(required-{'FADD','FMUL'}),'remaining_work':gaps(family,required,name),'connected_family_qualified':False,'PC_shape_config_binding':pcbindings})
put('family_bindings.json.gz',rows)
allops=sorted(set().union(*(set(r['required_primitives']) for r in rows)))
primitive=[]
for op in allops:
    primitive.append({'opcode':op,'families':[r['model']+':'+r['family'] for r in rows if op in r['required_primitives']],'H1_status':'exposed ADD path exercised by directed fixture' if op=='FADD' else 'exposed MUL path in source, tied off in H1' if op=='FMUL' else 'no corresponding native opcode entry in H1 command path','implementation_requirement':'C0' if op in {'FADD','FMUL'} else 'S1' if op in {'DIV','SQRT'} else 'M1' if op in move else 'N1' if op=='PACKET_COMMIT' else 'C0' if op=='ASSERT' else 'V1'})
put('primitive_capabilities.json',primitive)
# Pin existing candidate modules without claiming contract-compatible implementation.
candidates=[]
for p in ['rtl/hdc/v41x/ot_hdc_v41x_sfu.sv','rtl/hdc/v41/ot_hdc_fdiv.sv','rtl/abi3/ot_a3_fp32_div_rne_pipe.sv','rtl/abi3/ot_a3_fp32_sqrt_rne.sv','rtl/ot_fp32_rsqrt_rne.sv']:
    rec,_=source(p);rec.update(H1_reachable=False,contract_compatible='UNPROVEN; IEEE divider/sqrt is not automatic match for approximate native contract');candidates.append(rec)
put('candidate_RTL_elsewhere.json',candidates)
for p in ['tools/h3_qwen_bounded_native.py','tools/h3_deepseek_bounded_tiles.py','tools/h3_native_microop_adapter.py']:source(p,NATIVE)
calendar_paths=['results/uarch/h3_complete_native_calendar_20261002/final_ds_bed325f89/calendar_provider_interface.json','results/uarch/h3_complete_native_calendar_20261002/final_ds_bed325f89/calendar_r1/summary.json','results/uarch/h3_qwen_complete_native_20261002/bounded_r2/Qwen_serial_calendar.json.gz']
for p in calendar_paths:read(p)
put('Dewey_handoff.json',{'recipient':'Dewey existing native cost-calendar owner','status':'LOCAL_SOURCE_HANDOFF_NO_NEW_CALENDAR_NO_HARDWARE_ADMISSION','native_commit':NATIVE,'H1_commit':H1,'existing_calendars':calendar_paths,'family_join_key':['model','family','source_PC','program_sha256','template_id','ordered_native_steps'],'matrix_file':'family_bindings.json.gz','work_file':'remaining_work.json','required_cost_updates':['Native128B shared counts -> actual64B scratch transactions; retain distinct128B matrix ingest.','RF serialized full transaction through ACK, scalar broadcast and view/gather movement must have positive costs.','DS actualLEV4/op_gs0 versus model stack3/group-slot enabled: resolve configuration before latency admission.','Add missing vector integer/predicate/SFU/reduction/PC dispatch resource domains and source/model/measured cost labels.','Distributed accept vs completion, persistent KV/state ACK and reverse-grant retirement reuse existing provider bindings.'],'unknown_cost_policy':'positive provisional input required, never0; no measured/physical credit inferred','maximum_useful_parallelism':'Independent software ABI/shape checks for V1,R1,S1,M1,T1; single C0 version/command integration, Dewey owns one composed finite calendar; no engine builds.'})
validation={}
for name,expected,fc in [('Qwen',1737,21),('DeepSeek',2213,30)]:
    rr=[r for r in rows if r['model']==name];pcs=[p for r in rr for p in r['PCs']]
    assert len(rr)==fc and len(pcs)==expected and sorted(pcs)==list(range(expected))
    reference=q['coverage']['families'] if name=='Qwen' else dispatch['coverage']['families']
    assert {r['family']:r['PC_count'] for r in rr}==reference
    validation[name]={'PCs':len(pcs),'families':len(rr),'all_PCs_exactly_once':True,'all_PC_shapes_templates_bound':True}
assert all((r['required_primitives'] or r['family'] in {'KV_FENCE','QKV_SPLIT'}) and r['actual_H1_binding'] and r['remaining_work'] for r in rows)
validation.update(status='PASS_SOURCE_AUDIT_ONLY',total_families=51,total_PCs=3950,native_primitive_opcodes=len(allops),prepared_RTL_hash_checks=len(checks),all_prepared_RTL_hashes_match=True,connected_token_qualification=False,DS_bounded_dispatch_PCs=dispatch['coverage']['PCs'],new_jobs=0,new_engine_RTL=0,new_place_route=0)
put('validation.json',validation)
with (OUT/'family_summary.tsv').open('w') as f:
    f.write('model\tfamily\tPCs\tH1_arithmetic_candidates\tunexposed_native_ops\tremaining_work\tconnected_family_qualified\n')
    for r in rows:f.write('\t'.join([r['model'],r['family'],str(r['PC_count']),','.join(r['H1_arithmetic_candidates']),','.join(r['H1_unexposed_native_primitives']),','.join(r['remaining_work']),'false'])+'\n')
put('source_pins.json',pins)
print(json.dumps(validation,sort_keys=True))
