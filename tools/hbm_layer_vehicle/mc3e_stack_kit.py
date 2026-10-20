#!/usr/bin/env python3
"""HBM-MC3E 10-20: compact R0 abutted-stack MC3c v6 kit (fallback / release candidate to the literal-lattice square).

Geometry (all gen-legal: >=20 um channels, R0 N-S abutted stacks of the W/E-pinned p192 SRAM, fill >= 35%):
  six 54 um macro columns (x = 23.76 + 54 k), two stack rows around one full-width central std-cell band.
  S row (PHY face): response[i] / write[i] stacked in column i (i = 0..3, aligned with data group i on BOTH faces),
                    queue / pending_identity (col 4), response_identity (col 5).
  N row (K face):   head 0/1, head 2/3, post[j] 0/1 for j = 0..3 (cols 0..5).
Pins: 64-bit data group i of every 256-bit bus sits over macro column i (two interleaved buses per face, 0.192 um),
controls centred; clk/rst_n at the W face centre of the band.  Same RTL/params/benches as hdie_pc_ctrl_mc3c6_p540.
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'physical/ref_tile/hdie_pc_ctrl_mc3c6_p540/spec.json'
LAYOUT = sys.argv[1] if len(sys.argv) > 1 else 't242'
NAME = f'hdie_pc_ctrl_mc3c6_{LAYOUT}'
KIT = ROOT / f'physical/ref_tile/{NAME}'
if LAYOUT == 's350':
    W, H = 349.92, 213.84
    COLS = [23.76 + 54 * k for k in range(6)]
    YS, YN = 23.76, 133.92
else:   # t242: 4 columns = 4 data groups; 3-high stacks; width < the 265.584 um PHY PC pitch (one shoreline row)
    W, H = 241.92, 272.16
    COLS = [23.76 + 54 * k for k in range(4)]
    YS, YT = 23.76, 221.424
P = 27.552                      # abutted N-S stack pitch: array height + 0.012 (M4 0.048 track multiple; ref_tile abutted_stack gap <= 0.1)
if LAYOUT == 's350':
    BAND = (YS + P + 27.54, YN)     # full-width central std-cell band
    CLK_Y = 106.368                 # centre of the band, on the M4 grid (old p540 face)
    CTRL_X = None
else:
    BAND = (YS + 2 * P + 27.54, YT - 2 * P)
    CLK_Y = 136.32
    CTRL_X = COLS[1] + 30.72        # controls between data groups 1 and 2 (centre of the face)
WIDTHS = dict(clk=1, rst_n=1, pc_id=5, refresh_reload=8, k_v=1, k_rdy=1, k_we=1, k_addr=30, k_len=4, k_tag=17,
              k_wdata=256, k_wstrb=32, kr_v=1, kr_rdy=1, kr_tag=17, kr_beat=4, kr_data=256, k_wr_done=1, row_v=1,
              row_op=3, row_bank=5, row_row=19, col_v=1, col_we=1, col_bank=5, col_col=5, col_data=256, col_strb=32,
              dram_rvalid=1, dram_rdata=256, pc_fault=1, owner_fault_split=6)


def macros():
    if LAYOUT != 's350':
        return macros_t()
    m = []
    def add(inst, col, y):
        m.append(dict(view='physical/asap7_memory_macros/ot_sram_1r1w_128x64_m1_p192', count=1,
                      at=[round(COLS[col], 4), round(y, 4)], at_exact=True, orient='R0', inst=inst))
    for i in range(4):
        add(f'u_native.u_response_payload.M[{i}].P.u_m', i, YS)
        add(f'u_native.g_wpay.u_write_payload.M[{i}].P.u_m', i, YS + P)
    add('u_native.controller.u_queue.M[0].P.u_m', 4, YS)
    add('u_native.u_pending_identity.M[0].P.u_m', 4, YS + P)
    add('u_native.u_response_identity.M[0].P.u_m', 5, YS)
    for h in range(4):
        add(f'u_native.METADATA[{h}].u_head.M[0].P.u_m', h // 2, YN + P * (h % 2))
    for j in range(4):
        for k in range(2):
            add(f'u_native.METADATA[{j}].u_post.M[{k}].P.u_m', 2 + j, YN + P * k)
    assert len(m) == 23
    return m


def macros_t():
    """S stacks (PHY face): response[i] / post / post in column i; N stacks (K face, top-aligned): extra / head[i] /
    write[i]; extras = queue (col 0), pending_identity (col 1), response_identity (col 2)."""
    m = []
    def add(inst, col, y):
        m.append(dict(view='physical/asap7_memory_macros/ot_sram_1r1w_128x64_m1_p192', count=1,
                      at=[round(COLS[col], 4), round(y, 4)], at_exact=True, orient='R0', inst=inst))
    for i in range(4):
        add(f'u_native.u_response_payload.M[{i}].P.u_m', i, YS)
        add(f'u_native.METADATA[{i}].u_post.M[0].P.u_m', i, YS + P)
        add(f'u_native.METADATA[{i}].u_post.M[1].P.u_m', i, YS + 2 * P)
        add(f'u_native.g_wpay.u_write_payload.M[{i}].P.u_m', i, YT)
        add(f'u_native.METADATA[{i}].u_head.M[0].P.u_m', i, YT - P)
    for c, inst in enumerate(('u_native.controller.u_queue.M[0].P.u_m', 'u_native.u_pending_identity.M[0].P.u_m',
                              'u_native.u_response_identity.M[0].P.u_m')):
        add(inst, c, YT - 2 * P)
    assert len(m) == 23
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
                    x = COLS[b // 64] + 4.608 + .192 * (2 * (b % 64) + (bus in ('kr_data', 'col_data')))
                    add(name, side, x, H if side == 'N' else 0)
                else:
                    controls.append(name)
        if side == 'W':
            controls = ['clk'] + [p for p in controls if p != 'clk']
        if side in ('N', 'S'):
            # controls in the free span right of data group 3 (cols 4/5 carry no data group)
            start = COLS[4] + 2.304 if CTRL_X is None else CTRL_X
            for i, name in enumerate(controls):
                add(name, side, start + .192 * i, H if side == 'N' else 0)
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
                       owner='Claude:HBM-MC3E (parent LEAD4-HBM)', branch='claude/hbm-mc3e-1020')
    spec['orfs_vars']['POST_IO_PLACEMENT_TCL'] = f'physical/ref_tile/{NAME}/post_iop_exact.tcl'
    spec['description'] = ('MC3c v6 (source 272b37645, native32 PASS) compact R0 abutted-stack floorplan ' + LAYOUT + ': '
                           + ('response/write payload stacks on the PHY (S) face aligned with their data groups, metadata '
                              'on the K (N) face' if LAYOUT == 's350' else
                              'response payload + post metadata stacks on the PHY (S) face, write payload + head + '
                              'queue/identity stacks on the K (N) face, column i = data group i on both faces; width '
                              '241.92 < 265.584 PHY PC pitch (one shoreline row)')
                           + '; one full-width central std band; fill >= 35%.')
    spec['floorplan_note'] = ('HBM-MC3E 10-20: Codex literal-43.2 square (hdie_pc_ctrl_mc3c6_p540) fails ref_tile gen: '
                              '15.66 um N-S macro channels (<20, not abutted) and fill 18% (lattice_channel_bound needs '
                              'ROOT approval + all std cells in one 40-60% band). This variant keeps every macro on the '
                              'asap7 track lattice (0.432/2.16, at_exact R0, abutted stacks per ref_tile abutted_stack), '
                              'NOT on the literal 43.2 child lattice: coordinator decision owed.')
    spec['reroute_reason'] = {'kind': 'rtl_change', 'why': 'Structural successor after v3 mapped native fanout rejection; '
                              'v6 exact same-edge regional bank/control partition, strict mapped census before layout; '
                              'new compact R0-stack floorplan with response SRAM beside the PHY return. MC3b superseded '
                              '(ACT starvation).'}
    KIT.mkdir(parents=True, exist_ok=True)
    (KIT / 'spec.json').write_text(json.dumps(spec, indent=1) + '\n')
    pins = pin_plan(spec)
    lines = [f'# Generated by tools/hbm_layer_vehicle/mc3e_stack_kit.py ({NAME}); all 1229 pins.',
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
    print(json.dumps(dict(kit=str(KIT.relative_to(ROOT)), pins=len(pins), band=BAND)))


if __name__ == '__main__':
    main()
