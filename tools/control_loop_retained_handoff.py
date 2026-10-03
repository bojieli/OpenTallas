#!/usr/bin/env python3
"""Offline terminal collection/calibration only; never launches or modifies a screen."""
import argparse,hashlib,json,math,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'results/uarch/control_loop_retained_handoff_20261003'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def finite(x):return type(x) in (int,float) and math.isfinite(x)

def phase(record, tag):
 d=record.get('phases',{}).get(tag,{})
 period=record['period_ns']*1000
 def timing(slack,path):
  if not finite(slack):return None
  required=period-slack
  if required<=0:raise ValueError('nonpositive required period')
  return {'setup_wns_ps':slack,'required_period_ps':required,'fmax_MHz':1e6/required,
          'startpoint':path.get('startpoint'),'endpoint':path.get('endpoint'),
          'largest_fanout':path.get('max_fanout_on_path'),'worst_cell':path.get('worst_cell'),
          'register_origin_named':bool(path.get('startpoint') and re.search(r'\$_S?DFF',path['startpoint'])),
          'explicit_loop_graph_proved':False}
 return {'r2r':timing(d.get('r2r_setup_wns_ps'),d.get('r2r_path',{})),
         'focused_endpoints':{n:timing(v.get('setup_wns_ps'),v.get('path',{}))
                              for n,v in d.get('focus',{}).items()},
         'FF_hold':None,'physical_signoff':False}

def screen(record,binding):
 if not finite(record.get('period_ns')) or record['period_ns']<=0:raise ValueError('invalid period')
 terminal_success=record.get('openroad_rc')==0 and bool(record.get('completed_at'))
 matched=bool(binding) and all(v.get('matched') is True for v in binding.values())
 repaired=phase(record,'rep')
 # Failure and absent terminal markers are not usable clock measurements.
 usable=terminal_success and repaired['r2r'] is not None
 return {'label':record['label'],'top':record['top'],'parameters':record.get('parameters',{}),
         'period_ns':record['period_ns'],'domain':record.get('domain'),
         'completed_at':record.get('completed_at'),'openroad_exit':record.get('openroad_rc'),
         'source_commit_reported':record.get('source_commit'),'retained_source_all_matched':matched,
         'source_bindings':binding,'blackboxes':record.get('blackboxes',[]),
         'raw':phase(record,'raw'),'placed':repaired,
         'status':'TERMINAL_SS_SCREEN' if usable else 'TERMINAL_EXECUTION_OR_MEASUREMENT_FAIL',
         'timing_usable':usable,'all_path_fmax_excluded':True,
         'scope':'SS placed/repaired preCTS/preRoute screen, TT-mapped; control-endpoint focus may include input-origin paths. Not actual product clock adoption; blackboxes/patches/stubs and current-program association need enrollment.',
         'route_before_small_miss_conclusion':usable and -150<repaired['r2r']['setup_wns_ps']<0,
         'functional_fix_or_cycle_cost_measured':False}

def routed(d):
 ss=d['setup_ss'];ff=d['hold_ff'];period=float(d['sdc'].split('-period ',1)[1].split()[0])
 if ss.get('errors') or ff.get('errors'):raise ValueError('STA execution errors')
 return {'period_ps':period,'SS_all_slack_ps':ss['worst_slack_ps'],
         'SS_register_to_register_slack_ps':ss['worst_reg_to_reg_slack_ps'],
         'FF_all_hold_slack_ps':ff['worst_slack_ps'],
         'reported_closes_signoff':d['closes_signoff'],
         'r2r_SS_sensitivity_fmax_MHz':1e6/(period-ss['worst_reg_to_reg_slack_ps']),
         'all_SS_sensitivity_fmax_MHz':1e6/(period-ss['worst_slack_ps']),
         'scope':'Retained exact routed variant only. Fmax from fixed-netlist slack is sensitivity, not closure at a new clock.',
         'physical_hashes':{k:ss[k] for k in ['odb_sha256','spef_sha256','sdc_sha256']}}

def ha6(cross):
 price=cross['latency']['model_charge']
 fast=1.2;slow=.9;conditional=1.091
 return {'status':'CONDITIONAL_PRICE_NOT_ADOPTION','reuse_commit':'27d86cfe4',
         'closed_FIFO_source_SHA256':cross['rtl_sha256'],
         'stale_minus75ps_repair_requested':False,'new_FIFO_or_PnR_job':False,
         'related_dividers':cross['clocking'],
         'current_successor_worst_destination_cycles':{'fast_to_slow':2,'slow_to_fast':2},
         'positive_accept_cost_ns':{'fast_to_slow':2/slow,'slow_to_fast':2/fast,
                                   'one_round_trip_sum':2/slow+2/fast},
         'retained_old_4_5_charge_ns':price['fast_to_slow_slow_cycles']/slow+price['slow_to_fast_fast_cycles']/fast,
         'replace_once_per_actual_round_trip_saving_ns':price['fast_to_slow_slow_cycles']/slow+price['slow_to_fast_fast_cycles']/fast-(2/slow+2/fast),
         'CDC_scope':'One word in flight, consumer ready, related /3 and /4 clocks. Backpressure/credit queueing/refresh add costs; actual HBM boundary multiplicity and overlap must be measured. No ROM token-rate transfer.',
         'LAT3':{'current_GHz':slow,'conditional_GHz':conditional,'current_dependent_add_ns':3/slow,
                 'conditional_dependent_add_ns':3/conditional,'conditional_period_ps':1000/conditional,
                 'saving_per_dependent_add_ns':3/slow-3/conditional,
                 'cycle_count_change':0,'whole_token_measured_gain':None},
         'assumed_study_serial_share_of_local':.75,
         'conditional_fraction_of_local_time_saved':.75*(1-slow/conditional),
         'higher_clock_CDC_reuse_qualified':False,
         'required_before_higher_clock':'Exact LAT3 serial units and real program gate; measured serial critical path/wire/CDC/credits/refresh; area and corridor; new related-clock/reset relation and loaded CDC setup/hold at higher clock; SS60/FF25; composed measured gain>=1%. Current /3:/4 FIFO closure is not that higher-clock evidence.',
         'measured_composed_rate':None,'ladder_published_as_result':False}

FIXES={
 'ot_gpu_issue':{'proposal':'Protected next-row/last lookahead flags; do not halve issue II', 'conditional_extra_edges':1,'charged_per':'operation','recurring_II_increase_selected':False},
 'ot_gpu_bulk_copy':{'proposal':'Registered next-slot-full lookahead or explicitly priced bank occupancy', 'conditional_extra_edges':1,'charged_per':'stream','recurring_II_increase_selected':False},
 'ot_rom_oneshot_die':{'proposal':'Registered FIFO head and precomputed push/pop flags', 'conditional_extra_edges':1,'charged_per':'collective fill','recurring_II_increase_selected':False},
 'ot_w15_rom_oneshot_die_px':{'proposal':'Registered FIFO head and precomputed push/pop flags', 'conditional_extra_edges':1,'charged_per':'collective fill','recurring_II_increase_selected':False},
 'ot_hdc_v41x_idx_kctl_ring':{'proposal':'Drain-head compare and next-run lookahead', 'conditional_extra_edges':1,'charged_per':'index scan burst','recurring_II_increase_selected':False},
 'ot_v41_rom_elem_q_w10':{'proposal':'Next-need precompute with one result per edge; naive two-cycle walker rejected', 'conditional_extra_edges':1,'charged_per':'ROM sweep','recurring_II_increase_selected':False},
 'ot_gpu_qwen_kv_lifecycle_controller':{'proposal':'Registered tag-match lookup over independent keys', 'conditional_extra_edges':1,'charged_per':'lease operation','recurring_II_increase_selected':False},
 'ot_v41_rom_adapt':{'proposal':'Stage stride multiply/key lookup, exact admitted-source variant required', 'conditional_extra_edges':[1,2],'charged_per':'operation setup','recurring_II_increase_selected':False},
 'protected_SECDED_control':{'proposal':'No unprotected control shadow selected; any registered protection split must preserve current fault/debt/quarantine semantics and exactness before measurement', 'conditional_extra_edges':None,'charged_per':'unpriced','recurring_II_increase_selected':False}}

def generate(base=EVIDENCE):
 retained=base/'retained';m=json.loads((retained/'capture_manifest.json').read_text())
 for name,v in m['files'].items():
  if sha(retained/name)!=v['SHA256']:raise ValueError('captured artifact hash mismatch '+name)
 screens={}
 for rel,b in sorted(m['source_bindings'].items()):screens[rel]=screen(json.loads((retained/rel).read_text()),b)
 routes={str(p.parent.name):routed(json.loads(p.read_text())) for p in sorted((retained/'routes').glob('*/corner_sta.json'))}
 worst={}
 for rel,d in screens.items():
  if not d['timing_usable'] or not d['retained_source_all_matched']:continue
  group=Path(rel).parts[1]
  for typ,candidate in [('all_internal_r2r',d['placed']['r2r'])]+[(f'focus:{n}',v) for n,v in d['placed']['focused_endpoints'].items()]:
   if candidate is None:continue
   name=group+'/'+('control_endpoint' if typ.startswith('focus:') else typ)
   if name not in worst or candidate['fmax_MHz']<worst[name]['timing']['fmax_MHz']:
    worst[name]={'record':rel,'type':typ,'timing':candidate,'design':d['top'],'actual_loop_graph_proof':False}
 cross=json.loads((base/'references/current_crossing_model.json').read_text())
 fifo={p.stem:routed(json.loads(p.read_text())) for p in (base/'references').glob('*_corner_sta.json')}
 return {'schema':'control-loop.retained-terminal-handoff.v1','capture_UTC':m['UTC'],
         'retained_source_commit':m['actual_retained_source_commit'],'requested_emitter_commit':'feffc134a',
         'retained_emitter_SHA256':sha(retained/'src/tools/risk_clock_loops_screen.py'),
         'feffc_emitter_SHA256':'7b49c8d3ecce277a535cbc06fc1670d7ba7743adbd8927154863d8ff38b435ef',
         'retained_emitter_matches_requested_commit':False,
         'emitter_scope':'Retained emitter and DS/HBM wrapper snapshots are archived; they include uncommitted screen adaptations. Engine record source closures are checked separately, no equivalence to the requested feffc emitter assumed.',
         'historical_image_digest_binding':'records use mutable tag; capture-time inspectID in manifest is not proof of historical image ID',
         'actual_terminal_records':len(screens),'execution_or_measurement_failures':sum(not d['timing_usable'] for d in screens.values()),
         'source_binding_gaps':[n for n,d in screens.items() if not d['retained_source_all_matched']],
         'screens':screens,'worst_retained_terminal_by_group':worst,'routed_Qwen_TP_variants':routes,
         'HA6':ha6(cross),'closed_related_FIFO_variants':fifo,
         'cycle_cost_fixes_MODEL_ONLY':FIXES,
         'cycle_price_rule':'For a +1 source-edge proposal, multiply actual admitted operation/stream/collective/lease count by its source-domain period; subtract overlap only from measured serial trace. Actual counts/composed gains are null here.',
         'gate_order':['EXACT','MEASURED_SERIAL_CRITICAL_PATH_WIRE_CDC_CREDITS_REFRESH','AREA_COMPOSED','ROUTED_CORRIDOR','SS60_FF25_IN_CONTEXT','MEASURED_COMPOSED_GAIN>=1%'],
         'no_new_screen_or_route':True,'all_ladder_rates_unvalidated_and_excluded':True,
         'whole_target_SSFF_or_rate_PASS':False,'remaining_live_screens':'retained/live_process_snapshot.txt',
         'scope':'Partial retained AG128 control-loop campaign, no relaunch. Terminal failures preserved. Group minima are block screens, not whole-design functional or clock qualification. No main/placement mutation.'}

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path);p.add_argument('--verify',action='store_true');a=p.parse_args();d=generate();b=json.dumps(d,sort_keys=True,indent=2)+'\n'
 if a.verify:
  if (EVIDENCE/'model.json').read_text()!=b:raise SystemExit('cold model mismatch')
  print('retained hashes and byte-exact cold model PASS')
 elif a.out:a.out.write_text(b)
 else:print(b,end='')
if __name__=='__main__':main()
