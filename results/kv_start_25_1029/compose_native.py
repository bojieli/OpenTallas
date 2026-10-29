#!/usr/bin/env python3
"""Compose one KV native-origin event, preserving qualified ECTL/LC/source pin deltas."""
import copy,json,os,sys
from pathlib import Path
R=Path(sys.argv[1]);sys.path.insert(0,str(R/'source'))
import count_align_bind as C,clock_landing_plan as L,schema as S,gen
old=Path('/srv/opentallas-scratch2/claude/codex-kv-1028');W=Path('/srv/opentallas-scratch2/claude/wt/codex-kv-ectl-1028')
p=json.load(open(R/'native6/native_plan.json'));cached=json.load(open(R/'inputs/ca_mixed_replan.json'));current=json.load(open(old/'event24/bind.json'))
extra={};T=833.;ap=T/8
for x in p['crossings']:
 d=current['ports'][x['port']]['sched_lat']-cached['ports'][x['port']]['sched_lat']
 assert d>=0
 if not d:continue
 lo=x['L_lo_ps']+d*T;hi=x['L_hi_ps']+d*T
 depth=next(n for n in [4,8,16] if hi <= (n-.5)*T-ap)
 for k in ['K_eff','K','lat_cycles','rx_lat_counts']:x[k]+=d
 x.update(L_lo_ps=lo,L_hi_ps=hi,depth=depth,margin_lo_ps=lo-.5*T,margin_hi_ps=(depth-.5)*T-hi)
 x['rtl'].update(K=x['K'],DEPTH=depth,GUARD_HI=depth);extra[x['port']]=d
b=C.bind(p,parts={pid:(v['src_part'],v['dst_part']) for pid,v in current['ports'].items()})
checks=C.verify(b,samples=32)
assert not checks['identity_and_loop_errors'] and checks['sim_window_violations']==0,checks
O=R/'event26';O.mkdir()
(O/'bind.json').write_text(json.dumps(b,indent=1));(O/'verify.json').write_text(json.dumps(checks,indent=1))
base=old/'event24w_current/base/plan.json';raw=json.load(open(base));I=W/'results/die_kv_7_1028/input';raw['die']['io']=json.load(open(I/'die_io.json'))
t=json.load(open(I/'l128_table.json'));P=S.Plan(raw)
t['regions']=[dict(k=k,tag=q,parts=[q],box_um=list(P.rect(q))) for k,q in enumerate(sorted(x['name'] for x in raw['partitions']))]
t['regions_count']=len(t['regions']);t['mode']='native_partition_origins'
for x in t['ports']:x['src_region'],x['dst_region']=x['src'],x['dst']
t=C.annotate_table(t,b,strap_form=True)
t['count_aligned']['start_reset_wave']=True
(O/'regions_ca.json').write_text(json.dumps(t,indent=1))
observer=dict(module='qkd_seq_core_static_s',instance_suffix='u_seq_u_core',fault_port='hf',ready_port='lp_run')
plan,side=L.compose(raw,t,plan_path=base,observer_part='hub_C',observer=observer,monitor='reset',band_reserve='live',forward_source='clk')
previous=json.load(open(R/'inputs/event/plan_sites_astk.json'))
# Preserve qualified LC bank modules and their exact pin documents; no stale source reintroduction.
oldcores={h['module']:h for typ in previous['partition_types'].values() for h in typ.get('hard_cores',[]) if h['module']=='kv3_pv_pair'}
lc=0
for typ in plan['partition_types'].values():
 for c in typ.get('contents',[]):
  if c['module']=='ot_qwen_tp8_pv_slice_t':c['module']='ot_qwen_tp8_pv_slice_lc_t';lc+=1
 for h in typ.get('hard_cores',[]):
  if h.get('pins_file') and not Path(h['pins_file']).is_absolute():h['pins_file']=str((base.parent/h['pins_file']).resolve())
  if h['module']=='kv3_pv_pair':
   mirrored='fMX' in h['pins_file'];f=W/'results/die_kv_23_1028/cores'/('kv3_pv_pair_pins_'+('fMX_' if mirrored else '')+'r26c_lc.json');assert f.exists(),f;h['pins_file']=str(f)
plan['note']=plan.get('note','')+' | KV25 candidate:160nativecounterclockorigins;1528legalSTARTproviderstages/ordinaryresetwave;350pointbudget/405rowrule;ECTL14cyclesretained;loadedclockproofpending'
(O/'plan.json').write_text(json.dumps(plan,indent=1));(O/'sidecar.json').write_text(json.dumps(side,indent=1));gen.write_latency(plan,O/'latency',O/'plan.json')
straps=C.strap_ties(side['count_aligned'],plan);(O/'straps.json').write_text(json.dumps(straps,indent=1))
summary=dict(types=len(plan['partition_types']),parts=len(plan['partitions']),core_lc_bank_modules=lc,ectl_equalisation_extra=extra,
 placements_failed=len(side.get('collector',{}).get('placement_failures',[])),straps=straps['summary'],max_origin_cycles=max(x['n_nominal'] for x in b['parts'].values()),
 data_sched_latency=sum(v['sched_lat'] for v in b['ports'].values()),clock_load_proof='NOT RUN',provider_synth='NOT RUN')
(O/'summary.json').write_text(json.dumps(summary,indent=1));print(json.dumps(summary),flush=True)
