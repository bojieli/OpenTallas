#!/usr/bin/env python3
"""Generate the die-granted, wires-only DMA parent after the new controller view exists.

The 511.92 x 360.72 candidate uses eight real geo1 bank views and the new
registered-stk controller. Geometry is taken from the die contract, including
assigned pin ranges. The old STK0 controller cannot stand in for the new view.
An emitted kit still requires source/view binding, native child audits, actual
PG connectivity/spacing, fill and trial GRT before a parent route.
"""
import argparse, json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
ap = argparse.ArgumentParser()
ap.add_argument('--ctl-view', default='physical/ref_tile/hv15_dbk_vp4_ctl/views/ot_hgi_dma_back_static_vp4_controller')
ap.add_argument('--name', default='hv15_dbk_cl')
ap.add_argument('--tag', default='c1')
ap.add_argument('--contract', default='results/arch/hier_contract_1015/hbm_v15.json')
a = ap.parse_args()
G = json.loads((ROOT / a.contract).read_text())
slot = next(s for s in G['slots'] if s['name'] == 'hb_dbk_NE')
base = lambda n: re.sub(r'\[.*$', '', n)
faces = {}
for p in slot['pins']:
    faces.setdefault(p['face'], []).append(base(p['name']))
assert sum(v.count('stk') for v in faces.values()) == 1, 'die grant must assign stk exactly once'
pin_ranges = {base(p['name']): p['span_um'] for p in slot['pins']}
BANK = 'physical/ref_tile/hv15_dbk_bank/views/ot_hgi_dma_back_landing_bank'
ctl_lef = ROOT / a.ctl_view / 'ot_hgi_dma_back_static_vp4_controller.lef'
if not ctl_lef.is_file():
    ap.error('new registered-stk controller view is absent; collect its actual route first')
ctl_pins = {line.split()[1].replace('\\', '') for line in ctl_lef.read_text().splitlines()
            if line.strip().startswith('PIN ')}
if not {'stk[0]', 'stk[1]'} <= ctl_pins:
    ap.error('controller LEF lacks registered stk[1:0]; old STK0 view is not a valid substitute')
homes = {c['inst']: c for c in slot['children']}
assert set(homes) == {'u_control'} | {f'L[{b}].u_bank' for b in range(8)}
children = [dict(view=(a.ctl_view if name == 'u_control' else BANK), count=1,
                 inst=name, at=home['at'], orient=home.get('orient', 'R0'))
            for name, home in homes.items()]
SR = 'physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2'
B = lambda n, c, e, **k: dict(name=n, cmd=c, expect=e, threads=1, peak_ram_gb=4, needs=['iverilog'], **k)
spec = dict(
    name=a.name, top='ot_hgi_dma_back_static_vp4_banks', kind='cluster',
    sources=['rtl/hbm_accel/generic/peers/static/ot_hgi_dma_back_static_vp4_banks.sv',
             'rtl/hbm_accel/generic/peers/static/ot_hgi_dma_back_static_vp_banks.sv', SR + '/ot_sram_1r1w_128x256_m1_r2c2_bb.v'],
    clock='entries', clock_port='clk', clock_ports=['clk'] + [f'clk_bank[{b}]' for b in range(8)], reset_ports=['rst_n'],
    pins=faces, pin_ranges=pin_ranges, outline=dict(w=slot['outline']['w'], h=slot['outline']['h'], exact=True),
    pg_layer='M7', signal_max_layer='M6', child_lattice_um=2.16,
    children=children, recipe=3, hard_define='OT_DBK_HARD', defines=['OT_DBK_HARD'], contract=dict(file=a.contract, slot='hb_dbk_NE'),
    pin_regs=dict(enable=False, reason='Parent is wires only; actual hard children own the registered endpoints and nine independently compensated clock entries. Parent wires remain part of the die hop budget.'),
    route=dict(pd=0.5, period_ps=833.333, threads=8, peak_ram_gb=8, hold_margin_ns=0.03, macro_halo_um=5.4),
    params={}, macros=[], inter=[],
    job=dict(owner='Claude:H-HARDEN', branch='claude/hnl-harden-2210', tag=a.tag, record_to=f'results/rtl/ref_tile/{a.name}',
             purpose=('hb_dbk wires-only cluster ot_hgi_dma_back_static_vp4_banks, ONE master for the four stacks (stk[1:0] '
                      'strap pin): 8 closed native-PASS geo1 landing banks + the stk-strap DMA controller at the H-DIE v7 '
                      'grant homes (511.92 x 360.72), nine clock entries (clk, clk_bank[7:0]), parent = wires only; '
                      'actual new controller view and all parent PG/hop/native checks required.'),
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
