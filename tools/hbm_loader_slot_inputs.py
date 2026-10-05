#!/usr/bin/env python3
"""Emit opt-in isolated loader floorplan/pins and priced CRC locality inputs.

Scalar arithmetic only; never invokes synthesis/STA/P&R. Region costs are
provisional reservations, not measured closure or a full-parent allocation.
"""
import argparse
import hashlib
import json
import math
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = Path('results/uarch/hbm_accel_fulldie_inputs_20261004/loader_slot')
TURING = Path('results/rtl/tapeout_hbm_loader_20261004')


def read(root, path, refs):
    raw = (root/path).read_bytes()
    refs[str(path)] = hashlib.sha256(raw).hexdigest()
    return json.loads(raw)


def emit(root, out):
    refs = {}
    locality = read(root, BASE/'final_def_locality.json', refs)
    width = read(root, TURING/'high_address/price_before_rtl.json', refs)
    read(root, TURING/'installed_roundtrip/clock_r2_final/physical.json', refs)
    recipe = read(root, TURING/'installed_roundtrip/crc_matrix_price_before_build.json', refs)
    assert width['request_internal_packet_bits'] == 342
    assert width['request_service_packet_bits'] == 341
    assert abs(width['FF_area_floor_um2_ESTIMATE'] - 63*.2916) < 1e-8
    assert locality['sha256'] == 'c832c453115aa005b815376bcb1e6247988b7c53b0539dc6092f64ce6f788141'
    for name in ['ot_hbm_accel_loader_host_addr.sv', 'ot_hbm_accel_loader_addr.sv',
                 'ot_hbm_accel_store_addr.sv', 'ot_hbm_accel_loader_addr_to_service.sv']:
        path = Path('rtl/hbm_accel/loader')/name
        refs[str(path)] = hashlib.sha256((root/path).read_bytes()).hexdigest()
    # The dimensions cover both perpendicular cut directions. M2 uses the
    # seven actual row-track origins per .270um period, not a fictitious pitch.
    side, outer, halo, gap = 264.384, 576.288, 8.64, 25.92
    horizontal = math.floor(7*math.floor(side/.270)/2) + sum(
        math.floor(math.floor(side/p)/2) for p in [.048,.064,.080])
    vertical = sum(math.floor(math.floor(side/p)/2) for p in [.036,.048,.064,.080])
    demand = 2*4424+32 + 2*288 + 8*32 + 3*32
    assert min(horizontal, vertical) >= demand
    regions = {}
    for name, x, y, domain, instance, state in [
        ('crc_got_load',halo,298.944,'host','u_load','crc_got'),
        ('crc_got_store',298.944,298.944,'host','u_store','crc_got'),
        ('vcrc_load',halo,halo,'mem','u_load','vcrc'),
        ('mcrc_store',298.944,halo,'mem','u_store','mcrc')]:
        regions[name] = dict(box_xywh_um=[x,y,side,side], clock_domain=domain,
            existing_state_hierarchy=f'g_on.g_die[0].{instance}.g_on.{state}',
            placement_members='existing state plus its new exclusive matrix cone, input buffers and hold muxes',
            signal_cut_capacity=dict(horizontal=horizontal,vertical=vertical),
            signal_cut_demand=demand, required_no_cross_fold_matrix_sharing=True)
    # Gross proxy census: 65-bit add/compare/mux for both engine guards,
    # formatter add/compare/mask, CSR decode. No removal credit for old logic.
    nand, xor = .08748, .17496
    adder, cmp, mux = 2*xor+5*nand, xor+5*nand, 4*nand
    guard = 2*65*(3*adder+4*cmp+3*mux)+65*(adder+cmp)+341*2*nand+2*32*mux+2*27*2*nand
    costs = dict(retained_final_routed_cells_um2=23294.1,
        added_parallel_matrix_um2=4*4424*xor,
        selected_wide_guard_FF_floor_um2=63*.2916,
        guard_mux_decode_gross_operator_proxy_um2=guard,
        input_fanout_buffers_um2=4*288*.4374,
        additional_route_CTS_repair_reserve_um2=2*(23294.1-22022.5))
    gross = sum(costs.values())
    core = [halo,halo,outer-halo,outer-halo]
    core_area = (outer-2*halo)**2
    # Actual retained facade pin census; only the five new high address bits
    # are added. Natural bit ordering and original names are preserved.
    names = [p['name'] for p in locality['pins']]+[f'req_addr[{i}]' for i in range(32,37)]
    assert len(names) == len(set(names)) == 1410
    natural = lambda s: [int(v) if v.isdigit() else v for v in re.split(r'(\d+)',s)]
    groups = {key: sorted([n for n in names if match(n)],key=natural) for key,match in [
        ('host',lambda n:n.startswith(('m_','h_','s_'))),
        ('request',lambda n:n.startswith('req_')),
        ('response',lambda n:n.startswith('rsp_'))]}
    assert [len(groups[k]) for k in ['host','request','response']] == [785,344,275]
    pins = []
    for group, ns in groups.items():
        for i,n in enumerate(ns):
            xy = [26.892+i*.192,outer-.042] if group=='host' else [outer-.042,(31.116 if group=='request' else 128.028)+i*.192]
            pins.append(dict(name=n,group=group,layer='M5' if group=='host' else 'M4',xy_um=[round(v,6) for v in xy]))
    for n,x,y in [('clk_host',518.028,outer-.042),('rst_host_n',518.220,outer-.042),
                  ('clk_mem',518.028,.042),('rst_mem_n',518.220,.042),
                  ('irq',520.140,outer-.042),('fault',520.332,outer-.042)]:
        assert n in names
        pins.append(dict(name=n,group='clock_reset_status',layer='M5',xy_um=[x,y]))
    assert {p['name'] for p in pins} == set(names)
    assert len({(p['layer'],tuple(p['xy_um'])) for p in pins}) == 1410
    crc_commit = subprocess.check_output(['git','rev-parse','94cc829e1^{commit}'],cwd=root,text=True).strip()
    crc_sources = {}
    for name in ['ot_hbm_accel_loader_host_addr_crc.sv','ot_hbm_accel_loader_addr_crc.sv','ot_hbm_accel_store_addr_crc.sv']:
        path = 'rtl/hbm_accel/loader/'+name
        raw = subprocess.check_output(['git','show',crc_commit+':'+path],cwd=root)
        crc_sources[path] = hashlib.sha256(raw).hexdigest()
    model = dict(selected_route_source=dict(commit=crc_commit,sha256=crc_sources,
        facade='ot_hbm_accel_loader_host_addr_crc',parameters=dict(ENABLE=1,ND=1,ADDR_W=37,STACK_W=2,STACK_BYTES=22500000000,CRC_MATRIX=1)), name='service.loader',status='PROVISIONAL_ISOLATED_CRC_CLOSURE_INPUT',
        default_enabled=False, actual_fit=False, signoff=False, full_parent_adopted=False,
        die_box_xyxy_um=[0,0,outer,outer],core_box_xyxy_um=core,
        outer_area_um2=outer**2, core_area_um2=core_area,
        placement_edge_keepout_um=halo, central_corridor_width_um=gap,
        placement_core_cell_utilization_limit=.55, costs=costs,
        gross_cell_and_repair_budget_um2=gross,
        cell_only_minimum_core_area_um2=gross/.55,
        remaining_cell_capacity_um2=.55*core_area-gross,
        fold_regions=regions,
        layers=dict(horizontal=['M2','M4','M6','M8'],vertical=['M3','M5','M7','M9'],
            signal_fraction_reserved=.5,other_fraction_reserved=.5,
            other_uses=['PG','clock','vias','non-CRC escape/control'], M1='power only',
            actual_track_statements=locality['tracks']),
        corridors=[dict(name='retained_CDC_control_vertical',box_xywh_um=[273.024,halo,gap,559.008]),
                   dict(name='retained_CDC_control_horizontal',box_xywh_um=[halo,273.024,559.008,gap])],
        pin_groups={k:dict(count=len(v)) for k,v in groups.items()},
        facade_request_signal_bits=344,formatted_parent_request_signal_bits=343,
        response_signal_bits=275,
        source_bindings=refs, retained_final_def_sha256=locality['sha256'],
        retained_context_clock_verdict=dict(SS_setup_ps=-3672.04,FF_hold_ps=10.39,slew_violations=8,adopted=False),
        arithmetic_and_flow=dict(added_capture_edges=0,added_CDC_stages=0,added_credit_cycles=0,
            existing_ACK_state_lifetimes_preserved=True, CRC_recipe=recipe),
        pricing_grade='positive provisional reservation; guard/mux and repair are estimates, not mapped upper bounds',
        clock_IR_contingency=dict(cell_reserve_included=True,half_track_reserve_included=True,
            edge_escape_keepout_included=True, loaded_SS_FF_wire_PG_IR_latency_priced=False),
        remaining_gates=['new matrix function/cycle gate by Turing','mapped area and local cone placement',
            'SS60/FF25 including extracted wire/clock/PG effects','slew/cap/fanout/DRC',
            'parent service anchor, all other service/storage/port costs and full-frame fit'],
        storage_budget_independent=True)
    out.mkdir(parents=True,exist_ok=True)
    (out/'model.json').write_text(json.dumps(model,indent=2)+'\n')
    (out/'pins.json').write_text(json.dumps(pins,indent=2)+'\n')
    # This script must be explicitly sourced after linked wide ND1 facade.
    # It does not create jobs, change clocks, adopt RTL or modify the parent.
    lines = ['# Opt-in isolated wide ND1 loader ONLY. Source after initialize_floorplan.',
             '# Preserve existing constraints; no clock/uncertainty changes.',
             '# CRC cone regions are in model.json; bind new exclusive cone names before placement.']
    for p in pins:
        x,y=p['xy_um']; lines.append(f"place_pin -pin_name {{{p['name']}}} -layer {p['layer']} -location {{{x:.6f} {y:.6f}}}")
    (out/'pins.tcl').write_text('\n'.join(lines)+'\n')
    (out/'floorplan.tcl').write_text('# Opt-in isolated closure vehicle; not a full-die placement.\n'
        'initialize_floorplan -die_area {0 0 576.288 576.288} -core_area {8.64 8.64 567.648 567.648}\n')
    print(json.dumps(dict(slot_um=[outer,outer],gross_cells_um2=gross,horizontal=horizontal,vertical=vertical,pins=len(pins))))


if __name__ == '__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root',type=Path,default=ROOT)
    ap.add_argument('--out',type=Path)
    a=ap.parse_args()
    emit(a.root,a.out or a.root/BASE)
