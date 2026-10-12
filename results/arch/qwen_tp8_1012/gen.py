#!/usr/bin/env python3
"""Qwen3-8B ROM TP8 top-down numbers (qwen-tp8 stream, owner 2026-10-12).

Derives per-die ROM shard / tile count from the model shape (tools/hdc_qwen_fullshape_placement_w12.py),
the slot area of track A (TP8 ROM die + existing KV die) and track B (TP8 ROM die with the KV die merged),
KV capacity / HBM need, and the token composition at P8191 by scaling the TP4 ROM+KV-die token path
(results/arch/token_path_20261009/qwen_rom.json, 249,431 cycles, 4,810.9 tok/s; per-op grades kept).
Writes tp8.json next to this file.  Every TP8 number is MODELLED from TP4 windows; none is a TP8 RTL run.
"""
import json, os, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'tools'))

def placement(tp, g):
    os.environ['QWEN_O4_TP'] = str(tp); os.environ['QWEN_O4_GROUPS'] = str(g)
    out = subprocess.run([sys.executable, '-c', 'import json,hdc_qwen_fullshape_placement_w12 as P;p=P.placement();'
                          'print(json.dumps({k:p[k] for k in ("matrix_code_words_per_die","matrix_code_word_bits","matrix_scale_words_per_die")}|'
                          '{"scale_rows":p["matrix_scale_rows_per_die"],"head":[x for x in p["matrices_per_die"] if x["name"]=="lm_head"][0]}))'],
                         cwd=ROOT / 'tools', capture_output=True, text=True, check=True, env=dict(os.environ))
    return json.loads(out.stdout)

H, L, NQ, NKV, HD, FF, V = 4096, 36, 32, 8, 128, 12288, 151936
W_LANES, GROUPS_PER_TILE, BANK_DEPTH, MACRO_BITS = 16, 4, 4096, 266
weights = L * (H * H + 2 * H * NKV * HD + H * H + 3 * H * FF) + V * H   # INT8 bytes, lm_head untied; embedding in HBM
rom = {}
for tp, g in ((4, 6144), (8, 6144), (8, 3072)):
    p = placement(tp, g)
    words = p['matrix_code_words_per_die']
    tiles = g // GROUPS_PER_TILE
    banks = -(-words // BANK_DEPTH)                    # per column (group pair), ot_rom_4096x266_m8
    rom[f'TP{tp}_G{g}'] = {
        'weight_bytes_per_die': weights // tp, 'weight_bits_per_die': weights // tp * 8,
        'code_words_per_die': words, 'code_word_bits': p['matrix_code_word_bits'],
        'code_bits_per_die': words * p['matrix_code_word_bits'],
        'tiles': tiles, 'code_banks_per_column': banks, 'macros_per_tile': 2 * banks,
        'macro_bits_per_tile': 2 * banks * BANK_DEPTH * MACRO_BITS,
        'bank_fill': round(words / (banks * BANK_DEPTH), 4),
        'scale_rows_per_die': p['scale_rows'], 'lm_head': {k: p['head'][k] for k in ('rows', 'split', 'rounds', 'words')}}

# ---- area (mm2): TP4 contract v5 slot sums, scaled per element class -------------------------------------
C = json.load(open(ROOT / 'results/arch/hier_contract_1011/qwen_rom.json'))
K = json.load(open(ROOT / 'results/arch/hier_contract_1011/qwen_kv.json'))
def sums(c):
    a = {}
    for s in c['slots']:
        if s['kind'] == 'die': continue
        a[s['cell']] = a.get(s['cell'], 0) + s['outline']['w'] * s['outline']['h'] / 1e6
    return a
ra, ka = sums(C), sums(K)
tp4_slots = sum(ra.values())
scale = {  # TP8 multiplier on the TP4 slot area of each cell (reason in SPEC.md section 2)
    'qfd_tile_nk': 0.5, 'qfd_cst_n': 0.5, 'qfd_cst_s': 0.5,               # 768 tiles, one station each
    'qfd_sp_band_lanes': 0.5, 'qfd_sp_res_ser': 0.5,                      # 3 bands of 256 tiles (was 6)
    **{k: 0.5 for k in ra if k.startswith('qfd_port_tiles_')},            # 6 of 12 slab port groups (count halves)
    'qfd_io_serdes': 3.0,                                                 # 3 off-package peers (K4 board), was 1 adapter
    'qfd_io_collective': 1.5,                                             # + 2-input in-package stage, half-vector owner select
}
trackA = {k: v * scale.get(k, 1.0) for k, v in ra.items()}
# port tiles: 12 named slots in TP4, keep 6 (count) -> the 0.5 scale above on every one is the same total
a_slots = sum(trackA.values())
kv_keep = {k: v for k, v in ka.items() if k not in ('ot_qkvd_ucie_x64_phy', 'qkd_d2d', 'ot_qfd_serdes_112g_x12_phy', 'qkd_pll', 'qkd_ckbump')}
b_rom = {k: v for k, v in trackA.items() if k not in ('ot_qkvd_ucie_x64_phy', 'qfd_d2d_rom')}
b_slots = sum(b_rom.values()) + sum(kv_keep.values())
die = {'TP4_r22ko4': {'w': 25.04, 'h': 32.80}, 'A': {'w': 25.0, 'h': 23.0}, 'B': {'w': 25.0, 'h': 31.0}}
for k, d in die.items(): d['mm2'] = round(d['w'] * d['h'], 1)
area = {
    'tp4_slot_mm2': round(tp4_slots, 1), 'tp4_slot_share': round(tp4_slots / die['TP4_r22ko4']['mm2'], 3),
    'A_slot_mm2': round(a_slots, 1), 'A_die': die['A'], 'A_slot_share': round(a_slots / die['A']['mm2'], 3),
    'A_kv_die_mm2_unchanged': round(K['slots'][0]['outline']['w'] * K['slots'][0]['outline']['h'] / 1e6, 1),
    'B_slot_mm2': round(b_slots, 1), 'B_kv_part_mm2': round(sum(kv_keep.values()), 1), 'B_die': die['B'],
    'B_slot_share': round(b_slots / die['B']['mm2'], 3), 'reticle_mm2': 858.0,
    'tile_mm2_each': round(ra['qfd_tile_nk'] / 1536, 4),
    'trackA_by_cell': {k: round(v, 2) for k, v in sorted(trackA.items(), key=lambda x: -x[1])},
}

# ---- KV capacity / bandwidth per die at P8191 (FP8 K and V codes) ------------------------------------------
pos = 8192
kv_user_die = {tp: L * (NKV // tp) * HD * 2 * pos for tp in (4, 8)}           # bytes
stack_gb, stack_tbs = 24.0, 1.0      # HBM3E 8-high 24 GB; 1.0 TB/s per stack as the KV-die contract (4.0 TB/s / 4)
# ---- token composition -------------------------------------------------------------------------------------
T = json.load(open(ROOT / 'results/arch/token_path_20261009/qwen_rom.json'))
L1 = {n['id'].split('.', 1)[1]: n for n in T['nodes'] if n['group'] == 'L1'}
base_token = T['totals']['cycles']
def cyc(op): return L1[op]['cycles']
def relay(op): return sum(a[1] for a in L1[op].get('adders') or [] if a[0] == 'die_relays_430um')
def layer(case):
    """case: dict of knobs -> per-layer delta vs the TP4 L1 row (cycles)."""
    d = {}
    for op in ('qkv', 'o_proj', 'gate_up', 'down'):                 # stream words per die unchanged at G 3,072
        d[op] = -relay(op) * (1 - case['relay_scale'])                # shorter die -> fewer relay stages
    d['qknorm_rope'] = -cyc('qknorm_rope') * (1 - case['heads_scale'])
    d['attn_kv'] = case['attn_kv'] - cyc('attn_kv')
    d['allreduce1'] = d['allreduce2'] = case['ar_delta']
    d['residual'] = -821 * (1 - case['relay_scale'])                    # rom_split_stations_and_issue_relays
    return d
ATT_TP4_ENGINE = 1361.0      # TP4 ROM-die attention window (token_path_20261008), engine-bound, 2 KV heads / 128 PCs
ATT_TP8_ENGINE = 849.0       # same engine at 1 KV head over 128 PCs (stream halves, fixed 131 kept; qwen_tp8_vs_sysdie_20261009)
LINK_ATT = cyc('attn_kv') - ATT_TP4_ENGINE                           # 455: q / KV / result crossing the UCIe pair (measured)
ONDIE_ATT = 100.0             # on-die registered path SU <-> KV region (~8 relays each way + skid), track B
cases = {
    'A_central': dict(relay_scale=0.65, heads_scale=0.5, attn_kv=ATT_TP8_ENGINE + LINK_ATT, ar_delta=0, embed=272),
    'A_conservative': dict(relay_scale=1.0, heads_scale=1.0, attn_kv=cyc('attn_kv'), ar_delta=100, embed=272),
    'B4_central': dict(relay_scale=0.75, heads_scale=0.5, attn_kv=ATT_TP8_ENGINE + ONDIE_ATT, ar_delta=0, embed=150),
    'B4_conservative': dict(relay_scale=1.0, heads_scale=1.0, attn_kv=ATT_TP4_ENGINE + ONDIE_ATT, ar_delta=100, embed=272),
    'B2_central': dict(relay_scale=0.75, heads_scale=0.5, attn_kv=ATT_TP4_ENGINE + ONDIE_ATT, ar_delta=0, embed=150),
}
head_delta = (rom['TP8_G3072']['lm_head']['words'] - 1584) + 10              # 1,600 vs 1,584 words; 8-way argmax gather
thr = {'TP4_basis': {'cycles': base_token, 'tok_s': round(1.2e9 / base_token, 1), 'layer_L1': sum(n['cycles'] for n in L1.values())}}
for name, c in cases.items():
    d = layer(c)
    tok = base_token + L * sum(d.values()) + head_delta + (c['embed'] - 272)
    thr[name] = {'cycles': round(tok), 'tok_s': round(1.2e9 / tok, 1), 'vs_tp4': round(base_token / tok - 1, 4),
                 'layer_delta': {k: round(v, 1) for k, v in d.items()}, 'knobs': c}
tok_s_A = thr['A_central']['tok_s']
layer_us = lambda name: (thr[name]['cycles'] / 37) / 1.2e3      # ~per-layer time (us)
kv = {}
for name, stacks in (('A_kv_die_4stack', 4), ('B4', 4), ('B2', 2)):
    bw = stacks * stack_tbs * 1e12
    per_user_layer = kv_user_die[8] / L
    t_layer = layer_us('A_central' if name.startswith('A') else name + '_central') * 1e-6
    kv[name] = {'stacks': stacks, 'capacity_GB': stacks * stack_gb,
                'kv_MB_per_user_per_die_P8191': round(kv_user_die[8] / 1e6, 1),
                'capacity_users': int(stacks * stack_gb * 1e9 // kv_user_die[8]),
                'bw_TBs': stacks * stack_tbs,
                'users_before_kv_bw_bound': round(bw * t_layer / per_user_layer, 1)}
out = {'schema': 'opentallas.qwen-tp8-1012.v1', 'date': '2026-10-12', 'model': {'hidden': H, 'layers': L, 'q_heads': NQ, 'kv_heads': NKV,
       'head_dim': HD, 'ffn': FF, 'vocab': V, 'int8_weight_bytes_rom': weights},
       'rom': rom, 'area': area, 'kv_tp4_MB_per_user_per_die': round(kv_user_die[4] / 1e6, 1), 'kv': kv, 'throughput': thr,
       'grade': 'modelled: TP4 token-path windows (measured/apportioned/priced as graded there) with the TP8 deltas listed; no TP8 RTL run'}
json.dump(out, open(HERE / 'tp8.json', 'w'), indent=1)
print(json.dumps({k: out[k] for k in ('rom', 'kv')}, indent=0)[:3000]); print({k: {kk: v[kk] for kk in ('cycles', 'tok_s') } | ({'vs': v.get('vs_tp4')}) for k, v in thr.items()})
print({k: v for k, v in area.items() if k != 'trackA_by_cell'})
