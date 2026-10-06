#!/usr/bin/env python3
"""Extract CP/W2 context from the selected existing DS die, without allocating new slots."""
from pathlib import Path
import hashlib
import json

import hbm_accel_die_fp as F
from chip_assembly.v41_die import ASAP7_LAYERS

ROOT = Path(__file__).resolve().parents[1]


def extract():
    m = F.build()
    inputs = [
        'tools/hbm_accel_die_fp.py', 'tools/chip_assembly/v41_die.py',
        'results/rtl/hbm_accel_die_floorplan_20261005/floorplan.json',
        'results/rtl/hbm_accel_die_floorplan_20261005/feasibility.json',
        'results/rtl/hbm_accel_die_floorplan_20261005/domains.sdc',
        'results/uarch/hbm_cp_balanced_veto_20261005/protected_clock_context_r1.json',
        'results/uarch/hbm_w2_publication_20261005/model.json',
        'results/uarch/hbm_w2_publication_20261005/inputs/immutable_parent.sv',
    ]
    pinned = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in inputs}
    fp = json.loads((ROOT / inputs[2]).read_text())
    feas = json.loads((ROOT / inputs[3]).read_text())
    containers = {}
    for it in m['insts']:
        if it.name not in ('hb_cmdproc', 'hb_vm'):
            continue
        containers[it.name] = dict(
            master=it.master, bbox_um=[it.x, it.y, it.x + it.w, it.y + it.h],
            dimensions_um=[it.w, it.h], outline_area_um2=it.w * it.h,
            source_grade=fp['block_ledger']['cmdproc' if it.name == 'hb_cmdproc' else 'vm']['grade'],
            connected_buses=[dict(id=bid, kind=kind, bits=bits, endpoints=eps)
                             for bid, kind, bits, eps in m['buses']
                             if any(ep[0] == it.name for ep in eps)],
            internal_child_placement=None, usable_child_area_um2=None,
            CTS_internal_area_reservation_um2=None,
            internal_PG_and_route_area_reservation_um2=None)
    layers = [dict(layer=n, direction=d, native_pitch_um=p,
                   k16_GRT_pitch_um=16*p,
                   GRT_removed_fraction=(1.0 if n in ('M2', 'M3', 'M4', 'M5')
                                         else F.VIA_OBS + (2*F.COV['spine'] if n in ('M8', 'M9') else 0)))
              for n, d, p, *_ in ASAP7_LAYERS if n != 'M1']
    cp = json.loads((ROOT / inputs[5]).read_text())
    w2 = json.loads((ROOT / inputs[6]).read_text())
    return dict(
        schema='opentallas.hbm-selected-die-parent-context.v1',
        selected_die='DS r14b; existing floorplan only', sources_sha256=pinned,
        die=fp['die'], containers=containers,
        channels=dict(spine_side_width_um=m['geo']['spch'],
                      west_x_interval_um=[m['hub']['cmdproc'].x-m['geo']['spch'], m['hub']['cmdproc'].x],
                      east_x_interval_um=[m['hub']['cmdproc'].x+m['hub']['cmdproc'].w,
                                          m['hub']['cmdproc'].x+m['hub']['cmdproc'].w+m['geo']['spch']],
                      hub_edge_width_um=F.HCH, layers=layers, PDN=fp['pdn'],
                      available_CP_tracks=None, available_W2_tracks=None,
                      selected_child_channel_length_um=None,
                      residual_capacity_policy='Aggregate GRT resources and overflow do not allocate a child channel; competing trunks already occupy these corridors.'),
        existing_measurements=dict(
            grt=feas['cases']['r14b/b_k16_i50']['grt'],
            IR=feas['ir_summary']['ir14'],
            limits='Bundled abstract GRT and density-based IR; no selected CP/W2 child netlist or parent STA/CTS.'),
        clock=dict(floorplan_target_stream_period_ns=0.833,
                   floorplan_target_serial_period_ns=1.111,
                   setup_uncertainty_ps=60, hold_uncertainty_ps=25,
                   logical_parent_CP_port='g_die[d].u_su_cp.clk(clk_sm)',
                   logical_parent_W2_port=w2['timing']['parent_sink_clock_port'] if 'timing' in w2 else 'g_on.g_die[d].u_w2_sink.clk(clk_sm)',
                   logical_W2_reset='rst_sm_n',
                   actual_parent_clock_constraint=None, phase_and_insertion=None,
                   actual_boundary_IO_loads_and_delays=None,
                   characterization='domains.sdc is a target declaration; case_grt does not read SDC, create CTS, or characterize boundary loads.'),
        CP=dict(boundary_tracks_lower_bound=cp['ports']['boundary_signal_tracks_lower_bound'],
                intended_container='hb_cmdproc', installed_physical_instance=None,
                usable_slot_bbox_um=None, slot_fit=None, channel_fit=None),
        W2=dict(boundary_tracks_lower_bound=w2['routing']['provider_boundary_tracks_lower_bound'],
                planned_placement_um2=w2['area']['planned_50pct_placement_um2'],
                logical_instance=w2['area']['parent_instance_path'],
                container_association='VM ledger mentions result publication buffers, but no selected W2 sink is bound to hb_vm or an index quarter.',
                installed_physical_instance=None, usable_slot_bbox_um=None,
                slot_fit=None, channel_fit=None),
        physical_launch_admitted=False,
        blocker='Existing die lacks selected CP/W2 child macro abstracts, internal allocations/competing occupancy and loaded parent clock/IO constraints. No spare index allowance or component IO20 context can supply them.',
        next_action='Integrate the selected child abstracts and actual parent boundary constraint export into the existing cmdproc/publication containers once their enclosing inventory is available; preserve the r14b evidence and all live jobs.')


if __name__ == '__main__':
    print(json.dumps(extract(), indent=2) + '\n', end='')
