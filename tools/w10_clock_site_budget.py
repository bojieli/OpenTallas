#!/usr/bin/env python3
"""One fixed, source-backed clock reserve hypothesis; never generates hardware/P&R."""
import argparse
import hashlib
import json
import math
import re
from decimal import Decimal as D
from pathlib import Path
import w10_fullmap_slot_fit as S
import w10_allport_access_audit as A
from w10_capture_local_fit import block

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / 'results/uarch/w10_clock_tree_site_budget_r1'
OWNER = ROOT / 'results/uarch/w10_baseline_wake/local_fit_r1'

def verify_netlist(path):
    """Reproduce endpoint inventory directly from the owner's immutable synthesis."""
    raw=path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == 'd6b8f7848db0fdfb1f1142deaa298154c4a6366447ee5d1906df8055ed4ba2ea'
    mapped=json.loads((INPUT/'mapped_clock_endpoints.json').read_text())
    names={};hist={};gates=[]
    for typ,name,body in re.findall(r'^\s+(\w+)\s+(\\?\S+)\s+\((.*?)\n\s*\);',raw.decode(),re.M|re.S):
        ports={k:v.strip() for k,v in re.findall(r'\.(\w+)\(([^)]+)\)',body)}
        if typ.startswith('DFF'):
            net=ports['CLK'];names.setdefault(net,[]).append(name)
            h=hist.setdefault(net,{});h[typ]=h.get(typ,0)+1
        if typ.startswith('ICG'):
            assert ports['CLK']=='clk'
            gates.append(name)
    assert hist==mapped['histograms'] and {k:sorted(v) for k,v in names.items()}==mapped['endpoint_names']
    owner=json.loads((OWNER/'audit.json').read_text())
    assert set(gates)=={g['name'] for g in owner['icg_gates']} and len(gates)==8
    return dict(netlist_sha256=hashlib.sha256(raw).hexdigest(),flops=sum(len(v) for v in names.values()),ICG_CLK_on_source_clk=len(gates),verdict='PASS')

def scalar(text, key):
    return float(re.search(r'\b'+key+r'\s*:\s*([\d.eE+-]+)', text)[1])

def tree(sinks, leaf_limit=32, fanout=4, depth=7):
    """Bottom-up integer populations; singleton pads make each tree depth seven."""
    assert sinks > 0 and leaf_limit > 0 and fanout > 1
    levels = [math.ceil(sinks/leaf_limit)]
    while levels[-1] > 1:
        levels.append(math.ceil(levels[-1]/fanout))
    assert len(levels) <= depth, 'Fixed seven-stage hypothesis cannot cover endpoints'
    natural = len(levels)
    levels += [1]*(depth-natural)
    return dict(sinks=sinks, leaf_buffers=levels[0], levels_leaf_to_root=levels,
                natural_depth=natural, depth=depth, buffers=sum(levels),
                internal_buffer_edges=sum(levels)-1,
                leaf_assignment='Contiguous chunks of at most 32 in sorted endpoint_names; parent chunks of four; singleton root pads.')

def slot(buffers, area_um2, sites_per_buffer, clock_columns=54):
    # Nine disjoint abstract clock channels. Four demanded branch tracks need
    # ceil(4/.75)=6 physical M5 tracks under the actual .25 routing adjustment;
    # ceil(6*48/54)=6 sites. Capacity pricing, not a legal channel location.
    b = S.budget()
    demand = b['standard_cell_demand_sites'] + buffers*sites_per_buffer
    blocked = b['macro_sites']+b['exclusive_escape_sites']+b['exclusive_top_bottom_halo_sites']
    rows = math.ceil((2*demand+blocked)/(b['width_sites']-clock_columns))
    free = b['width_sites']*rows-blocked-clock_columns*rows
    capacity = D(free)*D('0.01458')/2
    return dict(width_sites=b['width_sites'], rows=rows, density=.5,
                baseline_stdcell_um2=62705.9, additional_clock_buffer_um2=buffers*area_um2,
                additional_buffer_sites=buffers*sites_per_buffer,
                standard_cell_demand_sites=demand, reserved_clock_columns=clock_columns,
                exclusive_clock_channel_sites=clock_columns*rows,
                fixed_obstacle_sites=blocked, free_sites=free,
                stdcell_capacity_um2=float(capacity),
                stdcell_spare_um2=float(capacity-D('62705.9')-D(str(buffers))*D(str(area_um2))),
                core_um=[998.568, rows*.270], outline_um=[1002.89, rows*.270+4.32],
                previous_slot_fits=2*demand+blocked+clock_columns*b['rows'] <= b['width_sites']*b['rows'])

def cap_witness(sink_ff, max_ff, wire_um, source_c=.145426, multiplier=2):
    # Nominal platform RC coefficient interpreted in SS Liberty's fF units.
    # 2x is a fixed analytical guard, not extracted/SS/FF qualified wire RC.
    total=sink_ff+wire_um*source_c*multiplier
    return dict(sink_ff=sink_ff, wire_sum_bound_um=wire_um, guarded_wire_ff=wire_um*source_c*multiplier,
                total_ff=total, limit_ff=max_ff/2, full_library_max_ff=max_ff,
                pass_half_maxcap=total<=max_ff/2,
                additional_wire_budget_um=(max_ff/2-sink_ff)/(source_c*multiplier))

def build():
    lib=(INPUT/'buffer_SS.lib.txt').read_text()
    lef=(INPUT/'buffer.lef.txt').read_text()
    buf=block(lib,r'cell\s*\(BUFx12_ASAP7_75t_R\)')
    a=block(buf,r'pin\s*\(A\)'); y=block(buf,r'pin\s*\(Y\)')
    inc=scalar(a,'capacitance'); maxc=scalar(y,'max_capacitance')
    width,height=map(D,re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',lef).groups())
    assert width/D('.054') == 16 and height == D('.270')
    area=float(width*height)
    assert abs(area-scalar(buf,'area')) < 1e-10
    owner=json.loads((OWNER/'audit.json').read_text())
    _,_,tracks,_,_=A.read_inspection((ROOT/A.DIR/'inspection.log').read_text())
    assert tracks['M5','X'][1] == 48
    platform=(INPUT/'platform_source.txt').read_text()
    adjustment=float(re.search(r'export ROUTING_LAYER_ADJUSTMENT\s*\?=\s*([\d.]+)',platform)[1])
    assert adjustment==.25
    physical_tracks=math.ceil(4/(1-adjustment))
    columns_each=math.ceil(physical_tracks*48/54)
    rc=(INPUT/'rc_source.txt').read_text()
    rc_c=float(re.search(r'set_wire_rc -clock -resistance\s+\S+ -capacitance\s+(\S+)',rc)[1])
    assert rc_c == .145426, 'Only the pinned fixed nominal RC hypothesis is supported'
    units=json.loads((INPUT/'library_units.json').read_text())
    assert units['time_unit']=='1ps' and units['capacitive_load_unit']==[1,'ff']
    seq=(OWNER/'selected_cell_SS_liberty.txt').read_text()
    icg=block(seq,r'cell\s*\(ICGx\d+_ASAP7_75t_R\)')
    icg_in=scalar(block(icg,r'pin\s*\(CLK\)'), 'capacitance')
    icg_out=scalar(block(icg,r'pin\s*\(GCLK\)'), 'max_capacitance')
    assert icg_out == owner['icg_GCLK_max_capacitance_ff']
    caps={typ:scalar(block(block(seq,r'cell\s*\('+re.escape(typ)+r'\)'),r'pin\s*\(CLK\)'), 'capacitance')
          for typ in owner['flop_clock_capacitance_ff']}
    assert caps == owner['flop_clock_capacitance_ff']
    mapped=json.loads((INPUT/'mapped_clock_endpoints.json').read_text())
    hist=mapped['histograms']; names=mapped['endpoint_names']
    assert sum(sum(h.values()) for h in hist.values()) == 91733
    allnames=[n for v in names.values() for n in v]
    assert len(allnames)==len(set(allnames))==91733
    groups=[]
    for gate in owner['icg_gates']:
        n=gate['flop_clock_sinks'] or len(gate['macro_clock_sinks'])
        if gate['flop_clock_sinks']:
            assert hist[gate['gclk']] == gate['flop_types']
            assert len(names[gate['gclk']]) == n
        t=tree(n)
        sink_cap= min(32,n)*max(caps.values()) if gate['flop_clock_sinks'] else owner['macro_CLK_capacitance_ff']
        t.update(name=gate['name'], clock=gate['gclk'], macros=gate['macro_clock_sinks'],
                 summed_endpoint_cap_ff=gate['total_endpoint_CLK_capacitance_ff'],
                 leaf_load=cap_witness(sink_cap,maxc,500),
                 tree_driver=cap_witness(inc,icg_out,25),
                 internal_load=cap_witness(4*inc,maxc,500))
        groups.append(t)
    root_n=sum(hist['clk'].values())+8
    root=tree(root_n)
    root.update(name='source_clk_to_ungated_flops_and_eight_ICG_CLK_pins',
                leaf_load=cap_witness(8*icg_in+24*max(caps.values()),maxc,500),
                leaf_bound_scope='Worst possible leaf with all eight ICG inputs and 24 flops; other 32-flop leaves have smaller input load.',
                internal_load=cap_witness(4*inc,maxc,500),
                source_driver='External clk port drive, slew and wire capacity remain unqualified.')
    groups.append(root)
    count=sum(g['buffers'] for g in groups)
    b=slot(count,area,16,9*columns_each)
    composition=S.price(b['outline_um'])
    # Keep rate/headline untouched: report only geometric composition delta.
    baseline=S.price(S.budget()['outline_um'])
    composition.pop('conditional_ar_tokens_s'); composition.pop('conditional_token_us')
    composition['baseline_stages']=baseline['stages']; composition['baseline_dies']=baseline['dies']
    b['composed_model']=composition
    delay={}
    for key in ('cell_rise','cell_fall','rise_transition','fall_transition'):
        table=block(buf,r'\b'+key+r'\s*\(')
        values=re.search(r'values\s*\((.*?)\);',table,re.S)[1]
        delay[key+'_grid_max_ps']=max(map(float,re.findall(r'[\d.]+',values)))
    grid_max=max(delay['cell_rise_grid_max_ps'],delay['cell_fall_grid_max_ps'])
    paths=['tools/uarch_model.py','tools/w10_fullmap_slot_fit.py','tools/w10_clock_site_budget.py',
           'results/uarch/w10_baseline_wake/local_fit_r1/audit.json',
           'results/uarch/w10_baseline_wake/local_fit_r1/selected_cell_SS_liberty.txt',
           'results/uarch/w10_baseline_wake/local_fit_r1/selected_cell_lef.txt',
           'physical/asap7_memory_macros/ot_rom_4096x274_m8/ot_rom_4096x274_m8_ss.lib']
    paths += [str(A.DIR/'inspection.log')]
    paths += [str(p.relative_to(ROOT)) for p in sorted(INPUT.iterdir()) if p.name not in ('receipt.json','validation.txt')]
    pins={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}
    return dict(schema='opentallas.w10.clock.site.reserve.v1',verdict='MODEL_SIZED_PHYSICAL_HOLD',adopt=False,
        physical_admission=False,jobs_launched=0,source_sha256=pins,
        buffer=dict(type='BUFx12_ASAP7_75t_R',size_um=[float(width),float(height)],area_um2=area,
                    sites=16,SS_input_ff=inc,SS_output_max_ff=maxc,SS_table_domain_slew_ps=[5,320],
                    SS_table_domain_load_ff=[5.76,368.64],**delay),
        fixed_hypothesis=dict(leaf_limit=32,buffer_branch_limit=4,depth_per_tree=7,
            wire_sum_per_buffer_output_um=500,wire_sum_per_ICG_output_um=25,
            source_RC_clock_cap_ff_per_um=.145426,cap_guard_multiplier=2,used_maxcap_fraction=.5,
            note='One analytical tree only; alphabetical endpoints are deterministic electrical assignments, not spatial clusters. No optimized candidate or netlist emitted.'),
        groups=groups,buffer_replicas=count,slot=b,
        clock_network=dict(endpoint_pins=91733+8+4,buffer_input_pins=count,
            buffer_to_buffer_edges=sum(g['internal_buffer_edges'] for g in groups),
            added_buffer_output_wire_sum_bound_um=count*500,ICG_wire_sum_bound_um=8*25,
            bits_per_cycle_per_clock_edge=1,logical_streaming_clock_hz=1.2e9,
            memory_bytes_per_cycle_added=0,MACs_per_cycle_added=0,muxes_added=0,
            per_internal_branch_tracks=4,per_leaf_branch_endpoint_tracks=32,
            leaf_endpoint_tracks_scope='32 distinct terminal branches locally; shared upper tree is four-way. No common cut proves all branches coexist on one channel.',
            reserved_channels=9,tracks_each=physical_tracks,M5_pitch_nm=48,channel_width_sites_each=columns_each,
            actual_routing_capacity_adjustment=adjustment,
            modeled_usable_tracks_each=physical_tracks*(1-adjustment),
            leaf32_local_cut_physical_tracks_if_all_coincident=math.ceil(32/(1-adjustment)),
            channel_reserve_scope='Exclusive gross strip budget charged outside macros, capture/escape and halos. No contiguous legal position through obstacles/PDN proved.'),
        latency=dict(ungated_buffer_stages=7,gated_buffer_stages=14,ICG_delay='UNKNOWN',
            buffer_table_grid_delay_max_ps=grid_max,
            seven_buffer_grid_sum_ps=7*grid_max,fourteen_buffer_grid_sum_ps=14*grid_max,
            grid_sum_scope='Sums of finite table-grid maxima only, excludes wire/ICG; not actual insertion delay, period feasibility or a bound outside table domain.',
            transition_grid_max_exceeds_next_input_table_domain=max(delay['rise_transition_grid_max_ps'],delay['fall_transition_grid_max_ps'])>320,
            minimum_buffer_input_load_below_table_domain=inc<5.76,
            additional_architectural_cycles='UNKNOWN; pure clock distribution adds no intended data stage, but phase/protocol and setup/hold must be qualified.',
            composed_scope='LAT8 retained only to price geometry through unified model; this is not a qualified token latency or headline rate.'),
        predicates=dict(integer_density_slot_fits=b['stdcell_spare_um2']>=0,
            fixed_endpoint_cap_and_guarded_nominal_wire_pass=all(g[k]['pass_half_maxcap'] for g in groups for k in ('leaf_load','internal_load')) and all(g['tree_driver']['pass_half_maxcap'] for g in groups[:-1]),
            original617row_slot_fits=b['previous_slot_fits'],actual_clock_route=False,
            endpoint_spatial_assignment=False,generated_PG=False,SS_FF_timing=False,clock_protocol_exactness=False),
        classification=dict(provable=['Integer 625-row gross capacity at unchanged 50% density',
            'Fixed integer buffers cover all mapped flop/macro/ICG input endpoints',
            'SS max-cap checks pass under stated wire-sum/RC guard hypothesis'],
            refuted=['Existing 617-row slot with this buffer/channel reserve fits'],
            missing=['Legal spatial clock-channel and buffer assignment',
                'Actual generated PG/cut/EOL and extracted RC',
                'Source clock, slew propagation, ICG phase/protocol and SS/FF timing']),
        unresolved=['Actual spatial leaves and clock spine/channel continuity around four macros and capture bins',
            'Candidate PG/cut/EOL conflicts, vias, coupling/extracted RC and IR/EM',
            'Slew propagation/load-table range, ICG gating checks and clock source drive',
            'Seven versus fourteen buffer-stage clock phase alignment and reset/wake protocol exactness',
            'SS setup/FF hold with 60ps/25ps uncertainty and final tap/endcap/hold repair reserve'],
        constraints=dict(streaming_GHz=1.2,density=.5,setup_uncertainty_ps=60,hold_uncertainty_ps=25),
        prior_failures='c8 DRT-0255 and FRONT_PAR FLW0024 rejected unchanged; bankmap FAIL_model_mismatch retained. No retry/tuning.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    p.add_argument('--verify-netlist',type=Path);a=p.parse_args()
    if a.verify_netlist:print(json.dumps(verify_netlist(a.verify_netlist)))
    a.output.write_text(json.dumps(build(),indent=2)+'\n')
