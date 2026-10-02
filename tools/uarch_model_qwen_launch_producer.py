#!/usr/bin/env python3
"""Source-allocated launch producer-to-pin model screen; no hardware admission.

Prices existing joined_ready/held_valid ASR-QN plus restoring inverter cells
against current per-corner parent requirements. Local2um wires are an explicit
finite screen, not the unbound hub-to-provider route or a mapped producer.
"""
import argparse,hashlib,json,re
from pathlib import Path
import qwen_rom_owned_ready_context as Q
ROOT=Q.R.ROOT
OUT=Path('results/uarch/qwen_rom_launch_producer_context_20261002')


def price():
 R=Q.R;rows,_=Q.allocation();sites={r['instance']:r for r in rows}
 ready=R.obj(Q.OUT/'model-r1.json');parent=R.obj(Q.P.OUT/'model-r1.json')
 joins_path=R.OUT/'inputs/launch_join_cells_r1.json';joins=R.obj(joins_path)
 targets={'joined_ready[0]':'B','held_valid[0]':'A'}
 rc_path=R.OUT/'inputs/setRC.tcl'
 rc=re.search(r'set_wire_rc -signal -resistance ([\d.Ee+-]+) -capacitance ([\d.Ee+-]+)',R.read(rc_path))
 if rc is None:raise ValueError('selected signal RC missing')
 wire_R,C=map(float,rc.groups())
 length=2.;results={};worst_setup=0.;worst_hold=0.;phase_bounds=[]
 for corner in ('ss','ff'):
  _,lib,caps=R.library(corner);result={}
  for name,pin in targets.items():
   row=sites[name]
   if (row['domain'],row['cell'],row['restoring_cell'])!=('stream',R.ASR,Q.INV):raise ValueError('source allocated producer changed')
   inv_input=caps[(Q.INV,'A')]['cap_fF'];and_input=joins[corner]['pin_caps_fF'][pin]
   qcap=inv_input+length*C;icap=and_input+length*C
   qrc=wire_R*length*(inv_input+length*C/2)/1000
   irc=wire_R*length*(and_input+length*C/2)/1000
   transitions={}
   for transition,qn in [('rise','fall'),('fall','rise')]:
    clkq=R.envelope(lib[R.ASR],'cell_'+qn,qcap,5,80,related='CLK')
    qs=R.envelope(lib[R.ASR],qn+'_transition',qcap,5,80,related='CLK')
    invd=R.envelope(lib[Q.INV],'cell_'+transition,icap,*qs)
    invs=R.envelope(lib[Q.INV],transition+'_transition',icap,*qs)
    arrival=[clkq[0]+invd[0]+qrc+irc,clkq[1]+invd[1]+qrc+irc]
    constraints=[]
    for scenario in parent['numeric_parent_root_launch']['corners'][corner]['scenarios']:
     req=scenario['launch'][transition]['required_go_and_owned_ready_after_provider_clock_ps']
     slack=[arrival[0]-req[0],req[1]-arrival[1]]
     phase_bounds.append([req[0]-arrival[0],req[1]-arrival[1]])
     constraints.append(dict(provider_clock_slew_ps=scenario['primary_clock_slew_ps'],required_input_minmax_ps=req,
      nominal_same_phase_hold_setup_slack_ps=slack,allowed_producer_clock_minus_provider_clock_ps=[req[0]-arrival[0],req[1]-arrival[1]]))
     if corner=='ss':worst_setup=min(worst_setup,slack[1])
     if corner=='ff':worst_hold=min(worst_hold,slack[0])
    transitions[transition]=dict(QN_transition=qn,QN_clkq_minmax_ps=clkq,QN_slew_minmax_ps=qs,INV_delay_minmax_ps=invd,
     INV_slew_minmax_ps=invs,arrival_minmax_after_producer_clock_ps=arrival,constraints=constraints)
   result[name]=dict(source_allocation=row,actual_provider_AND_pin=pin,QN_cap_fF=qcap,INV_cap_fF=icap,local_wire_RC_ps=qrc+irc,transitions=transitions)
  results[corner]=result
 paths=[Q.OUT/'model-r1.json',Q.OUT/'register-allocation-r1.json',Q.P.OUT/'model-r1.json',joins_path,rc_path,
        R.RESET/'inputs/seq_ss.lib.gz',R.RESET/'inputs/seq_ff.lib.gz',R.RESET/'inputs/invbuf_ss.lib.gz',R.RESET/'inputs/invbuf_ff.lib.gz',
        Path('rtl/physical/ot_qwen_rom_reset_parent_provider.sv'),Path('tools/qwen_rom_owned_ready_context.py'),Path('tools/qwen_rom_current_reset_construction.py')]
 return dict(schema='QWEN_PRICED_LAUNCH_PRODUCER_PIN_CONTEXT_V1',status='FAIL_NOMINAL_SOURCE_PRODUCER_SETUP_CONTEXT',
  source_sha256={str(p):R.sha(p) for p in paths},producer_instances=targets,corners=results,
  worst_SS_setup_slack_ps=worst_setup,worst_FF_hold_violation_ps=worst_hold,
  necessary_common_producer_minus_provider_clock_phase_ps=[max(p[0] for p in phase_bounds),min(p[1] for p in phase_bounds)],
  boundary='registered held-valid and joined-ready -> existing AND3 A/B -> existing finite provider/tile launch route',
  explicit_local_QN_to_INV_wire_um=length,explicit_local_INV_to_AND_wire_um=length,
  RC=dict(R_ohm_per_um=wire_R,C_fF_per_um=C,source='already selected setRC.tcl; finite local wires only'),
  clock_period_ps=1000/1.2,SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,
  source_clock_phase_vs_provider_unbound=True,actual_hub_to_provider_route_um=None,actual_source_instance_connected=False,
  scope='nominal same-phase candidate cell/finite local-wire screen; full source clock/route missing and no routed timing credit',
  model_charge=dict(already_in_owned_ready_1201_FFs=True,FF_and_INV_cells_added=0,new_cycles=0,existing_steady_launch_stage_cycles=ready['steady_added_staging_cycles'],
   MACs_per_cycle_unchanged=True,payload_bits_per_issue=379+128,control_boundary_bits=2,control_route_tracks_already_allocated=False,full_parent_cost_complete=False),
  physical_source_admission=False,default_enabled=False,RTL_changed=False,new_map=False,new_token=False,
  next_gate='Ampere must compose actual producer clock phase/route and reset with existing parent and collector graph; retain failed nominal phase and do not relax833.333/60/25 or assume zero hub route')

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
 if a.out.exists():p.error('preserve existing verdict')
 r=price()
 with a.out.open('x') as f:json.dump(r,f,indent=2);f.write('\n')
 print(r['status'])
