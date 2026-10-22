#!/usr/bin/env python3
"""Write the S81 HEAD glue R3 kit specs (MAIN s81hd_glue_r3m 2160x3888 = H10 MAIN reserve, FALLBACK s81hd_glue_r3f
2592x4320 = H10 FB reserve) from the R2 kit spec (physical/ref_tile/s81hd_glue_m/spec.json), then run ref_tile gen."""
import copy, json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/s81_head'))
import glue_rg_gen as G   # noqa: E402

T = 'rtl/dsrom_sys/s81_head'
SRC = ['rtl/lib/ot_rst_relay_tree3.sv',
       'physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2_bb.v',
       'rtl/dsrom_sys/mtp/ot_dsrom_mtp_link_pair.sv', f'{T}/ot_s81hd_util.sv', f'{T}/ot_s81hd_ctl.sv',
       f'{T}/ot_s81hd_glue_rg.sv', f'{T}/ot_s81hd_ctl_glue_r3.sv']
KEEP = ['ot_s81hd_kf', 'ot_s81hd_hreg32', 'ot_s81hd_cmp', 'ot_s81hd_pick', 'ot_s81hd_rs32', 'ot_s81hd_rs8', 'ot_s81hd_rv1',
        'ot_s81hd_rr1', 'ot_s81hd_g_mtx', 'ot_s81hd_g_dtx']
BENCH = 'bash rtl/dsrom_sys/s81_head/test/run_hd_glue_r3_bench.sh {RUN}/ctl sim'


def spec(v):
    g = G.VAR[v]; W, H = g['W'], g['H']
    s = json.loads((ROOT / 'physical/ref_tile/s81hd_glue_m/spec.json').read_text())
    s = copy.deepcopy(s)
    s['name'] = g['name']; s['sources'] = SRC; s['outline'] = {'w': W, 'h': H}
    x0 = round(0.4 * W / 43.2) * 43.2; y0 = round((H / 2 - 259.2) / 43.2) * 43.2
    for i, m in enumerate(s['macros']):
        m['at'] = [round(x0, 4), round(y0 + 129.6 * i, 4)]
    pins, dens, base = G.gen_pins(v)
    faces = {'N': [], 'S': [], 'W': [], 'E': [], 'ANY': []}
    for b, fs in sorted(base.items()):
        faces['ANY' if len(fs) > 1 else next(iter(fs))].append(b)
    s['pins'] = {f: n for f, n in faces.items() if n}
    s.pop('pin_ranges', None)
    s['io_tcl'] = f'physical/ref_tile/{g["name"]}/io_pins.tcl'
    s['route']['synth_keep_modules'] = KEEP
    s['route']['peak_ram_gb'] = 96
    if v == 'm':
        s.pop('pre_cts_extra', None); s['orfs_vars'] = {}
        s['route']['cts_sink'] = {'size': 24, 'diameter_um': 30, 'extra': '-distance_between_buffers 15 -balance_levels'}
    s['structural_change'] = (
        'R3 regional glue (STW-S81c-HEAD-GLUE 10-22) after s81hd_glue_m2/f2 FAIL (wire_reach: synthesis merged identical-D '
        'frame-header flops of different faces, core 856/999 um from pins; one-root spread 89.5/98.5). FROZEN interface '
        '(exact ot_s81hd_ctl_glue ports, ck, rst_n). Function by zone at its pins (WL lep / C core / N seq+spine / S spine / '
        'WH0 WH1 host / per-lane kept TX stages); every zone-to-zone signal on kept non-mergeable relay stages, hops <= 380 um, '
        'equal ages per bus group (relay_ledger.json); exact per-bit io_tcl at the H10 die link positions (draft 0/1 W as '
        'the die routes them), proven seq peer windows; equal-depth reset forest. Bench PASS + 3 mutants caught; measured '
        '+12 cyc stream start, +52 cyc token per position (8,870-cyc model, 20,555 slot gap).')
    s['fill_reason'] = {'pin_bound': (
        f'Pin-bound outline = the H10 die ctl reserve {W:g} x {H:g} (the die plan sized it so every face carries only the '
        f'links that go that way: E {dens["E"]["pins"]} pins = {dens["E"]["per_um_face"]}/um, W {dens["W"]["per_um_face"]}/um). '
        'Std cells (~20k um2 incl. ~48k relay flops) + 4 SRAM leave fill far below 40%: the reserve, not the area, sets the '
        'outline; a smaller outline re-creates the H4 star-hub funnel.')}
    s['job'].update(owner='Claude:STW-S81c-HEAD-GLUE', branch='claude/s81hd-glue-r3-1021', tag=g['name'],
                    purpose='S81.HEAD ctl glue R3 (frozen interface, relay-pipelined zones) to closure (TT setup / FF hold / DRC 0).',
                    views_to=f'physical/ref_tile/{g["name"]}/views', record_to=f'results/rtl/ref_tile/{g["name"]}')
    s['job']['extra_paths'] = ['rtl/lib', 'rtl/common', 'rtl/dsrom_sys/mtp', 'rtl/dsrom_sys/s81_head',
                               'physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2', 'tools/s81_head',
                               'results/arch/s81_head_1021/glue_r3', 'results/arch/s81_head_1021/peer_pin_plan_m.json',
                               'results/arch/s81_head_1021/peer_pin_plan_f.json', 'results/rtl/s81_head_glue_r3_1022']
    s['job']['benches'] = [
        {'name': 'hd_glue_r3_base', 'cmd': BENCH + ' base', 'expect': 'pass', 'threads': 8, 'peak_ram_gb': 8, 'needs': ['verilator'],
         'pass_regex': '^PASS hd_ctl streams 2 tokens 2 slices/stream 8248', 'pass_witness': 'results/rtl/s81_head_glue_r3_1022/base.log'},
        {'name': 'hd_glue_r3_mut_slice', 'cmd': BENCH + ' SLICE', 'expect': 'fail', 'threads': 8, 'peak_ram_gb': 8, 'needs': ['verilator'],
         'pass_regex': '^PASS hd_ctl streams 2 tokens 2 slices/stream 8248', 'fail_regex': '^FAIL hd_ctl xa slice mismatch',
         'fail_witness': 'results/rtl/s81_head_glue_r3_1022/SLICE.log'},
        {'name': 'hd_glue_r3_mut_tie', 'cmd': BENCH + ' TIE', 'expect': 'fail', 'threads': 8, 'peak_ram_gb': 8, 'needs': ['verilator'],
         'pass_regex': '^PASS hd_ctl streams 2 tokens 2 slices/stream 8248', 'fail_regex': '^FAIL hd_ctl local best',
         'fail_witness': 'results/rtl/s81_head_glue_r3_1022/TIE.log'},
        {'name': 'hd_glue_r3_mut_tkf', 'cmd': BENCH + ' TKF', 'expect': 'fail', 'threads': 8, 'peak_ram_gb': 8, 'needs': ['verilator'],
         'pass_regex': '^PASS hd_ctl streams 2 tokens 2 slices/stream 8248', 'fail_regex': '^FAIL hd_ctl token count',
         'fail_witness': 'results/rtl/s81_head_glue_r3_1022/TKF.log'}]
    return s


for v in G.VAR:
    s = spec(v)
    p = ROOT / f'physical/ref_tile/{G.VAR[v]["name"]}/spec.json'
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(s, indent=1) + '\n')
    r = subprocess.run([sys.executable, str(ROOT / 'tools/ref_tile/ref_tile.py'), 'gen', str(p)], cwd=ROOT, capture_output=True, text=True)
    print(v, r.returncode, r.stdout[-1500:], r.stderr[-2500:])
