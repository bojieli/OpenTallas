#!/usr/bin/env python3
"""Price the missing finite PHW6 configuration-ROM provider, before RTL."""
import hashlib
import json
from pathlib import Path


def model(root):
    macro = root/'physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8.json'
    parent = root/'results/uarch/dsrom_v9_parent_context_20261005/model.json'
    m = json.loads(macro.read_text())
    p = json.loads(parent.read_text())
    width, height = m['area']['macro_width_um'], m['area']['macro_height_um']
    # Single PHW6 native vehicle, not PHW10 field capacity: 64*25=1600 words.
    halo = 2.16
    rectangle = [4.32, 4.32, 4.32+width, 4.32+height]
    reserved_area = (width+2*halo)*(height+2*halo)
    parent_box = [2.16, 2.16, 525.096, 237.60]
    available = (parent_box[2]-parent_box[0])*(parent_box[3]-parent_box[1])-reserved_area
    # Existing loader address increment/phase multiply may share logic; do not
    # credit that sharing until mapping. No additional sequential state.
    added_logic_upper = 1000.
    parent_upper = p['area']['cell_upper_um2']
    assert (parent_upper+added_logic_upper)/.5 < available
    period = 1000/1.2
    timing = {}
    for corner, uncertainty in [('ss',60), ('ff',25)]:
        row = m['timing'][corner]
        timing[corner] = dict(macro_clk_to_q_ps=row['clk_to_q_ps'],
            macro_setup_ps=row['setup_ps'], macro_hold_ps=row['hold_ps'],
            macro_min_period_ps=row['min_period_ps'],
            macro_clock_cap_fF=row['clk_cap_ff'],
            address_pin_cap_fF=row['pin_cap_ff'],
            twelve_address_pin_cap_fF=12*row['pin_cap_ff'],
            uncertainty_ps=uncertainty,
            remaining_after_intrinsic_clkQ_and_uncertainty_ps=period-row['clk_to_q_ps']-uncertainty,
            actual_slew_load_wire_capture_setup_unpriced=True)
    return dict(schema='opentallas.dsrom.v9.cfg_provider.v1',
        inputs={str(x.relative_to(root)):hashlib.sha256(x.read_bytes()).hexdigest() for x in (macro,parent)},
        scope='one PHW6/NSEG8/CW25 native pair configuration provider; no full PHW10 field claim',
        compute=dict(added_MACs_per_cycle=0, added_rounding_points=0),
        memory=dict(words=1600,payload_bits=48,physical_words=4096,physical_bits=72,
                    payload_bytes_per_read=6,macro_bytes_per_read=9,read_ports=1,reads_per_phase=25,
                    read_cycles_per_phase=25,ROM_ECC=False,spare_bits=24),
        boundary=dict(logical_address_bits=11,physical_address_bits=12,payload_bits=48,
                      read_enable_bits=1,selected_macro_replicas=1),
        mux_fanout=dict(first_read='actual ld_start phase*25', subsequent_reads='actual ld_a+1',
                       enable='ld_start || (ld_run && ld_k<CW-1)', banks=1,
                       payload_demux=0, added_sequential_bits=0),
        geometry=dict(parent_bbox_um=parent_box,macro_bbox_um=rectangle,
                      macro_body_um2=m['area']['macro_area_um2'],halo_um=halo,
                      macro_reserved_um2=reserved_area,remaining_parent_um2=available,
                      parent_cell_upper_um2=parent_upper,added_logic_upper_um2=added_logic_upper,
                      combined_cell_placement_upper_um2=(parent_upper+added_logic_upper)/.5,
                      analytical_fit=True,routed_fit=False),
        routing=dict(local_provider_signal_bits=12+1+48,clock_bits=1,
                     local_tracks_upper=62,channel_capacity_tracks=4291,
                     capacity_basis='existing native parent M4/M6 model, half clock/PG reserve',
                     pin_escape_and_placement_unqualified=True),
        clocks=dict(root='same actual free clk as loader/D3',macro='free clk; no new divider/gate',
                    capture='original loader c_d at next free edge',period_ps=period,corners=timing),
        latency=dict(added_loader_cycles=0,added_engine_stages=0,source_configuration_service_cycles=27,
                     mechanism='macro reads first address on ld_start edge; one-word lookahead thereafter; original c_d/c_v/c_a sequence unchanged',
                     token_rate_credit=0,exact_gate_required=True),
        build_ready_for_minimum_component=True,full_field_build_ready=False,
        physical_qualified=False,missing_input_clocks=True)


def composed_capture_model(root, terms_path):
    """Fill measured local cells/load/setup; leave wire and clock insertion open."""
    result = model(root)
    terms = json.loads(terms_path.read_text())
    baseline = root / terms['source_model']
    assert hashlib.sha256(baseline.read_bytes()).hexdigest() == terms['source_model_sha256']
    assert json.loads(baseline.read_text()) == result
    assert terms['setup_uncertainty_ps'] == 60 and terms['hold_uncertainty_ps'] == 25
    assert abs(terms['clock_period_ps'] - result['clocks']['period_ps']) < 1e-6
    assert terms['new_pipeline_stages'] == 0
    for corner in ('SS', 'FF'):
        for mode in ('min', 'max'):
            row = terms['reported_capture_paths'][corner][mode]
            path = root / row['file']
            assert hashlib.sha256(path.read_bytes()).hexdigest() == row['sha256']
            assert row['unique_endpoints'] == 48
    result['mapped_capture'] = terms
    result['inputs'][str(terms_path.relative_to(root))] = hashlib.sha256(terms_path.read_bytes()).hexdigest()
    result['clocks']['local_capture_cells_load_and_setup_priced'] = True
    result['clocks']['routed_wire_clock_slew_and_insertion_priced'] = False
    result['clocks']['SS_remaining_before_wire_and_skew_ps'] = terms['SS_worst']['remaining_before_wire_and_relative_skew_ps']
    return result


if __name__ == '__main__':
    import argparse
    import uarch_model
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--capture-terms', type=Path)
    args=parser.parse_args()
    args.out.parent.mkdir(parents=True,exist_ok=True)
    result = (composed_capture_model(Path(__file__).resolve().parents[1], args.capture_terms.resolve())
              if args.capture_terms else uarch_model.dsrom_v9_cfg_context_model())
    args.out.write_text(json.dumps(result,indent=2)+'\n')
