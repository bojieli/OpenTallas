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
TILE_SLOT = (311.04, 1296.0)          # coordinator 2026-10-12: lsl6 tile needs >= 288 um; par kit physical/ref_tile/qfd_tile_nk_tp8.json
b_rom = {k: v for k, v in trackA.items() if k not in ('ot_qkvd_ucie_x64_phy', 'qfd_d2d_rom')}
b_rom['qfd_tile_nk'] = 768 * TILE_SLOT[0] * TILE_SLOT[1] / 1e6
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
# ---- CUT ANALYSIS (SPEC section 0): candidate floorplans of the merged die, bits per cut vs usable tracks ------------
CU = json.load(open(HERE / 'cuts.json'))          # measured on the generator networks by cuts.py (tp8a core, KV die, r22ko4)
G8 = CU['tp8a']['geometry']; KVD = CU['kv_die']
TPU = {'M4': 1 / 0.048, 'M5': 1 / 0.048, 'M6': 1 / 0.064, 'M7': 1 / 0.064, 'M8': 1 / 0.080, 'M9': 1 / 0.080}
TGT = 0.55                                         # owner target 0.55-0.60; we design to the low end
CH_PER_UM = 0.75 * TPU['M6'] + 0.5 * TPU['M4']     # channel layers added to the die layer (H; V is the same numbers)
DIE_PER_UM = 0.75 * TPU['M8']                      # die layer over blocks (M8 H / M9 V) after the PDN
def usable(L, Lch): return L * DIE_PER_UM + Lch * CH_PER_UM
def pins(face_um): return face_um / 0.048          # face pin rule: 2 tracks a bit on 2 pin layers
SPINE = G8['spine_x'][1] - G8['spine_x'][0]; KVHALF, KVCH, IOBAND, MARG = 3700.0, 100.0, 1564.0, 22.0
tp8a_core_h = G8['row_pitch'] * G8['rows'] - (G8['row_pitch'] - G8['tile'][1])   # 12 rows incl. link channels (measured)
RET = (26000.0, 33000.0)
def fits(w, h): return min(w, h) <= RET[0] and max(w, h) <= RET[1]
fp = {
    'F1': dict(desc='64 cols x 12 rows (tp8a core), KV-die halves rotated into N and S strips under 2 HBM PHYs each, IO on the W/E edges',
               cols=64, rows=12, col_pitch=TILE_SLOT[0] + 52.7, row_gap=G8['row_pitch'] - G8['tile'][1], io='W/E edge column'),
    'F2': dict(desc='48 cols x 16 rows, KV-die W half on the die W edge and E half on the E edge UNROTATED (2 HBM PHYs per edge), '
                    'KV centre blocks (seq/host/ahub/embgw) in the ROM spine, all IO (UCIe peer, collective, xfifo, 3 SerDes) in one S band + 400-um IO word channel',
               cols=48, rows=16, col_pitch=TILE_SLOT[0] + 83.5, row_gap=190.0, io='S band + 400-um word channel'),
}
f1 = fp['F1']; f1['w'] = f1['cols'] * f1['col_pitch'] + SPINE + IOBAND + 2 * MARG
f1['h'] = tp8a_core_h + (TILE_SLOT[1] - G8['tile'][1]) * 12 + 2 * (KVHALF + KVCH) + 2 * MARG
f2 = fp['F2']; f2['w'] = f2['cols'] * f2['col_pitch'] + SPINE + 2 * (KVHALF + KVCH) + 2 * MARG
f2['h'] = f2['rows'] * (TILE_SLOT[1] + f2['row_gap']) + IOBAND + 400.0 + 2 * MARG
b_slots_311 = sum(b_rom.values()) + sum(kv_keep.values())
for f in fp.values():
    f['w'], f['h'] = round(f['w']), round(f['h']); f['mm2'] = round(f['w'] * f['h'] / 1e6, 1)
    f['reticle_fit'] = fits(f['w'], f['h']); f['slot_share'] = round(b_slots_311 / f['mm2'], 3)
# per-cut budgets.  Measured inputs: tp8a row/column/spine families (face-projected generator buses), KV-die boundary rows.
row = CU['tp8a']['row_H']
tb_row = max(r['fam'].get('tree_block', 0) for r in row)                     # intra-block legs in one row (measured max)
oth_row = max(sum(v for k, v in r['fam'].items() if k not in ('tree_block', 'tree_spine', 'io', 'crom')) for r in row)
kv_rows = KVD['W_rows_1496'] + KVD['E_rows_1496']; kv_side = max(sum(KVD['W_rows_1496']), sum(KVD['E_rows_1496']))
spv = CU['tp8a']['spine_V_max']; kvc = KVD['centre_col_V_max']
WORD = 512
def cutrow(name, f, bits_parts, L, Lch, rule):
    b = sum(bits_parts.values()); u = usable(L, Lch)
    return dict(cut=name, floorplan=f, bits=round(b), parts={k: round(v) for k, v in bits_parts.items()}, usable_tracks=round(u),
                util=round(b / u, 3), ok=b / u <= TGT, rule=rule)
cuts = []
for fn in ('F1', 'F2'):
    f = fp[fn]; rp = TILE_SLOT[1] + f['row_gap']
    kv_row = 2 * WORD * 2 if fn == 'F2' else 0                  # F2: KV<->spine words cross the half array, <= 2 kb per row
    cuts.append(cutrow('tile row H (1 row pitch, vertical cut at the spine face)', fn,
                       dict(tree_block=tb_row, block_roots=2 * WORD, kv_links=kv_row, other=oth_row, **({'serdes_words': 3 * 4 * 1024 // 2} if fn == 'F1' else {})),
                       rp, f['row_gap'], 'block roots spread over the 4 rows of a block-row (root row = r0 + blockcol mod 4), <= 2 root/band words per row; '
                       'KV links (F2) <= 2,048 b per row over >= 4 middle rows; any 260-um sub-window over tiles <= 2 words'))
    cuts.append(cutrow('tile column V (1 column pitch, horizontal cut in a row gap)', fn,
                       dict(station_corridor=509, tree_legs=3 * WORD, band_word=WORD), f['col_pitch'], f['col_pitch'] - TILE_SLOT[0],
                       'the vertical legs of a 4x4 block spread over its 4 columns (<= 3 words per column pitch), legs in the column channel'))
    cuts.append(cutrow('spine column V (worst y)', fn, dict(rom_spine=spv['bits'], kv_centre=kvc['bits'], **({'kv_strip_to_spine': kv_side} if fn == 'F1' else {})),
                       SPINE, SPINE - spv['block_um'] * SPINE / (spv['win'][1] - spv['win'][0]), 'measured tp8a spine + KV-die centre column (F1: + one KV strip running N/S to the spine)'))
    cuts.append(cutrow('KV region <-> core boundary (worst 1,496-um window, channel)', fn, dict(kv_words=max(kv_rows)), 1496, 1496,
                       'KV halves keep their internal geometry (KV die GRT overflow 0); boundary is a 100-um channel'))
cuts.append(dict(cut='HBM PHY DFI face (per PHY, abutted)', floorplan='F1/F2', bits=9207, usable_tracks=round(pins(12000)),
                 util=round(9207 / pins(12000), 3), ok=True, rule='face pin rule (face um / 0.048)'))
cuts.append(cutrow('IO word channel (vertical cut, 400-um channel under the IO band)', 'F2', dict(serdes_words=2 * 2 * 1024), 400, 400,
                   'xfifo and UCIe abut the collective; SerDes split 1 W / 2 E of the collective so <= 2 SerDes word pairs cross any x'))
cuts.append(cutrow('crom -> cbuf word row (channel)', 'F1/F2', dict(crom=2462), 150, 150, '>= 150-um channel for the constant-buffer word row'))
for nm, b, face in (('VM S <-> SU N (abutted)', 8511, 777.6), ('band_lanes S <-> port_tiles N (abutted)', 8192, 777.6),
                    ('tt_up4 W face (NB 3)', 4622 // 2, 388.8), ('qfd_tile_nk W face (tree words)', 2048, TILE_SLOT[1]),
                    ('collective E face (2 SerDes x 2,048 b)', 4096, 950.4)):
    cuts.append(dict(cut='stack face: ' + nm, floorplan='F1/F2', bits=b, usable_tracks=round(pins(face)), util=round(b / pins(face), 3),
                     ok=b / pins(face) <= TGT, rule='face pin rule (face um / 0.048)'))
as_generated = dict(tp8a_fine_max=CU['tp8a']['fine'][0], tp8a_fine_tree_max=CU['tp8a']['fine_tree'][0], kv_die_fine_max=KVD['fine'][0],
                    r22ko4_fine_max=CU['r22ko4_calibration']['fine'][0])
choice = [n for n, f in fp.items() if f['reticle_fit'] and all(c['ok'] for c in cuts if c['floorplan'] in (n, 'F1/F2'))]
cut_analysis = dict(target=TGT, floorplans=fp, cuts=cuts, as_generated=as_generated, chosen=choice[0] if choice else None,
                    b_slots_mm2_311=round(b_slots_311, 1))
# ---- per-unit throughput budget (B4 central basis; every unit sized to stream without stalling the token path) ----------
unit_budget = [
    ('qfd_tile_nk (768)', '1 code word (2 x 266-b macro reads) per cycle per tile, stall-free over 512 words/layer + 1,600 head words', 'stream words/die unchanged at G 3,072'),
    ('block tree + band tree', '1 reduced 16-lane FP32 word (512 b) per cycle per band, equal relay depth at every node (no deskew)', '3 band words/cycle into tt_up4'),
    ('qfd_sp_band_lanes / res_ser / port_tiles (x3 / x3 / x6 groups)', '1 band word per cycle per band; 1 scale row per cycle per port group', 'TP4 per-band shape'),
    ('qfd_tt_up4 / tt_ctlm', '1 combined word per cycle (NB 3: one adder level)', ''),
    ('qfd_sp_vector_memory / su64_sfu', '4,096-wide FP32 vector in 32 cycles at 4,096 b/cycle (VM <-> collective)', 'RMSNorm/residual over full hidden'),
    ('qfd_io_collective (2-level)', 'all-reduce <= TP4 measured 1,121 / 979 cycles (central)', 'section 3'),
    ('qfd_io_serdes (x3)', '8 KiB per all-reduce per link in <= 128 cycles = 512 b/cycle/direction payload; 1,024-b adapter word (2x)', 'x12 112G PHY ~150 GB/s'),
    ('qfd_io_ucie (in-package peer)', '16 KiB + 8 KiB per all-reduce at 1,024 b/cycle/direction (16 + 8 cycles payload)', ''),
    ('KV region (128 rheads, 32 ectl, astk, land, ctrl, 4 HBM PHYs)', f"attention <= {ATT_TP8_ENGINE:.0f} cycles/layer at 1 KV head over 128 PCs; HBM 4 x 1.0 TB/s = 3,333 B/cycle", 'B4 central'),
    ('KV <-> SU/VM on-die links (replace rom_end/kv_end)', f"q / new K,V / result per layer in <= {ONDIE_ATT:.0f} cycles incl. ~8 relays each way", 'credit flow, one clock'),
    ('embedding gateway (qkd_embgw, on-die)', '16 KiB row per token in <= 150 cycles = >= 874 b/cycle (a 513-b word takes 256 cycles: widen to 1,024 b or charge +106 cycles/token)', 'B4 central assumes 150'),
]
out = {'schema': 'opentallas.qwen-tp8-1012.v1', 'date': '2026-10-12', 'model': {'hidden': H, 'layers': L, 'q_heads': NQ, 'kv_heads': NKV,
       'head_dim': HD, 'ffn': FF, 'vocab': V, 'int8_weight_bytes_rom': weights},
       'rom': rom, 'area': area, 'cut_analysis': cut_analysis, 'unit_budget': unit_budget, 'kv_tp4_MB_per_user_per_die': round(kv_user_die[4] / 1e6, 1), 'kv': kv, 'throughput': thr,
       'grade': 'modelled: TP4 token-path windows (measured/apportioned/priced as graded there) with the TP8 deltas listed; no TP8 RTL run'}
json.dump(out, open(HERE / 'tp8.json', 'w'), indent=1)
print(json.dumps({k: out[k] for k in ('rom', 'kv')}, indent=0)[:3000]); print({k: {kk: v[kk] for kk in ('cycles', 'tok_s') } | ({'vs': v.get('vs_tp4')}) for k, v in thr.items()})
print({k: v for k, v in area.items() if k != 'trackA_by_cell'})
print({n: {k: f[k] for k in ('w', 'h', 'mm2', 'reticle_fit', 'slot_share')} for n, f in fp.items()}, 'chosen', cut_analysis['chosen'])
for c in cuts: print(c['floorplan'], c['cut'][:60], c['bits'], c['usable_tracks'], c['util'], c['ok'])
# ELEMENT_IMPACT.md from element_impact.json (track B classes)
EI = json.load(open(HERE / 'element_impact.json'))
cnt = {}
for e in EI['elements']: cnt[e['cls'].split()[0]] = cnt.get(e['cls'].split()[0], 0) + 1
md = [f"# TP8 element impact, track B (single merged die, floorplan {cut_analysis['chosen']})", '',
      EI['preamble'], '', 'Counts: ' + ', '.join(f'{k} {v}' for k, v in sorted(cnt.items())) + '.', '',
      '| element | region | class (track B) | needs | RTL | reason | TP8 status |', '|---|---|---|---|---|---|---|']
for e in EI['elements']:
    md.append(f"| {e['element']} | {e['region']} | {e['cls']} | {e['needs']} | `{e['rtl']}` | {e['reason']} | {e.get('status', '')} |")
(HERE / 'ELEMENT_IMPACT.md').write_text('\n'.join(md) + '\n')

# ---- generated tables in SPEC.md (between the GEN markers) ------------------------------------------------------------
def tbl(head, rows): return '\n'.join(['| ' + ' | '.join(head) + ' |', '|' + '---|' * len(head)] + ['| ' + ' | '.join(map(str, r)) + ' |' for r in rows])
gen_fp = tbl(['', 'arrangement', 'die (mm)', 'mm²', 'fits 26 x 33', 'slot share'],
             [[n, f['desc'], f"{f['w']/1e3:.2f} x {f['h']/1e3:.2f}", f['mm2'], 'yes' if f['reticle_fit'] else '**no**', f"{f['slot_share']*100:.1f}%"] for n, f in fp.items()])
gen_cuts = tbl(['cut', 'plan', 'bits/cycle (parts)', 'usable tracks', 'util', 'rule that holds it'],
               [[c['cut'], c['floorplan'], f"{c['bits']:,}" + (' (' + ', '.join(f'{k} {v:,}' for k, v in c['parts'].items() if v) + ')' if c.get('parts') else ''),
                 f"{c['usable_tracks']:,}", f"**{c['util']:.2f}**" if not c['ok'] else f"{c['util']:.2f}", c['rule']] for c in cuts])
ag = as_generated
gen_hot = tbl(['network (as generated)', 'worst 260-um window', 'bits', 'usable', 'util', 'families'],
              [[k, f"{v['ax']} = {v['pos']:,} um, {v['win'][0]:,}-{v['win'][1]:,}", f"{v['bits']:,}", f"{v['usable']:,}", v['util'], ', '.join(f'{a} {b:,}' for a, b in v['fam'].items())] for k, v in ag.items()])
gen_unit = tbl(['unit', 'throughput budget', 'basis'], unit_budget)
sp = (HERE / 'SPEC.md').read_text()
for key, body in (('FLOORPLANS', gen_fp), ('CUTS', gen_cuts), ('HOTSPOTS', gen_hot), ('UNITS', gen_unit)):
    a, b = f'<!-- GEN:{key} -->', f'<!-- /GEN:{key} -->'
    if a in sp:
        sp = sp[:sp.index(a) + len(a)] + '\n' + body + '\n' + sp[sp.index(b):]
(HERE / 'SPEC.md').write_text(sp)
