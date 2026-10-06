#!/usr/bin/env python3
"""Join the existing full QX10 element and native parent terms before P&R."""
import argparse
import hashlib
import json
import re
from pathlib import Path


def model(root, boundary_hold=False, hard_cfg=False):
    parent_path = root/'results/uarch/dsrom_v9_parent_context_20261005/model.json'
    boundary_path = root/'results/uarch/dsrom_v9_field_boundary_20261005/model.json'
    parent = json.loads(parent_path.read_text())
    boundary = json.loads(boundary_path.read_text())
    stat = root / 'results/uarch/dsrom_qx10_parent_context_20261005/inputs/Z18a_synth_stat.txt'
    text = stat.read_text()
    total = float(re.search(r"Chip area for top module .*: ([0-9.]+)", text)[1])
    macro_area = boundary['macro_area_um2']
    logic = total - macro_area
    box = parent['reserved_QX_bbox_um']
    engine_available = (box[2]-box[0])*(box[3]-box[1])-macro_area
    parent_upper = parent['area']['cell_upper_um2']
    cfg = None; cfg_body = 0.; cfg_logic = 0.; cfg_reserve = 0.
    if hard_cfg:
        cfg_path=root/'results/uarch/dsrom_v9_cfg_context_20261005/model.json'
        cfg=json.loads(cfg_path.read_text())
        cfg_receipt=json.loads((root/'results/rtl/dsrom_v9_cfg_context_20261005/record.json').read_text())
        if cfg_receipt['functional_gate']['verdict']!='PASS': raise ValueError('actual cfg source exact gate absent')
        cfg_body=cfg['geometry']['macro_body_um2']
        cfg_logic=cfg['geometry']['added_logic_upper_um2']
        cfg_reserve=cfg['geometry']['macro_reserved_um2']
        parent_upper+=cfg_logic
    # Mandatory baseline hold repair: one positive buffer on each of the three
    # source-matched Z18d data sinks. No clock load or sequential stage is added.
    hold_area = 3 * .0729 if boundary_hold else 0.
    # Conservative sum: the parent projection's redundant engine boundary
    # registers remain in this bound, although the join instantiates them once.
    fits = logic + hold_area <= .6*engine_available and parent_upper <= .5*(parent['parent_available_um2']-cfg_reserve)
    return dict(schema='opentallas.dsrom.qx10.native_parent.v1',
        source=dict(engine='0032b735573af2d24416eee1cf5911c0ac99ff5d',
                    engine_sha256='88e58e80d79dece71346b3123174d0ae0188b6590de88938575877b2209fc3b6',
                    parent_model_sha256=hashlib.sha256(parent_path.read_bytes()).hexdigest(),
                    boundary_model_sha256=hashlib.sha256(boundary_path.read_bytes()).hexdigest(),
                    Z18a_synth_stat_sha256=hashlib.sha256(stat.read_bytes()).hexdigest()),
        scope='one full NB2/PP1 QX10 engine, D3 broadcast, PQ0 descriptor loader, D64 first return and separate root capture',
        compute=dict(FP8_MACs_per_cycle=64, FP4_MACs_per_cycle=128,
                     weight_payload_bytes_per_cycle=64, FP8_MACs_per_weight_byte=1,
                     new_MACs_per_cycle=0),
        memory_bytes_per_cycle=dict(weight=68.5, configuration=6, configuration_macro=9 if hard_cfg else 0),
        ROM_reliability=dict(selected_policy='fault-free ROM reads, no ECC', ROM_ECC=False,
             SECDED=False, ROM_parity_sidecars=0, weight_physical_bits=274,
             weight_used_packed_FP8_bits=264, weight_used_packed_FP4_bits=272,
             weight_metadata='source exponent fields, not ECC; no ROM checking/correction in selected0032',
             configuration_physical_bits=72 if hard_cfg else 0, configuration_payload_bits=48,
             configuration_spare_bits=24 if hard_cfg else 0,
             configuration_source='q[47:0]; upper24 unused, not parity',
             mutable_control_identity_address_and_fault_protection_retained=True),
        configuration_provider=dict(selected=hard_cfg, default_OFF=True,
             source='physical/dsrom_v9_cfg_context/ot_v41_pair_cfgrom_context.sv' if hard_cfg else None,
             finite_words=1600 if hard_cfg else 0, PHW=6, NSEG=8, CW=25,
             physical_rows=4096 if hard_cfg else 0, macro_replicas=1 if hard_cfg else 0,
             payload_receiver_bits=48, physical_address_bits=12 if hard_cfg else 0, read_enable_bits=1,
             macro_bbox_um=cfg['geometry']['macro_bbox_um'] if hard_cfg else None,
             macro_reserved_um2=cfg_reserve, additional_logic_upper_um2=cfg_logic,
             measured_component_standard_cell_um2=cfg_receipt['mapped_component']['standard_cell_area_um2'] if hard_cfg else None,
             exact_checks_per_PQ=6070 if hard_cfg else 0, exact_added_loader_cycles=0,
             actual_receiver_bounds=cfg_receipt['receiver_measurements'] if hard_cfg else None,
             timing=cfg['clocks'] if hard_cfg else None,
             same_root_clock=True, original_capture_stage=True, extra_pipeline_stages=0,
             full_field_clock_qualified=False),
        boundary_bits_per_cycle=dict(XS=549, configuration=54, go=1, pair_result=126, root_capture=69),
        replicas=dict(element=1, logical_banks=2, real_weight_ROMs=4, real_configuration_ROMs=1 if hard_cfg else 0, first_return_node=1),
        mux_demux_fanout='unchanged QX10 ping-pong capture mux, QZ_NS8/QZ_NE4 copies, class-valid admission and protected return identity',
        floorplan=dict(slot_um=parent['full_slot_um'], engine_frame_um=parent['reserved_QX_frame_um'],
                       engine_bbox_um=box, parent_bbox_um=parent['parent_cell_bbox_um']),
        area=dict(Z18a_total_um2=total, ROM_um2=macro_area+cfg_body, weight_ROM_um2=macro_area, configuration_ROM_um2=cfg_body, engine_logic_um2=logic+hold_area,
                  engine_stdcell_available_um2=engine_available, engine_density=.6,
                  parent_conservative_cell_upper_um2=parent_upper, parent_density=.5, parent_available_after_cfg_halo_um2=parent['parent_available_um2']-cfg_reserve,
                  sum_conservative_body_um2=total+parent_upper+hold_area+cfg_body, analytical_slot_fit=fits,
                  routed_slot_fit=False),
        boundary_hold=dict(selected=boundary_hold, default=False,
                           mandatory_baseline_repair=True, buffers=3 if boundary_hold else 0,
                           cell='BUFx2_ASAP7_75t_R', added_area_um2=hold_area,
                           added_clock_load_fF=0, added_register_stages=0,
                           added_MACs=0, added_memory_bytes_per_cycle=0,
                           added_boundary_bits_per_cycle=0,
                           SS60_FF25_loaded_context_required=True,
                           buffer_area_source='results/physical/dsrom_qx10_boundary_hold_20261005/buffer_library.json'),
        routing=dict(local_boundary_tracks=809+(3 if boundary_hold else 0)+(62 if hard_cfg else 0),
                     conservative_channel_height_um=parent['parent_cell_bbox_um'][3]-parent['parent_cell_bbox_um'][1],
                     channel_capacity_source='existing M4/M6 48/64nm track estimates in uarch_model; 50% clock/PG reserve',
                     estimated_channel_capacity_tracks=int((235.44/.048+235.44/.064)*.5),
                     signal_layers='M2-M7', clock_layers='M7-M8', actual_routing_fit=False),
        clocks=dict(period_ps=1000/1.2, SS_uncertainty_ps=60, FF_uncertainty_ps=25,
                    root='clk/core_clk', gated='u_qx.u_e.g_cg.u_cg.u_icg/GCLK',
                    XS='actual selected g_qb.g_bx posedge gclk lines257/260',
                    reset_launch='eight g_mac.g_mz copies on core_clk',
                    macro=boundary['macro_timing'], loaded_root_cuts_qualified=False),
        latency=dict(new_pipeline_cycles=0, measured_QX10_vs_QX9_minimum_cycles=0,
                     source_BST_edges=3, existing_first_return_edges=6,
                     existing_field_wire_cycles=80, charge_transport_once=True,
                     whole_node_or_token_reprice=False),
        fault=dict(no_constant_fault_waiver=True, engine_frontend='existing Z18 synthesis frontend',
                   frontend_loader_source='physical/dsrom_qx10_parent_context/parent_loader/ot_v41_pair_pq_ld_frontend.sv',
                   frontend_loader_sha256=hashlib.sha256((root/'physical/dsrom_qx10_parent_context/parent_loader/ot_v41_pair_pq_ld_frontend.sv').read_bytes()).hexdigest(),
                   frontend_loader_origin='/srv/opentallas-scratch2/codex/fspine-v9-parent-context-20261005/pq0_fault_lowering_r3/fixed.sv',
                   semantic_and_mapped_producer_gate_required=True),
        full_context_build_ready=fits, full_field_build_ready=False,
        missing_input_clocks=True, physical_qualified=False,
        existing_terms=dict(parent_model='results/uarch/dsrom_v9_parent_context_20261005/model.json',
                            boundary_model='results/uarch/dsrom_v9_field_boundary_20261005/model.json'),
        resource=dict(host='EPYC1', reservation_GiB=32, cores=4, smoke_cores=1,
                      basis='full existing Z18 element admitted at30GiB plus one parent; no whole field',
                      actual_fresh_fit_required=True))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args=parser.parse_args()
    import uarch_model
    record=uarch_model.dsrom_qx10_parent_context_model()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, indent=2)+'\n')
    if not record['full_context_build_ready']:
        raise SystemExit('full existing element/parent terms exceed their unchanged floorplan allocations')
