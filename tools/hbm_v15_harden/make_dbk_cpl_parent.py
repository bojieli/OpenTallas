#!/usr/bin/env python3
"""HCDMA-DBK 2026-10-17: hb_dbk cluster successor hv16_dbk_cpl = 8 CLOSED landing banks + CLOSED vp4 controller + the new
collar LEAF (physical/ref_tile/hv16_dbk_collar, ot_hgi_dma_back_cp_collar) + regional reset relays on clk_rst.

Measured reasons (hv15_dbk_cp gate 1f18141cb, 10-16): clk_cp 1,844 sinks TT 421.6 / spread 126.5 (collar flops smeared
between the 8 banks), rst_n port -> 793 loads unregistered incl. 8 bank macros + controller (in->macro -296.1),
in->reg -170.8 u_cp.cmd[26] with the W face 98% pin-full; children off the 43.2 um lattice; 645.84 x 360.72 (1.79:1).

Why not the d4f slot 560 x 400: on the 43.2 um child lattice three 87.48-um bank rows need y = 43.2/172.8/302.4 (top
389.9, no N channel left in 400) and three 140.4-um columns need x up to 529.2, so 560 x 400 holds at most 2 x 3 = 6 banks;
8 banks + controller + collar leaf = 10 objects, and every bank must stay within ~480 um of BOTH the W face (rr) and the
N face (wd) (textbook wire_reach 500 um/stage).  A 3-row ring (controller centre) cannot take the leaf within 1.5:1
(width >= 712 at height 432).  Chosen: 4 rows x 3 columns, 604.8 x 540 (1.12:1):
  * col0 (x 86.4, 4 banks; 86.4 um W channel carries their 1,156 wd bits N), col1/col2 (x 259.2/432) banks in rows 0
    and 3; the controller in col1 between rows 1-2 (bank star <= ~430 um), the collar leaf in col2 between rows 1-2
    (W face -> controller E face 104 um; E face 21.6 um from the cluster E face where the F20 host bus enters);
  * channels >= 32.4 um (columns) / 42.1 um (rows), every child on the 43.2 lattice;
  * W face: rr per bank row (rq + rr_valid beside the controller row), <= 4.6 pins/um; N face: wd per bank column + wb/wa,
    <= 4.5 pins/um; each clk_bank entry on the face point nearest its bank clock pin; clk_cp at the leaf clock pin."""
import json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
NAME = 'hv16_dbk_cpl'
OUT = ROOT / 'results/arch/hbm_die_v16_d4f/dbk_cpl_1017'
W, H = 606.96, 542.16   # OWNERS-HBM/STK 10-18: +2.16 each way (604.8x540 left the top bank row 18.4 um and the collar 19.4 um
                         # from the N/E core edges, pin faces need >= 20; gen FAIL macro_edge). Children/pins unchanged.
BW, BH = 140.4, 87.48
COLS = [86.4, 259.2, 432.0]
ROWS = [43.2, 172.8, 302.4, 432.0]
CTRL = (259.2, 259.2)                       # 69.12 x 69.12
LEAF = (432.0, 216.0)                       # 151.2 x 129.6
LW, LH = 151.2, 129.6
HOME = {0: (0, 0), 1: (1, 0), 2: (2, 0), 3: (0, 1), 4: (0, 2), 5: (0, 3), 6: (1, 3), 7: (2, 3)}
BANK = 'physical/ref_tile/hv15_dbk_bank/views/ot_hgi_dma_back_landing_bank'
CTLV = 'physical/ref_tile/hv15_dbk_vp4_ctl/views/ot_hgi_dma_back_static_vp4_controller'
LEAFV = 'physical/ref_tile/hv16_dbk_collar/views/ot_hgi_dma_back_cp_collar'
CLKX_IN_BANK = 21.7     # bank clock pin: N face, x offset (LEF)
CTL_CLK_Y = 51.5        # controller clock pin: E face, y offset (LEF)

def grid(lo, hi, n, avoid=()):
    """n legal track centres (.012 + k*.048) spread over [lo, hi], >= .096 apart, >= .192 from every avoid point"""
    cand = [round(.012 + k * .048, 6) for k in range(int((lo - .012) / .048) + 1, int((hi - .012) / .048) + 1)]
    cand = [c for c in cand if all(abs(c - a) >= .192 - 1e-9 for a in avoid)]
    picks, last = [], -1e9
    step = max(.096, (hi - lo) / max(n, 1))
    for c in cand:
        if c - last >= .096 - 1e-9 and (not picks or c >= picks[0] + step * len(picks) - .024):
            picks.append(c); last = c
            if len(picks) == n: break
    assert len(picks) == n, (lo, hi, n, len(picks))
    return picks

def snap(v):
    return round(.012 + round((v - .012) / .048) * .048, 6)

def leaf_clk_y():
    """the routed leaf's clock pin (E face) once its view exists, else the leaf mid-height"""
    lef = ROOT / LEAFV / 'ot_hgi_dma_back_cp_collar.lef'
    if lef.is_file():
        m = re.search(r'PIN clk\n.*?RECT\s+[\d.]+\s+([\d.]+)\s+[\d.]+\s+([\d.]+)', lef.read_text(), re.S)
        if m: return LEAF[1] + (float(m.group(1)) + float(m.group(2))) / 2
    return LEAF[1] + LH / 2

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    pins = {}
    bx = {b: COLS[c] for b, (c, r) in HOME.items()}; by = {b: ROWS[r] for b, (c, r) in HOME.items()}
    clkpt = {}
    for b, (c, r) in HOME.items():
        x, ytop = bx[b] + CLKX_IN_BANK, by[b] + BH
        if r == 3: clkpt[b] = ('N', snap(x))                              # top row: straight up (20.5 um)
        elif c == 0: clkpt[b] = ('W', snap(ytop + 10.26))                 # left column: along the row channel
        elif c == 1: clkpt[b] = ('S', snap(COLS[c] - 16.2))               # (1,0): up the column channel
        else: clkpt[b] = ('E', snap(ytop + 10.26))                        # (2,0): along the row-0/1 channel
    for b, (f, v) in clkpt.items(): pins[f'clk_bank[{b}]'] = (f, v)
    pins['clk'] = ('E', snap(CTRL[1] + CTL_CLK_Y))
    pins['clk_cp'] = ('E', snap(leaf_clk_y()))
    pins['clk_rst'] = ('E', snap(190.0))
    avoid = {f: [v for n, (ff, v) in pins.items() if ff == f] for f in 'NSEW'}
    # W face: rr per bank row; rq + rr_valid beside the controller rows
    # HBM-DBKCPL 10-18: the col2 banks (2 = row 0, 7 = row 3) take rr on the N/S face beside their wd, not the W face.
    # With rr on W (432 um away) their 547 block pins had a centroid 157 um from the bank (daemon FLOORPLAN_MARGIN
    # bank_distance, hv16_dbk_cpl-q1-c2094045d) and rr[2*257+..] was the gate's worst in->macro path (-58.8 ps TT placement):
    # 2 x 256 unregistered bits ran 430 um across the cluster.  Now they run ~110 um (bank W edge -> col1/col2 channel ->
    # face); the die carries them on its own relayed lanes.  rr_valid (rr[b*257+256]) stays on W with the controller.
    # Wires only, 0 cycles.  Banks never sit more than 100 um from their pins' centroid on the 3-column lattice otherwise:
    # with rr on W a bank needs x0 <~ 290 um, so only two columns qualify.
    FARC = 2
    rowbanks = {r: [b for b, (c, rr) in sorted(HOME.items(), key=lambda t: t[1][0]) if rr == r and c != FARC] for r in range(4)}
    seg = {0: (2.4, 170.0), 1: (172.0, 248.0), 2: (296.0, 368.0), 3: (370.0, 537.6)}
    for r, banks in rowbanks.items():
        names = [f'rr[{b*257+i}]' for b in banks for i in range(256)]
        for n, v in zip(names, grid(*seg[r], len(names), avoid['W'])): pins[n] = ('W', v)
    ctl = [f'rr[{b*257+256}]' for b in range(8)] + [f'rq[{i}]' for i in range(136)]
    for n, v in zip(ctl, grid(250.0, 294.0, len(ctl), avoid['W'])): pins[n] = ('W', v)
    # N face: wd per bank column, wb/wa between col1 and col2
    # OWNERS-HBM/STK 10-18: wd leaves through the NEAREST N/S face (rows 2-3 N, rows 0-1 S).  All-N (HCDMA-DBK 10-17)
    # failed the gate wire_reach: row-0 banks' unregistered wd ran 654 um to the N face (bank -> pin, > 500 um/stage) and
    # macro->out wd[839] -149.5 ps.  wd stays wires-only (no parent flop, no added cycle); the die takes wd from both faces.
    nseg = {0: (2.4, 262.0), 1: (264.0, 398.0), 2: (432.0, W - 2.4)}
    # HH-7 10-19 (hv16_dbk_cpl-q1-65c2387ab TT: L[4].wd[277] -> wd[1433] -7.63 / wd[1415] -6.15): in column 0 the bank
    # FARTHER from the face takes the channel-side (W-most) range, as on S (row 1 -> 2.4..131.8).  N had it inverted
    # (row 3 first): row 2's wd climbed the W channel past bank 5 and then ran 46..175 um east (~375 um bank -> pin);
    # now ~290 um, bank 5's ~270 um.  Wires only, 0 cycles.
    for face, rows in (('N', (2, 3)), ('S', (1, 0))):
        for c in range(3):
            banks = [b for r in rows for b, (cc, rr) in HOME.items() if cc == c and rr == r]
            names = [f'wd[{b*289+i}]' for b in banks for i in range(289)]
            if c == FARC: names += [f'rr[{b*257+i}]' for b in banks for i in range(256)]
            avoid.setdefault(face, [])
            for n, v in zip(names, grid(*nseg[c], len(names), avoid[face])): pins[n] = ('N' if face == 'N' else 'S', v)
    wb = (['wb_reserve_v', 'wb_reserve_bank', 'wb_fill_bank'] + [f'wb_reserve_epoch[{i}]' for i in range(16)] +
          [f'wb_fill_epoch[{i}]' for i in range(16)] + [f'wb_reserve_sectors[{i}]' for i in range(12)] +
          [f'wb_reserve_base[{i}]' for i in range(32)] + ['wb_fill_start', 'wb_ready'] + [f'wa[{i}]' for i in range(12)])
    for n, v in zip(wb, grid(400.0, 430.0, len(wb), avoid['N'])): pins[n] = ('N', v)
    # E face: F20 host bus + tgt + collar status at the leaf, controller strap/status + reset beside them
    # HBM-KITS-C/DBKCP 10-18: the controller's own E-face pins (stk[1:0] in, busy/quiet out; LEF y 51.4..64.2 on its E
    # edge x 328.3) leave at the controller row (~280 um straight east).  At the ends of the full-face list they ran
    # 598 um (stk -> E-face bottom) and 506 um (busy -> top): gate wire_reach FAIL at 90f961852.  Wires only, 0 cycles.
    cy = CTRL[1] + 57.8
    for n, v in zip(['busy', 'quiet', 'stk[0]', 'stk[1]'], grid(cy - 4.0, cy + 4.0, 4, avoid['E'])): pins[n] = ('E', v)
    avoid['E'] = [v for n, (ff, v) in pins.items() if ff == 'E']
    e = (['rst_n'] + [f'tgt[{i}]' for i in range(8)] + ['cfg_v'] + [f'cfg_target[{i}]' for i in range(8)] +
         [f'cfg_addr[{i}]' for i in range(12)] + [f'cfg_data[{i}]' for i in range(256)] + ['desc_v'] +
         [f'desc_base[{i}]' for i in range(12)] + [f'desc_limit[{i}]' for i in range(13)] + [f'desc_loops[{i}]' for i in range(16)] +
         ['launch_v', 'cp_configured', 'cp_fault', 'cp_active', 'mv_src', 'mv_done', 'mv_fault'])
    # OWNERS-HBM/STK 10-18: full E face (was 200..362 beside the leaf: a partial-face cluster); the leaf sits mid-face, so
    # the farthest host pin is <= ~330 um from it (one registered F20 hop, reach 405)
    for n, v in zip(e, grid(2.4, H - 2.4, len(e), avoid['E'])): pins[n] = ('E', v)
    lines = ['# HCDMA-DBK hv16_dbk_cpl: exact pin plan (tools/hbm_v15_harden/make_dbk_cpl_parent.py); ODB readback mandatory.',
             'source /src/physical/common_flow/assigned_pin_exact.tcl']
    for n, (f, v) in sorted(pins.items()):
        lines.append(f'ot_assigned_pin_exact {{{n}}} {"M5" if f in "NS" else "M4"} {f} {v:.6f}')
    (OUT / 'assigned_pins.tcl').write_text('\n'.join(lines) + '\n')
    faces = {}
    for n, (f, v) in pins.items(): faces.setdefault(re.sub(r'\[\d+\]$', '', n), set()).add(f)
    face_map = {'W': [], 'N': [], 'E': [], 'S': [], 'ANY': []}
    for base, fs in faces.items():
        (face_map['ANY'] if len(fs) > 1 else face_map[next(iter(fs))]).append(base)
    children = [dict(view=BANK, count=1, inst=f'u_dbk.L[{b}].u_bank', at=[bx[b], by[b]], orient='R0') for b in range(8)]
    children.append(dict(view=CTLV, count=1, inst='u_dbk.u_control', at=list(CTRL), orient='R0'))
    children.append(dict(view=LEAFV, count=1, inst='u_cp', at=list(LEAF), orient='R0'))
    why = (__doc__.split('\n\n', 1)[1]).replace('\n', ' ')
    spec = dict(name=NAME, top='ot_hgi_dma_back_static_vp4_banks_cp', kind='cluster',
        sources=['rtl/hbm_accel/generic/peers/static/ot_hgi_dma_back_static_vp4_banks_cp.sv',
                 'rtl/hbm_accel/generic/peers/static/ot_hgi_dma_back_cp_collar.sv',
                 'rtl/hbm_accel/host_static_20261015/ot_static_cmd_target.sv',
                 'rtl/hbm_accel/generic/peers/static/ot_hgi_dma_back_static_vp4_banks.sv',
                 'rtl/hbm_accel/generic/peers/static/ot_hgi_dma_back_static_vp_banks.sv',
                 'rtl/lib/ot_rst_relay.sv',
                 'physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_bb.v'],
        clock='hybrid_entries', clock_port='clk',
        clock_ports=['clk', 'clk_cp', 'clk_rst'] + [f'clk_bank[{b}]' for b in range(8)],
        clock_cts_roots=['clk_rst'], reset_ports=['rst_n'],
        pins={k: v for k, v in face_map.items() if v}, outline=dict(w=W, h=H, exact=True),
        pg_layer='M7', signal_max_layer='M6', child_lattice_um=43.2, children=children, macros=[],
        recipe=3, hard_define='OT_DBK_HARD', defines=['OT_DBK_HARD'],
        pin_regs=dict(enable=False, reason=('Banks, controller and the collar leaf are hard children owning their registered '
            'endpoints (bank/controller pin flops, collar core pin flops); the parent holds only wires and the reset relay '
            'flops (ot_rst_relay on clk_rst). A parent pin flop would add a cycle to rr/wd/rq and the host bus.')),
        route=dict(pd=0.5, period_ps=833.333, threads=8, peak_ram_gb=16, hold_margin_ns=0.03, io_hold_margin_ns=0.03, macro_halo_um=5.4,
                   pin_balance=dict(h='M4', v='M5', group_max=1)),
        # HH-7 10-19: 65c2387ab DRC 1 = parent M4 wire in the landing bank's M4 OBS pocket (M2-M4 belong to the child)
        boundary_tcl=['physical/common_flow/child_pocket_guard.tcl'],
        params={}, inter=[], io_flop_at_pins=dict(cols=4, allow_none=True), inhold=False, outhold=False,
        keep_pin_regs=True, io_tcl=f'results/arch/hbm_die_v16_d4f/dbk_cpl_1017/assigned_pins.tcl',
        slot_change_request=(f'hb_dbk_<q> (d4f slot 560.0 x 400.0) -> {W} x {H} (1.12:1): 8 banks + controller + collar leaf '
            'on the 43.2 lattice cannot fit 560 x 400 (see make_dbk_cpl_parent.py); master ports: clk_tab[1:0] removed, '
            'clk_rst added (reset relay root, same die clock); rr/rq W, wd/wb/wa N, F20 host bus/status/straps E, '
            'clk_bank on the nearest face (W x3, N x3, S x1, E x1); OWNERS-HBM/STK 10-18: 606.96 x 542.16 (macro_edge 20 um), wd of bank rows 0-1 on the S face, rows 2-3 on N (wire_reach), F20 host bus over the full E face; HBM-DBKCPL 10-18: rr of the col2 banks (rr[514..769] bank 2 -> S face, rr[1799..2054] bank 7 -> N face, beside their wd; rr_valid stays W) for daemon bank_distance (157 um).'),
        structural_change=why,
        reroute_reason=dict(kind='slot_change', source='physical/ref_tile/hv15_dbk_cp (gate 1f18141cb, structural FAIL)', why=why))
    # HBM-DBKCPL 10-18: retry of the refused c2094045d (FLOORPLAN_MARGIN bank_distance) with the fixed pin plan
    reroute_flow = dict(kind='flow_failure', failed_job='hv16_dbk_cpl-q1-c2094045d',
        failure=('FLOORPLAN_MARGIN bank_distance: u_dbk.L[7].u_bank 157.6 um / u_dbk.L[2].u_bank 157.2 um from their 547 '
                 "pins' centroid (rr on the W face 432 um away); fixed: their rr on the N/S face beside wd, wires only"),
        why=why)
    spec['reroute_reason'] = reroute_flow
    # HH-7 10-19: valid re-route hv16_dbk_cpl-q1-65c2387ab ended NEEDS_RTL TT -12.30 / FF +20.59 / DRC 1 (routed sign-off,
    # 4 endpoints, all parent wires of ~360-460 um between hard-child pins): controller faces split per bank group (RTL +
    # re-hardened hv15_dbk_vp4_ctl view), column-0 N wd order fixed, child pocket guard for the M4 DRC.
    spec['reroute_reason'] = dict(kind='rtl_change', failed_job='hv16_dbk_cpl-q1-65c2387ab',
        source='rtl/hbm_accel/generic/peers/static/ot_hgi_dma_back_static_vp4_banks.sv',
        failure=('TT -12.30: u_control/bank_read_addr[166] -> L[5].read_addr[6] -12.30 (S-face pin, ~457 um U-turn), '
                 'u_control/bank_write_slot[6] -> L[2].write_slot[6] -11.73 (one W-face 7-bit star to 8 banks), '
                 'L[4].wd[277] -> wd[1433] -7.63 / wd[1415] -6.15 (N wd order inverted in column 0); DRC 1 M4 Metal '
                 'Spacing inside u_dbk.L[0].u_bank (parent wire in the bank M4 OBS pocket)'),
        why=('controller bank_read_addr / slot copies leave on the face of the bank group they serve (S 0-2, W 3-4, '
             'N 5-7; worst leg ~457 -> ~343 um); column-0 N wd: farther bank on the channel side; parent M2-M4 '
             'obstructed over hard children between GRT and DRT (child_pocket_guard.tcl). 0 cycles, exact.'))
    spec['job'] = dict(owner='Claude:HOURLY-HBM/HH-7', branch='claude/hh7-dbkcpl-1019', tag='h7', record_to=f'results/rtl/ref_tile/{NAME}',
        purpose=('HBM die d4g hb_dbk_<q> x4 (per quadrant, master unchanged; F20 tgt 104+QID: SW 104 / SE 105 / NW 106 / NE 107; '
                 'RBH-STK). ' + why),
        extra_paths=sorted(['physical/common_flow/assigned_pin_exact.tcl', 'physical/common_flow/child_pocket_guard.tcl', BANK, CTLV, LEAFV,
                            'physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2',
                            'physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2',
                            'physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2',
                            'results/arch/hbm_die_v16_d4f/dbk_cpl_1017', 'rtl/hbm_accel/generic/peers/static',
                            'rtl/hbm_accel/generic/vm/static', 'rtl/hbm_accel/host_static_20261015', 'rtl/lib/ot_rst_relay.sv',
                            'tools/hbm_v15_harden']),
        benches=[dict(name='cp_fold_exact', cmd='bash tools/hbm_v15_harden/bench_dma_vp4_banks_cp.sh {RUN}/bench/cp', expect='pass',
                      threads=1, peak_ram_gb=4, needs=['iverilog'], pass_regex='DMA_CP_FOLD_GATE PASS',
                      min_count_regex='CP_FOLD PASS commands=(\\d+)'),
                 dict(name='reset_latency_mutant', cmd='bash tools/hbm_v15_harden/bench_dma_vp4_banks_cp.sh {RUN}/bench/rst rst',
                      expect='fail', threads=1, peak_ram_gb=4, needs=['iverilog'], pass_regex='CP_FOLD PASS',
                      fail_regex='DMA absolute cycle did not advance by one',
                      fail_witness=f'results/rtl/ref_tile/{NAME}/witness/reset_latency_mutant.log'),
                 dict(name='exact', cmd='bash tools/hbm_v15_harden/bench_dma_vp4_banks.sh {RUN}/bench/exact 0', expect='pass',
                      threads=1, peak_ram_gb=4, needs=['iverilog'], pass_regex='DMA_VP4_BANKS_BENCH_PASS'),
                 dict(name='strap_mutant', cmd='bash tools/hbm_v15_harden/bench_dma_vp4_banks.sh {RUN}/bench/mut4 4', expect='fail',
                      threads=1, peak_ram_gb=4, needs=['iverilog'], fail_regex='FATAL: .*dispatcher/engine fault at\\d+',
                      fail_witness=f'results/rtl/ref_tile/{NAME}/witness/strap_mutant.log')],
        reroute_reason=spec['reroute_reason'])
    d = ROOT / 'physical/ref_tile' / NAME; d.mkdir(parents=True, exist_ok=True)
    (d / 'spec.json').write_text(json.dumps(spec, indent=1) + '\n')
    print(NAME, len(pins), 'pins', {f: sum(1 for v in pins.values() if v[0] == f) for f in 'NSEW'}, 'clk entries', clkpt)

if __name__ == '__main__':
    main()
