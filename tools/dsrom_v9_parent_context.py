#!/usr/bin/env python3
"""Size the parent-only v9/QX10 register/clock cut before physical mapping.

The remaining element is a terminal dependency, not a shrunken compute tile.
Its entire actual Z18 frame stays reserved inside the S81 slot.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path


def model(root):
    base = root/'results/uarch/dsrom_v9_parent_context_20261005'
    pinfile = base/'inputs/loaded_ports.json'
    loaded = json.loads(pinfile.read_text())
    floorfile = root/'results/rtl/dsrom_recovery_20261004/physcost/layer/floorplan.json'
    floor = json.loads(floorfile.read_text())
    slot = floor['field']['slot_um']
    frame = [510.84, 151.2]  # actual source-pinned Z18a config.mk; not frame A or a scaled pilot
    boundary_ff_upper = 20000
    # Complete first return-node queues: two sides, tag32/data32/error1,
    # D64, plus full 1630-bit BST2+RPT1 and full NB2 QX boundary registers.
    exact_queue_bits = 2*64*65
    broadcast_bits = 1+6+3+1+1+2+1+8+3+2+256+10+256+10+3+3+1+3+4+32+1024
    assert broadcast_bits == 1630
    clocks = {}
    for c in ('SS', 'FF'):
        row = loaded[c]
        gc = row['cut_pins']['u_e.g_cg.u_cg.u_icg/GCLK']
        if gc['cap_fF'] <= 0 or len(row['input_port_cap_fF']) != 606:
            raise ValueError('incomplete actual QX10 terminal load extraction')
        clocks[c] = dict(gated_engine_terminal_cap_fF=gc['cap_fF'],
                         actual_downstream_pins=gc['pins'],
                         primary_input_bits=len(row['input_port_cap_fF']))
    # Upper bounds, not fitted gate counts. Actual mapping/repair must fit.
    ff_cell_upper_um2 = boundary_ff_upper*0.729
    comb_cell_upper_um2 = 6000
    clock_buffer_upper = sum(math.ceil(boundary_ff_upper/8**level) for level in range(1, 7))
    clock_cell_upper_um2 = clock_buffer_upper*.2916
    mapped_budget = ff_cell_upper_um2+comb_cell_upper_um2+clock_cell_upper_um2
    parent_box = [2.16, 2.16, 525.096, 237.60]
    available = (parent_box[2]-parent_box[0])*(parent_box[3]-parent_box[1])
    if mapped_budget/.5 >= available:
        raise ValueError('complete register/control cut does not fit the actual remaining slot')
    return dict(schema='opentallas.dsrom.v9.parent_clock_context.v1',
        generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        input_hashes={str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in (pinfile, floorfile, base/'inputs/source.sha256', base/'terminal_profiles.json')},
        source=dict(v9='f284118df', QX10='0032b7355', QX10_vehicle='Z18a',
                    QX10_ODB='existing immutable 4_cts.odb; no re-synthesis or route',
                    SS_FF_load_basis='real mapped downstream Liberty pin sums in existing CTS DB; no capacitance guessed'),
        scope='actual v9 broadcast/loader/root-input registers, QX10 input/gate/reset/output registers, one full D64 first return node',
        excluded='remaining QX engine, later return network and whole field; terminal interfaces retain known source clocks and loads',
        full_slot_um=slot, die_um=slot,
        reserved_QX_frame_um=frame, reserved_QX_bbox_um=[527.256,44.28,1038.096,195.48],
        parent_cell_bbox_um=parent_box, parent_available_um2=available,
        mapping_density=.5, register_bits_upper=boundary_ff_upper,
        actual_first_return_node_queue_bits=exact_queue_bits,
        broadcast=dict(bits=broadcast_bits, stages=3, BST=2, RPT=1, reset=True),
        clocks=dict(period_ps=1000/1.2, setup_uncertainty_ps=60, hold_uncertainty_ps=25,
                    root='core_clk on actual clk; Qfree',
                    gated='g_qx.g_cg.u_cg.u_icg/GCLK, combinational passed core_clk edges',
                    source_loaded_cuts=clocks, propagated=True,
                    insertion_ps=None, actual_clock_wire_cap_fF=None,
                    conditional_terminal_budget_ps=dict(min=360,max=727, basis='existing QX source vehicle; actual remaining-cone arrivals unqualified')),
        area=dict(FF_cell_upper_um2=ff_cell_upper_um2, combinational_upper_um2=comb_cell_upper_um2,
                  conditional_fanout8_clock_buffer_upper=clock_buffer_upper,
                  conditional_clock_cell_upper_um2=clock_cell_upper_um2,
                  cell_upper_um2=mapped_budget, placement_upper_um2=mapped_budget/.5,
                  mapping_must_fit=True, routed_fit_proven=False),
        ports=dict(broadcast_source_bits=broadcast_bits, configuration_ROM_bytes_per_cycle=6,
                   remaining_engine_XS_bits=549, pair_result_bits=126,
                   root_result_capture_bits=69, reset_copies=8,
                   source_bound_terminal_loading=str((base/'terminal_profiles.json').relative_to(root)),
                   per_bit_child_loading_qualified=False,
                   observation_terminal_downstream_loading_qualified=False),
        routing=dict(local_data_cut_tracks=549+54+3+126+69+8,
                     signal_layers='M2-M7', clock_layers='M7-M8',
                     physical_channel_capacity_qualified=False,
                     whole_element_frame_not_shrunk=True, route_must_validate_actual_PG_and_channel_capacity=True),
        compute=dict(new_MACs_per_cycle=0, new_rounding_points=0, replicas=1,
                     full_QX_MACs_and_four_ROMs='remain the QX10 owner dependency; no omitted-hardware credit'),
        latency=dict(added_source_pipeline_edges=0, projected_register_edges_are_existing=True,
                     existing_v9_baseline_record='results/rtl/dsrom_field_spine_20261004/field_baseline_v9.json',
                     first_return_node_cycles=6, minimum_context_is_not_full_matvec_latency=True,
                     reprice_AR_MTP=False, adoption_credit=0),
        resource=dict(host='EPYC1', expected_peak_GiB=8, cores=4,
                      justification='<=20k state bits, one return node, no QX compute synthesis or whole-die database',
                      admission='unchanged host guard plus fresh measured CPU/RAM/disk before actual execution',
                      wall_file_AS_limits='none'),
        parent_only_mapping_admitted=True, full_QX_context_admitted=False,
        full_field_build_admitted=False, missing_input_clocks=True,
        remaining_dependency='qualified full-shape QX10 LEF/SS/FF timing and exact gate from live Z18; all terminal arrival/child clock-tree qualification still outstanding',
        physical_closed=False)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args=parser.parse_args()
    import uarch_model
    args.out.write_text(json.dumps(uarch_model.dsrom_v9_parent_context_model(), indent=2)+'\n')
