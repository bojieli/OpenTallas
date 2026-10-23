#!/usr/bin/env python3
"""KVPC-R 10-23: structural floorplan redesign of the KV die PC tile (qkd_kvs_pc, 124 instances) -> kits
physical/ref_tile/qkd_kvs_pc_r3a (MAIN) and qkd_kvs_pc_r3b (ALT), derived from qkd_kvs_pc_sr15f (sr13a RTL byte-identical,
FT-KV-PC abutment-aligned chain pins, layer cap M5 = OT_KV_OBS_CONTRACT kit cap).

COORD visual review 10-23 (tile-review-1023 contact_01 #2) of sr15f: 389x356 um, 23 SRAMs gridded over the lower half
(5 columns of 4-6, 20-um channels, pins facing away from the logic), logic in scattered blobs (13% fill, 61% empty).

What changes (RTL, ports, clocks, CTS recipe, SDC unchanged):
  1. MACRO BANK: the 23 ot_sram_1r1w2c_32x64_m1 (31.992 x 17.304, all 208 pins on the LEF W edge) form ONE bank of two
     abutted N-S stacks (ref_tile abutted_stack: no signal pin on the touching faces), back to back across one 20.3-um
     channel (the arrays carry PG on both side faces, so abutted_row refuses a 0-um back-to-back pair):
       column A (R0, pins face W -> the PHY band): u_front 5 + u_return 5 + u_sched.u_tq 2 = 12 arrays
       column B (MY, pins face E -> the main logic band): u_ecdc.down 6 + u_ecdc.up 5 = 11 arrays
     pitch = array height + 0.024 (17.328 um, on the M4 track), bank 84.3 x 216.6 um, vertically centred.
     The PHY band (W of the bank) carries the HBM-side logic (u_port read capture of pc__pi, front read -> pc__po,
     return ring write); the main band (E of the bank) carries controller / scheduler / chain stations / CDC / embedding
     return hop.  Both bands are contiguous rectangles; they meet above and below the bank.
  2. OUTLINE from content + pins: the tile is PIN-BOUND, not area-bound.  4,658 data pins (synthesis netlist census:
     4,389 flop-direct within <= 4 buffers, 266 dead inputs, 3 tied outputs; kv_netlist_pin_reg_census.py).  The height
     stays 356.4 (die PC pitch 378, groups at 4 x 378); the width shrinks 388.8 -> 270.0 (MAIN) / 302.4 (ALT) by moving the
     group return word o_grp (295 b) from the N face to the E face's N end (canonical E = toward the group column).
     Face loads MAIN: N 1,252 / 268 um = 4.7 /um, S 1,116 = 4.2 /um, E 1,665 / 354 um = 4.7 /um, W 625 (unchanged PHY
     abutment ranges).  60-70 % utilisation would need ~45-50k um2 (e.g. 220 x 220), i.e. >= 7 pins/um on every face:
     not buildable at a 4-5 pins/um face (sr12g 267.8 x 300.2 at 5.9 /um failed); reported as pin-bound fill.
  3. FT-KV: the column-chain words stay abutment-aligned (S o_prev = N i_next x range and bit order, S i_prev = N o_next,
     S pc__ko = N pc__ki, S pc__fi = N pc__fo) so tile k+1 meets tile k straight across the gap; no foreign die lane
     crosses the PC column (FT-KV census 00:22), so no extra ft ports; M5 kit cap (OBS contract) kept.
  4. PIN REGISTERS: every live data pin is already flop-direct in RTL and in the mapped netlist (pin_regs off with the
     recorded reason, io_flop_at_pins anchors them at the face): 0 added cycles, 0 schedule change.
Usage: kvs_pc_r3_kits.py   (writes the two spec.json files; then ref_tile.py gen each)
"""
import copy
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
BASE = 'physical/ref_tile/qkd_kvs_pc_sr15f/spec.json'
SRAM = 'physical/asap7_memory_macros_v2/ot_sram_1r1w2c_32x64_m1'
MW, MH = 31.992, 17.304
PITCH = MH + 0.024                       # abutted N-S stack (ref_tile.abutted_stack)
GAP_AB = 20.304                         # A | B channel: the arrays carry PG on both W / E faces (abutted_row needs bare faces)
H = 356.4
WIDTH = {'N': None}

# widths (bits) of every port
BITS = dict(i_next=780, o_next=299, pc__ki=33, pc__fo=1, x__est__0_1=1, i_grp=33, i_grp_h=95, o_grp_h=10,
            i_prev=299, o_prev=780, pc__ko=33, pc__fi=1, pc__hfx=3, o_grp=295,
            hrst_n=1, pc__cfg_stack=2, pc__completion_v=1, pc__completion_we=1, pc__er=261, pc__hcompletion_v=1,
            pc__hcompletion_we=1, pc__her=261, pc__hes=288, pc__land_er=261, pc__land_es=288, pc__pc=5, rst_n=1)
COL_A = ['*u_front.u_mem.g_b?%d?.u_m' % i for i in range(5)] + ['*u_return.u_mem.g_b?%d?.u_m' % i for i in range(5)] + \
        ['*u_sched.u_tq.u_e', '*u_sched.u_tq.u_o']
COL_B = ['*u_ecdc.down.g_sram.u_mem.g_b?%d?.u_m' % i for i in range(6)] + \
        ['*u_ecdc.up.g_sram.u_mem.g_b?%d?.u_m' % i for i in range(5)]


def spread(order, lo, hi, gap=0.36):
    """consecutive ranges for the ports in `order` over [lo, hi], proportional to their bits, `gap` um between ports"""
    n = sum(BITS[p] for p in order)
    pitch = (hi - lo - gap * (len(order) - 1)) / n
    out, x = {}, lo
    for p in order:
        w = max(BITS[p] * pitch, 0.29)
        out[p] = [round(x, 4), round(x + w, 4)]
        x += w + gap
    return out, pitch


def build(name, tag, W, x0, why, base=BASE, vlay=None, ya=73.44):
    s = json.load(open(os.path.join(ROOT, base)))
    head = s['top'] == 'qkd_kvs_pc_h'      # chain head (4 instances): no S chain words (no i_prev / o_prev)
    s = copy.deepcopy(s)
    s['name'] = name
    s['outline'] = {'w': W, 'h': H, 'exact': True}
    # ---- pins: N = chain (aligned) + group inputs at the E end; S = mirrored chain; E = host words + o_grp (N end)
    nord = ['o_next', 'pc__fo', 'i_next', 'x__est__0_1', 'pc__ki', 'i_grp', 'i_grp_h', 'o_grp_h']
    rng, pn = spread(nord, 1.0, W - 1.0)
    srng = {'i_prev': rng['o_next'], 'pc__fi': rng['pc__fo'], 'o_prev': rng['i_next'], 'pc__ko': rng['pc__ki']}
    if head:
        del srng['i_prev'], srng['o_prev']
    hx = rng['i_grp'][0]
    srng['pc__hfx'] = [round(hx, 4), round(hx + 1.0, 4)]
    eord = ['hrst_n', 'pc__cfg_stack', 'pc__completion_v', 'pc__completion_we', 'pc__er', 'pc__hcompletion_v',
            'pc__hcompletion_we', 'pc__her', 'pc__hes']
    eord2 = ['pc__land_er', 'pc__land_es', 'pc__pc', 'rst_n', 'o_grp']
    # clocks keep their mid-face entry (the sr15 clock tree enters at E 170.7 / 182.7)
    e1, pe1 = spread(eord, 5.4, 168.2)
    e2, pe2 = spread(eord2, 188.2, H - 1.0)
    pr = dict(s['pin_ranges'])
    for k in list(pr):
        if k in rng or k in srng or k in e1 or k in e2:
            del pr[k]
    pr.update(rng)
    pr.update(srng)
    pr.update(e1)
    pr.update(e2)
    s['pin_ranges'] = pr
    s['pins'] = dict(s['pins'])
    s['pins']['N'] = [p for p in s['pins']['N'] if p != 'o_grp']
    s['pins']['E'] = s['pins']['E'] + ['o_grp']
    # ---- macro bank
    # ya default 73.44 = 23.76 + 23 x 2.16: the sr15 on-track row origin family (r5: 23.76, the bank on the S pin edge)
    yb = ya + 8.64
    macros = []
    for k, inst in enumerate(COL_A):
        macros.append(dict(view=SRAM, count=1, inst=inst, at=[round(x0, 4), round(ya + k * PITCH, 4)], orient='R0',
                           at_exact=True))
    for k, inst in enumerate(COL_B):
        macros.append(dict(view=SRAM, count=1, inst=inst, at=[round(x0 + MW + GAP_AB, 4), round(yb + k * PITCH, 4)], orient='MY',
                           at_exact=True))
    s['macros'] = macros
    dens = {f: sum(BITS.get(p, 0) for p in s['pins'][f]) for f in 'NSE'}
    s['fill_reason'] = {'pin_bound': (
        f"KVPC-R r3 pin-bound outline: N {dens['N']} pins / {W - 2:.1f} um = {dens['N'] / (W - 2):.2f} /um (chain words "
        f"aligned with S), S {dens['S']} = {dens['S'] / (W - 2):.2f} /um, E {dens['E']} (incl. o_grp moved from N) / "
        f"{H - 2:.1f} um = {dens['E'] / (H - 2):.2f} /um, W 625 = PHY abutment ranges unchanged; height fixed by the die PC "
        "pitch 378.  Content (std ~14-17k + macros 12.7k um2) would fit ~220 x 220 at 60-70 %, which needs >= 7 pins/um on "
        "every face (sr12g at 5.9 /um failed); the width is the smallest that keeps every face <= ~4.7 /um.")}
    if vlay:
        # KVPC-R r4 (GEOM-REVIEW 02:05 FAIL of r3: empty SE quadrant, S / E-low face strips cut off from the logic mass):
        # the N / S chain words alternate M3 / M5 (ref_tile pin_balance default layers, both <= the M5 cap), which halves
        # the per-layer N / S density, so the width shrinks to the content: one PHY band W of the bank and ONE main band
        # E of it spanning N to S (the chain words pass N <-> S through it), no empty quadrant.
        s['route'] = dict(s['route'], pin_balance=dict(s['route']['pin_balance'], v=vlay))
        nl = len(vlay.split())
        s['fill_reason'] = {'pin_bound': (
            f"KVPC-R r4 outline {W} x {H}: N {dens['N']} pins / {W - 2:.1f} um = {dens['N'] / (W - 2):.2f} /um over {nl} "
            f"layers ({vlay}) = {dens['N'] / (W - 2) / nl:.2f} /um/layer, S {dens['S']} = {dens['S'] / (W - 2) / nl:.2f} "
            f"/um/layer, E {dens['E']} / {H - 2:.1f} um = {dens['E'] / (H - 2):.2f} /um (M4; M6 is above the cap); height "
            "fixed by the die PC pitch 378.  Width = PHY band + macro bank (84.3) + main band sized to the std content.")}
    s['kits_b'] = dict(s['kits_b'], frame=[round(W + 2.16, 2), 358.56], kit_outline=[W, H])
    bname = os.path.basename(os.path.dirname(base))
    s['pre_cts_extra'] = [p.replace(bname, name) for p in s['pre_cts_extra']]
    s['safe_design_checklist'] = f'see physical/ref_tile/{name}/README.md'
    pur = (f"KVPC-R 10-23 {tag}: COORD-review redesign of {'qkd_kvs_pc_h (sr15b' if head else 'qkd_kvs_pc (sr15f'} geometry: 23 SRAMs gridded, pins away from "
           f"logic, 13% fill / 61% empty). One macro bank (2 abutted back-to-back stacks of 12 R0 + 11 MY arrays at x "
           f"{x0}), PHY band W of the bank faces column A (front/return/tq), main band E faces column B (ecdc); outline "
           f"{W} x {H} (pin-bound; o_grp N -> E); chain pins abutment-aligned N/S (FT-KV); RTL = sr13a byte-identical "
           f"(every live pin flop-direct: 0 cycles). {why}")
    s['purpose'] = pur
    s['job'] = dict(s['job'], owner='Claude:KVPC-R', branch='claude/kvpc-r-1023', tag=tag, purpose=pur)
    # KVPC-R 10-23: the tile lockstep runs 20k edges (the sr9 witness length).  At the bench default 3k edges mutant 7
    # (static-row match without lookahead) is NOT detected (KVPC_TILE PASS mut=7); at 20k it FAILs (7476 errors) and
    # the positive still PASSes (528046 checks, 0 errors).
    for b in s['job']['benches']:
        if '--unit tile' in b['cmd'] and '--edges' not in b['cmd']:
            b['cmd'] = b['cmd'].replace(' --threads ', ' --edges 20000 --threads ', 1)
    s['structural_change'] = pur
    d = os.path.join(ROOT, 'physical/ref_tile', name)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, 'spec.json'), 'w') as f:
        json.dump(s, f, indent=1)
        f.write('\n')
    print(name, W, 'N/S/E pins per um', {k: round(v / ((W if k in 'NS' else H) - 2), 2) for k, v in dens.items()},
          'pin pitch N', round(pn, 4), 'E', round(pe1, 4), round(pe2, 4))
    return d


if __name__ == '__main__':
    build('qkd_kvs_pc_r3a', 'r3a', 270.0, 43.2, 'MAIN: 270.0 wide, PHY band 41 um.')
    build('qkd_kvs_pc_r3b', 'r3b', 302.4, 64.8, 'ALT: 302.4 wide (N/S 4.1-4.2 /um), PHY band 63 um.')
    # PC_H (chain head, 4 instances, base qkd_kvs_pc_h_sr15b): same bank / bands / faces, no S chain words
    BH = 'physical/ref_tile/qkd_kvs_pc_h_sr15b/spec.json'
    # r4 (after GEOM-REVIEW FAIL of r3): N / S pins on M3 + M5, width from content
    for nm, b in (('qkd_kvs_pc', BASE), ('qkd_kvs_pc_h', BH)):
        build(f'{nm}_r4a', nm[8:] + '_r4a', 205.2, 43.2, 'r4 MAIN: 205.2 wide, N/S on M3+M5, PHY band 41 um.', b, 'M3 M5')
        build(f'{nm}_r4b', nm[8:] + '_r4b', 226.8, 43.2, 'r4 ALT: 226.8 wide (wider main band), N/S on M3+M5.', b, 'M3 M5')
        # r5 (r4 placed image: the S 60 um stayed light -- the chain station registers sit N, the S face only lands its
        # pin registers): the bank moves onto the S pin edge (y 23.76, 20 um inside the core), the freed ~125 um at the
        # N end takes the N-heavy logic; S pin registers sit in the 20-um strip under the bank and beside it
        build(f'{nm}_r5a', nm[8:] + '_r5a', 205.2, 43.2, 'r5: r4a with the bank on the S pin edge.', b, 'M3 M5', 23.76)
    build('qkd_kvs_pc_h_r3a', 'h_r3a', 270.0, 43.2, 'PC_H MAIN: 270.0 wide, PHY band 41 um.', BH)
    build('qkd_kvs_pc_h_r3b', 'h_r3b', 302.4, 64.8, 'PC_H ALT: 302.4 wide, PHY band 63 um.', BH)
