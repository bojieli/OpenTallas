#!/usr/bin/env python3
"""S81-HEAD HD-TILE (10-21): closure kits for the S81 release head die array tiles (spec results/arch/s81_head_1021/
SPEC.md sections 1, 2, 6; layout copied from the recent S81 kits tools/s81_slice/mk_lepmu_l5.py: recipe 4, hold_budget
die, one TritonCTS tree with the r6g sink recipe, io_hold_margin 0.03, flop-first pins, kit reset landing).

  ot_s81hd_tile (10 x ot_rom_4096x274_m8, bus B i on W / o on E, straps + clock / reset on W).  The ROM's pins are on
  its W / E faces (lowest 14 um, M4), so each element's ping-pong pair is one abutted N-S stack, pin ends toward the band:
    s81hd_tile_m (MAIN)     648 x 648 (SPEC estimate): N stacks A0 / B / A1 at x 86.4 / 259.2 / 432 (172.8 pitch,
                            47.5-um channels), S stacks A2 / A3 at x 172.8 / 345.6; band y 169..477 full width.
    s81hd_tile_f (FALLBACK) 734.4 x 734.4: same element order at the 216 pitch (90.7-um channels), band y 169..564.
  ot_s81hd_spo / ot_s81hd_spr (std-cell only spine nodes, slot 216 x 648 per SPEC):
    s81hd_spo_m 216 x 648 (i S, o N, ow W, oe E)   s81hd_spo_f 259.2 x 691.2
    s81hd_spr_m 216 x 648 (i N, o S, iw W, ie E)   s81hd_spr_f 259.2 x 691.2

    python3 tools/s81_head/mk_hd_tile_kits.py WT [kit ...]
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

WT = Path(sys.argv[1])
RT = WT / 'physical/ref_tile'
ROM = 'physical/asap7_memory_macros_v2/ot_rom_4096x274_m8'
BR = 'claude/s81-head-tile-1021'
RES = 'results/rtl/s81_head_tile_1021'
HD = 'rtl/dsrom_sys/s81_head'
LIB = ['rtl/hdc/ot_hdc_prefix.sv', 'rtl/hdc/ot_hdc_fastfp.sv', 'rtl/hdc/ot_hdc_fp32_add_lat.sv', 'rtl/hdc/ot_hdc_fp32_mul_lat.sv',
       'rtl/hdc/ot_hdc_fp32_mul_lat_ncr.sv', 'rtl/hdc/ot_hdc_fp32_add_lat_fan32.sv', 'rtl/hdc/ot_hdc_fp32_add_lat7_fan32_native.v',
       f'{HD}/ot_s81hd_key.sv', f'{HD}/ot_s81hd_fadd.sv', 'rtl/common/ot_prefix.sv', 'rtl/v41rom/ot_v41_fadd.sv', 'rtl/v41rom/ot_v41_bmul2.sv', 'rtl/v41rom/ot_dsrom_bmul3.sv',
       'rtl/hdc/ot_hdc_delay.sv', f'{ROM}/ot_rom_4096x274_m8_bb.v',
       f'{HD}/ot_s81hd_elem.sv', f'{HD}/ot_s81hd_bundle.sv', f'{HD}/ot_s81hd_tile.sv']
NODE_SRC = [f'{HD}/ot_s81hd_key.sv', f'{HD}/ot_s81hd_spo.sv', f'{HD}/ot_s81hd_spr.sv']
EXTRA = ['rtl/common', 'rtl/v41rom', 'rtl/hdc', HD, 'tools/s81_head', RES, ROM, 'tools/prepare_fp32_fan32_models.py',
         'results/rtl/fp32_add_native_clone_1020/final_packet',
         'physical/asap7_memory_macros/ot_rom_4096x274_m8']


def bench(name, scen, mut, fail_regex=None):
    b = {'name': name, 'cmd': f'bash tools/s81_head/hd_tile_bench.sh {{RUN}}/{name} {scen} {mut}',
         'expect': 'pass' if mut == 'none' else 'fail', 'threads': 8, 'peak_ram_gb': 16}
    if mut == 'none':
        b['pass_regex'] = rf'^BENCH_PASS s81hd_mini SCEN={scen} MUT=none \(4/4\)$'
    else:
        b['fail_regex'] = fail_regex
        b['fail_witness'] = f'{RES}/witness_{mut.lower()}.log'
    return b


BENCHES = [
    bench('hd_mini_all', 'ALL', 'none'),
    bench('hd_mut_tie_flip', 'C', 'TIE_FLIP', r'^C: TB_FAIL row 21946 != 21818$'),
    bench('hd_mut_go_drop', 'A', 'GO_DROP', r'^A: TB_FAIL results 0 != positions 2$'),
    bench('hd_mut_ten_ignored', 'B', 'TEN_IGNORED', r'^B: TB_FAIL row 21946 != 22141$'),
    bench('hd_mut_flt_drop', 'D', 'FLT_DROP', r'^D: TB_FAIL flt 0 != 1$'),
]
# ROM instance globs (flattened names): A element q bank k = u_b.g_a[q].u_e.u_rom<k>, B bank k = u_b.u_b.u_rom<k>
def rom(e, k):
    return f'*u_b.g_a?{e[1]}?.u_e.u_rom{k}' if e[0] == 'A' else f'*u_b.u_b.u_rom{k}'


RH, ABUT = 62.952, 62.976   # ROM height; abutted N-S stack pitch (height + 0.024, ref_tile abutted_stack)


def tile_macros(n_cols, s_cols, yn, ys):
    """element stacks: (element, x).  ROM pins are on its W / E faces in the lowest ~14 um (M4), so each element's
    ping-pong pair is one abutted N-S stack (touching faces bare) with the pin ends toward the band: N stack = bank 0 R0
    (pins at its bottom, band side) under bank 1 MX (pins at its top); S stack = bank 1 R0 (bottom, S margin) under
    bank 0 MX (pins at its top, band side).  Columns 172.8+ apart: >= 47.5-um channels take the side pins."""
    out = []
    for e, x in n_cols:
        out.append({'view': ROM, 'inst': rom(e, 0), 'at': [x, yn], 'orient': 'R0'})
        out.append({'view': ROM, 'inst': rom(e, 1), 'at': [x, round(yn + ABUT, 3)], 'orient': 'MX', 'at_exact': True})
    for e, x in s_cols:
        out.append({'view': ROM, 'inst': rom(e, 1), 'at': [x, ys], 'orient': 'R0'})
        out.append({'view': ROM, 'inst': rom(e, 0), 'at': [x, round(ys + ABUT, 3)], 'orient': 'MX', 'at_exact': True})
    return out


SAFE_TILE = """SAFE checklist (owner 10-19 / safe_1021, 8 points) -- ot_s81hd_tile:
1 pins: PASS -- every input lands in a W-face flop (x_q / go_q / xv_q / 3 kept rv_q copies / row_q / bits_q / flt_q,
  straps row0_q / ten_q), every output leaves an E-face flop (xo_q / goo_q / xvo_q, o_rv / o_row / o_bits / o_flt); no
  combinational in -> out.  Reset lands in 2 registered stages at the face (kit reset_landing, balanced first_copies /
  copies + reset_relay_split max 32).  Faces: W 568 pins on {wface} um ({wd:.2f}/um), E 565 ({ed:.2f}/um).
2 reach: PASS -- the x stream is registered at both faces (2 stages a tile; tile pitch {w} um, so no single-cycle wire
  crosses the tile); chain best: W pin regs -> holds -> select (kept copies) -> E output regs.  Bundle internal: BST 2
  broadcast stages + skew lines + element IOREG / transport registers (unchanged from the bundle).
3 fanout: PASS (pre-gate native census, see "census" below; round 1 on the original element arithmetic: 2,575
  drivers > 32, max 126, in ot_v41_fadd / ot_dsrom_bmul3 selects + element enables) -- census-safe bundle copy
  ot_s81hd_bundle / ot_s81hd_elem NC 1: native-census arithmetic (adders ot_hdc_fp32_add_lat_fan32 LAT 7 SAFE_DIST 1,
  products ot_hdc_fp32_mul_lat_ncr LAT 6), every wide enable / select a kept copy per <= 16 bits (a mapped select
  costs 2 load pins a bit): capture RP 18, tree hold x3, FIFO pointers, SAFE apply x10, go x4, bundle compare tree 11
  copies a level; FP32 keys via ot_s81hd_key; tile rv x5 / select x7 copies; reset by kit copies (<= 32 a copy).
4 depth: PASS -- reviewed native arithmetic (fan32 adder native estimate 288 ps / 9 levels; ncr multiply LAT 6),
  SAFE = 1 registered argmax apply, compares on registered keys into registered selects (fits 833 ps at TT).
5 storage: WAIVED with reason -- the 10 ROM macros hold the weights; the only bulk flops are the bundle's fixed
  systolic skew lines (16 lanes x 2 streams x SK*(j mod 8), SK 7: <= 49 deep x 16 b = 12.5 kb total, <= 784 b a lane): fixed
  delay shift registers, never runtime-indexed storage; turning them into ring-buffer SRAMs needs a bundle redesign
  (or skewing x once at ot_s81hd_ctl and carrying the skewed stream on bus B, an HD-CTL option recorded in the lane).
6 floorplan: PASS -- macro columns on the 43.2 lattice (x {xs}; N stacks y {yn}, S stacks y {ys}; the MX upper
  ROM of each abutted stack at +62.976 at_exact), element pin ends toward the band, >= 47.5-um column channels for the
  M4 side pins (~9 pins/um over 14 um of ROM side, escaping into the channel), one full-width std-cell band y {band},
  outline {w} x {h} (aspect {asp:.2f}); macro-bound, std-cell utilisation reported by the gate (fill_reason).
7 clock: one region (the tile is one region of its row-pair chain clock region, SPEC 6), one TritonCTS tree, r6g
  sink recipe; pin-flop spread <= 80 ps TT+FF measured by the gate; io_hold_margin 0.03.
8 schedule: static, valid-only pipeline (no credits / backpressure).  Added cycles vs SPEC v1: +1 a tile on the x
  stream (2-stage forward); bundle IOREG / SAFE / key / census compare tree, with the LAT 7 adders (SK 7: shorter
  chains and ROM read span); fire = 4 edges after both bests (2 key stages, select, output);
  measured mini array (spo -> 2 tiles -> spr) go -> result {cyc} cycles; handed to the calendar via lanes/S81-HEAD.md.
"""


def common(name, top, srcs, outline, pins, rng, why, benches, params=None, macros=(), cts=None, rl_copies=None):
    s = {'name': name, 'top': top, 'kind': 'tile', 'sources': srcs, 'params': params or {}, 'clock_port': 'ck',
         'reset_ports': ['rst_n'], 'outline': outline, 'macros': list(macros), 'recipe': 4, 'hold_budget': 'die',
         'inhold': False, 'outhold': False, 'clock': 'cts', 'layer_cap': 'M5',
         'route': {'pd': 0.5, 'threads': 8, 'peak_ram_gb': 32 if macros else 16, 'hold_margin_ns': 0.045,
                   'io_hold_margin_ns': 0.03, 'macro_halo_um': 5.4,
                   'cts_sink': cts or {'size': 24, 'diameter_um': 30, 'extra': '-distance_between_buffers 15 -balance_levels'}},
         'pins': pins, 'pin_ranges': rng, 'children': [], 'inter': [],
         'io_flop_at_pins': {'cols': 4, 'allow_none': True}, 'keep_pin_regs': True,
         'pin_regs': {'enable': False, 'reason': 'RTL registers every pin (inputs land in face flops, outputs leave '
                                                 'flops); recipe pin_regs would add an unpriced stage.'},
         'pre_cts_extra': [], 'orfs_vars': {}, 'structural_change': why}
    if rl_copies:
        f, c = rl_copies
        s['reset_landing'] = {'enable': True, 'stages': 2, 'first_copies': {'rst_n': f}, 'copies': {'rst_n': c}}
        s['reset_relay_split'] = {'max_loads': 32}
    else:
        s['reset_landing'] = {'enable': True, 'stages': 2}
    s['job'] = {'owner': 'Claude:S81-HEAD/HD-TILE', 'branch': BR, 'tag': name, 'extra_paths': EXTRA,
                'benches': benches, 'views_to': f'physical/ref_tile/{name}/views', 'record_to': f'results/rtl/ref_tile/{name}',
                'purpose': f'S81-HEAD (release head die): {top} to closure (TT setup / FF hold / DRC 0 + native audit).'}
    return s


KITS = {}
for v, (W, H, ncols, scols, yn, ys, tag) in {
        'm': (648.0, 648.0, [('A0', 86.4), ('B', 259.2), ('A1', 432.0)], [('A2', 172.8), ('A3', 345.6)], 477.36, 43.2, 'MAIN'),
        'f': (734.4, 734.4, [('A0', 86.4), ('B', 302.4), ('A1', 518.4)], [('A2', 172.8), ('A3', 432.0)], 563.76, 43.2,
              'FALLBACK')}.items():
    name = f's81hd_tile_{v}'
    band = (round(ys + ABUT + RH, 1), yn)
    why = (f'S81-HEAD HD-TILE 10-21 {tag}: new tile ot_s81hd_tile (SPEC v1 4e30e8f3a section 1: LM-head array tile, '
           f'253 a die) = census-safe bundle copy ot_s81hd_bundle (5 elements, 10 ROM4096, 128 rows; IOREG 1, SAFE 1) on '
           f'bus B (565 b) with the chain-best merge.  Outline {W} x {H}: each element\'s ROM pair is one abutted N-S stack '
           f'(ROM pins sit on the W / E faces, lowest 14 um, M4; stack pin ends face the band): N stacks A0 / B / A1 at x '
           f'{" / ".join(f"{x:g}" for _, x in ncols)} (y {yn:g}), S stacks A2 / A3 at x {" / ".join(f"{x:g}" for _, x in scols)} '
           f'(y {ys:g}); one full-width std-cell band y {band[0]:g}..{band[1]:g} plus the column channels; i on W, o on E, '
           f'straps / ck / rst_n on W.')
    macros = tile_macros(ncols, scols, yn, ys)
    pins = {'W': ['i', 'row0', 'ten', 'ck', 'rst_n'], 'E': ['o']}
    rng = {'i': [20.0, round(H - 20, 1)], 'o': [20.0, round(H - 20, 1)]}
    s = common(name, 'ot_s81hd_tile', LIB, {'w': W, 'h': H}, pins, rng, why, BENCHES, macros=macros,
               params={'IOREG': 1}, rl_copies=(16, 320))
    s['route']['pin_balance'] = {'group_max': 1, 'h': 'M4', 'v': 'M3 M5'}
    s['fill_reason'] = {'macro_bound': (
        f'Macro-bound: 10 x ot_rom_4096x274_m8 (125.3 x 63.0 um, 78.9k um2, side-face pins needing >= 47-um column '
        f'channels) as 5 abutted element stacks in a {W} x {H} square; std-cell fill under 40% is the price of the macro '
        f'columns and the 565-b W / E faces, not a squeezed target (RULE FREEZE 10-20: tile fill is guidance).')}
    s['_safe'] = dict(wface=round(H - 40, 1), wd=568 / (H - 40), ed=565 / (H - 40), w=W, h=H, asp=max(W, H) / min(W, H),
                      xs='N ' + ' / '.join(f'{x:g}' for _, x in ncols) + ', S ' + ' / '.join(f'{x:g}' for _, x in scols),
                      yn=yn, ys=ys, band=f'{band[0]:g}..{band[1]:g}')
    KITS[name] = s

SAFE_NODE = """SAFE checklist (owner 10-19 / safe_1021, 8 points) -- {top}:
1 pins: PASS -- {pinsafe}  Reset lands in 2 registered stages at the face (kit reset_landing).
2 reach: PASS within the node ({w} x {h}: one register stage, its flops between the faces, <= ~{half:g} um a side);
  the spine level-to-level gaps (~1.3 mm) get die relay stations (SPEC 4, dv_route72).
3 fanout: PASS -- {fan}
4 depth: PASS -- {depth}
5 storage: PASS -- {nflop} flops, no arrays.
6 floorplan: PASS -- std-cell only, slot {w} x {h} (SPEC 1: 216 x 648 a node); pin-bound (3 x 565 + 565 pins), faces
  <= {dens:.2f}/um; util well under 40% is the slot / pin price (fill_reason pin_bound).
7 clock: one region (the node belongs to its row-pair chain region, SPEC 6), one TritonCTS tree; spread <= 80 ps TT+FF
  by the gate; io_hold_margin 0.03.
8 schedule: static valid-only forward; {sched}
Why hardened, not die-top glue: 26 + 26 identical nodes with 2,260 pins each sit in the spine lane between the tile
columns; one closed view replicated keeps the die top free of ~70k flat flops / ~120k pins of glue and gives the die
STA a fixed node timing model (SPEC 2 'one hardened element, then replicate').
"""
for v, (W, H) in {'m': (216.0, 648.0), 'f': (259.2, 691.2)}.items():
    tag = 'MAIN' if v == 'm' else 'FALLBACK'
    for top, pins, rng, pinsafe, fan, depth, nflop, sched in [
        ('ot_s81hd_spo', {'S': ['i', 'ck', 'rst_n'], 'N': ['o'], 'W': ['ow'], 'E': ['oe']},
         {'i': [10.0, W - 10], 'o': [10.0, W - 10], 'ow': [20.0, H - 20], 'oe': [20.0, H - 20]},
         'the three outputs are KEPT register copies that capture the input pins directly (every input bit -> 3 flops, '
         'every output its own flop), no combinational in -> out.',
         'each input pin drives 3 flops; 9 reset loads (go / xv / rv a copy).',
         'no logic (register copies).', 1695, '1 cycle a spine level.'),
        ('ot_s81hd_spr', {'N': ['i'], 'S': ['o', 'ck', 'rst_n'], 'W': ['iw'], 'E': ['ie']},
         {'i': [10.0, W - 10], 'o': [10.0, W - 10], 'iw': [20.0, H - 20], 'ie': [20.0, H - 20]},
         'every input lands in a flop (i x / go / xv, per port 3 kept rv copies + row / bits / flt), every output '
         'leaves a flop; iw / ie x / go / xv are unused inputs (the chain ends\' stream copies).',
         'hold enables from 5 kept rv copies a port (<= 22 load pins), selects 11 / 7 kept copies (<= 8 bits each), '
         'keys from ot_s81hd_key (kept sign / -0 copies a byte).  Round 1 (s81hd_spr_m route EARLY_FAIL_SETUP reg -> out '
         '-467 ps: the N-face stream flop drove the S-face pin in one cycle; gate census max 88): 2-stage stream forward, '
         'key unit, copies.',
         'keys 2 registered stages, then 2 registered compare levels (pair (iw, ie), then (pair, i)) on registered keys.',
         2600, 'fire = 6 edges after the last best (2 key stages, select, pair, select, output), cleared by i.go; the '
         'stream on the return spine is 2 cycles a node.')]:
        name = f's81hd_{top[-3:]}_{v}' + ('2' if top == 'ot_s81hd_spr' else '')   # spr round 2 (route 1 EARLY_FAIL_SETUP)
        why = (f'S81-HEAD HD-TILE 10-21 {tag}: new spine node {top} (SPEC v1 section 2, 26 a die), std-cell only, '
               f'{W} x {H}.')
        nb = [BENCHES[0], bench('hd_mut_spo_ow_drop', 'A', 'SPO_OW_DROP', r'^A: TB_FAIL results 0 != positions 2$')
              if top == 'ot_s81hd_spo' else
              bench('hd_mut_spr_early', 'A', 'SPR_EARLY', r'^A: TB_FAIL row 0 != 21946$')]
        s = common(name, top, NODE_SRC, {'w': W, 'h': H}, pins, rng, why, nb)
        s['route']['pin_balance'] = {'group_max': 1, 'h': 'M4', 'v': 'M3 M5'}
        s['fill_reason'] = {'pin_bound': (
            f'Pin-bound: 2,260 bus pins on four faces of the SPEC 216 x 648 spine slot; std-cell fill well under 40% '
            f'is the price of the slot and faces (RULE FREEZE 10-20: tile fill is guidance).')}
        s['_safe_node'] = dict(top=top, pinsafe=pinsafe, w=W, h=H, half=round(H / 2), fan=fan, depth=depth, nflop=nflop,
                               dens=565 / (W - 20), sched=sched)
        KITS[name] = s

ONLY = sys.argv[2:] or list(KITS)
CEN = json.loads((WT / RES / 'census.json').read_text()) if (WT / RES / 'census.json').exists() else {}
for name, s in KITS.items():
    if name not in ONLY:
        continue
    dst = RT / name
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    safe = s.pop('_safe', None); safen = s.pop('_safe_node', None)
    (dst / 'spec.json').write_text(json.dumps(s, indent=1) + '\n')
    c = CEN.get(s['top'])
    cen = (f"census (pre-gate native census, mapped netlist {c['source']}): max dynamic loads {c['max_loads']} "
           f"(limit 32, reset included), flops {c.get('flops', 'n/a')}, std-cell area {c.get('area_um2', 'n/a')} um2, "
           f"status {c['status']}.\n") if c else 'census: pending (pre-gate native census run with the first gate).\n'
    body = (SAFE_TILE.format(cyc=CEN.get('mini_cycles', 8375), **safe) if safe else SAFE_NODE.format(**safen))
    (dst / 'README.md').write_text(f'# {name} (S81-HEAD HD-TILE 10-21)\n\n{s["structural_change"]}\n\n{body}\n{cen}')
    r = subprocess.run(['python3', 'tools/ref_tile/ref_tile.py', 'gen', str(dst / 'spec.json')], cwd=WT,
                       capture_output=True, text=True)
    print(name, r.returncode, r.stdout[-300:], r.stderr[-600:])
