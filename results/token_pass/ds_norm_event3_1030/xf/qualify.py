import hashlib,json,re
from pathlib import Path
P=Path(__file__).resolve().parent;read=lambda p:json.loads(p.read_text())
base=(P/'base.log').read_text();negative=(P/'duplicate_sid.log').read_text();status=(P/'status.txt').read_text()
assert 'BASE_RC=0\nDUPLICATE_SID_RC=1\nGATE_PASS'in status
assert 'XFIN_SOURCE_PASS'in base and 'count=0 seen=0000 disagreement=0 faults=ffff mut=1'in negative
positive=read(P/'positive_scalar.json');native=read(P.parent/'norm_control.json');stage=read(P/'stage.json')
assert positive['actual_rstd']==positive['golden_rstd']=='40ca3c85'
assert (P/'eps_actual_config.hex').read_text().strip()==native['eps_fp32_bits']=='1e3ce508'
assert native['epsilon_source']==dict(path='compiler/models/deepseek-v4.1-flash/inference_config.json',sha256='2e84f45cf1dac8c7fcbb200e96667d4b913275690668ed496f24c7747207a809',key='norm_eps',value=1e-20)
for c in native['commands']:
 if c['kind']=='XFIN_GO':
  payload=int(native['templates'][c['template']]['payload186'],16);assert payload>>26==0x1e3ce508 and (payload>>16)&31==1
assert len(stage['selected_XF']['slices'])==16 and all(s['params']==dict(LA=6,LM=5,NS=16,NVL=5,SIW=7)for s in stage['selected_XF']['slices'])
traces=positive['actual16traces'];assert len(traces)==16 and {r['sid']for r in traces}==set(range(16))
result=dict(schema='opentallas.s81.current_native16XF_math_producer.v1',status='PASS_CURRENT_SELECTED_MATH_COMPONENT_ONLY',
 actual_rstd32='40ca3c85',independent_FP32_tree_scoreboard='40ca3c85',actual_rstd_traces=traces,
 component_output_cycle_range=[min(r['cycle']for r in traces),max(r['cycle']for r in traces)],
 component_input_epoch=stage['source_input_epoch'],component_ring=stage['ring_scope'],
 clock_ps=833,actual_selected_parameters=dict(NS=16,NVL=5,LM=5,LA=6,SIW=7),
 source_sha256=stage['source_sha256'],selected_source_top_sha256=stage['selected_XF']['source_top_sha256'],
 actual_partial_input_sha256=hashlib.sha256((P/'actual_partials80.hex').read_bytes()).hexdigest(),
 native_GO_config_epsilon_source=native['epsilon_source'],native_GO_payloads_checked=16,
 epsilon_wiring='actualXRT59a53960 lines490/496 decodebody[31:0],767/773 holdx_eps;actual16XF eps pins direct32bit wires fromXR,xfin has runtimeeps input not borrowed default',
 matched_duplicate_SID_control='sourceSID3duplicates4; count0/rstdmask0000/faultsffff',
 original_1000ps_SIW8_proof_reused=False,golden_rstd_used_as_input=False,
 global_GO_qualified=False,global_RSTD_dates_qualified=False,physical_START_qualified=False,full_stage=False,full_token=False)
(P/'receipt.json').write_text(json.dumps(result,indent=1)+'\n');print(result['status'],result['actual_rstd32'],result['component_output_cycle_range'],'duplicateSIDcaught')
