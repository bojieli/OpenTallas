#!/usr/bin/env python3
"""SFU-PS-FUND 10-17: spec for the r10 one-stripe spine leaf (ot_hgi_sfu_store_stripe_leaf_r10).
Usage: mkspec_r10.py WT   -> WT/physical/ref_tile/hbm_sfu_store_stripe_r10_1017/spec.json
Geometry (um): 4 x ot_sram_1r1w_512x256_m1_r2c2 (96.552 x 69.660; A edge = clk/addr/rd_out/wd_in[136:0] at x=0,
B edge = wd_in[255:137] + ties), 2 rows of a mirrored pair: left MY (A edge faces E), right R0 (A edge faces W), so all
four A edges face ONE centre spine (44.3 um); B edges face 24 um outer bands (no clock sinks: wiring + ties).
Rows abutted N-S (pitch = array height + 0.024, abutted_stack; no pin on the touching faces).  N band 27 um (input
pin flops, chain-out = the same flops), S band 28 um (relay + gated output registers).  Pins: N face = inputs + chain
out, S face = outputs, clk at the S-face spine foot (x = spine centre)."""
import json, sys, copy
from pathlib import Path

WT = Path(sys.argv[1])
RT = WT / 'physical/ref_tile'
tmpl = json.loads((RT / 'hbm_sfu_store_leaf2_r9d_1017/spec.json').read_text())
s = copy.deepcopy(tmpl)
name = 'hbm_sfu_store_stripe_r10_1017'
MW, MH = 96.552, 69.660
W, H = 285.12, 194.4
XL, XR = 23.76, 164.592              # left MY, right R0 (0.432 lattice; >= 20 um from the W / E core edge)
Y0 = 28.08
PITCH = 69.696                       # abutted N-S stack: array height + 0.036 (M4 0.048 track multiple; +0.024 is off-track)
spine = (XR - (XL + MW))
xc = round(XL + MW + spine / 2, 3)   # spine centre
VIEW = 'physical/hbm_accel_macros/ot_sram_1r1w_512x256_m1_r2c2'
s['name'] = name
s['top'] = 'ot_hgi_sfu_store_stripe_leaf_r10'
s['sources'] = ['rtl/hbm_accel/generic/peers/ot_hgi_sfu_store_stripe_leaf_r10.sv',
                VIEW + '/ot_sram_1r1w_512x256_m1_r2c2_bb.v']
s['params'] = {}
s['outline'] = {'w': W, 'h': H, 'exact': True}
s['macros'] = []
for p in range(4):
    row, col = p // 2, p % 2
    s['macros'].append({'view': VIEW, 'count': 1, 'inst': f'*g_page?{p}?.u_program',
                        'at': [XL if col == 0 else XR, round(Y0 + row * PITCH, 3)], 'at_exact': True,
                        'orient': 'MY' if col == 0 else 'R0'})
AW = 11
bits = dict(clk=1, rst_a=1, in_we=1, in_addr=AW, in_data=256, out_addr=AW, out_data=256, in_start_v=1, in_start_base=AW,
            in_legal=1, in_span=AW + 1, in_loops=16, in_loops_one=1, in_cv=1, out_cal=222, out_v=1, out_active=1,
            out_done=1, out_fault=1, out_ord=32, out_hz=2, out_b26=1)


def ranges(order, lo, hi):
    fixed = sum(1.0 for p in order if bits[p] == 1)
    var = [p for p in order if bits[p] > 1]
    tot = sum(bits[p] for p in var)
    room = hi - lo - fixed
    out, x = {}, lo
    for p in order:
        w = 1.0 if bits[p] == 1 else room * bits[p] / tot
        out[p] = [round(x, 3), round(x + w, 3)]
        x += w
    return out


pr = {}
# N face (W -> E): chain out (out_addr, out_data) | control + launch | in_data (chain in).  The data flops sit between
# their in pin (E half) and out pin (W half); control enters at the spine column.
n_out = ['out_addr', 'out_data']
n_ctl = ['in_we', 'in_addr', 'in_start_v', 'in_start_base', 'in_legal', 'in_span', 'in_loops', 'in_loops_one', 'in_cv',
         'rst_a']
n_in = ['in_data']
pr.update(ranges(n_out, 3.0, xc - 12.0))
pr.update(ranges(n_ctl, xc - 12.0, xc + 14.0))
pr.update(ranges(n_in, xc + 14.0, W - 3.0))
# S face (W -> E): out_cal | clk (spine foot) | status
pr.update(ranges(['out_cal'], 3.0, xc - 2.0))
pr['clk'] = [round(xc - 0.5, 3), round(xc + 0.5, 3)]
s_st = ['out_v', 'out_active', 'out_done', 'out_fault', 'out_ord', 'out_hz', 'out_b26']
pr.update(ranges(s_st, xc + 3.0, W - 60.0))
s['pins'] = {'N': n_out + n_ctl + n_in, 'S': ['out_cal', 'clk'] + s_st}
s['pin_ranges'] = pr
s['pin_regs'] = {'enable': False, 'reason': 'the r10 leaf RTL registers every input at the pin (pure flops: rb/we_q/addr_q/'
                 'data_q/start_*_q/cv_q) and every output is a register (out_cal relay+gate, calendar_v/active/done/fault/'
                 'ordinal, out_hz, calendar[26], chain out = addr_q/data_q); a kit flop stage would add an edge to the '
                 'priced r7c schedule (D=4)'}
s['structural_change'] = (
    'r10 (SFU-PS-FUND 10-17, design decision lanes/SFU-PS-FUND.md): ONE stripe per leaf, 11 identical leaves '
    '(replaces r9 leaf2/leaf3 and every stacked-SRAM store). Root cause of r7c4..r9d: 1024x256 macros carry ~416 pins '
    'on each 70 um short edge, so stacks put the register mass, the pins and the clock on one face and the far edge '
    'needs sinks reached round the stack (insertion 408-617, spread 131-261, M4 overflow under the M5 cap). r10 uses '
    'four narrow 512x256 macros as two mirrored pairs (MY | spine | R0): every A edge (read data, address, clock, low '
    'write data) faces ONE centre spine that holds the read path; B edges (high write data + ties) face outer bands '
    'with no clock sinks; inputs + config chain-out on the N face (N band pin flops), outputs on the S face (S band '
    'relay + gated output registers), clk at the S-face spine foot (outputs launch early, inputs capture late). '
    f'Outline {W} x {H} ({W / H:.2f}:1), ~1.7k sinks, cycles identical to r7c (lockstep).')
s['job']['purpose'] = ('SFU programme store r10 one-stripe spine leaf (x11 in ot_hgi_sfu_programme_store_r10). '
                       'CRITICAL (hbm_sfu_programme_store family): coordinator reviews the gate PNG before submit.')
s['job']['owner'] = 'Claude:SFU-PS-FUND'
s['job']['branch'] = 'claude/sfu-ps-fund-1017'
s['job']['tag'] = 'r10'
s['job']['views_to'] = f'physical/ref_tile/{name}/views'
s['job']['record_to'] = f'results/rtl/ref_tile/{name}'
V = ('VERILATOR=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator ')
fl = '"SFU_SPLIT_EQUIV_MISMATCH|SFU_SPLIT_EQUIV FAIL|SFU_SPLIT_FAULT"'
benches = [
 {"name": "lint", "cmd": "mkdir -p {RUN} && verilator --lint-only -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD "
  "-Wno-MULTIDRIVEN -Wno-MODMISSING -DSYNTHESIS --top-module ot_hgi_sfu_programme_store_r10 "
  "rtl/hbm_accel/generic/peers/ot_hgi_sfu_store_stripe_leaf_r10.sv rtl/hbm_accel/generic/peers/ot_hgi_sfu_programme_store_r10.sv "
  + VIEW + "/ot_sram_1r1w_512x256_m1_r2c2_bb.v && echo lint-ok", "expect": "pass", "threads": 1, "peak_ram_gb": 4,
  "needs": ["verilator"]},
 {"name": "store_lockstep_r7c", "cmd": "OUT={RUN}/bench/ls MODE=0 SEED=12345 bash tools/hbm_static/run_sfu_store_r10_lockstep.sh",
  "expect": "pass", "pass_regex": "SFU_STORE_R10_GATE POSITIVE PASS", "threads": 8, "peak_ram_gb": 8, "needs": ["verilator"]},
 {"name": "store_lockstep_mutant_chain", "cmd": "OUT={RUN}/bench/lsc EQ_MUT=chain bash tools/hbm_static/run_sfu_store_r10_lockstep.sh",
  "expect": "pass", "pass_regex": "SFU_STORE_R10_GATE MUTANT chain REJECTED", "threads": 8, "peak_ram_gb": 8, "needs": ["verilator"]},
 {"name": "split_equiv_exact", "cmd": "OUT={RUN}/bench/pos SFU_LG_R=23 STORE10=1 bash tools/hbm_static/run_sfu_split_equiv.sh",
  "expect": "pass", "pass_regex": "SFU_SPLIT_GATE POSITIVE PASS", "min_count_regex": "SFU_SPLIT_EQUIV PASS edges=(\\d+)",
  "threads": 8, "peak_ram_gb": 64, "needs": ["verilator"]},
]
for m in ("flip", "early", "chain"):
    benches.append({"name": f"split_mutant_{m}", "cmd": f"OUT={{RUN}}/bench/{m} SFU_LG_R=23 STORE10=1 EQ_MUT={m} bash "
                    f"tools/hbm_static/run_sfu_split_equiv.sh; cat {{RUN}}/bench/{m}/run.log; exit 1", "expect": "fail",
                    "fail_regex": fl.strip('"'), "threads": 8, "peak_ram_gb": 64, "needs": ["verilator"]})
s['job']['benches'] = benches
s['job']['extra_paths'] = sorted(set(s['job']['extra_paths'] + ['physical/hbm_accel_macros', 'rtl/test/hbm_accel/generic']))
d = RT / name
d.mkdir(exist_ok=True)
(d / 'spec.json').write_text(json.dumps(s, indent=1) + '\n')
print(name, W, H, f'{W / H:.2f}', 'spine', round(spine, 3), 'xc', xc, json.dumps(pr))
