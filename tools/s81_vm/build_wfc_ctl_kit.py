#!/usr/bin/env python3
"""Hard-leaf kit for dsfd_vm_static_wfc_ctl (die clock categories ck_wfc_control_t / ck_wfc_control_s): the WFC
endpoint's control flops, two related 3:4 roots.  Faces: W = x34 side (xv, xd, x34f) + clocks/resets, E = core side
(write source 52, aux ports 8..11 requests / returns), N = x43 side (s_v, s_d) + serial grant / t_err + faults.
Pin registers opted out WITH reason: every output is a flop and every input lands on a flop in its first stage; extra
pin stages would move the fixed 3:4 / 4:3 sample slots (x43 sample index rule, RESPONSE_PAD) of the WFC protocol.
Bench: wfc_ctl_equiv_gate.sh (wires-only parent vs the r9 body, 2 configs x 2 seeds) + two observed DUT mutants."""
import json, pathlib, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import die_port_bind as D  # noqa: E402

SRC = 'rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_wfc.sv'
OUT = ROOT / 'physical/s81_vm_ctl_native_1015'
SPEC = ROOT / 'tools/ref_tile/specs_s81vm_ctl_native_1015/dsfd_vm_static_wfc_ctl.json'
W_UM, H_UM = 194.4, 394.2
FACES = {'W': ['ck_control_t', 'rss_control_t', 'ck_control_s', 'rst_control_s', 'xv', 'xd', 'x34f'],
         'E': ['w_v', 'w_row', 'w_d', 'a_v', 'a_row', 'e_v', 'e_d'],
         'N': ['s_v', 's_d', 'g_q', 'e_q', 'x43f', 'vm_fault', 'fault']}


def sites(length, layer):
    out = []
    for k in range(int(length / .048) + 2):
        x = round(.012 + .048 * k, 3)
        if x < 4.32 or x > length - 4.32:
            continue
        if layer == 'M5' and .18 <= x % 5.4 <= .74:
            continue
        if not out or x - out[-1] >= .144 - 1e-6:
            out.append(x)
    return out


src = ROOT / SRC
mod = next(m for m in D.parse_modules(src.read_text(), str(src)) if m.name == 'dsfd_vm_static_wfc_ctl')
env = mod.env({'RLAT': '17', 'RESPONSE_PAD': '0'})
widths = {n: mod.width(n, env) for n in mod.ports}
bits = {f: [(n, i) for n in names for i in range(widths[n])] for f, names in FACES.items()}
assert sorted(b for v in bits.values() for b in v) == sorted((n, i) for n, w in widths.items() for i in range(w))
pins, tcl = [], ['# dsfd_vm_static_wfc_ctl (S-VM 1015): M4 W/E, M5 N, .012 mod .048 tracks.']
for f, b in bits.items():
    layer = 'M5' if f in 'NS' else 'M4'
    s = sites(W_UM if f in 'NS' else H_UM, layer)
    assert len(s) >= len(b), (f, len(s), len(b))
    pts = [s[int((i + .5) * len(s) / len(b))] for i in range(len(b))]
    for (n, i), d in zip(b, pts):
        port = n if widths[n] == 1 else f'{n}[{i}]'
        x, y = (d, H_UM if f == 'N' else 0) if f in 'NS' else (W_UM if f == 'E' else 0, d)
        sz = '.024 .192' if layer == 'M5' else '.192 .024'
        pins.append(dict(port=port, face=f, layer=layer, x_um=x, y_um=y))
        tcl.append(f'place_pin -pin_name {{{port}}} -layer {layer} -location {{{x:.3f} {y:.3f}}} -pin_size {{{sz}}} -force_to_die_boundary')
OUT.mkdir(parents=True, exist_ok=True)
(OUT / 'dsfd_vm_static_wfc_ctl.tcl').write_text('\n'.join(tcl) + '\n')
G = 'bash tools/s81_vm/wfc_ctl_equiv_gate.sh {RUN}/wfc %s'
spec = dict(
    name='dsfd_vm_static_wfc_ctl_native_1015_r1', top='dsfd_vm_static_wfc_ctl', kind='tile', sources=[SRC],
    params={'RLAT': 17, 'RESPONSE_PAD': 0}, defines=[], clock='multiple_cts_roots', clock_port='ck_control_t',
    clock_ports=['ck_control_t', 'ck_control_s'], clock_data_paths='related_pll_ratio',
    clock_relationship={'kind': 'same_pll_fixed_phase', 'ratio': [4, 3], 'phase_ps': 0},
    clock_entry_domains={'core': {'ratio': [1, 1], 'ports': ['ck_control_t'],
                                  'inputs': ['rss_control_t', 'xv', 'xd', 'x34f', 'x43f', 'e_v', 'e_d', 'vm_fault'],
                                  'outputs': ['w_v', 'w_row', 'w_d', 'a_v', 'a_row', 's_v', 's_d', 'fault']},
                         'serial': {'ratio': [4, 3], 'ports': ['ck_control_s'], 'inputs': ['rst_control_s'],
                                    'outputs': ['g_q', 'e_q']}},
    reset_ports=['rss_control_t', 'rst_control_s'], outline=dict(w=W_UM, h=H_UM, exact=True), layer_cap='M5',
    pins={f: n for f, n in FACES.items()}, io_tcl=str((OUT / 'dsfd_vm_static_wfc_ctl.tcl').relative_to(ROOT)), macros=[],
    route=dict(pd=.4, threads=8, peak_ram_gb=16, period_ps=770, hold_margin_ns=.03), recipe=2,
    pin_regs={'enable': False, 'reason': ('every output is a flop and every input lands on a flop in its first stage; '
                                          'extra pin stages would move the fixed 3:4 / 4:3 x43 sample slots of the WFC protocol')},
    io_flop_at_pins=dict(cols=4, allow_none=True), inhold=True, outhold=True, keep_pin_regs=True, pin_reg_split=True,
    hold_pad=dict(cell='HB2xp67_ASAP7_75t_R'),
    structural_change=('WFC control glue (decode, return, grant/t_err) hardened as its own two-root leaf on the '
                       'ck_wfc_control_t / ck_wfc_control_s die categories (previously parent flops with no view); '
                       'parent dsfd_vm_static_wfc is wires only; data edges unchanged, diagnostic fault +1 stream edge.'),
    slot_change_request=dict(contract='S81 VM native control-leaf geometry candidate', version='wfc-ctl-1015',
                             why='new hardened leaf; die/parent pin grant required before parent adoption'),
    job=dict(owner='claude:S-VM ctlglue', branch='claude/s81-vm-ctlglue-1015', tag='native1',
             extra_paths=['tools/s81_vm', 'rtl/dsrom_sys/s81_ph/vm', 'physical/s81_vm_ctl_native_1015'],
             purpose='Native WFC control leaf: differential bench vs the r9 parent body + observed DUT mutants, native CTS.',
             benches=[dict(name='wfc_ctl_equiv', cmd=G % '', expect='pass', pass_regex='WFC_CTL_GATE PASS', threads=1,
                           peak_ram_gb=2, needs=['iverilog']),
                      dict(name='wfc_ctl_mut_lane', cmd=G % 'OT_VM_WFC_CTL_MUT_LANE', expect='fail',
                           fail_regex='WFC_CTL_GATE FAIL OT_VM_WFC_CTL_MUT_LANE', threads=1, peak_ram_gb=2, needs=['iverilog']),
                      dict(name='wfc_ctl_mut_fault', cmd=G % 'OT_VM_WFC_CTL_MUT_FAULT', expect='fail',
                           fail_regex='WFC_CTL_GATE FAIL OT_VM_WFC_CTL_MUT_FAULT', threads=1, peak_ram_gb=2, needs=['iverilog'])],
             cycles_added=0))
SPEC.parent.mkdir(parents=True, exist_ok=True)
SPEC.write_text(json.dumps(spec, indent=1) + '\n')
subprocess.run(['python3', str(ROOT / 'tools/ref_tile/ref_tile.py'), 'gen', str(SPEC)], cwd=ROOT, check=True)
print(json.dumps(dict(outline=[W_UM, H_UM], pins=len(pins), faces={f: len(b) for f, b in bits.items()})))
