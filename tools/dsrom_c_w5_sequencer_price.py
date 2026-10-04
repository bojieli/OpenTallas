#!/usr/bin/env python3
"""Price the added admission/control inventory; close the uncomposed lever."""
import hashlib
import json
from pathlib import Path
from dsrom_c_w5_pg import control_allocation

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/uarch/dsrom_c_w5_sequencer_20261003'
netlist=json.loads((OUT/'generic_netlist.json').read_text())
cells=netlist['modules']['ot_dsrom_c_w5_seq_gate']['cells']
cells={k:v for k,v in cells.items() if v['type']!='$scopeinfo'}
palette_path=ROOT/'results/uarch/dsrom_c_w5_pg_20261003/model_r7/liberty.json'
palette=json.loads(palette_path.read_text())
allocation=control_allocation({'modules':{'ot_dsrom_c_w5_pg':{'cells':cells}}},palette)
model=json.loads((OUT/'prebuild_model.json').read_text())
model['allocation']=allocation
model['allocation']['includes']='one ROM field-group PG controller plus retained start admission'
model['geometry']['actual_added_FF_bits']=allocation['FF_bits_measured']
model['geometry']['prebuild_FF_bits_are_conservative_reservation']=True
model['clock_gate']={'digital_latch_bits':1,'physical_ICG_mapping':'NOT_QUALIFIED',
    'Liberty_ICG_reference_only':{c:palette['cells']['ICGx1_ASAP7_75t_R/'+c] for c in ('SS','TT','FF')}}
model['latency']['ready_start_added_cycles_component_measured']=0
model['latency']['late_start_added_cycles_component_measured']=8
model['latency']['production_added_cycles']=None
model['production']={'calendar_bound':False,'retained_debt_signal_bound':False,
    'known_mask_unbound_behavior':'unknown class holds field awake; no sleep credit',
    'Engram_always_on':True,'ROM_only':True,'HA_builds':0,'adoption_closed':True}
paths=['rtl/v41rom/ot_dsrom_c_w5_pg.sv','rtl/v41rom/ot_dsrom_c_w5_seq_gate.sv',
       'rtl/v41rom/ot_dsrom_c_w5_core_v41x.sv','rtl/test/tb_dsrom_c_w5_seq_gate.sv',
       'results/uarch/dsrom_c_w5_pg_20261003/model_r7/liberty.json',
       'results/uarch/dsrom_c_w5_integration_20261003/production_dependency_packet.json']
model['source_sha256']={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}
(OUT/'model.json').write_text(json.dumps(model,indent=2,sort_keys=True)+'\n')
