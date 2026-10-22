#!/usr/bin/env python3
"""Exact Qwen ROM capacity, all stages, pinned/static resident layout (QW-ROMCAP, COORD 21:13 10-20).

The S81 lesson: a planning model (averaged words, perfect packing) said "fits"; the exact pinned allocator did not.
This check runs the REAL Qwen allocator functions, not a model:

  * layer stages 1..36: hdc_qwen_layer0_rom_w12.matrix_plan (the function emit() uses) on the exact TP8 per-rank
    shard shapes of every layer (qkv/o/gu/down, the same row/column split as layer_tp2_matrices), at TP=8 / G=3072;
    scale depth by emit()'s own expression for the layout the released banks use;
  * head stage 37: hdc_qwen_fullshape_placement_w12.matrix(lm_head, 151936/8, 4096) and qwen_o4_head_rom_w12's counts;
  * pinned resident slots: qwen_static_schedule/rom_relocation.stage_bases (the static relocation every program uses);
  * physical capacity: macro depth / bank count parsed from the real sources (ot_qwen_tile_romleaf.sv,
    qwen_code_rom/build.py, qwen_scale_rom/build.py) and the die's own ROM_BIND audit (tiles x macros) when given.

The allocator depends only on matrix shapes (no weight values), so this is exact for every rank and every layer.
It FAILS (exit 1) if any stage's actual allocation exceeds its pinned slot, any slot overlaps the next, or the resident
image exceeds the physical banks.  Weight values / mask bytes are proved separately (qwen_code_rom, qwen_scale_rom).
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

os.environ['QWEN_O4_TP'] = '8'
os.environ['QWEN_O4_GROUPS'] = '3072'
TOOLS = Path(__file__).resolve().parents[1]
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

import numpy as np  # noqa: E402
import hdc_qwen_fullshape_placement_w12 as PL  # noqa: E402
import hdc_isa as I  # noqa: E402
from qwen_static_schedule.rom_relocation import stage_bases  # noqa: E402

assert (PL.TP, PL.GROUPS) == (8, 3072), (PL.TP, PL.GROUPS)


def matrix_plan_real():
    # import here: hdc_qwen_layer0_rom_w12 pulls safetensors at import; the plan itself is shape-only
    # Fleet python may lack safetensors/torch; they are only used to READ weights, never by matrix_plan.
    import importlib.util
    import types
    if importlib.util.find_spec('safetensors') is None:
        stub = types.ModuleType('safetensors'); stub.safe_open = None; sys.modules['safetensors'] = stub
    if importlib.util.find_spec('torch') is None:
        # the weight reader (layer_tp2_matrices) needs torch; the allocator never calls it
        stub = types.ModuleType('hdc_qwen_int8_image_w12'); stub.layer_tp2_matrices = None
        sys.modules['hdc_qwen_int8_image_w12'] = stub
    from hdc_qwen_layer0_rom_w12 import matrix_plan
    cfg = json.loads(PL.CONFIG.read_text())
    h, nh, kv, hd, ff = (cfg['hidden_size'], cfg['num_attention_heads'], cfg['num_key_value_heads'],
                         cfg['head_dim'], cfg['intermediate_size'])
    tp = PL.TP
    # TP8 shard shapes = layer_tp2_matrices: 'rows' axis -> rows/TP, 'columns' axis -> columns/TP
    q, k, v = (nh * hd) // tp, (kv * hd) // tp, (kv * hd) // tp
    g = ff // tp
    if g % 128:
        raise ValueError('gate/up rows must have matching 128-row tiles')
    shapes = {'qkv': (q + k + v, h), 'o': (h, (nh * hd) // tp), 'gu': (2 * g, h), 'down': (h, ff // tp)}
    mats = {n: (np.empty(s, dtype=np.int8), np.empty(s[0], dtype=np.uint16)) for n, s in shapes.items()}
    out = {}
    for compact in (False, True):
        rows = matrix_plan(mats, compact_banks=compact)
        G, IL = PL.GROUPS, I.INTERLEAVE
        scale_depth = (rows[-1]['scale_end'] if compact else
                       max(r['base'] + (r['rounds'] - 1) * (G // r['split']) * IL + (G - 1) * IL + IL for r in rows))
        out['compact' if compact else 'shared_base_padded'] = dict(code_words=rows[-1]['end'],
                                                                   scale_words=scale_depth, layout=rows)
    return shapes, out


def head_real():
    rows = 151936 // PL.TP
    geo = PL.matrix(0, 'lm_head', rows, 4096)
    per_round, kc = PL.GROUPS // geo['split'], geo['k_per_split']
    return dict(rows=rows, geometry=geo, code_words=geo['rounds'] * kc * 8, scale_words=geo['rounds'] * per_round * 8)


def physical(rom_bind):
    leaf = (ROOT / 'rtl/physical/ot_qwen_tile_romleaf.sv').read_text() if (ROOT / 'rtl/physical/ot_qwen_tile_romleaf.sv').exists() else ''
    code_src = (TOOLS / 'qwen_code_rom/build.py').read_text()
    scale_src = (TOOLS / 'qwen_scale_rom/build.py').read_text()
    m = re.search(r'ROWS,TILES,BANKS,WORD_BYTES=(\d+),(\d+),(\d+),(\d+)', code_src)
    code = dict(tiles=int(m.group(2)), banks=int(m.group(3)), depth=4096, src='tools/qwen_code_rom/build.py')
    if leaf:
        b = re.search(r'ROM_BANK>=(\d+)', leaf); d = re.search(r'ot_rom_(\d+)x266', leaf)
        code.update(banks_rtl=int(b.group(1)), depth=int(d.group(1)), rtl='rtl/physical/ot_qwen_tile_romleaf.sv')
        if code['banks_rtl'] != code['banks']:
            raise ValueError('code-ROM bank count differs between RTL leaf and image builder')
    s = re.search(r'TP, GROUPS, LANES, DEPTH, BANKS = (\d+), (\d+), (\d+), (\d+), (\d+)', scale_src)
    scale = dict(depth=int(s.group(4)), banks=int(s.group(5)), src='tools/qwen_scale_rom/build.py')
    die = None
    if rom_bind:
        a = json.loads(Path(rom_bind).read_text())
        au = a['audit']
        die = dict(rom_bind=str(rom_bind), die_v_sha256=a.get('die_v_sha256'), verdict=au['verdict'],
                   clusters=au['clusters'], tiles=au['tiles'], macros=au['macros'])
        banks_per_tile = au['macros'] // au['tiles'] // 2
        if au['verdict'] != 'PASS' or au['tiles'] != code['tiles'] or banks_per_tile != code['banks']:
            raise ValueError(f'die ROM inventory differs from the image layout: {die}')
        die['banks_per_tile'] = banks_per_tile
    code['rows'] = code['banks'] * code['depth']
    scale['rows'] = scale['banks'] * scale['depth']
    return code, scale, die


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--rom-bind', help='die GEN case/rom_bind.json (physical tile/macro inventory of the release die)')
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    shapes, plans = matrix_plan_real()
    head = head_real()
    code, scale, die = physical(a.rom_bind)
    fails, stages = [], []
    # released banks are the layout whose (code, scale) equals the pinned per-layer slot (512, 816)
    cb1, sb1, cn, sn = stage_bases(1)
    chosen = [k for k, p in plans.items() if (p['code_words'], p['scale_words']) == (cn, sn)]
    layout = chosen[0] if chosen else 'shared_base_padded'
    if not chosen:
        fails.append(f'no allocator layout reproduces the pinned slot {cn}/{sn}: {[(k, p["code_words"], p["scale_words"]) for k, p in plans.items()]}')
    lp = plans[layout]
    for st in range(1, 38):
        cbase, sbase, cslot, sslot = stage_bases(st)
        cw, sw = (lp['code_words'], lp['scale_words']) if st < 37 else (head['code_words'], head['scale_words'])
        row = dict(stage=st, name=f'layer{st-1}' if st < 37 else 'lm_head', code_base=cbase, code_slot=cslot, code_used=cw,
                   code_slot_fill=round(100 * cw / cslot, 3), scale_base=sbase, scale_slot=sslot, scale_used=sw,
                   scale_slot_fill=round(100 * sw / sslot, 3))
        if cw > cslot or sw > sslot:
            fails.append(f'stage {st}: actual {cw}/{sw} exceeds pinned slot {cslot}/{sslot}')
        if st < 37:
            nb = stage_bases(st + 1)
            if cbase + cslot > nb[0] or sbase + sslot > nb[1]:
                fails.append(f'stage {st}: pinned slot overlaps stage {st+1}')
        stages.append(row)
    code_res = max(r['code_base'] + r['code_slot'] for r in stages)
    scale_res = max(r['scale_base'] + r['scale_slot'] for r in stages)
    code_used = sum(r['code_used'] for r in stages)
    scale_used = sum(r['scale_used'] for r in stages)
    if code_res > code['rows']:
        fails.append(f'code resident {code_res} > physical {code["rows"]} rows per tile')
    if scale_res > scale['rows']:
        fails.append(f'scale resident {scale_res} > physical {scale["rows"]} words per port')
    # per-bank fill of the resident image (static: bank b holds resident rows [4096b, 4096b+4096))
    def bank_fill(total, banks, depth):
        return [round(100 * max(0, min(depth, total - b * depth)) / depth, 3) for b in range(banks)]
    r = dict(schema='opentallas.qwen-rom-exact-capacity.v1', lane='QW-ROMCAP',
             verdict='PASS' if not fails else 'FAIL', fails=fails, tp=PL.TP, groups=PL.GROUPS,
             ranks=8, ranks_identical='yes: every rank has the same shard shapes (allocator is shape-only)',
             tp8_shard_shapes=shapes, released_layout=layout,
             allocator_layouts={k: dict(code_words=p['code_words'], scale_words=p['scale_words']) for k, p in plans.items()},
             layer_layout=lp['layout'], head=head, physical_code=code, physical_scale=scale, die=die,
             code_resident_rows=code_res, code_used_rows=code_used,
             code_fill_pct=round(100 * code_res / code['rows'], 3), code_bank_fill_pct=bank_fill(code_res, code['banks'], code['depth']),
             scale_resident_words=scale_res, scale_used_words=scale_used,
             scale_fill_pct=round(100 * scale_res / scale['rows'], 3),
             scale_bank_fill_pct=bank_fill(scale_res, scale['banks'], scale['depth']),
             worst_stage_slot_fill_pct=max(max(s['code_slot_fill'], s['scale_slot_fill']) for s in stages),
             stages=stages,
             scope='Exact allocator rows for all 36 layer + head stages on every TP8 rank in the pinned static resident '
                   'layout vs the physical ROM banks of the die. Weight bytes/masks: qwen_code_rom/qwen_scale_rom proofs. '
                   'Programme/table ROM: qwen_layerbench/programme_store (separate store).')
    a.out.write_text(json.dumps(r, indent=2) + '\n')
    print(json.dumps({k: r[k] for k in ('verdict', 'fails', 'released_layout', 'allocator_layouts', 'code_resident_rows',
                                         'code_fill_pct', 'code_bank_fill_pct', 'scale_resident_words', 'scale_fill_pct',
                                         'worst_stage_slot_fill_pct', 'die')}, indent=1))
    print('QW_ROMCAP', r['verdict'], f'code {code_res}/{code["rows"]} = {r["code_fill_pct"]}%',
          f'scale {scale_res}/{scale["rows"]} = {r["scale_fill_pct"]}%')
    return 0 if not fails else 1


if __name__ == '__main__':
    sys.exit(main())
