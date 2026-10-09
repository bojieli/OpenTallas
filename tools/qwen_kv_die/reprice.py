#!/usr/bin/env python3
"""kv-die 2026-10-09: re-price the Qwen3-8B TP4 token on the ROM die + KV die pair with realistic latency.

Per layer the on-ROM-die tile attention (attn_kv 1,361 + softmax_norm 395 cycles of the priced TP4 token,
results/arch/qwen_tp8_vs_sysdie_20261009/result.json tp4.rows) is replaced by the MEASURED attention layer step through
the link (bench.json: CTL / KVN / Q leave the ROM-die faces -> ROM relays -> ROM end -> UCIe macro pair -> KV end ->
KV-die relays -> qkd_seq -> near-HBM attention (the _p successors, R = 8, at the KV-die hub <-> aggregator stage count)
with the KV merge -> RES back to the VM), at ctx 8,192, for the PHY latency best / typical / worst.  The bench's ROM
relay count (ROM_ST) is corrected to the r22k relay chains of the x3 (q) and attn_ret (RES) buses.  The cold-layer
KV-prefetch penalty of L0 (762 cycles) goes away (each layer's attention streams its own KV; no prefetch to hide); the
per-token KV-path constants (+222) stay.  The embedding row fetch is composed from the r22k / KV-die relay chains, the
link and the EMB_HBM_FEASIBILITY DRAM / port / ingest constants.

    python3 tools/qwen_kv_die/reprice.py --bench results/arch/qwen_kv_die_20261009/bench.json \
        --kv results/arch/qwen_kv_die_20261009/kv_die/plan.json --rom results/arch/qwen_kv_die_20261009/rom_r22k.json \
        --out results/arch/qwen_kv_die_20261009/reprice.json
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASIS = 'results/arch/qwen_tp8_vs_sysdie_20261009/result.json'
CLOCK = 1.2e9
EMB = dict(port_fifo=7, dram_typ=71, dram_worst_extra=79 + 240, crossing=3, ingest=64,
           source='/home/ubuntu/claude-takeover-20261007/EMB_HBM_FEASIBILITY.md option 1 table (tagged-port FIFO, '
                  'DRAM row conflict, response crossing, 4 KiB ingest on eq; worst: AQ_STARVE + REFpb)')


def sha16(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()[:16]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--bench', type=Path, required=True)
    ap.add_argument('--kv', type=Path, required=True)
    ap.add_argument('--rom', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    basis = json.loads((ROOT / BASIS).read_text())
    tp4 = basis['tp4']
    rows = tp4['rows']
    bench = json.loads(a.bench.read_text())
    kv = json.loads(a.kv.read_text())
    rom = json.loads(a.rom.read_text())
    cs = kv['critical_stages']
    rs = rom['crossing_bus_stages']
    rom_q, rom_res = rs['x3'] + 1, rs['attn_ret'] + 1                 # + the registered endpoint port
    rom_ea, rom_eq = rs['emb_a'] + 1, rs['emb'] + 1
    gw_land = max(cs['gw_to_land'].values()) + 1
    land_gw = max(cs['land_to_gw'].values()) + 1
    out = dict(schema='opentallas.qwen-kv-die.reprice.v1', date='2026-10-09', clock_hz=CLOCK, position=8191,
               mode='AR (DSpark off), INT8 weights, FP8 KV in HBM',
               inputs={BASIS: sha16(BASIS), str(a.bench): sha16(a.bench), str(a.kv): sha16(a.kv), str(a.rom): sha16(a.rom)},
               basis=dict(token_cycles=tp4['token_cycles'], tok_s=tp4['tok_s'], layer=tp4['layer_cycles'],
                          attn_kv=rows['attn_kv'], softmax_norm=rows['softmax_norm'], l0_extra=984, l0_cold=762,
                          l0_kv_constants=222, head=3101.0, embed=7.0, handoffs=36,
                          sysdie_1a_central=basis['system_die']['by_latency']['central']['collective_stays']),
               stages=dict(rom_q=rom_q, rom_res=rom_res, rom_ea=rom_ea, rom_eq=rom_eq, kv_seq_to_far_aggregator=
                           max(cs['seq_to_astk'].values()), kv_hub_aggregator=max(cs['hub_to_astk'].values()),
                           kv_hub_to_seq=cs['hub_to_seq'], kv_seq_to_far_land=max(cs['seq_to_land'].values()),
                           kv_gw_land=gw_land, kv_land_gw=land_gw),
               cases={})
    for case, b in bench['cases'].items():
        step = b['layer_step_8192']
        adj = (rom_q - b['params']['ROM_ST']) + (rom_res - b['params']['ROM_ST'])
        step_adj = step + adj
        layer = tp4['layer_cycles'] - rows['attn_kv'] - rows['softmax_norm'] + step_adj
        link = b['adapter_plus_phy']
        emb = (rom_ea + link + 1 + gw_land + EMB['port_fifo'] + EMB['dram_typ'] + EMB['crossing'] + land_gw + 1 + link
               + rom_eq + EMB['ingest'])
        if case == 'worst':
            emb += EMB['dram_worst_extra']
        token = emb + 36 * layer + 222 + 3101.0 + 36
        out['cases'][case] = dict(
            phy_latency=b['params']['PHY_LAT'], adapter_plus_phy=link, layer_step_measured=step,
            rom_stage_correction=adj, layer_step=step_adj, layer_cycles=layer,
            layer_delta_vs_tp4=layer - tp4['layer_cycles'], embed_cycles=emb, l0_extra=222,
            token_cycles=round(token, 1), tok_s=round(CLOCK / token, 1),
            vs_tp4=round(tp4['token_cycles'] / token - 1, 4),
            vs_sysdie_1a_model=round(out['basis']['sysdie_1a_central']['token_cycles'] / token - 1, 4),
            bench_exact=b['exact_all'])
    c = out['cases'].get('typical') or next(iter(out['cases'].values()))
    out['headline'] = dict(
        tok_s=c['tok_s'], token_cycles=c['token_cycles'], vs_tp4=c['vs_tp4'],
        range_tok_s=[min(x['tok_s'] for x in out['cases'].values()), max(x['tok_s'] for x in out['cases'].values())],
        status='priced candidate: the attention layer step is MEASURED through the link RTL (bit-exact), the relay stages '
               'come from the r22k / KV-die placements; the near-HBM attention elements are not closed physically')
    out['notes'] = [
        'The decision record priced option 1a at 219,522 cycles assuming the TILE attention (1,756 cycles a layer) stays '
        'and only 2 x 14-cycle crossings are added.  Moving attention to the KV die means NEAR-HBM attention (row engines '
        'beside the HBM PHYs: KV never crosses), whose measured step is the layer_step here.',
        'L0 cold KV-prefetch (762) is removed: each layer\'s near-HBM attention streams its own 4 MiB a die inside its '
        'step (the bench HBM model: 750 B a cycle a stack, 16-cycle latency); the per-token KV constants (+222) stay.',
        'The row-engine <-> aggregator interface (16.5 k / 16.8 k bits) is abutted in the KV-die floorplan; if the '
        're-cut adds pipeline stages on the q broadcast or the leaf path, each stage adds ~1-2 cycles a layer.']
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps(out['headline']))
    for k, v in out['cases'].items():
        print(k, v['layer_cycles'], v['token_cycles'], v['tok_s'], v['vs_tp4'])


if __name__ == '__main__':
    main()
