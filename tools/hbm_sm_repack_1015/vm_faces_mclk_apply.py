#!/usr/bin/env python3
"""H-SM faces-mclk 1016: direct SRAM clock entries clk_macro0..2 for VM q0/q2 faces tiles.
usage: mclk_apply.py ROOT q0|q2 rtl            -- source/bench edits (shared by all variants)
       mclk_apply.py ROOT q0|q2 kit A          -- 270x270, original macro stack, abutment gap blocked
       mclk_apply.py ROOT q0|q2 kit B          -- 270x313.2, macro channels 20.136 um
       mclk_apply.py ROOT q0|q2 kit D          -- 270x313.2, u_b/u_c channel 28.776 um (q2 B/C GRT overflow 131 there), a/b 20.136,
                                                  margins 24.19 / 24.30, + balanced CTS sink clustering (C recipe)
"""
import json, math, re, sys, hashlib
from pathlib import Path
ROOT = Path(sys.argv[1]).resolve(); q = sys.argv[2]; what = sys.argv[3]
sys.path.insert(0, str(ROOT / 'tools/ref_tile'))
D = ROOT / f'rtl/hbm_accel/generic/vm/static/faces_{q}'
MC = ['clk_macro0', 'clk_macro1', 'clk_macro2']


def sub1(text, old, new, path):
    if text.count(old) != 1:
        raise SystemExit(f'{path}: expected exactly one {old!r}, found {text.count(old)}')
    return text.replace(old, new)


def rtl():
    p = D / f'ot_vms_bank_{q}_faces_body.sv'; t = p.read_text()
    t = sub1(t, '    input wire clk_n, clk_s, clk_e, clk_w,\n',
             '    input wire clk_n, clk_s, clk_e, clk_w,\n'
             '    input wire clk_macro0, clk_macro1, clk_macro2, // direct SRAM clock entries: each port -> one macro clock pin\n', p)
    for m, c in zip('abc', MC):
        t = sub1(t, f'ot_sram_1r1w_1024x256_m2_r2c2 u_{m} (.clk(clk),', f'ot_sram_1r1w_1024x256_m2_r2c2 u_{m} (.clk({c}),', p)
    p.write_text(t)
    p = D / f'ot_vms_bank_{q}_faces_core.sv'; t = p.read_text()
    t = sub1(t, 'input wire clk, clk_n, clk_s, clk_e, clk_w,', 'input wire clk, clk_n, clk_s, clk_e, clk_w, clk_macro0, clk_macro1, clk_macro2,', p)
    t = sub1(t, '.clk_w(clk_w),', '.clk_w(clk_w), .clk_macro0(clk_macro0), .clk_macro1(clk_macro1), .clk_macro2(clk_macro2),', p)
    p.write_text(t)
    p = D / f'hfd_vms_bank_native_{q}_faces.sv'; t = p.read_text()
    t = sub1(t, 'clk_w, rst_n,', 'clk_w, clk_macro0, clk_macro1, clk_macro2, rst_n,', p)
    t = sub1(t, 'input clk, clk_n, clk_s, clk_e, clk_w;', 'input clk, clk_n, clk_s, clk_e, clk_w, clk_macro0, clk_macro1, clk_macro2;', p)
    t = sub1(t, '.clk_w(clk_w),', '.clk_w(clk_w), .clk_macro0(clk_macro0), .clk_macro1(clk_macro1), .clk_macro2(clk_macro2),', p)
    p.write_text(t)
    p = D / f'tb_hbm_vm_{q}_faces.sv'; t = p.read_text()
    t = sub1(t, ".clk_w(FACE_DROP==4?1'b0:clk),",
             ".clk_w(FACE_DROP==4?1'b0:clk),.clk_macro0(FACE_DROP==5?1'b0:clk),"
             ".clk_macro1(FACE_DROP==6?1'b0:clk),.clk_macro2(FACE_DROP==7?1'b0:clk),", p)
    p.write_text(t)
    p = D / 'run.sh'; Q = q.upper()
    p.write_text(f"""#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../../../../../.."
D=rtl/hbm_accel/generic/vm/static/faces_{q}
O=${{1:?output dir required}}
mkdir -p "$O"
src=("$D"/*.sv rtl/hbm_accel/generic/vm/static/ot_vms_ce_counter_pipe.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v)
# OT_POS_DROP=<n> is the fail-mutant hook: the positive case runs with clock entry n held low (5..7 = clk_macro0..2).
for case in ${{OT_CASES:-positive latency response clock_n clock_s clock_e clock_w clock_m0 clock_m1 clock_m2}};do
 lat=1;mut=0;drop=0
 case $case in positive)drop=${{OT_POS_DROP:-0}};;latency)lat=0;;response)mut=1;;clock_n)drop=1;;clock_s)drop=2;;clock_e)drop=3;;clock_w)drop=4;;clock_m0)drop=5;;clock_m1)drop=6;;clock_m2)drop=7;;esac
 iverilog -g2012 -s tb_hbm_vm_{q}_faces -Ptb_hbm_vm_{q}_faces.EXPECT_INPUT_LAT=$lat -Ptb_hbm_vm_{q}_faces.MUT=$mut -Ptb_hbm_vm_{q}_faces.FACE_DROP=$drop -o "$O/$case.vvp" "${{src[@]}}" > "$O/$case.build.log" 2>&1
 rc=0;vvp "$O/$case.vvp" > "$O/$case.log" 2>&1||rc=$?
 echo "$case drop=$drop rc=$rc $(head -1 "$O/$case.log")"
 if [[ $case = positive ]];then
  if [[ $rc != 0 ]] || ! grep -q 'VM_NATIVE_ABI PASS' "$O/$case.log";then echo "{Q}_FACE_CLOCKS BENCH FAIL: positive rejected (drop=$drop)";exit 1;fi
 else
  if [[ $rc = 0 ]] || ! grep -q FATAL "$O/$case.log";then echo "{Q}_FACE_CLOCKS BENCH FAIL: negative $case accepted";exit 1;fi
 fi
done
echo "{Q}_FACE_CLOCKS BENCH PASS: cases=${{OT_CASES:-all10}} actual 8 banks/24 SRAM; return7/write4; latency, response, four face-clock and three direct SRAM clk_macro drops rejected"
""")


def kit(variant):
    from spread_face_pins import port_widths
    base = ROOT / f'physical/ref_tile/vm_native_{q}_faces'
    s = json.loads((base / 'spec.json').read_text())
    H = 270.0 if variant == 'A' else 313.2
    name = {'A': f'vm_native_{q}_faces', 'B': f'vm_native_{q}_faces_g313', 'D': f'vm_native_{q}_faces_g313d'}[variant]
    s['name'] = name
    roots = ['clk', 'clk_n', 'clk_s', 'clk_e', 'clk_w']
    s['clock'] = 'hybrid_entries'
    s['clock_ports'] = roots + MC
    s['clock_cts_roots'] = roots
    if variant == 'A':
        at = [[47.52, 29.232], [47.52, 99.744], [47.52, 170.256]]
    elif variant == 'B':  # 20.136 um channels (pitch 90.624 = 1888 x .048), margins 30.672 / 30.792
        at = [[47.52, 30.672], [47.52, 121.296], [47.52, 211.92]]
    else:  # D: u_a/u_b down 4.32, u_c up 4.32 (90 x .048): channel b/c 28.776 where B/C overflowed, a/b 20.136
        at = [[47.52, 26.352], [47.52, 116.976], [47.52, 216.24]]
    s['macros'] = [{'view': 'physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2', 'count': 1,
                    'inst': f'*bank.u_{m}', 'at': a, 'at_exact': True,
                    'clock_entry': {'port': c, 'pin': 'clk', 'reference': 'raw_liberty_clock_pin'}}
                   for m, c, a in zip('abc', MC, at)]
    s['outline'] = {'w': 270.0, 'h': H, 'exact': True}
    for i, c in enumerate(MC):
        s['clock_entry_domains'][f'macro{i}'] = {'ratio': [1, 1], 'ports': [c], 'inputs': [], 'outputs': []}
    # pins: SRAM clk pin is on the macro W edge at y + 0.780 (LEF RECT 0 .768 .024 .792) -> W face, same y, M4 track
    clocks = {'clk': ('N', 134.988), 'clk_n': ('N', 137.964), 'clk_s': ('S', 134.988),
              'clk_e': ('E', 134.988), 'clk_w': ('W', 134.988)}
    for c, a in zip(MC, at):
        y = round(a[1] + 0.78, 3); k = round((y - .012) / .048); assert abs(.012 + .048 * k - y) < 1e-6
        clocks[c] = ('W', y)
    if variant in 'BD':  # face clocks stay at the face centre of the grown W/E faces
        clocks['clk_e'] = ('E', 156.588); clocks['clk_w'] = ('W', 156.588)
    s['pins']['W'] = [p for p in s['pins']['W'] if p not in MC] + MC
    widths = port_widths(s, ROOT); pins = {}; metrics = []
    for face, ps in s['pins'].items():
        L = 270.0 if face in 'NS' else H
        data = []
        for p in ps:
            if p in clocks: continue
            n, vec = widths[p]; data.extend([f'{p}[{i}]' if vec else p for i in range(n)])
        cs = [x for f, x in clocks.values() if f == face]
        tracks = [round(.012 + .048 * k, 3) for k in range(math.ceil((5.4 - .012) / .048), math.floor((L - 5.4 - .012) / .048) + 1)
                  if all(abs(.012 + .048 * k - c) >= 1.08 - 1e-8 for c in cs)]
        usable = L - 10.8 - 2.16 * len(cs); cut = len(data) * .096 / usable; assert cut <= .60
        sel = [tracks[round(i * (len(tracks) - 1) / (len(data) - 1))] for i in range(len(data))]
        assert len(set(sel)) == len(data) and min(b - a for a, b in zip(sel, sel[1:])) >= .096 - 1e-7
        for p, x in zip(data, sel): pins[p] = {'face': face, 'layer': 'M4' if face in 'WE' else 'M5', 'position_um': x, 'clock': False}
        metrics.append({'face': face, 'bits': len(data), 'usable_um': round(usable, 3), 'cut': round(cut, 4)})
    for p, (f, x) in clocks.items(): pins[p] = {'face': f, 'layer': 'M4' if f in 'WE' else 'M5', 'position_um': x, 'clock': True}
    assert len(pins) == sum(x[0] for x in widths.values())
    # pin_ranges from the actual plan (lo/hi centre +-0.048 per port)
    rng = {}
    for p, v in pins.items():
        b = p.split('[')[0]; lo, hi = rng.get(b, (1e9, -1e9)); rng[b] = (min(lo, v['position_um']), max(hi, v['position_um']))
    s['pin_ranges'] = {b: [round(lo - .048, 3), round(hi + .048, 3)] for b, (lo, hi) in rng.items()}
    tag = {'A': '', 'B': '_g313', 'D': '_g313d'}[variant]
    pf = ROOT / f'physical/ref_tile_specs/smh/vm_{q}_faces{tag}_pins.tcl'
    lines = [f'# H-SM faces-mclk 1016 variant {variant}: actual-layer phase .012; 5 CTS roots + 3 direct SRAM clock entries (W face at each SRAM clk pin y).',
             'source /src/physical/common_flow/assigned_pin_exact.tcl', 'set vm_expected {']
    lines += [' {' + p + ' ' + v['face'] + ' ' + v['layer'] + f" {v['position_um']:.3f}" + '}' for p, v in pins.items()]
    lines += ['}', 'foreach vm_item $vm_expected {lassign $vm_item vm_p vm_f vm_l vm_x;ot_assigned_pin_exact $vm_p $vm_l $vm_f $vm_x}']
    pf.write_text('\n'.join(lines) + '\n')
    s['io_tcl'] = str(pf.relative_to(ROOT))
    src_iop = ROOT / f'physical/ref_tile_specs/smh/vm_{q}_faces_post_iop.tcl'
    t = src_iop.read_text()
    iop = ROOT / f'physical/ref_tile_specs/smh/vm_{q}_faces{tag}_post_iop.tcl'
    t = t.replace(f'source /src/physical/ref_tile_specs/smh/vm_{q}_faces_pins.tcl', f'source /src/{s["io_tcl"]}')
    if variant == 'A' and 'macro_channel_block.tcl' not in t:
        t = sub1(t, 'source /src/tools/fp_margin_lint.tcl\n',
                 '# abutted SRAM stack (pitch = height + .024 on the M4 lattice): block the .024 um slivers (textbook util_channel)\n'
                 'set ot_sliver_um 20.0\nsource /src/physical/common_flow/macro_channel_block.tcl\n'
                 'source /src/tools/fp_margin_lint.tcl\n', iop)
    iop.write_text(t)
    s['orfs_vars']['POST_IO_PLACEMENT_TCL'] = str(iop.relative_to(ROOT))
    ep = s['job'].setdefault('extra_paths', [])
    for x in ['physical/common_flow/macro_channel_block.tcl', 'physical/common_flow/clock_entries.tcl']:
        if x not in ep: ep.append(x)
    s['job']['tag'] = f'mclk{variant}'
    s['job']['owner'] = 'Claude H-SM faces-mclk helper 0945'
    s['job']['branch'] = 'claude/hsm-faces-mclk-1016'
    s['job']['views_to'] = f'physical/ref_tile/{name}/views'
    s['job']['record_to'] = f'results/rtl/ref_tile/{name}'
    run = f'rtl/hbm_accel/generic/vm/static/faces_{q}/run.sh'; Q = q.upper()
    s['job']['benches'] = [
        {'name': 'exact_real_memory', 'cmd': f'bash {run} {{RUN}}/bench/{q}_faces', 'expect': 'pass', 'threads': 1,
         'peak_ram_gb': 4, 'pass_regex': f'{Q}_FACE_CLOCKS BENCH PASS'},
        {'name': 'mutant_drop_clk_macro1', 'cmd': f'OT_CASES=positive OT_POS_DROP=6 bash {run} {{RUN}}/bench/{q}_mut_m1',
         'expect': 'fail', 'threads': 1, 'peak_ram_gb': 4, 'fail_regex': f'{Q}_FACE_CLOCKS BENCH FAIL'},
    ]
    if variant == 'D':  # C recipe: balanced CTS sink clustering
        s['route']['cts_sink'] = {'size': 16, 'diameter_um': 30, 'extra': '-balance_levels'}
    s['structural_change'] = (s.get('structural_change', '') + f' | faces-mclk {variant}: the 3 SRAM clock pins move off core clk onto '
                              'direct entries clk_macro0..2 (W face at each SRAM clk pin; hybrid_entries; CTS roots clk/clk_n/clk_s/clk_e/clk_w '
                              'reach standard cells only). ' + ('Abutted stack .024 um slivers hard-blocked (macro_channel_block).' if variant == 'A'
                              else 'Outline 270x313.2 (+16%): 20.136 um macro channels.' if variant == 'B' else
                              'Outline 270x313.2: u_b/u_c channel 28.776 um (B/C GRT-0116 overflow 131, all in that channel, E/W mouths), '
                              'u_a/u_b 20.136, N/S margins 24.2/24.3; balanced CTS sink clustering 16/30 um/-balance_levels.'))
    k = ROOT / f'physical/ref_tile/{name}'; k.mkdir(exist_ok=True)
    (k / 'spec.json').write_text(json.dumps(s, indent=1) + '\n')
    print(json.dumps({'kit': name, 'H': H, 'clocks': {c: clocks[c] for c in MC + ['clk_w', 'clk_e']}, 'windows': metrics, 'pins': len(pins)}, indent=1))


rtl() if what == 'rtl' else kit(sys.argv[4])
