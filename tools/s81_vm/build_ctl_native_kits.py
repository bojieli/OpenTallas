#!/usr/bin/env python3
"""Source-bound native hardening kits for the static S81 VM control leaves that own the ck_rsched_t, ck_seq_t and
ck_landing_t die clock categories (each its own clock root, no inherited view).

Every port of the ACTUAL module gets a per-bit pin (M4 on W/E, M5 on N/S, .012 mod .048 tracks, >= .144 um pitch,
M5 PG columns avoided) on the face its producer/consumer lies on in the VM core (W: engine/request side and clock/reset,
E: memory side, S: return / read-router / seq side, N: observation).  Outline = the larger of the pin-bound square and
the area estimate; the gate measures the real std area.  Geometry adoption needs the die/parent pin grant
(slot_change_request).  Usage: build_ctl_native_kits.py [rsched seq landing]
"""
import hashlib, json, math, pathlib, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import die_port_bind as D  # noqa: E402

VM = 'rtl/dsrom_sys/s81_ph/vm/'
OUT = ROOT / 'physical/s81_vm_ctl_native_1015'
SPECS = ROOT / 'tools/ref_tile/specs_s81vm_ctl_native_1015'
CORE_BENCH = 'bash tools/s81_vm/core_leaf_bench.sh {RUN}/bench/%s %s %s'
LEAVES = {
    'rsched': dict(top='dsfd_vm_static_rsched', file='dsfd_vm_static_rsched.sv', reset='rst_n', min_side=86.4,
                   faces={'W': ['ck', 'rst_n', 'su_v', 'su_row', 'hc_v', 'hc_row', 'aux_v', 'aux_row', 'mx_v', 'mx_row'],
                          'E': ['n_v', 'n_row', 'n_slot', 'n_group', 'a_v', 'a_row'],
                          'S': ['release_v', 'release_group', 'release_mask', 'prepare_v', 'prepare_group',
                                'prepare_mask', 'expected_v', 'release_slot', 'aux_expected', 'mx_expected', 'mx_rslot'],
                          'N': ['obs_row', 'sched_fault']},
                   benches=[('positive', CORE_BENCH % ('rsched_base', 'rsched', ''), 'pass', r'CORE_LEAF PASS rsched'),
                            ('mutant_slot', CORE_BENCH % ('rsched_mslot', 'rsched_mslot', 'OT_VM_RSCHED_MUT_SLOT'),
                             'fail', r'CORE_LEAF FAIL rsched_mslot'),
                            ('mutant_prepare', CORE_BENCH % ('rsched_mprep', 'rsched_mprep', 'OT_VM_RSCHED_MUT_PREPARE'),
                             'fail', r'CORE_LEAF FAIL rsched_mprep')]),
    'seq': dict(top='dsfd_vm_seq_static', file='dsfd_vm_seq_static.sv', reset='rst', min_side=86.4,
                faces={'W': ['ck', 'rst', 'c_cmd', 'c_done', 'c_st', 't_inp_su', 't_inp_hc', 'v_cv', 'v_cd', 'v_dv',
                             'v_dt', 'v_flt', 'o_rv'],
                       'E': ['o_ca:0:904'], 'N': ['o_cv', 'o_cm', 'o_ca:904:1152'], 'S': ['o_rr']},
                benches=[('positive', 'bash tools/s81_vm/vm_seq_static_gate.sh {RUN}/bench/seq', 'pass', r'VMSS_GATE PASS'),
                         ('mutant_dlat', 'bash tools/s81_vm/vm_seq_mutant_bench.sh {RUN}/bench/seq_mdlat DLAT', 'fail',
                          r'VMSS_MUTANT FAIL DLAT')]),
    'landing': dict(top='dsfd_vm_static_landing', file='dsfd_vm_static_landing.sv', reset='rst_n', min_side=86.4,
                    faces={'W': ['ck', 'rst_n', 'larm_v', 'larm_g', 'larm_base', 'fault', 'o_d:1024:2048'],
                           'N': ['i_v', 'i_d:0:1024'], 'S': ['o_v', 'o_row', 'o_d:0:1024'], 'E': ['i_d:1024:2048']},
                    benches=[('positive', CORE_BENCH % ('land_base', 'landing', ''), 'pass', r'CORE_LEAF PASS landing'),
                             ('mutant_stride', CORE_BENCH % ('land_mstride', 'landing_mstride', 'OT_VM_LANDING_MUT_STRIDE'),
                              'fail', r'CORE_LEAF FAIL landing_mstride')]),
}


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


def build(key):
    c = LEAVES[key]
    src = ROOT / VM / c['file']
    mod = next(m for m in D.parse_modules(src.read_text(), str(src)) if m.name == c['top'])
    env = mod.env({})
    widths = {n: mod.width(n, env) for n in mod.ports}
    def expand(e):  # 'name' (all bits) or 'name:lo:hi' (a bit range of one port)
        n, *r = e.split(':')
        lo, hi = (int(r[0]), int(r[1])) if r else (0, widths[n])
        return [(n, i) for i in range(lo, hi)]
    bits = {f: [b for e in names for b in expand(e)] for f, names in c['faces'].items()}
    allbits = sorted(b for v in bits.values() for b in v)
    assert allbits == sorted((n, i) for n, wd in widths.items() for i in range(wd)), key
    side = c['min_side']
    while True:  # 1.08 um lattice; every face must fit its bits
        if all(len(sites(side, 'M5' if f in 'NS' else 'M4')) >= len(b) for f, b in bits.items()):
            break
        side = round(side + 1.08, 2)
    w = h = side
    pins, tcl = [], ['# Source-exact native candidate (%s): M4 W/E, M5 N/S, .012 mod .048 tracks. Geometry adoption pending.' % c['top']]
    for f, b in bits.items():
        if not b:
            continue
        layer = 'M5' if f in 'NS' else 'M4'
        s = sites(side, layer)
        pts = [s[int((i + .5) * len(s) / len(b))] for i in range(len(b))]
        for (n, i), d in zip(b, pts):
            port = n if widths[n] == 1 else f'{n}[{i}]'
            x, y = (d, h if f == 'N' else 0) if f in 'NS' else (w if f == 'E' else 0, d)
            sz = '.024 .192' if layer == 'M5' else '.192 .024'
            pins.append(dict(port=port, face=f, layer=layer, x_um=x, y_um=y))
            tcl.append(f'place_pin -pin_name {{{port}}} -layer {layer} -location {{{x:.3f} {y:.3f}}} -pin_size {{{sz}}} -force_to_die_boundary')
    OUT.mkdir(parents=True, exist_ok=True)
    SPECS.mkdir(parents=True, exist_ok=True)
    (OUT / f'{c["top"]}.tcl').write_text('\n'.join(tcl) + '\n')
    sha = hashlib.sha256(src.read_bytes()).hexdigest()
    (OUT / f'{c["top"]}.pins.json').write_text(json.dumps(dict(
        schema='opentallas.s81.assigned_pins.v1', master=c['top'], outline_um=[w, h], source=str(src.relative_to(ROOT)),
        source_sha256=sha, port_bits=sum(widths.values()), clock_entries={'stream': ['ck']}, reset_entries=[c['reset']],
        face_bits={f: len(b) for f, b in bits.items()}, pins=pins,
        scope='SOURCE_BOUND_NATIVE_CANDIDATE_NOT_PHYSICAL_CLOSURE'), indent=1) + '\n')
    benches = []
    for name, cmd, expect, rx in c['benches']:
        b = dict(name=f'{key}_{name}', cmd=cmd, expect=expect, threads=2, peak_ram_gb=8 if 'core_leaf' in cmd else 2,
                 needs=['verilator'] if 'core_leaf' in cmd else ['iverilog'])
        b['pass_regex' if expect == 'pass' else 'fail_regex'] = rx
        benches.append(b)
    spec = dict(
        name=f'{c["top"]}_native_1015_r1', top=c['top'], kind='tile', sources=[VM + c['file']], clock_port='ck',
        reset_ports=[c['reset']], outline=dict(w=w, h=h, exact=True),
        pins={f: list(dict.fromkeys(e.split(':')[0] for e in n)) for f, n in c['faces'].items() if n}, io_tcl=str((OUT / f'{c["top"]}.tcl').relative_to(ROOT)),
        macros=[], route=dict(pd=.4, threads=8, peak_ram_gb=16, period_ps=770, hold_margin_ns=.03), recipe=2,
        io_flop_at_pins=dict(cols=4, allow_none=True), inhold=True, outhold=True, keep_pin_regs=True, pin_reg_split=True,
        hold_pad=dict(cell='HB2xp67_ASAP7_75t_R'),
        structural_change=(f'{c["top"]} hardened as its own independently clocked leaf on the {key} die clock category '
                           '(previously an unhardened core child with no view): actual RTL, full per-bit functional pins, '
                           'static schedule unchanged, zero added cycles; 833.333 sign-off / 770 route.'),
        slot_change_request=dict(contract='S81 VM native control-leaf geometry candidate', version='f3-1015',
                                 why='new hardened leaf; die/parent pin grant required before parent adoption'),
        job=dict(owner='claude:S81 VM F3 ctl', branch='claude/s81-vm-f3-ret-1015', tag='native1',
                 extra_paths=['tools/s81_vm', 'rtl/dsrom_sys/s81_ph/vm', 'rtl/dsrom_sys/s81_ph/test',
                              'physical/s81_vm_ctl_native_1015', 'physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2'],
                 purpose='Native hardened VM control leaf: exact production-shape bench + observed DUT mutant, native CTS, one route.',
                 benches=benches, cycles_added=0))
    path = SPECS / f'{c["top"]}.json'
    path.write_text(json.dumps(spec, indent=1) + '\n')
    subprocess.run(['python3', str(ROOT / 'tools/ref_tile/ref_tile.py'), 'gen', str(path)], cwd=ROOT, check=True)
    print(json.dumps(dict(leaf=key, outline=[w, h], pins=len(pins), faces={f: len(b) for f, b in bits.items()})))


for k in (sys.argv[1:] or list(LEAVES)):
    build(k)
