#!/usr/bin/env python3
"""HBM-MC3F 10-20: smallest LITERAL-43.2-lattice MC3c v6 kits (same RTL/params/benches as hdie_pc_ctrl_mc3c6_p540).

Why this geometry (derived, not chosen): the p192 SRAM is 33.696 x 27.540 um with signal pins on BOTH W and E faces.
With every macro origin on a 43.2 um multiple and >= 20 um macro channels:
  * E-W neighbours: pitch 43.2 leaves 9.50 um (FAIL); abutted_row needs bare faces (W/E carry pins) -> pitch 86.4.
  * N-S neighbours: pitch 43.2 leaves 15.66 um (FAIL); abutted_stack needs pitch 27.552 (off-lattice) -> pitch 86.4.
  * diagonal / brick offsets need the same 86.4 in one axis -> one macro per 86.4 x 86.4 lattice cell is the floor.
  * first origin 43.2 (core margin 2.16 + 20 um edge channel > 0), so 24 slots for 23 macros:
      l531: 6 cols x 4 rows -> 531.36 x 354.24 (2 PHY PC pitches wide = 531.168 + 0.19), fill 14.4 %
      l358: 4 cols x 6 rows -> 358.56 x 527.04 (fallback, mirrors t242: column i = data group i), fill 14.4 %
  fill < 35 % by construction -> only legal as fill_reason.lattice_channel_bound (ROOT / codex coordinator approval,
  one full-width std band at 40-60 % measured density, exact per-instance clock/pin exceptions outside the band).
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'physical/ref_tile/hdie_pc_ctrl_mc3c6_p540/spec.json'
LAYOUT = sys.argv[1] if len(sys.argv) > 1 else 'l531'
NAME = f'hdie_pc_ctrl_mc3c6_{LAYOUT}'
KIT = ROOT / f'physical/ref_tile/{NAME}'
L = 43.2
V = 'physical/asap7_memory_macros/ot_sram_1r1w_128x64_m1_p192'
if LAYOUT == 'l531':
    W, H = 531.36, 354.24
    COLS = [L * (1 + 2 * k) for k in range(6)]          # 43.2 .. 475.2
    ROWS = [L * (1 + 2 * r) for r in range(4)]          # 43.2, 129.6 | band | 216, 302.4
    DC = [0, 1, 4, 5]                                   # data group i sits over column DC[i] on N and S
    BAND = (175.23, 198.18)                             # in the 157.14..216 gap, row-lattice (0.27) aligned
    CLK_Y = 186.72
    CTRL_X = COLS[2] + 4.608
else:   # l358
    W, H = 358.56, 527.04
    COLS = [L * (1 + 2 * k) for k in range(4)]          # 43.2 .. 302.4
    ROWS = [L * (1 + 2 * r) for r in range(6)]          # 43.2, 129.6, 216 | band | 302.4, 388.8, 475.2
    DC = [0, 1, 2, 3]
    BAND = (255.15, 289.17)                             # in the 243.54..302.4 gap
    CLK_Y = 272.16
    CTRL_X = COLS[1] + 30.72
WIDTHS = dict(clk=1, rst_n=1, pc_id=5, refresh_reload=8, k_v=1, k_rdy=1, k_we=1, k_addr=30, k_len=4, k_tag=17,
              k_wdata=256, k_wstrb=32, kr_v=1, kr_rdy=1, kr_tag=17, kr_beat=4, kr_data=256, k_wr_done=1, row_v=1,
              row_op=3, row_bank=5, row_row=19, col_v=1, col_we=1, col_bank=5, col_col=5, col_data=256, col_strb=32,
              dram_rvalid=1, dram_rdata=256, pc_fault=1, owner_fault_split=6)
RESP = 'u_native.u_response_payload.M[{}].P.u_m'
WPAY = 'u_native.g_wpay.u_write_payload.M[{}].P.u_m'
POST = 'u_native.METADATA[{}].u_post.M[{}].P.u_m'
HEAD = 'u_native.METADATA[{}].u_head.M[0].P.u_m'
QUEUE, PEND, RID = ('u_native.controller.u_queue.M[0].P.u_m', 'u_native.u_pending_identity.M[0].P.u_m',
                    'u_native.u_response_identity.M[0].P.u_m')


def macros():
    m = []
    def add(inst, col, row):
        m.append(dict(view=V, count=1, at=[round(COLS[col], 4), round(ROWS[row], 4)], at_exact=True, orient='R0',
                      inst=inst))
    if LAYOUT == 'l531':
        # S half (PHY face): row 0 response[i] over its data group + post, row 1 post; N half (K face): row 3 write[i]
        # over its data group + head, row 2 head / queue / identities (one empty slot, col 5).
        free = [c for c in range(6) if c not in DC]
        for i in range(4):
            add(RESP.format(i), DC[i], 0)
            add(WPAY.format(i), DC[i], 3)
        posts = [POST.format(j, k) for j in range(4) for k in range(2)]
        for c, inst in zip(free + list(range(6)), posts):
            add(inst, c, 0 if c in free and posts.index(inst) < 2 else 1)
        add(HEAD.format(0), free[0], 3)
        add(HEAD.format(1), free[1], 3)
        for c, inst in enumerate((HEAD.format(2), HEAD.format(3), QUEUE, PEND, RID)):
            add(inst, c, 2)
    else:
        # mirrors t242: S rows response[i] / post[i].0 / post[i].1 in column i; N rows write[i] (top) / head[i] /
        # queue | pending | response_identity (one empty slot, col 3)
        for i in range(4):
            add(RESP.format(i), i, 0)
            add(POST.format(i, 0), i, 1)
            add(POST.format(i, 1), i, 2)
            add(WPAY.format(i), i, 5)
            add(HEAD.format(i), i, 4)
        for c, inst in enumerate((QUEUE, PEND, RID)):
            add(inst, c, 3)
    assert len(m) == 23 and len({tuple(x['at']) for x in m}) == 23 and len({x['inst'] for x in m}) == 23
    assert all(abs(v / L - round(v / L)) < 1e-9 for x in m for v in x['at'])
    return m


def pin_plan(spec):
    pins = {}
    def add(name, side, x, y):
        assert name not in pins
        if side in ('N', 'S'):
            x += .012
        else:
            y += .012
        pins[name] = dict(side=side, layer='M5' if side in ('N', 'S') else 'M4', at=[round(x, 6), round(y, 6)])
    for side, buses in spec['pins'].items():
        controls = []
        for bus in buses:
            for b in range(WIDTHS[bus]):
                name = bus if WIDTHS[bus] == 1 else f'{bus}[{b}]'
                if bus in ('k_wdata', 'kr_data', 'dram_rdata', 'col_data'):
                    x = COLS[DC[b // 64]] + 4.608 + .192 * (2 * (b % 64) + (bus in ('kr_data', 'col_data')))
                    add(name, side, x, H if side == 'N' else 0)
                else:
                    controls.append(name)
        if side == 'W':
            controls = ['clk'] + [p for p in controls if p != 'clk']
        if side in ('N', 'S'):
            for i, name in enumerate(controls):
                add(name, side, CTRL_X + .192 * i, H if side == 'N' else 0)
        else:
            for i, name in enumerate(controls):
                add(name, side, 0 if side == 'W' else W, CLK_Y + .192 * i)
    assert len(pins) == sum(WIDTHS.values()) == 1229
    for side in spec['pins']:
        pts = [tuple(p['at']) for p in pins.values() if p['side'] == side]
        assert len(pts) == len(set(pts))
        assert all(0 < (x if side in 'NS' else y) < (W if side in 'NS' else H) for x, y in pts)
    return pins


def main():
    spec = json.loads(SRC.read_text())
    spec['name'] = NAME
    spec['outline'] = {'w': W, 'h': H}
    spec['macros'] = macros()
    tag = NAME.replace('hdie_pc_ctrl_', '')
    spec['job'].update(tag=tag, record_to=f'results/rtl/ref_tile/{NAME}',
                       owner='Claude:HBM-MC3F (parent LEAD5-HBM)', branch='claude/hbm-mc3f-1020')
    spec['orfs_vars']['POST_IO_PLACEMENT_TCL'] = f'physical/ref_tile/{NAME}/post_iop_exact.tcl'
    spec['description'] = (f'MC3c v6 (source 272b37645, native32 PASS) LITERAL 43.2-lattice floorplan {LAYOUT}: all 23 '
                           'p192 SRAMs R0 on 43.2 origins (86.4 pitch, >= 52.7 um channels), one full-width std band '
                           f'y {BAND[0]}-{BAND[1]}, data group i over column {DC} on both faces.')
    spec['fill_reason'] = {'lattice_channel_bound': {
        'why': ('literal 43.2 lattice + >= 20 um channels with a W+E-pinned 33.696 x 27.54 SRAM forces one macro per '
                '86.4 x 86.4 cell (pitch 43.2 leaves 9.50 / 15.66 um; abutment needs 27.552 or bare faces); 23 macros '
                f'-> {W} x {H}, fill 14 % by construction'),
        'approved_by': '',                         # PENDING: ROOT / codex coordinator only (COORD-REVIEW-QUEUE)
        'std_band_y_um': list(BAND),
        'placed_exceptions': []}}                  # exact pin-register / clock instances, filled from the placed dump
    spec['floorplan_note'] = ('HBM-MC3F 10-20: literal-43.2 successor of the off-lattice t242/s350 stacks (HOLD). '
                              'Needs lattice_channel_bound approval + exact placed pin/clock exceptions before a gate '
                              'can run (pre_route_gate skips remote on the local fill FAIL).')
    spec['reroute_reason'] = {'kind': 'rtl_change', 'why': 'Structural successor after v3 mapped native fanout rejection; '
                              'v6 same RTL as t242/s350, literal 43.2 lattice floorplan (t242/s350 held off-lattice).'}
    KIT.mkdir(parents=True, exist_ok=True)
    (KIT / 'spec.json').write_text(json.dumps(spec, indent=1) + '\n')
    pins = pin_plan(spec)
    lines = [f'# Generated by tools/hbm_layer_vehicle/mc3f_lattice_kit.py ({NAME}); all 1229 pins.',
             'set ot_mc3_block [ord::get_db_block]']
    for name, p in pins.items():
        x, y = p['at']
        lines += [f'set ot_mc3_term [$ot_mc3_block findBTerm {{{name}}}]',
                  f'if {{$ot_mc3_term == "NULL"}} {{ error {{MC3c6 missing port {name}}} }}',
                  'foreach ot_mc3_bpin [$ot_mc3_term getBPins] { odb::dbBPin_destroy $ot_mc3_bpin }',
                  f'place_pin -pin_name {{{name}}} -layer {p["layer"]} -location {{{x} {y}}} -force_to_die_boundary']
    lines += ['orfs_write_db $::env(RESULTS_DIR)/3_2_place_iop.odb',
              'write_pin_placement $::env(RESULTS_DIR)/3_2_place_iop.tcl']
    (KIT / 'post_iop_exact.tcl').write_text('\n'.join(lines) + '\n')
    (KIT / 'pin_plan.json').write_text(json.dumps(dict(outline_um=[W, H], pins=pins), indent=1) + '\n')
    print(json.dumps(dict(kit=str(KIT.relative_to(ROOT)), pins=len(pins), band=BAND, area_um2=round(W * H, 1))))


if __name__ == '__main__':
    main()
