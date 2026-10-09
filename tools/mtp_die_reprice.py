#!/usr/bin/env python3
"""Released-checkpoint correction to the reduced-shape MTP die budget.

Retain the 2026-10-08 plan as history.  Storage is sized in its four-ROM
allocation pairs; the proposed two-ROM head successor has a separate unit.
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


def compose():
    old = read(OLD)
    tensors, sources = released_markov()
    sources.add(OLD)
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
    return dict(
        schema='opentallas.mtp_die_reprice.v1',
        status='STORAGE_SIZED_TIMING_AND_RTL_INCOMPLETE',
        released_markov=tensors,
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
        latency=dict(historical_budget=old['budget']['ds_rom'],
                     historical_budget_qualification='reduced Markov32, cannot support released Markov256 claims',
                     adopted_full_shape_MTP_tok_s=None,
                     requirements=['separate 256-term dot with golden order and logits add',
                                   'released embed lookup and 512-byte broadcast',
                                   'measure successor exactness, accumulation cycles, and join',
                                   'compose additional cycles and qualify SS/FF interfaces']),
        physical=dict(historical_head_case='511-pair headmtp, source0544fca2c',
                      released_head_case_required=True,
                      routing_or_clock_closure_credit=False),
        loader=dict(historical_svc_bits=[904,624], native_svc_bits=[678,550],
                    external_host_AXI_bits=[226,74], additional_host_DMA_write_data_bits=64,
                    status='protocol endpoint RTL and revised chain area remain required'),
        inputs={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sorted(sources)},
    )


if __name__ == '__main__':
    result = compose()
    path = ROOT / OUT
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result['storage'], indent=2))
