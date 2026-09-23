#!/usr/bin/env python3
"""ROM designs referenced to the shipping Taalas HC1, against same-dataflow HBM.

HC1 is a published design point: Llama-3.1-8B on one 815 mm2 N6 die at 16,960
tok/s per user, batch 1 per chip, 200-250 W. This tool takes its per-die envelope
as the ROM die basis (capacity, weight-select throughput, per-stage latency) and
builds Qwen3-8B and DeepSeek-V4.1-Flash machines from it. The HBM baseline gets the
same hardwired dataflow and stage latencies, so the comparison isolates the weight
store, not software overhead. Everything is analytical; nothing is simulated.

HC1 publishes no microarchitecture. Its token time is split two ways, which
bracket the truth: (i) throughput-bound, every cycle spent selecting weights at
rate R; (ii) latency-bound, a fixed time per dependent stage. Both are reported.
"""
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUTS = ['configs/hardware/technology.json', 'configs/hardware/technology_inputs.json',
          'configs/models/anchors/llama-3.1-8b.json', 'configs/models/qwen3-8b.json',
          'configs/models/candidates/deepseek-v4.1-flash.json',
          'results/architecture/v41_dense_inventory.json',
          'configs/architecture/rom_hbm_review_v3.json', 'configs/architecture/rom_density_evidence.json',
          'tools/audit_hc1_referenced_designs.py']
LINK_DELAYS_US = (0.1, 0.25, 0.5, 1.0)       # one-way die-to-die delivery, assumed sweep
LINK_BYTES_S = 900e9                          # B300 NVLink 1.8 TB/s bidirectional / 2
CONTEXTS = (8192, 65536)
# Weight-select cells per stored weight. HC1 stores a 3/6-bit mixture with one
# transistor per <=4-bit weight (Bajic); wider formats are assumed to split into
# 4-bit nibble cells with shift-add, which is not published.
CELLS = {'FP4': 1, 'F8_E4M3': 2, 'BF16': 4, 'F32': 8}
BYTES = {'FP4': 0.5, 'F8_E4M3': 1, 'BF16': 2, 'F32': 4}
EXPERT_WEIGHTS = 3 * 5120 * 2304
EXPERT_BYTES = 18_800_640                     # FP4 payload plus 1x32 E8M0 scales
LLAMA_STAGES_PER_LAYER = 5                    # norm+qkv, attention, o, norm+gate/up, down
SINKHORN_US = 0.2                             # 20 iterations x 2 normalizations x ~5 cycles at 1 GHz, assumed
HBM_DEPENDENT_LATENCY_US = 0.3                # first data-dependent expert access, assumed
ATTENTION_MAC_MM2 = 50                        # provisioned on BOTH die types for attention and index scans


def load():
    return [json.loads((ROOT / n).read_text()) for n in INPUTS[:-1]]


def hc1_envelope(tech, llama):
    spec = tech['reference_parts']['taalas_hc1']
    rate = spec['published_tokens_s_per_user']['value']
    token_s = 1 / rate
    ctx = int(spec['input_tokens']['value'] + spec['output_tokens']['value'])
    layers, heads, hd = llama['num_layers'], llama['metadata']['num_attention_heads'], llama['metadata']['head_dim']
    attention_macs = 2 * layers * heads * hd * ctx
    active = llama['active_parameters']
    transistors = spec['transistors']['value']
    return {
        'die_mm2': spec['die_area_mm2']['value'], 'node': spec['node'],
        'published_tokens_s_per_user': rate, 'token_us': token_s * 1e6,
        'weights_per_die_lower_bound': llama['total_parameters'],
        # (i) Throughput reading: every active weight selected once per token.
        'select_rate_cells_s': active / token_s,
        # (ii) Latency reading: the whole token is dependent stages.
        'stage_latency_us': token_s * 1e6 / (layers * LLAMA_STAGES_PER_LAYER),
        'attention_mac_s_lower_bound': attention_macs / token_s,
        'power_w_band': [spec['power_w']['range_low'], spec['power_w']['range_high']],
        'sram_bytes_upper_bound_from_transistors': (transistors - llama['total_parameters']) / 6 / 8,
        'kv_bytes_at_published_context_bf16': ctx * sum(g['count'] * g['entry_bytes'] for g in llama['attention_groups']),
        'context_tokens': ctx,
        'grades': {'die_mm2': 'published', 'tokens_s': 'published, self-run by Taalas, BS=1 per chip',
                   'weights_per_die': 'derived: Llama-3.1-8B holds all 8.03B weights on the die',
                   'one_cell_per_weight': 'published statement (Bajic), mechanism unpublished',
                   'power': 'published band, secondary press'},
    }


def mac_rate_per_mm2(ti):
    """FP8 MACs/s per mm2 of whole die, from the B300 published dense FP8 rate over two reticle dies."""
    b = ti['source_facts']['b300']
    return b['fp8_dense_ops_s'] / 2 / (2 * 815)


def layer_inventory(inv):
    """Per-layer dense weights by dtype, split into attention-side and FFN-side work."""
    attn, ffn = defaultdict(lambda: defaultdict(float)), defaultdict(lambda: defaultdict(float))
    head = defaultdict(float)
    for r in inv['tensor_rows']:
        n, dt = r['name'], r['dtype']
        if dt not in CELLS or r['bytes'] < 65536:        # norms, biases, scales: SRAM constants
            continue
        w = r['bytes'] / BYTES[dt]
        if not n.startswith('layers.'):
            head[dt] += w
            continue
        layer = int(n.split('.')[1])
        side = ffn if ('.ffn.' in n or 'hc_ffn' in n) else attn
        side[layer][dt] += w
    return attn, ffn, head


def cells(weights):
    return sum(CELLS[d] * w for d, w in weights.items())


def nbytes(weights):
    return sum(BYTES[d] * w for d, w in weights.items())


def attention_work(op, groups, layer, ctx):
    """MACs for attention core and index scan at one decode position."""
    ratio = op['compress_ratios'][layer]
    heads, hd = op['num_attention_heads'], op['head_dim']
    window = op['window_tokens']
    selected = window + (min(op['index_topk'], ctx // ratio) if ratio else 0)
    core = 2 * heads * hd * selected
    scan = 0
    if layer in op['index_source_layer_ids'] and ratio:
        entries = ctx // ratio
        if layer in (24, 28, 32, 36):
            entries = min(entries, 16384)
        scan = op['index_heads'] * op['index_head_dim'] * entries
    return core, scan


def v41_stages(op, layer):
    attn = 6 + (2 if layer in op['index_source_layer_ids'] and op['compress_ratios'][layer] else 0)
    attn += 1 if layer in op['engram_layer_ids'] else 0
    return attn, 6                               # FFN: hc, norm+router, top-k, w13, w2, combine


def rom_v41(env, ti, m, inv, d_us, ctx, reading, route):
    """HC1-class dies: two per layer (dense + half the experts, other half), head over spare capacity."""
    op = m['metadata']['operator_config']
    attn_w, ffn_w, head_w = layer_inventory(inv)
    capacity = env['weights_per_die_lower_bound'] * (1 - ATTENTION_MAC_MM2 / env['die_mm2'])
    R = env['select_rate_cells_s']
    mac_s = max(env['attention_mac_s_lower_bound'], ATTENTION_MAC_MM2 * mac_rate_per_mm2(ti))
    s0 = env['stage_latency_us'] if reading == 'latency' else 0.0
    experts_cells = op['num_routed_experts'] * EXPERT_WEIGHTS * CELLS['FP4']
    total_us, dies, worst_fill = 0.0, 0, 0.0
    for layer in range(m['num_layers']):
        a_cells, f_cells = cells(attn_w[layer]), cells(ffn_w[layer])
        need = a_cells + f_cells + experts_cells
        per_layer = math.ceil(need / capacity)
        dies += per_layer
        worst_fill = max(worst_fill, need / (per_layer * capacity))
        core, scan = attention_work(op, m['attention_groups'], layer, ctx)
        sa, sf = v41_stages(op, layer)
        attn_us = max(sa * s0, a_cells / R * 1e6 + (core + scan) / mac_s * 1e6 + 2 * SINKHORN_US / 2)
        on_a, on_b = {'spread': (3, 3), 'concentrated_on_dense_die': (6, 0),
                      'concentrated_off_die': (0, 6)}[route]
        a_path = max(sf * s0, (f_cells + on_a * EXPERT_WEIGHTS) / R * 1e6 + SINKHORN_US)
        b_path = 2 * d_us + max(2 * s0, on_b * EXPERT_WEIGHTS / R * 1e6) if on_b else 0.0
        total_us += attn_us + max(a_path, b_path) + d_us
    h_dies = 8
    head_us = 2 * d_us + max(s0, cells(head_w) / h_dies / R * 1e6)
    total_us += head_us
    return {'dies': dies, 'area_mm2': dies * env['die_mm2'], 'max_die_fill': worst_fill,
            'token_us': total_us, 'tokens_s_per_user': 1e6 / total_us,
            'power_w_upper': dies * env['power_w_band'][1]}


def hbm_die(c, ti):
    sram_mm2 = 815 - c['hbm_phy_area_mm2_per_die_assumed'] - sum(c['extra_area_caps_mm2_per_die'].values()) - ATTENTION_MAC_MM2 - 50
    b = ti['source_facts']['b300']
    sram = sram_mm2 * 3.65e6                      # published 7 nm UHD SRAM macro density
    return {'hbm_bytes_s': b['hbm_bandwidth_bytes_s'] / 2, 'hbm_bytes': b['hbm_capacity_bytes'] / 2,
            'sram_bytes': sram, 'sram_bytes_s': sram * 47.5e12 / 900e6,   # GC200 delivered rate per stored byte
            'mac_s': (ATTENTION_MAC_MM2 + 50) * mac_rate_per_mm2(ti),
            'power_w': b['system_allocated_power_w'] / 2}


def hbm_v41(env, ti, c, m, inv, n_dies, stripe, d_us, ctx, reading, cache):
    """Same dataflow and stage latencies; dense cached in SRAM, experts striped over `stripe` dies from HBM."""
    op = m['metadata']['operator_config']
    die = hbm_die(c, ti)
    attn_w, ffn_w, head_w = layer_inventory(inv)
    dense_bytes = sum(nbytes(attn_w[l]) + nbytes(ffn_w[l]) for l in attn_w) + nbytes(head_w)
    routed_total = m['num_layers'] * op['num_routed_experts'] * EXPERT_BYTES
    capacity_ok = n_dies * die['hbm_bytes'] >= dense_bytes + routed_total
    spare = n_dies * die['sram_bytes'] - dense_bytes
    if spare < 0 or stripe > n_dies:
        return None
    hit = min(1.0, spare / routed_total) if cache == 'expected_hit' else 0.0
    s0 = env['stage_latency_us'] if reading == 'latency' else 0.0
    total_us = 0.0
    for layer in range(m['num_layers']):
        core, scan = attention_work(op, m['attention_groups'], layer, ctx)
        sa, sf = v41_stages(op, layer)
        attn_us = max(sa * s0, nbytes(attn_w[layer]) / die['sram_bytes_s'] * 1e6
                      + (core + scan) / die['mac_s'] * 1e6 + SINKHORN_US)
        a_path = max(sf * s0, nbytes(ffn_w[layer]) / die['sram_bytes_s'] * 1e6 + SINKHORN_US)
        per_die = 6 * EXPERT_BYTES / stripe
        read = per_die * ((1 - hit) / die['hbm_bytes_s'] + hit / die['sram_bytes_s']) * 1e6
        reduce = d_us + stripe * 5120 * 4 / LINK_BYTES_S * 1e6 if stripe > 1 else 0.0
        b_path = 2 * d_us + (HBM_DEPENDENT_LATENCY_US if hit < 1 else 0) + max(2 * s0, read) + reduce
        total_us += attn_us + max(a_path, b_path) + d_us
    head_us = 2 * d_us + max(s0, nbytes(head_w) / 8 / die['sram_bytes_s'] * 1e6)
    total_us += head_us
    return {'dies': n_dies, 'stripe': stripe, 'capacity_ok': capacity_ok, 'expert_cache_hit': hit,
            'token_us': total_us, 'tokens_s_per_user': 1e6 / total_us,
            'power_w': n_dies * die['power_w']}


def best_hbm(env, ti, c, m, inv, n_dies, d_us, ctx, reading, cache):
    rows = [hbm_v41(env, ti, c, m, inv, n_dies, s, d_us, ctx, reading, cache) for s in (1, 2, 4, 8, 16, 32, 64)]
    rows = [r for r in rows if r and r['capacity_ok']]
    return min(rows, key=lambda r: r['token_us']) if rows else None


def qwen_single_die(env, ti, c, q, reading):
    """Qwen3-8B hardwired on one HC1-class die at HC1's weight format, versus one HBM die."""
    bits = 3.5                                    # HC1 technology.json assumption for its 3/6-bit mixture
    active, total = q['active_parameters'], q['total_parameters']
    layers = q['num_layers']
    rom_us = (active / env['select_rate_cells_s'] * 1e6 if reading == 'throughput'
              else layers * LLAMA_STAGES_PER_LAYER * env['stage_latency_us'])
    kv = {ctx: ctx * sum(g['count'] * g['entry_bytes'] for g in q['attention_groups']) for ctx in (2048, 8192)}
    die = hbm_die(c, ti)
    weight_bytes = active * bits / 8
    cached = min(weight_bytes, die['sram_bytes'])
    hbm_us = max(LLAMA_STAGES_PER_LAYER * layers * (env['stage_latency_us'] if reading == 'latency' else 0),
                 ((weight_bytes - cached) / die['hbm_bytes_s'] + cached / die['sram_bytes_s']) * 1e6)
    bf16_us = q['dense_weight_bytes'] / die['hbm_bytes_s'] * 1e6
    return {'reading': reading, 'weight_bits': bits,
            'capacity_ratio_to_hc1': total / env['weights_per_die_lower_bound'],
            'kv_bytes': kv, 'kv_fits_sram_upper_bound': {k: v <= env['sram_bytes_upper_bound_from_transistors'] for k, v in kv.items()},
            'rom_token_us': rom_us, 'rom_tokens_s': 1e6 / rom_us,
            'hbm_same_format_token_us': hbm_us, 'hbm_same_format_tokens_s': 1e6 / hbm_us,
            'hbm_bf16_shipped_tokens_s': 1e6 / bf16_us,
            'rom_over_hbm_same_format': hbm_us / rom_us,
            'rom_over_hbm_bf16': bf16_us / rom_us,
            'energy_mj_per_token': {'rom_at_250W': 250 * rom_us * 1e-3, 'hbm_die': die['power_w'] * hbm_us * 1e-3}}


def main():
    tech, ti, llama, qwen, v41, inv, c, _ = load()
    env = hc1_envelope(tech, llama)
    qwen_rows = [qwen_single_die(env, ti, c, qwen, r) for r in ('throughput', 'latency')]
    v41_rows = []
    for ctx in CONTEXTS:
        for reading in ('throughput', 'latency'):
            for d in LINK_DELAYS_US:
                routes = {r: rom_v41(env, ti, v41, inv, d, ctx, reading, r)
                          for r in ('spread', 'concentrated_on_dense_die', 'concentrated_off_die')}
                rom = routes['spread']
                worst = max(routes.values(), key=lambda r: r['token_us'])
                die = hbm_die(c, ti)
                equal_power = max(1, math.floor(rom['power_w_upper'] / die['power_w']))
                hbm = {}
                for label, n in (('equal_area', rom['dies']), ('equal_power', equal_power)):
                    hbm[label] = {cache: best_hbm(env, ti, c, v41, inv, n, d, ctx, reading, cache)
                                  for cache in ('all_miss', 'expected_hit')}
                v41_rows.append({
                    'context': ctx, 'reading': reading, 'link_delay_us': d,
                    'rom': rom, 'rom_worst_route': worst, 'hbm': hbm,
                    'rom_over_hbm_equal_area_all_miss': hbm['equal_area']['all_miss']['token_us'] / rom['token_us'],
                    'rom_over_hbm_equal_area_expected_hit': hbm['equal_area']['expected_hit']['token_us'] / rom['token_us'],
                    'rom_over_hbm_equal_power_all_miss': hbm['equal_power']['all_miss']['token_us'] / rom['token_us']
                    if hbm['equal_power']['all_miss'] else None})
    out = {
        'schema': 'opentallas.hc1-referenced-designs.v1',
        'status': 'analytical_design_envelope_referenced_to_published_hc1_not_simulated',
        'hc1_envelope': env, 'hbm_die': hbm_die(c, ti), 'mac_rate_per_mm2_fp8': mac_rate_per_mm2(ti),
        'qwen3_8b_single_die': qwen_rows, 'v41_flash_arrays': v41_rows,
        'assumptions': [
            'ROM die = HC1 envelope: >=8.03B weight cells per 815 mm2, select rate and stage latency derived from 16,960 tok/s on Llama-3.1-8B. HC1 figures are self-run by Taalas.',
            'Cells per weight: FP4 1, FP8 2, BF16 4, F32 8 (nibble cells with shift-add). Only the <=4-bit case is supported by a published statement.',
            'Both die types reserve 50 mm2 of FP8 MACs (B300-derived density) for attention and index scans; the ROM die loses that share of weight capacity.',
            'HBM die: B300 per-die bandwidth, capacity and system power (published/2), SRAM at the published 7 nm UHD density with GC200 delivered rate per byte, same stage latencies as ROM in the latency reading.',
            'Link: one-way die-to-die delay swept, 900 GB/s per direction. Collectives are one hop plus serialization; no software overhead on either side.',
            'V4.1 native formats: routed FP4, dense FP8, head/router/compressor BF16, hyper-connection F32. No quantization beyond the checkpoint.',
            'Qwen3-8B ROM uses HC1\'s 3.5-bit mixture, which is NOT the shipped BF16 contract and changes model quality.'],
        'limits': [
            'Neither reading of HC1 is its microarchitecture; the true split lies between them or outside if HC1 has idle slack.',
            'Stage counts per V4.1 layer are an operator census, not a scheduled RTL pipeline. Top-k, Sinkhorn and norms are folded into stages.',
            'Expert routes: spread (3+3) is the reported point; concentrated routes are in rom_worst_route. Multi-user queueing is not modelled.',
            'Power is an upper bound at the per-die band; no energy model is claimed for either side beyond published die/system power.',
            'Engram table lookups are assumed prefetched from token ids before the layer needs them; their external memory is not priced here.'],
        'input_sha256': {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in INPUTS},
    }
    (ROOT / 'results/architecture/hc1_referenced_designs.json').write_text(json.dumps(out, indent=2, sort_keys=True) + '\n')
    print(json.dumps({k: round(v, 4) if isinstance(v, float) else v for k, v in env.items() if k != 'grades'}, indent=1))
    for q in qwen_rows:
        print('qwen', q['reading'], round(q['rom_tokens_s']), round(q['hbm_same_format_tokens_s']), round(q['hbm_bf16_shipped_tokens_s']),
              round(q['rom_over_hbm_same_format'], 2), q['kv_fits_sram_upper_bound'], round(q['capacity_ratio_to_hc1'], 3))
    for r in v41_rows:
        ea, ep = r['hbm']['equal_area'], r['hbm']['equal_power']
        print(r['context'], r['reading'][:4], r['link_delay_us'], r['rom']['dies'], round(r['rom']['tokens_s_per_user']),
              round(r['rom_worst_route']['tokens_s_per_user']), '| HBM eqA miss', round(ea['all_miss']['tokens_s_per_user']), 'S', ea['all_miss']['stripe'],
              'hit', round(ea['expected_hit']['tokens_s_per_user']), '| eqP', ep['all_miss'] and (ep['all_miss']['dies'], round(ep['all_miss']['tokens_s_per_user'])),
              '| ratios', round(r['rom_over_hbm_equal_area_all_miss'], 2), round(r['rom_over_hbm_equal_area_expected_hit'], 2),
              r['rom_over_hbm_equal_power_all_miss'] and round(r['rom_over_hbm_equal_power_all_miss'], 2))


if __name__ == '__main__':
    main()
