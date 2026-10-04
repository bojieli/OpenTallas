"""Cold-only source, log, literal-vector and event audit. No simulator execution."""
from pathlib import Path
import re,json,hashlib,struct,gzip
ROOT=Path(__file__).resolve().parent;JOB=Path('/home/ubuntu/hbm-c0-pc40-connected-8c3dfbf79-r2')
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
r=json.loads((JOB/'terminal.json').read_text());assert r['compile_RC']==r['runtime_RC']==0 and r['status']=='PASS_CONNECTED_SELECTED_EXACT'
assert not Path('/proc/3535058').exists() and not Path('/proc/3625066').exists()
assert sha(JOB/'gate.vvp')==r['binary_sha256']
source={}
for row in r['source_pins']:
 p=Path(row['path']);assert sha(p)==row['sha256'];source[row['path']]={'sha256':row['sha256'],'text':p.read_text()}
tb=next(v['text'] for k,v in source.items() if k.endswith('/tb.sv'))
vectors={}
for name in ('gate_vector','expected_max','expected_min'):
 m=re.search(name+r"=4096'h([0-9a-fA-F]+)",tb);assert m and len(m[1])==1024
 n=int(m[1],16);vectors[name]=[(n>>(32*i))&0xffffffff for i in range(128)]
def float_value(bits):return struct.unpack('!f',bits.to_bytes(4,'big'))[0]
max_mismatch=[];min_mismatch=[]
for lane,a in enumerate(vectors['gate_vector']):
 assert ((a>>23)&255)!=255
 negative=a^0x80000000;b=0xc2ae0000
 actual_max=negative if float_value(negative)>float_value(b) else b
 actual_min=actual_max if float_value(actual_max)<88.0 else 0x42b00000
 if actual_max!=vectors['expected_max'][lane]:max_mismatch.append(lane)
 if actual_min!=vectors['expected_min'][lane]:min_mismatch.append(lane)
assert not max_mismatch and not min_mismatch
log=(JOB/'runtime.log').read_text();assert 'CONNECTED_PC40_PASS' in log and 'production_caller_FALSE' in log
actors=[];events=[];cases=[];lastcycle=-1
for line in log.splitlines():
 if line.startswith('EVENT '):
  fields=dict(x.split('=',1) for x in line.split()[1:]);fields['cycle']=int(fields['cycle']);assert fields['cycle']>=lastcycle;lastcycle=fields['cycle'];events.append(fields)
  if fields['phase']=='accepted':actors.append({'accepted':fields,'events':[],'cases':[]})
  assert actors;actors[-1]['events'].append(fields)
 elif line.startswith('CASE_PASS '):
  name=line.split()[1];cases.append(name);actors[-1]['cases'].append(name)
assert len(events)==95 and len(actors)==7
expected_cases=['NONFINITE_REFUSAL','STALE_ACK','RUNTIME_RESET','WRONG_REVERSE','WRONG_DRAIN','MISSING_ALLCOPY'];assert cases==expected_cases
positive=actors[0]['events'];phases=[x['phase'] for x in positive]
assert phases==['accepted','RF_read','mirrored_write','common_ACK','mirrored_write','common_ACK','RF_read','mirrored_write','common_ACK','mirrored_write','common_ACK','RF_read','mirrored_write','common_ACK','visible','RF_read','FMIN_result_accept','W6_consumer','retire']
assert [int(x['slot']) for x in positive if x['phase']=='mirrored_write']==[17,18,17,18,19]
assert [(int(x['a']),int(x['b'])) for x in positive if x['phase']=='RF_read']==[(38,38),(17,18),(17,18),(19,19)]
ids=[x['identity'] for x in positive if 'identity' in x];assert len(set(ids))==1
assert positive[0]['nativeTag']==positive[-1]['nativeTag'] and positive[0]['nativeGen']==positive[-1]['nativeGen']
assert all(a['accepted']['enteringWorkspaceLive']=='0' and a['accepted']['scope']=='cold_exclusive_actor' for a in actors)
assert all(not any(x['phase']=='retire' for x in a['events']) for a in actors[1:6])
assert actors[-1]['cases']==['MISSING_ALLCOPY'] and actors[-1]['events'][-1]['phase']=='retire'
assert len([x for x in actors[1]['events'] if x['phase']=='mirrored_write'])==2
assert not any(x['phase'] in ('visible','FMIN_result_accept','retire') for x in actors[1]['events'])
assert 'module ot_sram_1r1w_128x256_m1_r2c2' in tb and 'reg[255:0]mem[0:127]' in tb
report={'status':'PASS_INDEPENDENT_SCOPED_TERMINAL_SOURCE_EVENT_LITERAL_AUDIT','source_commit':r['source_commit'],'compile_RC':r['compile_RC'],'runtime_RC':r['runtime_RC'],'terminal_launcher_and_runtime_absent':True,'compiled_sources_exact':9,'events':len(events),'accepted_cold_fixture_actors':len(actors),'negative_controls':cases,'independent_literal_vector_check':{'words_per_vector':128,'FMAX_bit_mismatches':max_mismatch,'FMIN_bit_mismatches':min_mismatch,'rule':'finite F32 NEG sign XOR, max(negative,-87), min(result,+88); equal chooses second source word','includes_signed_zero_and_subnormal':True,'actual_simulator_data_dump_independently_recompared':False,'exact_simulated_lane_values':'source-pinned bench fatal checks plus runtimeRC0; no raw lane dump exists'},'positive_actor':{'event_sequence':positive,'paired_RF_reads':4,'logical_RF_writes':5,'mirrored_write_bytes':5120,'bare_ACK_handshakes':5,'single_controller_identity':ids[0],'native64_tag_generation_retained':True,'accepted_to_retire_cycles':positive[-1]['cycle']-positive[0]['cycle'],'conditional_priced_bound_cycles':117,'measured_hardware_rate_qualified':False},'negative_actor_event_groups':actors[1:],'qualified_scope':'Directed finite PC40 literal RF/FMAX/ACK/W6/FMIN software simulation with cold exclusive solewriter and retained-debt negative controls','strict_limits':['Gate payload is frozen literal fixture data; not actual released-checkpoint payload','Physical ACK is bare/untyped. Printed identity is controller state, not returned ACK_ID','Native64 tag/generation and owner46 are synthetic opaque fixture namespace, not production program provenance','Reverse/drain authorities and allcopy witness are fixture-held; no full global production queues or actual installed CDC qualification','Cold POR between mutants clears independent fixtures; not permission to release accepted runtime production debt','RF service logic uses bench behavioral SRAM arrays, not placed/hardened macro or PnR verification','No raw simulator lane dump: independent bit check validates literal expected vectors; runtime exactness relies on source-pinned lane fatal checks','W2/HBM command movement, production workspace entering leases and calendar adoption not closed','No trained fulltoken/physical/SSFF/protected upset/rate qualification'],'production_payload_qualified':False,'ACK_ID_qualified':False,'fulltoken_qualified':False,'source_pins':{k:v['sha256'] for k,v in source.items()},'output_pins':{p.name:{'sha256':sha(p),'bytes':p.stat().st_size} for p in JOB.iterdir() if p.is_file()},'binary_retained_external':str(JOB/'gate.vvp'),'no_gate_or_numerical_execution':True}
(ROOT/'review.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
(ROOT/'compiled_source_archive.json.gz').write_bytes(gzip.compress(json.dumps(source,sort_keys=True,separators=(',',':')).encode(),mtime=0))
(ROOT/'events.json').write_text(json.dumps(events,indent=2,sort_keys=True)+'\n')
for name in ['terminal.json','compile.log','runtime.log']:(ROOT/name).write_bytes((JOB/name).read_bytes())
(ROOT/'artifact_manifest.json').write_text(json.dumps({'artifacts':{p.name:sha(p) for p in ROOT.iterdir() if p.is_file() and p.name!='artifact_manifest.json'},'source_commit':r['source_commit'],'compiled_source_pins':report['source_pins'],'binary_retained_external':report['binary_retained_external'],'binary_sha256':r['binary_sha256']},indent=2,sort_keys=True)+'\n')
print(json.dumps({k:report[k] for k in ['status','compiled_sources_exact','events','accepted_cold_fixture_actors','negative_controls']},indent=2))
