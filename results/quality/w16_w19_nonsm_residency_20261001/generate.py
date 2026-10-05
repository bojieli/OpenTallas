"""Header/ISA logical extents; proposed striping, never a physical allocation gate."""
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = '35d0bdf7520a679cf721e521f6de56017f1f23c7'


def source(path):
    return subprocess.check_output(['git', 'show', f'{BASE}:{path}'], cwd=ROOT)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def counts(rows, block, ranks=96):
    cycles, tail = divmod(rows, block * ranks)
    return [cycles * block + min(block, max(0, tail - r * block)) for r in range(ranks)]


def stripe_bytes(size):
    """Proposal: logical line l -> controller l%4, local line l//4.

    Allocate full 128B lines; family base alignment is independently 256B.
    This function does not choose a base or place a family beside SM weights.
    """
    return [n * 128 for n in counts((size + 127) // 128, 1, 4)]


def generate():
    paths = ['compiler/models/deepseek-v4.1-flash/inference_config.json',
             'tools/w19_hbm_tp96_isa.py', 'tools/hdc_golden_v41.py',
             'tools/rtl_v41_fullshape_layer_campaign.py', 'tools/arch_budget_v41.py',
             'results/rtl/w19_hbm_tp96_program_oreduce.json',
             'results/uarch/w16_w19_address_prerequisite_20261001/prerequisite_r2.json']
    blobs = {p: source(p) for p in paths}
    config = json.loads(blobs[paths[0]])
    program = json.loads(blobs[paths[5]])
    inventory_bytes = (HERE / 'non_SM_source_inventory.json').read_bytes()
    inventory = json.loads(inventory_bytes)
    items = inventory['items']
    assert len(items) == 542 and sum(t['stored_bytes'] for t in items) == 204240953808
    assert program['tp'] == 96 and program['key_block'] == 8
    ctx = program['position'] + 1
    assert ctx == 1048576
    hc = [t for t in items if t['tensor'].endswith(('.hc_attn_fn', '.hc_ffn_fn'))]
    assert len(hc) == 80 and all(t['shape'] == [24, 20480] and t['dtype'] == 'F32' for t in hc)
    embedding = next(t for t in items if t['tensor'] == 'embed.weight')
    engrams = []
    for layer in config['engram_layer_ids']:
        weight = next(t for t in items if t['tensor'] == f'layers.{layer}.engram.embed.weight')
        scale = next(t for t in items if t['tensor'] == f'layers.{layer}.engram.embed.scale')
        assert weight['shape'][0] == scale['shape'][0] and weight['shape'][1] == 256 and scale['shape'][1] == 8
        rc = counts(weight['shape'][0], 1)
        engrams.append(dict(layer=layer, rows=weight['shape'][0], owner='id % 96',
                            rank_rows=rc, stored_bytes=weight['stored_bytes'] + scale['stored_bytes'],
                            stored_row_bytes=264, logical_rank_stored_bytes=[n * 264 for n in rc],
                            physical_consumer_format=None, stack_mapping=None))
    kv = []
    for layer in config['kv_source_layers']:
        ratio = config['compress_ratios'][layer]
        rc = counts(ctx // ratio, 8)
        kv.append(dict(layer=layer, compression_ratio=ratio, rows=ctx // ratio,
                       rank_rows=rc, owner='(row // 8) % 96',
                       reference_ckv_row_bytes=config['head_dim'] * 4,
                       reference_index_row_bytes=config['index_head_dim'] * 4))
    total_rank_rows = [sum(v['rank_rows'][r] for v in kv) for r in range(96)]
    window_rank = config['n_layers'] * config['window_size'] * config['head_dim'] * 4
    engram_bytes = sum(v['stored_bytes'] for v in engrams)
    hc_bytes = sum(v['stored_bytes'] for v in hc)
    residual = inventory['stored_bytes'] - embedding['stored_bytes'] - engram_bytes
    prereq = json.loads(blobs[paths[6]])
    return dict(
        schema='opentallas.w16.nonsm-logical-residency-proposal.v1',
        source_commit=BASE,
        source_pins={p: digest(b) for p, b in blobs.items()},
        inventory_commit='10a4071fb', inventory_sha256=digest(inventory_bytes),
        scope='Single-user AR at post-token 1M context. Logical extents and proposed striping only; not physical placement, bandwidth, exactness or adoption qualification.',
        context_tokens=ctx, ranks=96, controllers_per_rank=4,
        stored_text_inventory_bytes=inventory['stored_bytes'],
        embedding=dict(stored_bytes=embedding['stored_bytes'], shape=embedding['shape'],
                       dtype=embedding['dtype'], rank_row_ownership=None,
                       note='ISA fetches current token row then replicates activation; this does not establish table replication or table row ownership.'),
        engram=engrams,
        constants=dict(residual_stored_bytes=residual, hc_matrix_count=len(hc),
                       hc_matrix_stored_bytes=hc_bytes, remaining_text_objects_bytes=residual-hc_bytes,
                       hc_logical_consumers=96, physical_replica_count=None,
                       note='All ranks execute HC mixing on replicated h. Logical consumer count is not proof of 96 physical coefficient copies. Remaining objects require per-tensor consumer classification.'),
        state=dict(kv_sources=kv, index_compute_sources=config['index_source_layers'],
                   note='ISA index backing arrays belong to four KV sources, not eight index-compute layers. FP32 arrays hold quantized values; no physical packed writer contract.',
                   total_rank_rows=total_rank_rows,
                   reference_ckv_bytes=sum(total_rank_rows)*config['head_dim']*4,
                   reference_index_bytes=sum(total_rank_rows)*config['index_head_dim']*4,
                   replicated_window_reference_bytes_per_rank=window_rank,
                   replicated_window_reference_bytes_all_ranks=window_rank*96,
                   reference_rank_ckv_index_bytes=[n*(config['head_dim']+config['index_head_dim'])*4 for n in total_rank_rows],
                   entering_open_group_reference_bytes=3*2*config['head_dim']*4,
                   entering_open_group_owner=63, post_token_open_group_rows=0,
                   transient_workspace_and_append_capacity=None,
                   physical_ckv_row_bytes=None, physical_index_row_bytes=None, physical_window_row_bytes=None,
                   analytical_row_bytes={'CKV':288, 'index':68, 'window':528},
                   analytical_formats_are_actual_consumer_contract=False),
        striping_proposal=dict(status='PROPOSED_NOT_FROZEN', line_bytes=128,
                               family_base_alignment_bytes=256,
                               controller='floor(family_relative_byte_offset / 128) % 4',
                               controller_local_offset='floor(family_relative_byte_offset / 512)*128 + byte_offset%128',
                               scope='Within a rank-owned family only. No rank ownership changes; no reuse of SM quadrants.',
                               reference_state_controller_bytes_per_rank=[stripe_bytes(n*(config['head_dim']+config['index_head_dim'])*4) for n in total_rank_rows],
                               note='Combined reference extent illustration only; actual family boundaries, format and bases unknown.'),
        routes_and_ports=dict(
            hbm_controllers_per_rank=4, physical_port_bytes_per_cycle=None,
            engram_route='Hash request -> id%96 owner -> local four-controller proposal -> requesting activation consumer; request list multiplicity/coalescing and return format pending.',
            kv_index_route='Sequence block8 -> owner rank; index scoring local then distributed candidate selection, CKV gather to attention consumers. Local state writes preserve owner.',
            window_route='Window replicated across96 ranks; append distribution/producer route and physical consumer format pending.',
            constants_route='HC consumers96; replication versus remote coefficient service unresolved.',
            embedding_route='Current row lookup -> replicated initial h; table owner and broadcast path unresolved.',
            noc_bits_per_token=None, routing_tracks=None, latency_cycles=None,
            readiness='Not ready for transport RTL: endpoint ports, schedule, formats, consumer counts and golden-exact packed reads/writes must compose through unified model first.'),
        accepted_weight_authority=dict(path=paths[6], sha256=digest(blobs[paths[6]]),
                                      total_bytes=778764812288, busiest_stack_bytes=2597703680,
                                      sector_address_bits=27, scope='accepted256 SM weights only'),
        physical_non_sm_reservations={k:None for k in ['constants','embedding','Engram','KV','index']},
        full_resident_address_width=None, full_stack_fit=None, adoption=False,
        missing_contracts=[
            'Per-tensor constants consumer classification, precision, physical replication or remote service.',
            'Embedding table row owner; preserve row lookup and activation broadcast without assuming whole-table copies.',
            'Engram FP8/UE8M0 physical consumer format, row packing, request coalescing, response format and endpoint ports.',
            'KV/index/window actual packed state format and golden-exact read/write consumers; FP32 reference and analytical bytes do not freeze hardware.',
            'Open compressor state, score/candidate/gather workspace, append headroom and liveness for persistent versus temporary allocations.',
            'Per-rank per-family 256B-aligned bases, disjoint controller-local ranges including accepted256 weight homes; frozen128B stripe phase and padding.',
            'Four-controller bandwidth and concurrency, NoC topology/ports/traffic multiplicity, clock crossings, routing capacity and critical-path cycles.',
            'Full resident highest addresses and per-stack capacity including all above, before address-width/transport RTL gate.'])


if __name__ == '__main__':
    (HERE / 'logical_residency.json').write_text(json.dumps(generate(), indent=2) + '\n')
