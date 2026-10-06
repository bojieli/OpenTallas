#!/usr/bin/env python3
"""Bounded clock/load terms for the existing v9 field composition.

No synthetic port arrivals. This is the enclosing-context build prerequisite,
not a new q-element study or a substitute for the existing field measurements.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path


def model(root: Path) -> dict:
    paths = {
        'parent': 'rtl/v41die/ot_v41_fieldtop_pqc_w17w10.sv',
        'spine': 'rtl/v41die/ot_v41_spine_pqc_w17w10.sv',
        'field': 'rtl/v41die/ot_v41_field_pq_w17w10.sv',
        'loader': 'rtl/v41die/ot_v41_pair_pq_ld.sv',
        'pair': 'rtl/v41die/ot_v41_pair_pq_w17w10.sv',
        'gate': 'rtl/hdc/ot_hdc_cg.sv',
        'floorplan': 'results/rtl/dsrom_recovery_20261004/physcost/layer/floorplan.json',
        'composition': 'results/rtl/dsrom_field_spine_20261004/field_baseline_v9.json',
        'macro': 'physical/asap7_memory_macros/ot_rom_4096x274_m8/ot_rom_4096x274_m8.json',
        'contract': 'physical/dsrom_field_spine/field_boundary_clock.tcl',
    }
    sources = {k: dict(path=p, sha256=hashlib.sha256((root/p).read_bytes()).hexdigest())
               for k, p in paths.items()}
    floor = json.loads((root/paths['floorplan']).read_text())
    composed = json.loads((root/paths['composition']).read_text())
    macro = json.loads((root/paths['macro']).read_text())
    period = 1000/1.2
    # A QX pair has NB=2, PP=1: FOUR placed macros, two alternating
    # macros per logical bank. This is not a two-macro area claim.
    slot = floor['field']['slot_um']
    clocks = {}
    for c, uncertainty in [('ss', 60), ('ff', 25)]:
        t = macro['timing'][c]
        clocks[c] = dict(clk_to_q_ps=t['clk_to_q_ps'], macro_setup_ps=t['setup_ps'],
                         macro_hold_ps=t['hold_ps'], clock_pin_cap_fF=t['clk_cap_ff'],
                         four_macro_clock_pin_cap_fF=4*t['clk_cap_ff'],
                         uncertainty_ps=uncertainty)
    roles = {
        'activation': dict(bits=549, launch='u_sp.g_bst.u_bst', capture='QX g_qb.g_bx',
                           launch_clock='streaming parent', capture_clock='ICG passed parent edges'),
        'configuration': dict(bits=54, launch='u_f.g_p[*].u_p.u_ld', capture='QX g_qb b_cfg_* and b_cdec',
                              launch_clock='streaming parent', capture_clock='free parent'),
        'go': dict(bits=1, launch='u_f.g_p[*].u_p.u_ld go_e', capture='QX g_qb b_go',
                   launch_clock='streaming parent', capture_clock='free parent'),
        'result': dict(bits=126, launch='QX NB=2 partials with row/segment/position/error',
                       capture='u_f.g_lv[0].g_n[*].u_n',
                       launch_clock='ICG passed parent edges', capture_clock='free parent'),
        'vm_read': dict(bits=composed['vehicle']['VRD']*32 if 'VRD' in composed['vehicle'] else 64*32,
                        launch='VM x_q', capture='u_sp read/quantizer stages',
                        launch_clock='parent clk', capture_clock='parent clk'),
        'vm_write': dict(bits=32+composed['vehicle']['VAW']+1,
                         launch='u_sp w_data/w_addr/w_we registers', capture='VM write port',
                         launch_clock='parent clk', capture_clock='parent clk'),
        'macro_read': dict(bits=2*274, launch='four physical ROM rd_out buses, alternating per bank',
                           capture='QX g_mac bank capture registers',
                           launch_clock='ICG passed parent edges', capture_clock='ICG passed parent edges'),
        'busy': dict(bits=1, launch='QX g_qo.busy_d[QK-1]', capture='actual parent busy consumer',
                     launch_clock='free parent', capture_clock='free parent'),
        'fault': dict(bits=1, launch='QX g_qo.g_qyf.fq (QY=1)', capture='actual parent fault consumer',
                      launch_clock='free parent', capture_clock='free parent'),
        'free_to_gated': dict(bits=None, launch='Qfree cfg/go and control registers',
                             capture='gated FIFO/fw, i1/i2x, macro/lane/tree control',
                             launch_clock='free parent', capture_clock='ICG passed parent edges'),
        'gated_to_free_control': dict(bits=None, launch='gated busy_c and bank fault producers',
                                     capture='Qfree g_qo.busy_d/ff_d and g_mac[*].g_qyb.bkf_r',
                                     launch_clock='ICG passed parent edges', capture_clock='free parent'),
    }
    for row in roles.values():
        row.update(actual_launch_Q_pins=None, actual_capture_D_pins=None,
                   loaded_capacitance_fF=None, actual_fanout=None,
                   launch_clock_insertion_ps=None, capture_clock_insertion_ps=None,
                   SS_setup_slack_ps=None, FF_hold_slack_ps=None)
    return dict(schema='opentallas.dsrom.v9.field_boundary.v1', sources=sources,
        v9_source_commit='f284118df', v9_exact_record='results/rtl/dsrom_field_spine_20261004/exactness_v9.json',
        scope='one complete NB=2 PP=1 Q pair and its actual source-owned producer/capture boundary',
        QX_owner_source_commit='0032b7355', QX_live_Z18_untouched=True,
        QX_owner_source_sha256='88e58e80d79dece71346b3123174d0ae0188b6590de88938575877b2209fc3b6',
        QX_owner_source_path='rtl/v41rom/ot_v41_rom_elem_qx_w10.sv',
        XS_clock_source_note='0032b7355 lines257/260 use posedge gclk in g_qb.g_bx; not Qfree',
        current_v9_pair_selects_QX=False,
        clock_contract=dict(streaming_period_ps=period, serial_period_ps=1000/.9,
            serial_streaming_ratio='3:4', setup_uncertainty_ps=60, hold_uncertainty_ps=25,
            gate='ot_hdc_cg/u_icg ICGx1_ASAP7_75t_R, latch-low enable; passed root edges, no division',
            option_C_regions=floor['clock_regions'],
            source_parent='u_sp, u_f and VM share top clk in current exact RTL',
            separate_region_source_binding=None),
        macro_timing=clocks,
        SS_one_edge_residual_before_capture_and_wire_ps=period-60-clocks['ss']['clk_to_q_ps'],
        macro_residual_scope='diagnostic only; real ping-pong two-cycle macro paths retain their existing constraints',
        physical_macros_per_pair=4, active_macro_words_per_streaming_cycle=2,
        memory_bytes_per_cycle=dict(weight_payload=2*256/8, weight_macro_including_metadata=2*274/8,
                                    local_configuration=48/8, VM_read=64*32/8, VM_write_per_region=4),
        boundary_classes=roles, added_MACs_per_cycle=0,
        existing_QX_compute='inherited from the q-element owner; no new arithmetic or throughput credit',
        replicas=dict(local_pair=1, local_logical_weight_banks=2, physical_pingpong_macros=4,
                      field_pairs=floor['field']['pairs'], Q_pairs=floor['field']['q']),
        mux_demux_fanout='retain full QX capture mux, QZ_NS8/QZ_NE4 and existing return identity; loaded counts unresolved',
        macro_area_um2=4*macro['area']['macro_area_um2'],
        floorplan_slot_um=slot, floorplan_slot_um2=slot[0]*slot[1],
        actual_logic_and_clock_area_um2=None, slot_fit_proven=False,
        reset_boundary=dict(launch='g_mac[*].g_mz/u_rs,u_rsc,u_rsp,u_rst on Qfree',
                            capture='actual gated asynchronous reset pins',
                            copies_per_NB2_pair=8, checks='SS recovery and FF removal',
                            mapped_pins=None, recovery_slack_ps=None, removal_slack_ps=None),
        routing_tracks=dict(logical_local_payload_bits=sum(x['bits'] for x in roles.values() if x['bits'] is not None),
                            actual_channel_capacity=None, loaded_clock_tracks=None, fit_proven=False),
        latency=dict(existing_field_record_wire_term=composed['wire_stages_s81_floorplan_per_crossing'],
            current_floorplan_stages=floor['trunk_stages']['stages_at_504'],
            region_crossings=floor['trunk_stages']['option_C_crossing_cycles'],
            charge_transport_once=True, added_source_pipeline_edges=0,
            new_QX_plus_v9_composed_latency=None,
            rate_adoption_credit=0),
        missing_input_clocks=True, minimum_context_build_ready=False, full_field_die_build_ready=False,
        blockers=['Selected v9 field still instantiates PQ element, not the owner QX source: no source-bound combined pair yet',
            'Option-C inter-region FIFO/clock connections are not implemented in the current single-clk field vehicle',
            'Actual mapped enclosing producer/capture pins, CTS/SPEF, loaded port and channel terms absent'],
        action='Bind the real source-composed pair and enclosing register paths with field_boundary_clock.tcl; preserve Z18 and all v9 live routes')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    # Invoke the unified model entry, so this bounded term has one owner.
    import uarch_model
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(uarch_model.dsrom_v9_field_boundary_model(), indent=2)+'\n')
