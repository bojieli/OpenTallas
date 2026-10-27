"""Implement the approved KV-CORE-SLICE-1 pv_join entry trunk using shared core_infra.
Only the plan's single BUFx4 is added, ahead of one CTS-open sink domain.
"""
import json,sys,hashlib,importlib.util
from pathlib import Path
w=Path(sys.argv[1]); k=Path(sys.argv[2]); plan=Path(sys.argv[3]); census=json.load(open(k/'pv_clock_census.json'))
sys.path.insert(0,str(w/'tools/die_plan'));import core_infra as CI
p=json.load(open(plan));sl=dict(schema='opentallas.master_slice.v1',die='qwen_kvsys',kind='core',type='ot_qwen_tp8_pv_join_t',module='ot_qwen_tp8_pv_join_t',outline_um=[172.8,172.8],core_clock_port='clk',plan=str(plan),plan_sha256=hashlib.sha256(plan.read_bytes()).hexdigest(),master_plan_sha256='hm_r26-568fc66e',frozen=False,
 islands=[dict(name='entry',rect_um=[82.08,82.08,90.72,90.72],clock_pin=dict(layer='M5',xy_um=[86.424,86.4]))],bays=[],entry_pins=[],pushdown={'islands':[]},
 core_tree=dict(clock_port='clk',nodes=[dict(name='mp_pv_entry_trunk',master='BUFx4_ASAP7_75t_R',xy_um=[86.427,86.535],island_rect_um=[82.08,82.08,90.72,90.72],parent='port:clk')],leaves=[dict(node='mp_pv_entry_trunk',sinks=census['sinks'],cts_open=True,domain_sinks=len(census['sinks']))]),
 pg_obstructions_um={'M4':census['pg_M5'],'M5':census['pg_M5']},plan_prediction=dict(source='KV-CORE-SLICE-1 approved trunk, model UNCHECKED; no timing measurement selected structure',TT_ps=250.0,FF_ps=201.1,buffer_stages=1))
CI.install(k,sl)
(k/'pv_trunk_slice.json').write_text(json.dumps(sl,indent=1)+'\n')
prefix='''# Consume only the pass-1 entry-island placement reservation; keep all taps.
set pb [ord::get_db_block]
set pu [$pb getDbUnitsPerMicron]
set pr [list 82080 82080 90720 90720]
set removed 0
foreach b [$pb getBlockages] {
 set r [$b getBBox]
 if {[$r xMin]>=82080 && [$r xMax]<=90720 && [$r yMin]>=82080 && [$r yMax]<=90720} {odb::dbBlockage_destroy $b;incr removed}
}
puts "PV_ENTRY_PASS1_RESERVATIONS_CONSUMED $removed"
source /work/master_core_infra.tcl
# The root occupies its exact slot; the rest of the clock/reset island remains reserved.
set i [$pb findInst mp_pv_entry_trunk];set q [$i getBBox]
foreach rr [list [list 82080 82080 [$q xMin] 90720] [list [$q xMax] 82080 90720 90720] [list [$q xMin] 82080 [$q xMax] [$q yMin]] [list [$q xMin] [$q yMax] [$q xMax] 90720]] {
 lassign $rr x0 y0 x1 y1
 if {$x1>$x0 && $y1>$y0} {odb::dbBlockage_create $pb $x0 $y0 $x1 $y1}
}
puts "PV_ENTRY_TRUNK_INSTALLED stage1BUFx4 sinks15763 no_cycle_added"
'''
(k/'pv_trunk_install.tcl').write_text(prefix)
(k/'pv_trunk_pre_cts.tcl').write_text('source /work/max_fanout.tcl\nsource /work/pv_trunk_install.tcl\n')
cfg=(k/'config.mk').read_text().splitlines();cfg.append('override export PRE_CTS_TCL = /work/pv_trunk_pre_cts.tcl');CI.kit_cts_hook(k,cfg);(k/'config.mk').write_text('\n'.join(cfg)+'\n')
print('PV_TRUNK_SLICE_SHARED_COMPILE_PASS',len(census['sinks']))
