#!/usr/bin/env python3
"""Per-root 3:4 CDC leaf kits for the static VM (claude S81 VM F4 cdc-leaves, 2026-10-15).

One hard leaf per clock root, F2's split pattern (ot_s81_vm_x34_s / _t, and the new ot_s81_vm_x43_t / _s): the
wrapper modules stay bit-identical, the 3:4 related arcs are parent paths (the open A/B arc decision with S-DIE).

Geometry fixes the native-audit capture misses of F2's x34 W542 r2 views (9 / 149 input pins > 190 ps): there the
pin placer grouped each bank bus on its own third of the 345.6 um face, so b0[i] / b1[i] / b2[i] (and the s_d[i]
fan-out to three bank flops) lay up to ~230 um apart.  Here every face is BIT-MAJOR: the three bank bits of word bit i
are adjacent M4 pins (2-track 0.096 um pitch) and the single-bit face (s_d / o_d) sits at the same y on the opposite
face (0.288 um pitch), so input pin -> capture flop -> output pin is a straight ~43 um row for every bit.

Usage: build_cdc_leaf_kits.py [--gen]   (writes pin files + specs; --gen also runs ref_tile.py gen per spec)
"""
import json, math, pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
PINS = ROOT / 'physical/s81_vm_cdc_leaves_1015'
SPECS = ROOT / 'tools/ref_tile/specs_s81vm_cdc_leaves_1015'
W_UM, H_UM, TRK, Y0 = 43.2, 345.6, 0.048, 0.012
OWNER = 'claude:S81 VM F4 cdc-leaves'
BRANCH = 'claude/s81-vm-f4-leaves-1015'
SRC = {'x34': 'rtl/dsrom_sys/s81_ph/vm/ot_s81_vm_x34.sv', 'x43': 'rtl/dsrom_sys/s81_ph/vm/ot_s81_vm_x43.sv'}

# (kind, side, W, ABI category, instances)
LEAVES = [
    ('x34', 's', 514, 'ck_landing_x34_s', 'u_xsel, u_xcol'), ('x34', 't', 514, 'ck_landing_x34_t', 'u_xsel, u_xcol'),
    ('x34', 's', 1026, 'ck_landing_x34_s', 'u_xsw'), ('x34', 't', 1026, 'ck_landing_x34_t', 'u_xsw'),
    ('x34', 's', 560, 'ck_wfc_x34_s', 'u_wfc.u_xi'), ('x34', 't', 560, 'ck_wfc_x34_t', 'u_wfc.u_xi'),
    ('x43', 't', 1026, 'ck_wfc_x43_t', 'u_wfc.u_xo'), ('x43', 's', 1026, 'ck_wfc_x43_s', 'u_wfc.u_xo'),
    ('x43', 't', 512, 'ck_xio_x43_t[0]', 'u_xio.u_xq'), ('x43', 's', 512, 'ck_xio_x43_s[0]', 'u_xio.u_xq'),
    ('x43', 't', 511, 'ck_xio_x43_t[1]', 'u_xio.u_xg'), ('x43', 's', 511, 'ck_xio_x43_s[1]', 'u_xio.u_xg'),
]


def ports(kind, side, w):
    """(clock, reset, W-face sequence, E-face sequence, bank-face pitch side) with bit-major bank order."""
    banks = ['b0', 'b1', 'b2'] if kind == 'x34' else ['b0', 'b2', 'b3']
    trip = [f'{b}[{i}]' for i in range(w + 1) for b in banks]
    single = lambda d, v: [f'{d}[{i}]' for i in range(w)] + [v]
    side_bits = ['bpar[0]', 'bpar[1]', 'bpar[2]'] + (['s_mark'] if kind == 'x34' else ['t_mark', 'ph1_bad'])
    serial_in = (kind == 'x34' and side == 's') or (kind == 'x43' and side == 't')
    ck, rst = ('s_ck', 's_rst_n') if side == 's' else ('t_ck', 't_rst_n')
    if serial_in:                       # bank writer: s_d / s_v in (W), banks out (E)
        return ck, rst, single('s_d', 's_v'), trip + side_bits
    return ck, rst, trip + side_bits, single('o_d', 'o_v') + ['fault']


def place(face, names, pitch):
    """center every pin on an M4 track (.012 + k .048), contiguous at `pitch`, the run centred on the face"""
    span = (len(names) - 1) * pitch
    start = Y0 + math.floor(((H_UM - span) / 2 - Y0) / TRK) * TRK
    assert start >= 4.32 and start + span <= H_UM - 4.32, (face, len(names))
    x = 0.042 if face == 'W' else round(W_UM - 0.042, 6)
    return [dict(port=n, face=face, layer='M4', x_um=x, y_um=round(start + k * pitch, 6)) for k, n in enumerate(names)]


def build(kind, side, w, cat, inst, gen):
    top = f'ot_s81_vm_{kind}_{side}'
    name = f'{top}_w{w}_1015_f4'
    ck, rst, wseq, eseq = ports(kind, side, w)
    pw = 0.096 if len(wseq) > len(eseq) else 0.288
    pe = 0.096 if len(eseq) > len(wseq) else 0.288
    pins = place('W', wseq, pw) + place('E', eseq, pe)
    # the single-bit face sits at the same y as its triplet: same start rule makes both runs centred, 3:1 pitch
    for j, (nm, x) in enumerate([(ck, 21.588), (rst, 21.588 + 0.432)]):
        pins.append(dict(port=nm, face='N', layer='M5', x_um=x, y_um=round(H_UM - 0.042, 6)))
    PINS.mkdir(parents=True, exist_ok=True)
    tcl = PINS / f'{name}.tcl'
    tcl.write_text(f'# {name}: bit-major native pin plan (tools/s81_vm/build_cdc_leaf_kits.py); M4 W/E, M5 N, '
                   f'.012 mod .048 tracks.\n' + ''.join(
                       f"place_pin -pin_name {{{p['port']}}} -layer {p['layer']} -location {{{p['x_um']:.6f} "
                       f"{p['y_um']:.6f}}} -force_to_die_boundary\n" for p in pins))
    (PINS / f'{name}.pins.json').write_text(json.dumps(dict(top=top, params=dict(W=w), outline_um=[W_UM, H_UM],
                                                            pins=pins), indent=1) + '\n')
    base = lambda seq: list(dict.fromkeys(n.split('[')[0] for n in seq))
    gate = 'x34_gate.sh' if kind == 'x34' else 'x43_gate.sh'
    tag = 'X34' if kind == 'x34' else 'X43'
    mut = 'OT_VM_X34_MUT_SBANK' if (kind, side) == ('x34', 's') else (
        'OT_VM_X34_MUT_PHASE' if kind == 'x34' else 'OT_VM_X43_MUT_PHASE')
    tb = f'rtl/dsrom_sys/s81_ph/test/tb_ot_s81_vm_{kind}.sv'
    exact = (f"mkdir -p {{RUN}} && sed 's/localparam integer W = 64;/localparam integer W = {w};/' {tb} > {{RUN}}/tb_w.sv"
             f" && iverilog -g2012 -o {{RUN}}/sim -s tb_ot_s81_vm_{kind} {SRC[kind]} {{RUN}}/tb_w.sv")
    benches = [
        {'name': 'lint', 'cmd': f"mkdir -p {{RUN}} && printf '%s\\n' 'module ot_lint_top; {top} #(.W({w})) u_top (); endmodule'"
         f" > {{RUN}}/ot_lint_top.sv && verilator --lint-only -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD "
         f"-Wno-MULTIDRIVEN -Wno-MODMISSING -DSYNTHESIS --top-module ot_lint_top {{RUN}}/ot_lint_top.sv {SRC[kind]} && echo lint-ok",
         'expect': 'pass', 'threads': 1, 'peak_ram_gb': 4, 'needs': ['verilator']},
        {'name': f'exact_w{w}', 'cmd': exact + f' && for m in 0 1 2' + (' 3' if kind == 'x43' else '') +
         f'; do vvp -n {{RUN}}/sim +mode=$m; done', 'expect': 'pass', 'pass_regex': f'TB_{tag} PASS mode 0',
         'min_count_regex': r'words (\d+)', 'threads': 1, 'peak_ram_gb': 2, 'needs': ['iverilog']},
        {'name': f'gate_{kind}', 'cmd': f'bash tools/s81_vm/{gate} {{RUN}}/gate', 'expect': 'pass',
         'pass_regex': f'{tag}_GATE PASS', 'threads': 1, 'peak_ram_gb': 2, 'needs': ['iverilog']},
        {'name': f'neg_{side}', 'cmd': exact.replace('iverilog -g2012', f'iverilog -g2012 -D{mut}') +
         ' && vvp -n {RUN}/sim +mode=0', 'expect': 'fail', 'fail_regex': f'TB_{tag} FAIL mode 0',
         'threads': 1, 'peak_ram_gb': 2, 'needs': ['iverilog']},
    ]
    why = ('New per-root category master (ABI ' + cat + ') with no prior slot; die geometry reservation required '
           'before parent adoption')
    slot = {'contract': 'S81 VM CDC leaf native geometry candidate (F4 1015)', 'version': BRANCH, 'why': why}
    spec = {
        'name': name, 'top': top, 'kind': 'tile', 'sources': [SRC[kind]], 'params': {'W': w},
        'clock_port': ck, 'reset_ports': [rst],
        'outline': {'w': W_UM, 'h': H_UM, 'exact': True},
        'pins': {'W': base(wseq), 'E': base(eseq), 'N': [ck, rst], 'S': []},
        'io_tcl': str(tcl.relative_to(ROOT)), 'macros': [], 'children': [], 'inter': [],
        'recipe': 2, 'io_flop_at_pins': {'cols': 4, 'allow_none': True}, 'inhold': True, 'outhold': False,
        'keep_pin_regs': True, 'pin_reg_split': True, 'hold_pad': {'cell': 'HB2xp67_ASAP7_75t_R'}, 'layer_cap': 'M5',
        'route': {'pd': 0.4, 'threads': 8, 'peak_ram_gb': 16, 'period_ps': 770, 'hold_margin_ns': 0.03,
                  'macro_halo_um': 5.4},
        'structural_change': (
            f'{kind} 3:4 transfer split per clock root ({top}, W{w}, instances {inst}; ABI {cat}); wrapper '
            f'ot_s81_vm_{kind} bit-identical (tb_ot_s81_vm_{kind} counts identical at W64/W{w}). BIT-MAJOR pin plan: '
            'F2 x34 W542 r2 views failed native capture (9 / 149 pins > 190 ps) because the placer put each bank bus '
            'on its own third of the face (b0[i] .. b2[i] up to ~230 um apart); here the three bank bits of every word '
            'bit are adjacent 2-track M4 pins and the single-bit face sits at the same y, so every pin -> flop -> pin '
            'run is a straight row across the 43.2 um slice. outhold off: bank outputs are rewritten >= 1.6 ns after '
            'their fixed read (hold by construction), launch budget as F2 r2 (launch 181-187 <= 220).'),
        'slot_change_request': slot,
        'reroute_reason': {'kind': 'slot_change', 'slot_change_request': slot,
                           'why': 'new per-root CDC leaf master; no closed view exists for this category',
                           'contract': f'S81 VM CDC leaves F4 1015 ({BRANCH}): {top} W{w} 43.2x345.6 bit-major slice'},
        'job': {'owner': OWNER, 'branch': BRANCH, 'tag': 'f4',
                'extra_paths': ['tools/s81_vm', 'rtl/dsrom_sys/s81_ph/vm', 'rtl/dsrom_sys/s81_ph/test',
                                'physical/s81_vm_cdc_leaves_1015'],
                'purpose': f'Native {cat} master {top} W{w}: exact transfer bench at W{w} + gate + observed mutant, '
                           'TT/FF/DRC0 + measured R; parent 3:4 arcs and die slot remain open',
                'benches': benches, 'cycles_added': 0},
    }
    SPECS.mkdir(parents=True, exist_ok=True)
    path = SPECS / f'{name}.json'
    path.write_text(json.dumps(spec, indent=1) + '\n')
    if gen:
        subprocess.run([sys.executable, str(ROOT / 'tools/ref_tile/ref_tile.py'), 'gen', str(path)], cwd=ROOT, check=True)
    return name


if __name__ == '__main__':
    for leaf in LEAVES:
        print(build(*leaf, gen='--gen' in sys.argv))
