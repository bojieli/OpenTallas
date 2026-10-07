#!/usr/bin/env python3
"""Budget physical boundary delay before repairing the failed full front_s.

No timing constraint or RTL is modified. Actual cells/placement and fresh routed
SS/FF measurements remain mandatory; one observed arc is not a corner bound.
"""
import json
from pathlib import Path


def model():
    output_bits = 3108
    max_cells = 3 * output_bits
    # Same ASAP7 BUFx2 master used in the source-pinned QX10 boundary model.
    cell_area = 0.0729
    return dict(schema='opentallas.hbm.smh.front_s_hold.v1',
        original_source='f7f1a0ee4bfd331c9d6bb873d9a772a5fa88cb48',
        evidence='results/physical/hbm_smh_front_s_m3f_failure_20261007',
        default_enabled=False, adopted=False,
        measured=dict(SS_setup_ps=7.357004, SS_output_ps=152.749542,
            FF_hold_ps=-21.096708, FF_internal_ps=13.878565, DRC=0,
            fp_d39_launch_ps=276.56, fp_d39_arrival_ps=332.90,
            fp_d39_required_ps=354.00, output_buffer_FF_arc_ps=15.96),
        unchanged_contract=dict(streaming_period_ps=833, route_period_ps=770,
            setup_uncertainty_ps=60, hold_uncertainty_ps=25,
            neighbor_SS_latency_ps=519, neighbor_FF_latency_ps=329,
            FF_output_latency_compensation_ps=190,
            interpiece_setup_skew_ps=90, die_setup_skew_ps=150,
            output_load_fF=2, constraint_changes=0),
        proposal=dict(kind='Explicit noninverting delay cells on dedicated data boundary branches',
            cell='BUFx2_ASAP7_75t_R', provisional_cells_per_failing_output=3,
            chosen_endpoint_count=None,
            required_added_FF_delay_ps=15 + 21.096708,
            allowed_added_SS_delay_ps=152.749542 - 15,
            three_observed_FF_arcs_ps=3 * 15.96,
            three_arc_sum_is_validated_bound=False,
            selection='Fresh full output SS/FF inventory; no single fp_d bit extrapolation',
            internal_hold='Fresh list of every D pin below +15ps; size separate dedicated branches',
            setup_successor_owner='hbm/sm_views protected cached-nonempty FIFO',
            setup_successor_changes_pins_or_cycles=False),
        measured_endpoint_inventory=dict(output_count=3108, FF_outputs_below25ps=2794,
            internal_D_pins_below15ps=4, dedicated_output_branches=True,
            candidate_output_buffer_count=2794*3, candidate_internal_buffer_count=4,
            candidate_total_buffer_count=8386, candidate_added_area_um2=8386*.0729,
            eligible_output_min_SS_slack_ps=246.3385,
            internal_endpoint_min_SS_slack_ps=614.4506,
            observed_existing_buffer_FF_arc_range_ps=[13.762,17.2584],
            observed_existing_buffer_SS_arc_range_ps=[28.4662,38.7940],
            new_chain_delay_measured=False,
            evidence='Fresh preserved-ODB corner inventory from fleet_live/blocked_queue_audit'),
        sizing=dict(MACs_per_cycle_delta=0, memory_bytes_per_cycle_delta=0,
            output_bits_per_cycle=output_bits, added_boundary_bits_per_cycle=0,
            fp_d_width=1098, engine_replicas_per_SM=1, SMs_per_HBM_die=32,
            maximum_output_delay_cells=max_cells,
            maximum_output_delay_cell_area_um2=max_cells*cell_area,
            internal_delay_area_not_yet_sized=True,
            existing_logic_area_um2=5597.77,
            output_only_area_upper_fraction=max_cells*cell_area/5597.77,
            slot_um=[432,241.92],
            output_only_logic_area_fraction=(5597.77+max_cells*cell_area)/(432*241.92),
            added_per_output_local_net_segments_upper=3,
            extra_die_channel_tracks=0,
            local_pin_channel_fit='Requires actual endpoint locations and incremental legalization/DRC',
            added_clock_sinks=0, added_registers=0, added_latency_cycles=0,
            composed_per_user_token_latency_delta_cycles=0,
            applicability=['Qwen3-8B HBM','DeepSeek-V4.1 HBM'], ROM_design_delta=0),
        gates=['Source/checkpoint identity and unchanged timing budgets',
            'Fresh corner endpoint inventory and actual delay-cell arcs',
            'Dedicated data branch insertion with polarity/connectivity audit',
            'Re-extract after legalization/routing; fresh processes for SS and FF',
            'SS >=15ps, FF >=15ps, DRC0 including outputs and internal paths',
            'Compose with qualified cached-nonempty FIFO setup successor'],
        warning='This model authorizes preparation, not adoption or a claim of physical closure')


if __name__ == '__main__':
    print(json.dumps(model(), indent=2))
