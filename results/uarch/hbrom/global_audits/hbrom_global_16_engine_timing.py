from pathlib import Path
import json,sys,math,hashlib,collections
ROOT=Path('/home/ubuntu/OpenTallas-hbrom-cluster-20261005');sys.path.insert(0,str(ROOT/'tools'))
import w19_hbm_token_compose as W
paths=['results/rtl/dshbm_baseline_measured_20261004/program.json','results/rtl/w19_sm_real_ops.json','results/rtl/dshbm_baseline_measured_20261004/sm_real_ops.json','results/rtl/dshbm_baseline_measured_20261004/measured.json','tools/w19_hbm_token_compose.py','tools/dshbm_baseline_measure.py','tools/w19_sm_real_ops.py','rtl/gpu/ot_gpu_issue.sv']
prog=json.loads((ROOT/paths[0]).read_text());sm=W.SMTable([json.loads((ROOT/p).read_text())for p in paths[1:3]],'ar');meas=json.loads((ROOT/paths[3]).read_text())
FMT={'fp4':'v41_fp4','fp8':'v41_fp8','bf16':'v41_bf16'}
def shape(op,n,mode):
 nr=max(b-a for a,b in op['rows']);R=math.ceil(nr/n);fmt=FMT[op['fmt']];key=(fmt,op['k'],R);lines,drain,status=sm.op(op['fmt'],op['k'],R)
 G=math.ceil(math.ceil(op['k']/(8 if op['fmt']=='bf16' else 256))/{'bf16':64,'fp4':8,'fp8':4}[op['fmt']]);true_records=R*G*8
 same=[v for (f,k,r),v in sm.rows.items()if f==fmt and k==op['k']]
 startup=sm.rows[key]['start_to_done']-lines-drain if key in sm.rows else 0
 if mode=='exact_records_sameK_drain' and key not in sm.rows:
  lines=true_records;drain=max(v['drain']for v in same) if same else drain;status='analytic_records_and_transferred_drain'
 return dict(layer=op['layer'],tag=op['tag'],fmt=op['fmt'],K=op['k'],rank_max_rows=nr,sm_rows=R,groups=G,lines=lines,exact_records=true_records,drain=drain,observed_startup=startup,shape_status=status,active_engines_upper_bound=sum(min(n,b-a)for a,b in op['rows']))
def run(n,mode):
 groups=[];details=[];pend=None
 def flush():
  nonlocal pend
  if pend:groups.append(pend)
  pend=None
 for lay in prog['layers']:
  for op in lay['ops']:
   if op['kind']=='mv':
    d=shape(op,n,mode);details.append(d);batch=op['tag'].startswith('expert slot')
    if pend and batch and pend['batch']:
     pend['cycles']+=d['lines'];pend['max_drain_seen']=max(pend['max_drain_seen'],d['drain']);pend['ops'].append(d)
    else:
     flush();pend=dict(layer=lay['layer'],batch=batch,cycles=d['lines']+d['drain'],charged_first_drain=d['drain'],max_drain_seen=d['drain'],ops=[d])
   elif op['kind']=='local' and op['fn']=='swiglu':continue
   else:flush()
  flush()
 byfmt=collections.defaultdict(float)
 for d in details:byfmt[d['fmt']]+=d['lines']
 cyc=sum(g['cycles']for g in groups)
 return dict(engines_per_rank=n,mode=mode,sm_groups=len(groups),matrix_operations=len(details),cycles=cyc,matrix_service_us=cyc/1200,lines_by_format=dict(byfmt),drain_charged_cycles=sum(g['charged_first_drain']for g in groups),native_batching_max_drain_ignored_groups=sum(g['max_drain_seen']!=g['charged_first_drain']for g in groups),shape_status_counts=dict(collections.Counter(d['shape_status']for d in details)),groups=groups)
r32=run(32,'native_table');r16=run(16,'native_table');a32=run(32,'exact_records_sameK_drain');a16=run(16,'exact_records_sameK_drain')
ref=meas['published']['parts_us_1p2GHz'];delta=r16['matrix_service_us']-r32['matrix_service_us'];totalref=sum(ref.values())
record={'schema':'hbrom.global16.engine_timing.v1','scope':'Analytical W19 matrix composition only; no RTL simulation/build. Same96rankrows and32vs16 independent NC1 engines/rank, full private RF perengine retained, no shared-service benefit.','source_pins':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()for p in paths},'native32_replay':{'calculated_matrix_us':r32['matrix_service_us'],'committed_matrix_us':ref['sm'],'difference_us':r32['matrix_service_us']-ref['sm'],'committed_parts_us':ref,'program_variant':prog['variant']},'native16':{'matrix_service_us':r16['matrix_service_us'],'delta_vs_native32_us':delta,'flush_groups':r16['sm_groups'],'full_private_RF':True},'record_count_alternative':{'32_matrix_us':a32['matrix_service_us'],'16_matrix_us':a16['matrix_service_us'],'delta_us':a16['matrix_service_us']-a32['matrix_service_us'],'basis':'Known shapes preserved. Unknown shape lines exact R*golden_groups*8; drain max existing same-format/K shape, else native median. Not measured16engine cycles.'},'native_reference_only_full_sum':{'32_us':totalref,'16_us_if_all_other_terms_fixed':totalref+delta,'reference_ROM_us':725.057,'scope':'Historical conditional HBM target-clock accounting with unchanged reference nonmatrixterms; NOT a complete ROM-fed designTPOT. ROMbank capacity/feed/config/codec/fault service plus actual accelerator rungs/floorplan absent.'},'caveats':['Matrix default lines+drain omits measured start-to-done surplus; e.g FP4K5120R1 lines24+drain60 vs measured232. Do not call weightrecord count elapsed issue time.','Native missing shape uses maximum line-rate ratio across format and median drain; no measured16engine exactness/timing transferred by changingR.','Preserves composer expert batching literally: subsequent expert ops add only lines, max_drain tracked but not incorporated into cycles.','Matrix row ownership retained from program explicit96 ranges; withinrank balanced contiguous assumption and busiest ceil preserved.','343group schedule may hold while physical barrier endpoints fall32to16; reference barrier heldfixed, no benefit credited.','16 engine count changes full private compute/RF area, bandwidth andplacement; global ROMcapacity/service must be composed before comparison to725.057us.'],'scenarios':[r32,r16,a32,a16]}
Path('/tmp/hbrom-global-16-engine-timing.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items()if k not in ['source_pins','scenarios']},indent=2))
# Current accelerator component composition supersedes the older baseline total.
current_path='results/rtl/dshbm_1m_allmeasured_20261004/composition.json'
current=json.loads((ROOT/current_path).read_text())
record['source_pins'][current_path]=hashlib.sha256((ROOT/current_path).read_bytes()).hexdigest()
record['native32_replay']['current_committed_matrix_us']=current['AR_by_term']['sm']
record['native32_replay']['difference_vs_current_us']=r32['matrix_service_us']-current['AR_by_term']['sm']
ratio=1200/current['at_closing_clocks']['clocks']['sm']['mhz']
record['current_component_baseline_delta_application']={
 'source':current_path,'method':'Add native16-native32 analytical matrix delta; preserve every current nonmatrix term and existing32 rounding. No ROMservice removed or added yet.',
 'target':{'baseline_us':current['AR_us'],'baseline_sm_us':current['AR_by_term']['sm'],'new_sm_us':current['AR_by_term']['sm']+delta,'matrix_delta_us':delta,'total_us_before_ROM_service':current['AR_us']+delta,'remaining_margin_to_ROM725_057_us':725.057-current['AR_us']-delta},
 'component_clock_sensitivity':{'baseline_us':current['at_closing_clocks']['AR_us'],'baseline_sm_us':current['at_closing_clocks']['AR_by_term']['sm'],'new_sm_us':current['at_closing_clocks']['AR_by_term']['sm']+delta*ratio,'matrix_delta_us':delta*ratio,'total_us_before_ROM_service':current['at_closing_clocks']['AR_us']+delta*ratio,'remaining_margin_to_ROM725_057_us':725.057-current['at_closing_clocks']['AR_us']-delta*ratio,'frequency_mhz':current['at_closing_clocks']['clocks']['sm']['mhz']},
 'status':'EXTRAPOLATED_MATRIX_DELTA_ON_COMPONENT_BASELINE_NOT_ROM_TPOT_OR_SIGNOFF'}
record['native_reference_only_full_sum']['superseded']=True
record['native_reference_only_full_sum']['use']='Replay history only; do not use449.30 baseline for candidate screen.'
for scenario in record['scenarios']:
 byformat={}
 for g in scenario['groups']:
  for op in g['ops']:
   q=byformat.setdefault(op['fmt'],dict(operations=0,lines=0,unmeasured_operations=0))
   q['operations']+=1;q['lines']+=op['lines'];q['unmeasured_operations']+=(op['shape_status']!='measured')
 scenario['format_summary']=byformat
record['conservative_selection']='Use native136.415us rather than lower exact-record alternative for architecture screening, while explicitly marking extrapolated shapes. It is conservative relative to this alternative, NOT a proven bound on actual elapsed/starved compute.'
Path('/tmp/hbrom-global-16-engine-timing.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record['current_component_baseline_delta_application'],indent=2))
