#!/usr/bin/env python3
"""H-HARDEN 2026-10-16: DMA parent successor = folded collar (ot_hgi_dma_back_static_vp4_banks_cp) on a ring floorplan.

Measured reasons (hv15_dbk_cl gate on EPYC1, receipts 6d8f84699/8736a90db, evidence copied off EPYC1):
  * trial GRT overflow 240 -> 318 (M6 303), concentrated at ONE 21.6 um channel (top-left / top-middle banks): every
    bank carries 545 rr/wd pins on its W face, three banks shared each 21.6 um channel, rr/wd pins were ordered by bank
    index instead of by bank position (cross-traffic);
  * 136 reach violations = every rq bit (controller at the NE corner, rq pins on the W face: 552 um);
  * all nine clock entries sat at one E-face point: bank6's raw entry wire reached 701 ps / 2,222 ps slew.
Successor geometry (same R0 child views, no child re-route):
  * controller in the CENTRE of a 3x3 ring of the eight banks (bank-control star <= ~260 um, rq <= ~260 um);
  * channels 30.24 um (was 21.6) between columns, rows unchanged (20.52 um), >= 23.76 um from every pin face;
  * rr pins grouped per bank ROW on the W face, wd pins grouped per bank COLUMN on the N face;
  * every clk_bank[b] entry on the face point nearest its bank's clock pin (<= ~190 um, was <= 630 um);
  * the folded dispatcher collar (2 x 128x256 SRAM + pin-registered soft logic, clocked by clk) in an E column, with
    the F20 host bus and status on the E face; clk now has real soft sinks, so the parent builds a tree for it.
Outline grows 511.92 -> 645.84 um wide (same 360.72 height) for the collar column: a die slot change (H-DIE)."""
import json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
NAME = 'hv15_dbk_cp'
OUT = ROOT / 'results/arch/hbm_die_v15/dbk_cp_ring_1016'
W, H = 645.84, 360.72
BW, BH = 140.4, 87.48
COLS = [23.76, 194.4, 365.04]
ROWS = [23.76, 131.76, 239.76]
CTRL = (265.68, 140.4)
SRAMS = [(527.04, 118.8), (527.04, 181.44)]
# ring: (col, row) of each bank; the controller takes the centre
HOME = {0: (0, 0), 1: (1, 0), 2: (2, 0), 3: (0, 1), 5: (2, 1), 6: (0, 2), 7: (1, 2), 4: (2, 2)}
BANK = 'physical/ref_tile/hv15_dbk_bank/views/ot_hgi_dma_back_landing_bank'
CTLV = 'physical/ref_tile/hv15_dbk_vp4_ctl/views/ot_hgi_dma_back_static_vp4_controller'
SR = 'physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2'
CLKX_IN_BANK = 21.7     # bank clock pin: N face, x offset (LEF)

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

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    pins = {}
    bx = {b: COLS[c] for b, (c, r) in HOME.items()}; by = {b: ROWS[r] for b, (c, r) in HOME.items()}
    clkpt = {}
    for b, (c, r) in HOME.items():
        x, ytop = bx[b] + CLKX_IN_BANK, by[b] + BH
        if r == 2: clkpt[b] = ('N', snap(x))                              # top row: straight up
        elif c == 0: clkpt[b] = ('W', snap(ytop + 10.26))                 # left column: along the row channel
        elif r == 0: clkpt[b] = ('S', snap(COLS[c] - 15.12))              # bottom row: up the column channel
        else: clkpt[b] = ('N', snap(COLS[c] - 15.12))                     # (2,1): down the column channel
    for b, (f, v) in clkpt.items(): pins[f'clk_bank[{b}]'] = (f, v)
    avoid = {f: [v for (ff, v) in clkpt.values() if ff == f] for f in 'NSEW'}
    # W face: rr per bank row (+ valid bits and rq beside the controller row)
    rowbanks = {r: [b for b, (c, rr) in sorted(HOME.items(), key=lambda t: t[1][0]) if rr == r] for r in range(3)}
    seg = {0: (4.32, 117.0), 1: (124.0, 228.0), 2: (232.0, 356.4)}
    for r, banks in rowbanks.items():
        names = [f'rr[{b*257+i}]' for b in banks for i in range(256)]
        if r == 1:
            names += [f'rr[{b*257+256}]' for b in range(8)] + [f'rq[{i}]' for i in range(136)]
        for n, v in zip(names, grid(*seg[r], len(names), avoid['W'])): pins[n] = ('W', v)
    # N face: wd per bank column, wb/wa above the controller
    colbanks = {c: [b for b, (cc, r) in sorted(HOME.items(), key=lambda t: t[1][1]) if cc == c] for c in range(3)}
    nseg = {0: (4.32, 186.0), 1: (190.0, 262.0), 2: (336.0, 505.0)}
    for c, banks in colbanks.items():
        names = [f'wd[{b*289+i}]' for b in banks for i in range(289)]
        for n, v in zip(names, grid(*nseg[c], len(names), avoid['N'])): pins[n] = ('N', v)
    wb = (['wb_reserve_v', 'wb_reserve_bank', 'wb_fill_bank'] + [f'wb_reserve_epoch[{i}]' for i in range(16)] +
          [f'wb_fill_epoch[{i}]' for i in range(16)] + [f'wb_reserve_sectors[{i}]' for i in range(12)] +
          [f'wb_reserve_base[{i}]' for i in range(32)] + ['wb_fill_start', 'wb_ready'] + [f'wa[{i}]' for i in range(12)])
    for n, v in zip(wb, grid(265.0, 330.0, len(wb), avoid['N'])): pins[n] = ('N', v)
    # E face: collar clock/strap/F20 bus/status beside the collar column
    pins['clk'] = ('E', snap(178.0))
    e = (['rst_n', 'stk[0]', 'stk[1]'] + [f'tgt[{i}]' for i in range(8)] + ['cfg_v'] + [f'cfg_target[{i}]' for i in range(8)] +
         [f'cfg_addr[{i}]' for i in range(12)] + [f'cfg_data[{i}]' for i in range(256)] + ['desc_v'] +
         [f'desc_base[{i}]' for i in range(12)] + [f'desc_limit[{i}]' for i in range(13)] + [f'desc_loops[{i}]' for i in range(16)] +
         ['launch_v', 'cp_configured', 'cp_fault', 'cp_active', 'mv_src', 'mv_done', 'mv_fault', 'quiet', 'busy'])
    for n, v in zip(e, grid(100.0, 260.0, len(e), [pins['clk'][1]])): pins[n] = ('E', v)
    lines = ['# H-HARDEN dbk_cp ring: exact pin plan (tools/hbm_v15_harden/make_dbk_cp_parent.py); ODB readback mandatory.',
             'source /src/physical/common_flow/assigned_pin_exact.tcl']
    for n, (f, v) in sorted(pins.items()):
        lines.append(f'ot_assigned_pin_exact {{{n}}} {"M5" if f in "NS" else "M4"} {f} {v:.6f}')
    (OUT / 'assigned_pins.tcl').write_text('\n'.join(lines) + '\n')
    faces = {}
    for n, (f, v) in pins.items(): faces.setdefault(re.sub(r'\[\d+\]$', '', n), set()).add(f)
    face_map = {'W': [], 'N': [], 'E': [], 'S': [], 'ANY': []}
    for base, fs in faces.items():
        (face_map['ANY'] if len(fs) > 1 else face_map[next(iter(fs))]).append(base)
    old = json.loads((ROOT / 'physical/ref_tile/hv15_dbk_cl/spec.json').read_text())
    children = [dict(view=BANK, count=1, inst=f'u_dbk.L[{b}].u_bank', at=[bx[b], by[b]], orient='R0') for b in range(8)]
    children.append(dict(view=CTLV, count=1, inst='u_dbk.u_control', at=list(CTRL), orient='R0'))
    spec = dict(old)
    spec.update(name=NAME, top='ot_hgi_dma_back_static_vp4_banks_cp',
                sources=['rtl/hbm_accel/generic/peers/static/ot_hgi_dma_back_static_vp4_banks_cp.sv',
                         'rtl/hbm_accel/host_static_20261015/ot_static_cmd_target.sv'] + old['sources'],
                pins={k: v for k, v in face_map.items() if v}, outline=dict(w=W, h=H, exact=True),
                children=children, macros=[dict(view=SR, count=2, at=list(SRAMS[0])), ] if False else
                [dict(view=SR, count=1, inst='u_cp.g_tab.g_w[0].u_tab', at=list(SRAMS[0])),
                 dict(view=SR, count=1, inst='u_cp.g_tab.g_w[1].u_tab', at=list(SRAMS[1]))],
                io_tcl=f'results/arch/hbm_die_v15/dbk_cp_ring_1016/assigned_pins.tcl',
                pin_regs=dict(enable=False, reason=('Banks/controller are hard children owning their registered endpoints; the folded '
                    'collar registers every input in a pin flop and drives every output from a flop (ot_static_cmd_target pin rule).')),
                slot_change_request=('hb_dbk_<q> successor: master ot_hgi_dma_back_static_vp4_banks_cp (collar folded, H-DIE option A), '
                    'outline 511.92x360.72 -> 645.84x360.72, F20 host bus + tgt strap + cp status on E, per-bank clock entries on '
                    'the nearest face, rr/wd regrouped by bank row/column. Requires a new die slot grant.'))
    spec.pop('pin_ranges', None); spec.pop('contract', None)
    why = (__doc__.split('\n\n', 1)[1]).replace('\n', ' ')
    spec['reroute_reason'] = dict(kind='slot_change', source='results/rtl/hbm_harden_0253/parent_terminal.json', why=why)
    spec['structural_change'] = why
    j = dict(old['job']); j.update(owner='Claude:H-HARDEN-0600', branch='claude/hharden-dbk-ring-0600', tag='ring1',
        record_to=f'results/rtl/ref_tile/{NAME}', purpose=why, reroute_reason=spec['reroute_reason'])
    j['extra_paths'] = sorted(set(j['extra_paths'] + ['rtl/hbm_accel/host_static_20261015', 'results/arch/hbm_die_v15/dbk_cp_ring_1016',
                                                       'physical/common_flow/assigned_pin_exact.tcl']))
    j['benches'] = list(j['benches']) + [dict(name='cp_fold', cmd='bash tools/hbm_v15_harden/bench_dma_vp4_banks_cp.sh {RUN}/bench/cp',
        expect='pass', threads=1, peak_ram_gb=4, needs=['iverilog'], pass_regex='DMA_CP_FOLD_GATE PASS')]
    spec['job'] = j
    d = ROOT / 'physical/ref_tile' / NAME; d.mkdir(parents=True, exist_ok=True)
    (d / 'spec.json').write_text(json.dumps(spec, indent=1) + '\n')
    print(NAME, len(pins), 'pins', {f: sum(1 for v in pins.values() if v[0] == f) for f in 'NSEW'}, 'clk entries', clkpt)

if __name__ == '__main__':
    main()
