#!/usr/bin/env python3
"""Released-checkpoint correction to the reduced-shape MTP die budget.

Retain the 2026-10-08 plan as history.  Storage is sized in its four-ROM
allocation pairs; two-ROM row-bank units are distinct from native NB2 field pairs.
This record does not invent timing for the missing full-shape accumulator.
"""
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = 'results/arch/mtp_die_20261008/plan.json'
HEADERS = 'results/quality/w16_w17_checkpoint_header_catalogue_20261001'
OUT = 'results/arch/mtp_die_reprice_20261009/model.json'


def read(rel):
    return json.loads((ROOT / rel).read_text())


def released_markov():
    index_path = HEADERS + '/model.safetensors.index.json'
    index = read(index_path)['weight_map']
    tensors, sources = {}, {index_path}
    for part in ('embed', 'head'):
        name = f'mtp.2.markov_head.{part}.weight'
        source = HEADERS + '/headers/' + index[name] + '.header.json'
        sources.add(source)
        row = read(source)[name]
        assert row['dtype'] == 'BF16' and row['shape'] == [129280, 256], row
        size = row['data_offsets'][1] - row['data_offsets'][0]
        assert size == math.prod(row['shape']) * 2
        tensors[part] = dict(tensor=name, shape=row['shape'], bytes=size,
                             dtype=row['dtype'], header=source)
    return tensors, sources


def released_seed():
    index_path = HEADERS + '/model.safetensors.index.json'
    index = read(index_path)['weight_map']
    tensors, sources = {}, {index_path}
    shapes = {'weight': ('mtp.0.main_proj.weight', [5120,15360], 'F8_E4M3', 1),
              'scale': ('mtp.0.main_proj.scale', [160,480], 'F8_E8M0', 1),
              'norm': ('mtp.0.main_norm.weight', [5120], 'BF16', 2)}
    for part, (name, shape, dtype, width) in shapes.items():
        source = HEADERS + '/headers/' + index[name] + '.header.json'
        sources.add(source)
        row = read(source)[name]
        assert row['shape'] == shape and row['dtype'] == dtype
        size = row['data_offsets'][1] - row['data_offsets'][0]
        assert size == math.prod(shape) * width
        tensors[part] = dict(tensor=name, shape=shape, dtype=dtype, bytes=size, header=source)
    return tensors, sources


def compose():
    from dsrom_head_input_staging_model import model as dsrom_head_input_staging_model
    from dsrom_mtp_p2_transport_model import model as p2_transport
    old = read(OLD)
    tensors, sources = released_markov()
    seed, seed_sources = released_seed()
    sources.update(seed_sources)
    sources.add(OLD)
    placement_path = 'results/rtl/dsrom_recovery_20261004/draft/placement.json'
    sources.add(placement_path)
    sources.add('tools/uarch_model.py')
    sources.add('tools/dsrom_head_input_staging_model.py')
    sources.add('tools/dsrom_mtp_p2_transport_model.py')
    placement = read(placement_path)
    for part in seed.values():
        prior = next(t for t in placement['tensors'] if t['tensor'] == part['tensor'])
        assert prior['slices'] is None, 'seed now allocated: remove additive missing-seed assumption'
    source_pair_bytes = 4 * 4096 * 32
    successor_pair_bytes = 2 * 4096 * 32
    heads = old['ds_rom_array']['die_counts']['proposed']['head']
    embedded = tensors['embed']['bytes']
    head = tensors['head']['bytes']
    historical_markov = math.ceil(129280 * 32 * 2 / source_pair_bytes)
    historical_markov += math.ceil(129280 * 32 * 2 / source_pair_bytes / heads)
    new_markov = math.ceil(embedded / source_pair_bytes) + math.ceil(head / source_pair_bytes / heads)
    historical = old['ds_rom_array']['reconciliation']['head_content_pairs_per_die_after']
    new_pairs = historical - historical_markov + new_markov
    head_bundles = math.ceil(129280 / (128 * heads))
    physical_engines = head_bundles * 4
    logical_engines = math.ceil(math.ceil(129280 / heads) / 32)
    seed_bytes = sum(t['bytes'] for t in seed.values())
    seed_pairs_per_rank = math.ceil(math.ceil(seed_bytes / 4) / source_pair_bytes)
    # Native NB2 field pairs contain two row banks, each two real ROMs.
    # BF-double changes logic/slot width, not the physical ROM count per pair.
    globals_bf_slots = math.ceil((5051-2525)/heads)
    embed_bf_slots = math.ceil(embedded/source_pair_bytes)
    # The released FP8 seed projection uses 32 data bytes/word.  Its scales
    # fit in the carrier's 18 spare bits; norm spills beyond 75 full pairs.
    seed_row_bank_units = math.ceil((seed['weight']['bytes']/4+seed['norm']['bytes']/4)/successor_pair_bytes)
    seed_native_pairs = math.ceil(seed_row_bank_units/2)
    regular_slots = 282+seed_native_pairs
    bf_slots = globals_bf_slots+embed_bf_slots
    field_slots = regular_slots+bf_slots
    return dict(
        schema='opentallas.mtp_die_reprice.v1',
        status='STORAGE_SIZED_TIMING_AND_RTL_INCOMPLETE',
        released_markov=tensors,
        released_seed=seed,
        storage=dict(head_dies=heads, allocation_pair_bytes=source_pair_bytes,
                     allocation_pair_ROM4096_macros=4,
                     historical_reduced_K=32, released_K=256,
                     historical_markov_pairs_per_head=historical_markov,
                     released_embed_pairs_per_head=math.ceil(embedded / source_pair_bytes),
                     released_head_pairs_per_head=math.ceil(head / source_pair_bytes / heads),
                     released_markov_pairs_per_head=new_markov,
                     historical_total_pairs_per_head=historical,
                     released_total_pairs_per_head=new_pairs,
                     added_pairs_per_head=new_pairs-historical,
                     all_12_heads_have_primary_reservation=True,
                     successor_element_pair_bytes=successor_pair_bytes,
                     successor_element_pair_ROM4096_macros=2,
                     successor_embed_pairs_per_head=math.ceil(embedded / successor_pair_bytes),
                     successor_head_pairs_per_head=math.ceil(head / successor_pair_bytes / heads)),
        seed_allocation=dict(previous_primary_block_pairs=282,
                             original_seed_slices=None,
                             original_seed_counted_in_primary_capacity=False,
                             bytes_global=seed_bytes, bytes_per_TP4_rank=math.ceil(seed_bytes/4),
                             additional_storage_pairs_per_primary_rank_lower_bound=seed_pairs_per_rank,
                             primary_block_plus_seed_pairs_lower_bound=282+seed_pairs_per_rank,
                             head_dense_storage_with_seed_pairs_lower_bound=new_pairs+seed_pairs_per_rank,
                             qualification='payload bound; bank/port allocation and main_proj RTL timing required'),
        markov_ports=dict(logical_minimum_row_engines=logical_engines,
                          actual_head_bundles=head_bundles, actual_A_elements=physical_engines,
                          row_engines=physical_engines, weight_ROM4096_macros=2*physical_engines,
                          weight_macro_outline_um=[125.28,62.91],
                          raw_weight_macro_area_mm2=2*physical_engines*125.28*62.91/1e6,
                          weight_read_bytes_per_cycle_per_engine=32,
                          aggregate_weight_read_bytes_per_cycle=32*physical_engines,
                          staged_embedding_bytes_per_engine=512,
                          replicated_embedding_bytes=512*physical_engines,
                          embedding_broadcast_bits_per_beat=256, embedding_broadcast_beats=16,
                          local_weight_words_per_macro=256, macro_used_fraction=256/4096,
                          row_launch_interval_cycles=256,
                          measured_component_cycles_after_first_beat=177,
                          integrated_join_cycles=184,
                          measured_driver_head_to_join_ns=184/1.2,
                          driver_source='caf38a801',
                          added_embedding_cache_warmup_cycles=2,
                          reason_two_macros='real SS macro clkq needs two-edge capture; alternating banks preserve q',
                          row_engine_route_area_mm2=None,
                          physical_slot_fit=False),
        typed_head_inventory=dict(
            field_slots=field_slots, regular_NB2_four_ROM_slots=regular_slots,
            BF_double_four_ROM_slots=bf_slots,
            non_lm_head_global_BF_double_slots=globals_bf_slots,
            Markov_embed_BF_double_slots=embed_bf_slots,
            primary_block_regular_slots=282,
            seed_regular_slots=seed_native_pairs,
            seed_two_ROM_row_bank_units=seed_row_bank_units,
            seed_weight_two_ROM_row_bank_units=75, seed_norm_words_per_rank=80,
            seed_scale_carrier_bits=18,
            seed_scale_packing_qualification='proposed repeated scale in carrier; packed proof required',
            field_ROM4096_macros=field_slots*4,
            lm_head_bundles=head_bundles, lm_head_ROM4096_macros=head_bundles*10,
            local_Markov_ROM4096_macros=physical_engines*2,
            total_ROM4096_macros=field_slots*4+head_bundles*10+physical_engines*2,
            configuration_ROM4096x72_per_field_slot=7,
            configuration_ROM4096x72_macros=field_slots*7,
            total_all_ROM_macro_types=field_slots*11+head_bundles*10+physical_engines*2,
            weight_ROM_inventory_excludes_configuration=True,
            native_pair_ROM4096_macros=4,
            native_pair_inventory_sources=['tools/dsrom_s81_component_word_server.py:61',
                'tools/dsrom_s81_expert_placement_sweep.py:85',
                'tools/dsrom_head_source_binding.py:112'],
            BF_double_additional_ROM4096_macros=0,
            supersedes_proposed_inventory=dict(field_slots=696, total_ROM4096_macros=3598,
                reason="two-ROM row-bank units were incorrectly treated as native NB2 pairs"),
            dense_Markov_head_storage_slots_removed=math.ceil(head/source_pair_bytes/heads),
            generator_BF_map_must_be_explicit=True,
            floorplan_slot_fit=False,
            qualification='typed proposed inventory; not equivalent to --pairs631 with heuristic BF ratio'),
        aligned_head_input_staging=dsrom_head_input_staging_model(head_dies=heads, stages=4),
        exact_P2_expert_transport=p2_transport(),
        main_hidden_transport=dict(hidden_dimension=5120, captures=3, bytes_per_value=2,
                                   global_bytes_per_position=30720,
                                   bytes_per_TP4_rank_per_position=7680,
                                   link_bits=512, link_bytes_per_cycle=64,
                                   global_flits_if_single_lane=480,
                                   flits_per_rank_with_TP4_lanes=120,
                                   flits_per_capture_per_rank=40,
                                   rank_lane_tail_us=120/1200,
                                   rank_lane_occupancy_pct_of_historical_II=100*(120/1200)/old['budget']['ds_rom']['II_us'],
                                   RTL_capture_and_identity_qualified=False,
                                   note='SEND_HIDDEN sends ordinary core output; independent HC-mean capture and typed forwarding absent'),
        latency=dict(historical_budget=old['budget']['ds_rom'],
                     historical_budget_qualification='reduced Markov32, cannot support released Markov256 claims',
                     adopted_full_shape_MTP_tok_s=None,
                     requirements=['separate 256-term dot with golden order and logits add',
                                   'released embed lookup and 512-byte broadcast',
                                   'measure successor exactness, accumulation cycles, and join',
                                   'compose additional cycles and qualify SS/FF interfaces']),
        physical=dict(historical_head_case='511-pair headmtp, source0544fca2c',
                      released_head_case_required=True,
                      routing_or_clock_closure_credit=False,
                      vmx_fallback=dict(source_commit='a2f264c8b',
                                        outline_um=[291.6,280.8], gross_um2=81881.28,
                                        prior_gross_um2=60092.928,
                                        added_gross_um2=21788.352,
                                        historical_cells_um2=38438,
                                        estimated_gross_utilization=38438/81881.28,
                                        added_cycles=0,
                                        status='sized_from_prior_cells_route_pending')),
        loader=dict(historical_svc_bits=[904,624], native_svc_bits=[344,275],
                    per_die_native_targets=1, historical_two_die_target_bits=[688,550],
                    native_address_bits=37, physical_stacks=4,
                    external_host_AXI_bits=[226,74], additional_host_DMA_write_data_bits=64,
                    host_minimum_out_bits=404, host_minimum_in_bits=381,
                    host_physical_bits_with_forwarded_clocks=787,
                    status='protocol endpoint RTL and revised chain area remain required'),
        inputs={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sorted(sources)},
    )


if __name__ == '__main__':
    result = compose()
    path = ROOT / OUT
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result['storage'], indent=2))
