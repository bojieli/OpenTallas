#!/usr/bin/env python3
"""H-HARDEN 2026-10-15: ref_tile kit spec for the hb_dbk wires-only cluster ot_hgi_dma_back_static_vp4_banks (ONE
master x4 stacks, stk[1:0] strap pin) to the H-DIE grant v7 slot (tools/hbm_die_v15/grants_v7_1925.py): 488.16 x 360.72,
children on the 43.2 lattice: 8 geo1 landing banks (closed + native PASS) + the stk-strap controller; every child gets
its own clock entry (clk -> controller, clk_bank[b] -> bank b); parent pins at the granted faces.
    make_dbk_parent.py CONTROLLER_VIEW [--name N] [--orient-col ...]"""
import argparse, json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
ap = argparse.ArgumentParser()
ap.add_argument('--ctl-view', default='physical/ref_tile/hv15_dbk_vp4_ctl/views/ot_hgi_dma_back_static_vp4_controller')
ap.add_argument('--name', default='hv15_dbk_cl')
ap.add_argument('--tag', default='c1')
ap.add_argument('--contract', default='results/arch/hier_contract_1015/hbm_v15.json')
ap.add_argument('--bank-orient', default='R0,R0,R0,R0,R0,R0,R0,R0')
a = ap.parse_args()
G = json.loads((ROOT / 'results/arch/hier_contract_1015/hbm_v15.json').read_text())
slot = next(s for s in G['slots'] if s['name'] == 'hb_dbk_NE')
base = lambda n: re.sub(r'\[.*$', '', n)
faces = {}
for p in slot['pins']:
    faces.setdefault(p['face'], []).append(base(p['name']))
faces['E'].insert(faces['E'].index('rst_n') + 1, 'stk')     # strap pin (H-HARDEN request to H-DIE: E face next to rst_n)
BANK = 'physical/ref_tile/hv15_dbk_bank/views/ot_hgi_dma_back_landing_bank'
# ref_tile child rules: >= 20 um from every core edge and between children (the v7 grant homes at x=0 / 0-um gaps fail
# macro_edge/macro_outside) -> 3 x 3 grid, columns 160.4 + 1.2 apart, rows 108 apart; outline W 511.92 (v7 488.16 + 23.76)
XS, YS = [23.76, 185.76, 347.76], [23.76, 131.76, 239.76]
at = [[XS[b % 3], YS[b // 3]] for b in range(8)]
CTL_AT = [XS[2], YS[2]]
orient = a.bank_orient.split(',')
children = [dict(view=BANK, count=1, inst=f'L[{b}].u_bank', at=at[b], orient=orient[b]) for b in range(8)]
children.append(dict(view=a.ctl_view, count=1, inst='u_control', at=CTL_AT))
SR = 'physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2'
B = lambda n, c, e, **k: dict(name=n, cmd=c, expect=e, threads=1, peak_ram_gb=8, needs=['iverilog'], **k)
spec = dict(
    name=a.name, top='ot_hgi_dma_back_static_vp4_banks', kind='cluster',
    sources=['rtl/hbm_accel/generic/peers/static/ot_hgi_dma_back_static_vp4_banks.sv',
             'rtl/hbm_accel/generic/peers/static/ot_hgi_dma_back_static_vp_banks.sv', SR + '/ot_sram_1r1w_128x256_m1_r2c2_bb.v'],
    clock='entries', clock_port='clk', clock_ports=['clk'] + [f'clk_bank[{b}]' for b in range(8)], reset_ports=['rst_n'],
    pins=faces, outline=dict(w=slot['outline']['w'], h=slot['outline']['h'], exact=True),
    pg_layer='M7', signal_max_layer='M6', child_lattice_um=2.16,
    children=children, recipe=2, hard_define='OT_DBK_HARD', defines=['OT_DBK_HARD'], contract=dict(file=a.contract, slot='hb_dbk_NE'),
    route=dict(pd=0.5, period_ps=833.333, threads=8, peak_ram_gb=32, hold_margin_ns=0.03, macro_halo_um=5.4),
    params={}, macros=[], inter=[],
    job=dict(owner='Claude:H-HARDEN', branch='claude/hnl-harden-2210', tag=a.tag, record_to=f'results/rtl/ref_tile/{a.name}',
             purpose=('hb_dbk wires-only cluster ot_hgi_dma_back_static_vp4_banks, ONE master for the four stacks (stk[1:0] '
                      'strap pin): 8 closed native-PASS geo1 landing banks + the stk-strap DMA controller at the H-DIE v7 '
                      'grant homes (488.16 x 360.72), nine clock entries (clk, clk_bank[7:0]), parent = wires only.'),
             extra_paths=['tools/hbm_v15_harden', 'rtl/hbm_accel/generic/peers/static', 'rtl/hbm_accel/generic/vm/static', SR,
                          'physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2',
                          'physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2', BANK, a.ctl_view,
                          a.contract],
             benches=[B('exact', 'bash tools/hbm_v15_harden/bench_dma_vp4_banks.sh {RUN}/bench/exact 0', 'pass', pass_regex='DMA_VP4_BANKS_BENCH_PASS'),
                      B('strap_mutant', 'bash tools/hbm_v15_harden/bench_dma_vp4_banks.sh {RUN}/bench/mut4 4', 'fail'),
                      B('landing_address_mutant', 'bash tools/hbm_v15_harden/bench_dma_vp4_banks.sh {RUN}/bench/mut3 3', 'fail')]),
    io_flop_at_pins=dict(cols=4, allow_none=True))
out = ROOT / f'tools/ref_tile/specs_hnl_harden/{a.name}.json'
out.write_text(json.dumps(spec, indent=1) + '\n')
print(out, {f: len(v) for f, v in faces.items()})
