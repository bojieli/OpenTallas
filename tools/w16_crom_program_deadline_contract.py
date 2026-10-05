"""Bind Ram's existing 491PC ledger to actual ISA prerequisites and cycle providers.

No coefficient calendar is recomputed. Hardware model events may discharge these
constraints as a conditional scenario; CPU ordinal/walltime is never accepted.
"""
import argparse,gzip,hashlib,json,os,subprocess,tempfile
from pathlib import Path
from tools.w16_review_crom_control_join import ROOT,blob,require,load_tool

LEDGER_COMMIT='8eae3e907399f0791c2ad3e4293e9699305a0454'
LEDGER_PATH='results/quality/w16_engram_initializer_20261001/slot_PC_deadlines.json'
CAT_COMMIT='4580819043a4a0b2cbe78c700c771246affc91f0'
CAT_PREFIX='results/uarch/w11_crom_control_catalog_20261001/compiled_v2/'
PROGRAM_COMMIT='4080bb5fd'
PROGRAM_PREFIX='results/rtl/w17_connected_token_preparation_20261001/full40_crom_bound_templates_v2'
EXTRA_COSTS=('catalog_capture_page_select_delta','emit_local_register_arrival_delta',
             'actual_CDC_delta','shared_port_arbitration_delta','return_ACK_lease_delta')

def validate_events(contract,provider):
 require(provider.get('time_basis')=='hardware_model_3p6GHz_ticks','no CPU ordinal or walltime clock')
 require(provider.get('program_sha256')==contract['encoded_program_sha256'],'event program binding')
 require(provider.get('ledger_sha256')==contract['ledger_pin']['sha256'],'event ledger binding')
 require(provider.get('scope')=='CONDITIONAL_SOURCE_BOUND_MODEL','events do not qualify physical provider')
 require(provider.get('placement_basis')=='PINNED_FULLRANK45_BANK_LEDGER' and provider.get('relocation_source_pin') is None,
         'stage relocation needs new source-exact catalog and bank/packet/calendar rebind; no45bank transfer')
 require(type(provider.get('rank')) is int and 0<=provider['rank']<4,'exact consumer rank')
 require(type(provider.get('epoch')) is int and 0<=provider['epoch']<2**32,'exact generation')
 require(provider.get('cost_source_pins'),'model cost provenance required')
 for pin in provider['cost_source_pins']:
  _,actual=blob(pin['commit'],pin['path']);require(actual['sha256']==pin['sha256'],'model cost source')
 credit=provider.get('credits');require(credit in (2,4,128),'matched credit scenario')
 rows=contract['program'];events=provider.get('events',[])
 require(len(events)==len(rows),'all4778PC event coverage')
 retire={};previous_issue=0;previous_retire=0;previous_coefficient_lease=0;executed=0
 for row,event in zip(rows,events):
  pc=row['PC'];require(event.get('PC')==pc and event.get('instruction_sha256')==row['instruction_sha256'],'event PC/word identity')
  for name in ('issue_tick','retire_tick','operator_ticks'):
   require(type(event.get(name)) is int and event[name]>=0,'finite '+name)
  require(type(event.get('executed')) is bool and event.get('predicate_resolution_source'),'predicate/dynamic execution cause')
  issue=event['issue_tick'];finish=event['retire_tick']
  require(issue>=previous_issue and issue>=previous_retire,'serialized wholepoint, no free overlap')
  require(all(issue>=retire[d] for d in row['encoded_wait_predecessor_PCs']),'encoded wait retirement')
  require(finish>=issue+event['operator_ticks'],'operator completion')
  if event['executed'] and row['unit']!=0:
   require(event['operator_ticks']>0,'unknown operator cannot cost zero');executed+=1
  elif not event['executed']:
   require(event['operator_ticks']==0,'skipped instruction modeled work')
  if row.get('coefficient') and event['executed']:
   coefficient=row['coefficient'];base=coefficient['credit_scenarios'][str(credit)];e=event.get('coefficient',{})
   for name in ('service_release_tick','fill_valid_tick','reverse_credit_tick','emit_local_arrival_tick','lease_release_tick'):
    require(type(e.get(name)) is int and e[name]>=0,'finite coefficient '+name)
   deltas=e.get('critical_delta_ticks',{})
   require(set(deltas)==set(EXTRA_COSTS) and all(type(v) is int and v>=0 for v in deltas.values()),'all critical delta bounds required')
   require(e.get('runtime_context')==dict(rank=provider['rank'],image_sha256=contract['rank_bindings'][provider['rank']]['CROM_image_sha256'],
    layer=row['layer'],PC=pc,epoch=provider['epoch'],burst_count=coefficient['burst_count']),'coefficient live identity')
   require(e['service_release_tick']>=max(previous_retire,previous_coefficient_lease),'actual prerequisite/held prior lease')
   deadline=e['service_release_tick']+base['cold_fill_valid_and_reverse_credit_ticks']+sum(deltas.values())
   require(e['fill_valid_tick']>=deadline and e['reverse_credit_tick']>=deadline,'complete fill and returned credit deadline')
   require(e['emit_local_arrival_tick']>=max(e['fill_valid_tick'],e['reverse_credit_tick'])+coefficient['consumer_local_read_ticks'],'priced lane-local arrival')
   require(issue>=e['emit_local_arrival_tick'],'consumer cannot issue before coefficients arrive')
   require(e['lease_release_tick']>=finish,'lease held through actual last consumer use')
   previous_coefficient_lease=e['lease_release_tick']
  retire[pc]=finish;previous_issue=issue;previous_retire=finish
 return dict(verdict='PASS_CONDITIONAL_PROVIDER_CONSTRAINTS_NOT_PHYSICAL_ADMISSION',events=len(events),executed_operators=executed,
  full_program_end_tick=previous_retire,all_final_coefficient_leases_released_tick=max(previous_retire,previous_coefficient_lease),
  physical_admission=False,source_bound_scenario_only=True)

def build():
 raw,lp=blob(LEDGER_COMMIT,LEDGER_PATH);ledger=json.loads(raw)
 catraw,cp=blob(CAT_COMMIT,CAT_PREFIX+'catalog.json.gz');catalog=json.loads(gzip.decompress(catraw))
 auditraw,ap=blob(PROGRAM_COMMIT,PROGRAM_PREFIX+'.json');audit=json.loads(auditraw)
 isa_raw,ip=blob('d2c28c279','tools/hdc_isa_v41.py');isa=load_tool(isa_raw,'crom_deadline_pinned_ISA')
 pins=dict(ledger=lp,catalog=cp,encoded_audit=ap,ISA=ip);compressed={}
 def verify_pins(group):
  for name,item in group.items():
   if 'commit' in item and 'path' in item:
    _,actual=blob(item['commit'],item['path']);require(actual['sha256']==item['sha256'],'ledger input '+name);pins['ledger:'+name]=actual
   else:verify_pins(item)
 verify_pins(ledger['source_pins'])
 _,pins['ledger_tool']=blob(LEDGER_COMMIT,'tools/w17_crom_slot_deadlines.py')
 for rank in audit['ranks']:
  rr,rp=blob(PROGRAM_COMMIT,PROGRAM_PREFIX+f".rank{rank['rank']}.templates.bin.gz")
  data=gzip.decompress(rr);require(len(data)==4778*256 and hashlib.sha256(data).hexdigest()==rank['encoded_template_sha256'],'actual4778program identity')
  compressed[rank['rank']]=data;pins['rank'+str(rank['rank'])]=rp
 require(len(compressed)==4 and len(set(compressed.values()))==1,'rank equivalent ISA schedules')
 # Execute canonical guarded verifier on existing serialized controls, not a
 # new compiler run. No checkpoint payload is accessed.
 with tempfile.TemporaryDirectory(prefix='w16-crom-deadline-source-') as d:
  temp=Path(d)
  for name,commit in [('hdc_isa_v41.py','d2c28c279'),('w11_dsrom_crom_demand.py','7ed62357d'),('w11_dsrom_crom_control_catalog.py','04b75f90504cec9b3c6d2c1fa853df201506d40d')]:
   source,pin=blob(commit,'tools/'+name);pins[name]=pin;(temp/name).write_bytes(source)
  (temp/'catalog.json').write_bytes(gzip.decompress(catraw))
  for stem in ('request-controls','fill-controls'):
   source,pin=blob(CAT_COMMIT,CAT_PREFIX+stem+'.bin.gz');pins[stem]=pin;(temp/(stem+'.bin')).write_bytes(gzip.decompress(source))
  gitdir=subprocess.check_output(['git','rev-parse','--absolute-git-dir'],cwd=ROOT,text=True).strip()
  result=subprocess.run(['python3','-c','import sys,json,pathlib;sys.path.insert(0,sys.argv[1]);import w11_dsrom_crom_control_catalog as C;p=pathlib.Path(sys.argv[1]);print(C.verify_serialized(json.loads((p/"catalog.json").read_text()),(p/"request-controls.bin").read_bytes(),(p/"fill-controls.bin").read_bytes()))',d],cwd=ROOT,env=dict(os.environ,GIT_DIR=gitdir,GIT_WORK_TREE=str(ROOT)),check=True,capture_output=True,text=True)
  require(result.stdout.strip()=='549760','canonical549760 coefficient destination replay')
 require(len(catalog['commands'])==491,'canonical491PC coverage')
 commands={c['pc']:c for c in catalog['commands']};per_credit={c['credits']:{r['PC']:r for r in c['commands']} for c in ledger['candidates']}
 require(set(per_credit)=={2,4,128} and all(set(x)==set(commands) for x in per_credit.values()),'matched491PC credit coverage')
 layer_by_pc={};offset=0
 for stage in audit['ranks'][0]['stages']+[dict(layer='head',instruction_count=7)]:
  for pc in range(offset,offset+stage['instruction_count']):layer_by_pc[pc]=stage['layer']
  offset+=stage['instruction_count']
 require(offset==4778,'full40plushead boundaries')
 program=[];last_unit={};gamma=0
 for pc in range(4778):
  word=compressed[0][pc*256:(pc+1)*256];f=isa.decode(int.from_bytes(word,'little'),full_shape=True)
  deps=sorted({last_unit[u] for u in range(1,6) if f['wait']&(1<<(u-1)) and u in last_unit})
  row=dict(PC=pc,layer=layer_by_pc[pc],instruction_sha256=hashlib.sha256(word).hexdigest(),unit=f['unit'],pred=f['pred'],wait_mask=f['wait'],
   encoded_wait_predecessor_PCs=deps,serial_previous_PC=pc-1 if pc else None,
   required_provider='source-bound operator completion, predicate/dynamic resolution and resource/CDC/port waits',
   operator_fields={k:v for k,v in f.items() if v!=0},actual_issue_tick=None,actual_retire_tick=None)
  if f['unit']:last_unit[f['unit']]=pc
  if pc in commands:
   c=commands[pc];require((c['layer'],c['pred'])==(row['layer'],f['pred']),'catalog layer/predicate identity')
   scenarios={}
   for credit,cs in per_credit.items():
    cmd=cs[pc];require(cmd['layer']==row['layer'] and cmd['actual_program_absolute_release_tick'] is None,'existing partial calendar scope')
    require(cmd['selected_output_floor_fast_cycles']==(cmd['coefficient_reads']+15)//16,'16word selected port floor')
    scenarios[str(credit)]=dict(cold_fill_valid_and_reverse_credit_ticks=cmd['cache_visible_and_credit_return_tick']-cmd['service_release_tick'],
     selected16word_floor_fast_cycles=cmd['selected_output_floor_fast_cycles'],conditional_service_anchor_tick=cmd['service_release_tick'],
     bank_read_waves=cmd['bank_read_waves'],fill_packets=cmd['fill_packets'])
   isgamma=per_credit[2][pc]['source_gamma'];gamma+=int(isgamma)
   row['coefficient']=dict(operands=c['operands'],burst_count=len(c['bursts']),cold_gamma=isgamma,
    consumer_local_read_ticks=len(c['bursts'])*4,credit_scenarios=scenarios,
    burst_catalog=[dict(burst=b['burst'],coefficient_uses=b['coefficient_uses'],waves=b['waves']) for b in c['bursts']],
    runtime_identity_required=['rank','image_sha256','layer','PC','burst','operand_axis','epoch','valid_after_last_accepted_fill'],
    required_extra_cost_tick_fields=list(EXTRA_COSTS),
    issue_constraint='issue >= emit_local_arrival >= max(fill_valid,reverse_credit)+local_read; lease_release >= last consumer retirement',
    release_constraint='service_release >= previous actual PC retirement and previous coefficient lease release; all81gamma cold, no cross-layer reuse')
  program.append(row)
 require(gamma==81 and sum(c['coefficient_reads'] for c in ledger['candidates'][0]['commands'])==549760,'all cold gamma/read counts')
 return dict(schema='opentallas.w16.CROM-full-program-cycle-provider-contract.v1',source_pins=pins,ledger_pin=lp,
  encoded_program_sha256=hashlib.sha256(compressed[0]).hexdigest(),rank_bindings=catalog['rank_program_image_bindings'],program=program,
  program_PC_count=4778,coefficient_PC_count=491,cold_gamma_PC_count=81,canonical_serialized_destination_uses=549760,
  tick_basis='1/3.6GHz; streaming cycle3ticks, serial cycle4ticks. Hardware-model time only; never CPU ticks.',
  calendar_owner='Ram8eae existing finite ledger; capture/select/16word output and forward/reverse route assumptions retained, not repriced or promoted.',
  placement_basis='PINNED_FULLRANK45_BANK_LEDGER',
  stage_local_relocation_calendar_bound=False,
  stage_local_rebind_requirements=['Ram/Fermat immutable per41stage/rank source read-union and physical address map including all sharedconstant and L1/L14 references',
   'Relocated catalog/ISA operand-axis, predicate, burst and image identity replay without losing source references; L1 invalid source hole remains blocking',
   'Actual chosen bank/row/lane conflict schedule and fragmented masked16word packets; recompute capture/select/emit and both-direction credit calendar, no45bank latency transfer',
   'Pasteur chosen physical slots and Ram whole-phase shared-port/capture/CDC/operator/ACK deadlines'],
  canonical_generated_source_holes=[dict(PC=c['pc'],layer=c['layer'],operand=o) for c in catalog['commands'] for o in c['operands'] if o['kind']=='unbound_generated'],
  stage_union_or_bank_count_invented=False,
  slot_owner='Pasteur; existing SU+CROM slot REJECT retained, no accepted61macro placement',
  parallelism_policy='Conservative serialize actual PC retirements. Independent-unit or chase overlap requires a separate bounded hazard/port/calendar proof.',
  absolute_PC_deadlines_bound=False,hardware_admission=False,physical_admission=False,
  full_program_cycle_provider=None,headline_rate=None,jobs_launched=0,checkpoint_reads=0)

if __name__=='__main__':
 p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True);g.add_argument('--out',type=Path);g.add_argument('--check',type=Path);p.add_argument('--provider',type=Path);a=p.parse_args()
 r=build()
 if a.provider:r['provider_validation']=validate_events(r,json.loads(a.provider.read_text()))
 text=json.dumps(r,sort_keys=True,indent=2)+'\n'
 if a.check:
  raw=a.check.read_bytes();raw=gzip.decompress(raw) if a.check.suffix=='.gz' else raw
  require(raw==text.encode(),'contract receipt mismatch');print('PASS full4778PC source contract; absolute cycles require provider, admission BLOCKED')
 else:
  raw=gzip.compress(text.encode(),mtime=0) if a.out.suffix=='.gz' else text.encode()
  with a.out.open('xb') as f:f.write(raw)
