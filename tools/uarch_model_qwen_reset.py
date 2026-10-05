#!/usr/bin/env python3
"""Explicitly selected Qwen reset price extension of the unchanged unified model.

Importing this module does not register or mutate the baseline, change its
presets, or qualify reset/context hardware. The caller selects this price.
"""
import uarch_model as baseline

MODEL_EXTENSION = 'qwen-reset'


def qwen_rom_reset_context_price(tile, die, cells):
    """Additive G0 reset price for the complete source-elaborated Qwen context.

    Source WIDTH inventory is deliberately distinct from mapped pin load.
    The existing bank5 reservation and all failure records remain historical.
    No physical timing, routing fit or token-rate credit is inferred here.
    """
    tile_count = 6144 // 4
    area = cells['actual_library_cell_area_um2']
    # Source fulltile wrapper: ce1/address7/data512/mask512; only CE resets.
    tile_clock_bits = tile['clock_bits'] + 1032
    tile_reset_bits = tile['async_reset_bits'] + 1
    period_ps = 1e12 / 1.2e9
    corners = {}
    for corner, lib in cells['cell_liberty'].items():
        ff = lib['DFFASRHQNx1_ASAP7_75t_R']['nominal_pin_capacitance_fF']
        inv = lib['INVx1_ASAP7_75t_R']['nominal_pin_capacitance_fF']
        corners[corner] = dict(added_clock_cap_fF=2 * ff['CLK'],
            external_reset_cap_fF=2 * ff['RESETN'], stage1_QN_load_fF=inv['A'],
            stage1_INV_load_fF=ff['D'], stage2_QN_load_fF=inv['A'],
            stage2_INV_metadata_root_load_fF=lib['BUFx4_ASAP7_75t_R']['nominal_pin_capacitance_fF']['A'],
            stage2_INV_other_tile_reset_load_fF=None,
            note='Pin-only nominal inputs. Wire, CTS and all other tile reset loads require the actual mapped parent.')
    return dict(tile_count_per_die=tile_count, dies=4, root_cells_per_tile=4,
        root_cell_area_um2_per_tile=area,
        root_cell_area_mm2_per_die=tile_count * area / 1e6,
        prior_bank5_control_reservation_um2_per_tile=23.1822,
        root_plus_prior_reservation_um2_per_tile=23.1822 + area,
        complete_distribution_and_CTS_area_um2_per_tile=None,
        source_logic_tile_clock_bits=tile['clock_bits'],
        source_logic_tile_async_reset_bits=tile['async_reset_bits'],
        source_fulltile_KV_fill_clock_bits=1032,
        source_fulltile_KV_fill_reset_bits=1,
        source_tile_clock_bits=tile_clock_bits,
        source_tile_async_reset_bits=tile_reset_bits,
        metadata_reset_bits_already_on_15BUF_tree=90,
        remaining_tile_async_reset_bits=tile_reset_bits - 90,
        clock_inventory_after_root_and_physical_memories=tile_clock_bits + 2 + 10 + 2,
        memory_clock_note='10 ROM and 2 KV physical macro CLK ports added to logic-only inventory; macros themselves are not reset.',
        source_die_core_clock_bits=die['clock_bits'],
        source_die_core_async_reset_bits=die['async_reset_bits'],
        source_die_plus_all_tile_clock_bits=die['clock_bits'] + tile_count * tile_clock_bits,
        source_die_plus_all_tile_async_reset_bits=die['async_reset_bits'] + tile_count * tile_reset_bits,
        source_census_note='Pre-opt proc WIDTH totals, not mapped pin survival. Core includes bench/sequencer, spine and SU; hosted tile fabric added exactly once.',
        startup_release_edges=2, first_downstream_accept_edge=3,
        release_two_cycle_budget_ps=2 * period_ps,
        first_accept_edge_time_ps=3 * period_ps,
        startup_added_cycles_if_previous_accept_edge1=2,
        bench_start_added_cycles_if_first_sample_cyc8=0,
        startup_serial_domain_cycles=None,
        steady_token_added_cycles=0, per_layer_added_cycles=0,
        rate_gain_percent=0, adoption_1percent_gate=False,
        root_MACs_per_cycle=0, root_memory_bytes_per_cycle=0,
        root_boundary_bits=dict(external_reset=1, streaming_clk=1, tile_reset=1),
        per_die_root_replicas=tile_count,
        upstream_external_reset_added_nominal_pins_per_die=2 * tile_count,
        reset_replica_muxes=0, reset_replica_demuxes=0,
        global_reset_fanout_note='3072 root RESETN pins/die plus separate die/core branch; do not drive them with one assumed ideal source.',
        incremental_global_corridor_signals=0,
        corridor_note='One local root/tile; existing shared reset/clk still require fanout routing. Zero new global signals does not establish routing fit.',
        reset_and_clock_routing_tracks_required=None,
        corridor_track_capacity=None, physical_slot_fit=None,
        source_pin_loads=corners, physical_complete=False,
        setup_period_ps=period_ps, setup_uncertainty_ps=60,
        hold_uncertainty_ps=25, hold_relaxed=False)
