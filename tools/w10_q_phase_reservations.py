#!/usr/bin/env python3
"""Finite model reservations: existing ICG, data uncertainty, BF and hub. No admission."""
import argparse
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path
from tools.w10_liberty_event_energy import events
from tools.w10_q_power_envelope import coefficients,serial

def tree(n,leaf=32):
    if n<1:return 0
    levels=[(n+leaf-1)//leaf]
    while levels[-1]>1:levels.append((levels[-1]+3)//4)
    if len(levels)>7:raise ValueError('tree exceeds fixed seven stages')
    return sum(levels)+7-len(levels)

def build(clock,power,construction,netloads,geometry,bf_hist,bf_cells,bf_data,leakages,hub,libs,macros):
    hz=D('1.2e9');v=D('.77');cv=hz*v*v*D('1e-15');rc=D('.145426');extra_sources={}
    types={'DFFHQNx1_ASAP7_75t_R':'HQN','DFFASRHQNx1_ASAP7_75t_R':'SEQ'};ff={}
    for typ,group in types.items():
        cs=[];es=[]
        for corner in ('SS','TT','FF'):
            p=libs/(group+'_'+corner+'.cells.lib');s=p.read_text();extra_sources[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
            cs.append(coefficients(s,typ,D('1e-12')))
            es.append(events(s,typ,{'RESETN':True,'SETN':True}) if group=='SEQ' else events(s,typ))
        ff[typ]={'cap':max(c['pins']['CLK']['cap_fF'] for c in cs),
                 'CLK':max(D(e['event_cycle_fJ']['CLK']) for e in es),
                 'D':max(D(e['event_cycle_fJ'].get('D','0')) for e in es)}
    root_hist=bf_hist['histograms']['clk'];leaf_hist={t:sum(h.get(t,0) for n,h in bf_hist['histograms'].items() if n!='clk') for t in types}
    bc=D(power['conservative_coefficients']['buffer']['input_cap_fF']);be=D(clock['compatible_event_proof']['FF']['buffer']['event_cycle_fJ']['A'])
    icgcap=max(D(power['corner_coefficients'][c]['icg']['pins']['CLK']['cap_fF']) for c in ('SS','TT','FF'))
    mc=max(D(power['corner_coefficients'][c]['macro']['pins']['clk']['cap_fF']) for c in ('SS','TT','FF'))
    me=D(power['conservative_coefficients']['macro']['internal_cycle_fJ'])
    rootC=sum(root_hist[t]*ff[t]['cap'] for t in root_hist)+8*icgcap+107*bc+107*500*rc*2
    leafC=sum(leaf_hist[t]*ff[t]['cap'] for t in leaf_hist)+4*mc+3766*bc+3766*500*rc*2+200*rc*2
    bfroot=rootC*cv+(sum(root_hist[t]*ff[t]['CLK'] for t in root_hist)+107*be)*D('1e-15')*hz
    bfleaf=leafC*cv+(sum(leaf_hist[t]*ff[t]['CLK'] for t in leaf_hist)+3766*be+4*me)*D('1e-15')*hz
    bf_data_root=sum(root_hist[t]*ff[t]['D'] for t in root_hist)*D('1e-15')*hz
    bf_data_leaf=sum(leaf_hist[t]*ff[t]['D'] for t in leaf_hist)*D('1e-15')*hz
    bf_leak=sum(n*D(leakages['per_cell_all_state_leakage_upper_W'][t]) for t,n in bf_cells['cell_counts'].items() if t!='ot_rom_4096x274_m8')+4*D(power['conservative_coefficients']['macro']['leakage_W'])+3873*D(power['conservative_coefficients']['buffer']['leakage_W'])
    hub_clock=D(str(hub['CLOCK_J_MM2']))*hz*(D(str(hub['hub_logic_mm2']))+D('.15')*D(str(hub['vm_sram_mm2'])))
    hub_leak=D(str(hub['hub_logic_mm2']))*D(str(hub['LEAK']['logic']))+D(str(hub['vm_sram_mm2']))*D(str(hub['LEAK']['sram_array']))
    io=4*D(str(hub['HBM_IDLE_W_STACK']))+D(str(hub['serdes_always_on_W']))+D(str(hub['ucie_idle_W']))
    hub_dynamic={
      'indexer':hub['idx_macs']*D(str(hub['E_MAC']['fp4']))*hz,
      'attention':hub['att_macs']*D(str(hub['E_MAC']['bf16']))*hz,
      'SU':hub['su_lanes']*D(str(hub['E_MAC']['fp32']))*D('0.9e9'),
      'SFU':hub['sfu_lanes']*hub['SFU_OPS_PER_ELEM']*D(str(hub['E_MAC']['fp32']))*D('0.9e9'),
      'VM_ports':(hub['vm_read_elems']+hub['vm_write_elems'])*4*D(str(hub['E_SRAM_B']))*hz}
    hubW=hub_clock+hub_leak+io
    # Ram's proposed four 4096x274 config macros per 128 return regions:
    # charge all 512 clocks continuously until an actual provider proves gating.
    crom_n=512;crom_buf=tree(crom_n,3)
    crom_clock=(crom_n*mc+crom_buf*bc+crom_buf*500*rc*2)*cv+(crom_n*me+crom_buf*be)*D('1e-15')*hz
    crom_out=crom_n*274*D('46.08')*cv
    crom_leak=crom_n*D(power['conservative_coefficients']['macro']['leakage_W'])+crom_buf*D(power['conservative_coefficients']['buffer']['leakage_W'])
    qroot=D(clock['root']['conditional_clock_W']);qleaf=D(clock['leaf']['conditional_enabled_clock_W']);icgon=D(clock['icg']['enabled_internal_W']);icgoff=D(clock['icg']['stopped_internal_W'])
    qleak=D(power['construction_leakage_power_W'])
    # Only pure leaf-source primitive cones receive leaf activity suppression.
    # Unclassified memory/enable lowering remains in the root-data upper allocation.
    leaf_gates=netloads['primitive_nand2_activity_classes']['leaf_only_or_static']
    root_gates=netloads['primitive_nand2_activity_classes']['root_reachable']+10*(netloads['root_register_D_bits']+netloads['root_sensitive_leaf_D_bits'])
    original_memory=construction['memory_mux_nand2']+construction['memory_decode_enable_nand2']
    effective_memory=sum(m['read_mux_nand2']+m['write_mux_nand2']+m['decode_enable_nand2'] for m in netloads['memory_lowering'])
    cfg_memory=sum(m['read_mux_nand2']+m['write_mux_nand2']+m['decode_enable_nand2'] for m in netloads['memory_lowering'] if m['root_CFG_storage'])
    cfg_storage_bits=sum(m['storage_bits'] for m in netloads['memory_lowering'] if m['root_CFG_storage'])
    cfg_gates=cfg_memory+10*cfg_storage_bits
    effective_gates=construction['total_nand2']-original_memory+effective_memory
    leaf_gates=effective_gates-root_gates-cfg_gates
    cfg_read_leaf_extra=sum(m['read_mux_nand2'] for m in netloads['memory_lowering'] if m['root_CFG_storage'])
    nandE=D(power['conservative_coefficients']['nand']['internal_cycle_fJ'])
    nandC=D(power['conservative_coefficients']['nand']['input_cap_fF'])
    root_data=root_gates*(nandE*hz*D('1e-15')+nandC*cv)+D(clock['root']['worst_storage_D_internal_W'])
    leaf_data=(leaf_gates+cfg_read_leaf_extra)*(nandE*hz*D('1e-15')+nandC*cv)+D(clock['leaf']['worst_enabled_storage_D_internal_W'])
    cfg_data=cfg_gates*(nandE*hz*D('1e-15')+nandC*cv)
    bf_front_data=D(bf_data['terms']['root']['conditional_total_data_upper_W'])
    # Unresolved non-clock wire is a finite ceiling allocation, not actual route.
    wire_upper=D(netloads['nonclock_wire_upper_activity1_switching_W'])
    candidates=[]
    for c in geometry['candidates']:
        q=c['q_pairs'];base=q*(qroot+icgoff+qleak)+1024*(bfroot+icgoff+bf_leak)+hubW+crom_clock+crom_leak
        phases={}
        for family,active in c['per_family_active_q_pairs'].items():
            clk=q*qroot+active*(qleaf+icgon)+(q-active)*icgoff
            # Finite upper allocations; STREAM/CFG inputs may drive ungated
            # capture/combinational logic in all resident pairs. No zero-data
            # claim based solely on leaf clock suppression.
            data=q*root_data+active*leaf_data+1024*bf_front_data
            total=base+active*(qleaf+icgon-icgoff)+data+sum(hub_dynamic.values(),D(0))+crom_out
            phases[family]={'active_qpairs':active,'root_q_clock_W':q*qroot,
              'existing_ICG_leaf_clock_W':active*qleaf,'q_clock_total_W':clk,
              'resident_Q_leakage_W':q*qleak,'BF_idle_root_clock_and_ICG_W':1024*(bfroot+icgoff),
              'BF_raw_map_and_CTS_leakage_W':1024*bf_leak,
              'hub_clock_leak_IO_W':hubW,'hub_all_units_dynamic_upper_W':sum(hub_dynamic.values(),D(0)),
              'CROM_always_clock_and_leak_W':crom_clock+crom_leak,
              'root_reachable_Q_data_internal_pin_upper_W':q*root_data,
              'CFG_only_Q_memory_lowering_upper_W':q*cfg_data,
              'BF_root_reachable_data_and_wire_upper_W':1024*bf_front_data,
              'leaf_only_Q_data_internal_pin_upper_W':active*leaf_data,
              'unresolved_Q_wire_upper_W':q*wire_upper,
              'CROM_output_load_ceiling_upper_W':crom_out,
              'phase_pin_internal_reservation_upper_W':total,
              'phase_with_unresolved_wire_upper_W':total+q*wire_upper+q*cfg_data,
              'common_phase_duty_max_pin_internal_screen':max(D(0),min(D(1),(D('474.56')-base)/(total-base))),
              'common_phase_duty_max_including_wire_screen':max(D(0),min(D(1),(D('474.56')-base)/(total+q*wire_upper+q*cfg_data-base))),
              'duty_scope':'Common-duty sensitivity only; actual clock/drain and CFG/STREAM fractions differ and require separate interval integration',
              'interpretation':'Conditional instantaneous reservation; not actual power or steady thermal verdict. A source program is required for energy/time averaging.'}
        candidates.append({'q_pairs':q,'active_family_phases':phases,
          'always_clock_leak_IO_reservation_W':base,
          'expert_only_physical_stages':c['expert_only_physical_stages'],'TP4_expert_die_count':c['TP4_expert_die_count'],
          'per_expert_cfg_plus_stream_partial_cycles':c['per_expert_cfg_plus_stream_partial_cycles'],
          'source_order_dispatch_cycles':c['dispatch_sensitivity']['source_order_six_expert_worst_linear_dispatch_serialization_cycles'],
          'geometry_screen_pass':c['q_cfg_BF1024_area_screen_pass'],
          'whole_product_feasible':False,'verdict':'BOUND_UNCERTAINTY_NO_ADMISSION'})
    return serial({'schema':'w10_q_phase_reservation_v1','additional_library_sha256':extra_sources,
      'q_data':{'root_or_unclassified_NANDs':root_gates,'leaf_only_NANDs':leaf_gates,'CFG_only_NANDs':cfg_gates,'CFG_read_leaf_extra_NANDs':cfg_read_leaf_extra,
        'constant_disabled_write_port_pruned_NANDs':original_memory-effective_memory,
        'CFG_only_data_upper_W_per_pair':cfg_data,
        'memory_and_lowering_scope':'FAST FIFO payload captured in leaf fw registers; root CFG storage changes in configuration window. Pure literal zero write ports pruned. Root-sensitive leaf D charged separately. CFG read terms conservatively counted for both CFG and leaf events.',
        'root_data_internal_pin_upper_W_per_resident_pair':root_data,
        'leaf_data_internal_pin_upper_W_per_enabled_pair':leaf_data,
        'unresolved_wire_upper_W_per_resident_pair':wire_upper},
      'BF':{'root_buffers':107,'leaf_buffers':3766,'root_storage_bits':sum(root_hist.values()),
        'leaf_storage_bits':sum(leaf_hist.values()),'root_clock_W_per_pair':bfroot,'leaf_enabled_clock_W_per_pair':bfleaf,
        'root_storage_D_internal_upper_W_per_pair':bf_data_root,'leaf_storage_D_internal_upper_W_per_pair':bf_data_leaf,
        'raw_all_state_leakage_plus_CTS_W_per_pair':bf_leak,
        'raw_cell_scope':bf_cells['scope'],'reserved_pairs':1024,
        'root_reachable_data_and_wire_upper_W_per_pair':bf_front_data,
        'enabled_leaf_data_and_wire_upper_W_per_pair':bf_data['terms']['leaf']['conditional_total_data_upper_W'],
        'existing_suppression_rule':'Pure leaf combinational cones and stored state hold with stopped leaf clocks; root-reachable CFG/STREAM cones are charged during incoming data.'},
      'hub':{'clock_W':hub_clock,'leakage_W':hub_leak,'interface_idle_W':io,'total_static_reservation_W':hubW,
        'configured_all_units_dynamic_upper_W':hub_dynamic,'scope':hub['qualification']},
      'CROM_proposal':{'macros':crom_n,'ungated_buffers':crom_buf,'clock_W':crom_clock,'leakage_W':crom_leak,
        'output_load_ceiling_data_W':crom_out,'source':'Ram explicit conditional CROM proposal, not an actual instantiated provider',
        'area_mm2':'4.0352768','actual_provider_qualified':False,'root_stop_credit':0},
      'source_clock_only_concurrency_screens':[{'q_pairs':c['q_pairs'],'maximum_awake_pairs_under_static_plus_clock_limit':min(c['q_pairs'],int(max(D(0),(D('474.56')-D(c['always_clock_leak_IO_reservation_W']))/(qleaf+icgon-icgoff)))), 'scope':'Clock-only upper concurrency screen; excludes data, CFG, hub dynamic and BF enabled work, so supplies no admission or schedule credit.'} for c in candidates],
      'phase_simultaneity':'CFG-only charge is separate from STREAM. Wire-inclusive figure is an allocation envelope, not a simultaneous source schedule. Integrate each term with its own source interval.',
      'macro_leakage':{'Q_per_pair_W':4*D(power['conservative_coefficients']['macro']['leakage_W']),'BF_per_pair_W':4*D(power['conservative_coefficients']['macro']['leakage_W']),'included_in_Q_and_BF_leakage_totals':True},
      'CROM_revision_scope':'512-macro historical conditional reservation only. Ram newer 45-bank/rank packed proposal requires separately source-bound service/clock join; no current geometry adoption.',
      'candidates':candidates,'physical_admission':False,'actual_power_qualified':False,'root_stop_credit':0,
      'thermal_limit_W':D('474.56'),'decision':'No feasible qualified whole-model point established. Finite allocation bounds exist; output wire/activation and complete stage program remain too wide for admission.',
      'next_source_join':'Use Ram source-pinned stage calendar to integrate CFG/STREAM/go/busy/drain interval unions; pure leaf suppression is existing ICG, not root-stop.',
      'remaining':['Source-bound per-net wire capacity/placement budget','CFG/STREAM activation multiplicity and full reset/glitch bound',
        'Hub/network/descriptor data schedule beyond configured resource ceilings','Non-expert owner capacity and token latency','actual RC/phase/SSFF/PG/IR']})
def main():
    p=argparse.ArgumentParser()
    names=('clock','power','construction','netloads','geometry','bf_hist','bf_cells','bf_data','leakages','hub','libs','macros','output')
    for n in names:p.add_argument('--'+n,required=True)
    a=p.parse_args();data={n:json.loads(Path(getattr(a,n)).read_text()) for n in names if n not in ('libs','macros','output')}
    x=build(**data,libs=Path(a.libs),macros=Path(a.macros));x['input_files']={n:{'path':getattr(a,n),'sha256':hashlib.sha256(Path(getattr(a,n)).read_bytes()).hexdigest()} for n in data}
    Path(a.output).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
if __name__=='__main__':main()
