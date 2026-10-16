#!/usr/bin/env python3
"""Pilot hardening kits for the three new A2-F masters (tools/s81_vm/area_a2f.sv): s81_a2f_field16 (32 instances),
s81_a2f_meta26 (4), s81_a2f_control4 (4).  Purpose: MEASURE the planned outlines used by a2f_route_plan.py
(OUTLINES / 'mid*' variants) -- std-cell area, congestion, TT/FF closure, native launch/capture -- before adoption.
Pins: M5 on N/S, M4 on W/E (.012 mod .048 tracks, >= .144 um pitch, M5 PG columns avoided, as build_ctl_native_kits),
faces as the route plan: data in on S, records out on N, IDs/drains (control) on W/E.  Bench: the cycle-exact
A2-F == A2 differential (area_a2f_equiv_gate.py --bench gold) + an observed DUT mutant (quarter select swap).
Usage: build_a2f_kits.py [field16 meta26 control4]
"""
import hashlib, json, pathlib, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import die_port_bind as D  # noqa: E402


def sites(length, layer):
    """pin sites (build_ctl_native_kits.py rule; that module builds on import, so it is not imported)."""
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

SRC = 'tools/s81_vm/area_a2f.sv'
DEPS = ['tools/s81_vm/area_a2_controlled.sv', 'tools/s81_vm/area_id_native.sv', 'tools/s81_vm/area_id_native_join.sv',
        'tools/s81_vm/area_a2_hardmasters.sv']
OUT = ROOT / 'physical/s81_vm_a2f_1015'
SPECS = ROOT / 'tools/ref_tile/specs_s81vm_a2f_1015'
BRANCH = 'claude/s81-vm-a2hier-1015'
GATE = 'python3 tools/s81_vm/area_a2f_equiv_gate.py --seeds 1 --bench %s'
LEAVES = {
    'field16': dict(top='s81_a2f_field16', clock='ck', reset='rst_n', outline=(183.6, 140.4),
                    faces={'S': ['i_data'], 'N': ['o_data', 'o_v'], 'W': ['ck', 'rst_n', 'i_sel:0:336'],
                           'E': ['i_sel:336:672', 'i_drain_v', 'i_drain_slot', 'fault']}),
    'meta26': dict(top='s81_a2f_meta26', clock='ck', reset='rst_n', outline=(259.2, 162.0),
                   faces={'S': ['i_data'], 'N': ['o_data', 'o_v'], 'W': ['ck', 'rst_n', 'i_sel:0:336'],
                          'E': ['i_sel:336:672', 'i_drain_v', 'i_drain_slot', 'fault']}),
    'control4': dict(top='s81_a2f_control4', clock='ck_control', reset='rst_n', outline=(172.8, 86.4),
                     faces={'S': ['src_v', 'src_bank', 'header_epoch', 'payload_epoch'], 'N': ['ids', 'dr_v', 'dr_s'],
                            'W': ['ck_control', 'rst_n'], 'E': ['fault']}),
}


def build(key):
    c = LEAVES[key]
    src = ROOT / SRC
    mod = next(m for m in D.parse_modules(src.read_text(), str(src)) if m.name == c['top'])
    env = mod.env({})
    widths = {n: mod.width(n, env) for n in mod.ports}

    def expand(e):
        n, *r = e.split(':')
        lo, hi = (int(r[0]), int(r[1])) if r else (0, widths[n])
        return [(n, i) for i in range(lo, hi)]
    bits = {f: [b for e in names for b in expand(e)] for f, names in c['faces'].items()}
    assert sorted(b for v in bits.values() for b in v) == sorted((n, i) for n, wd in widths.items() for i in range(wd))
    w, h = c['outline']
    for f, b in bits.items():
        n = len(sites(w if f in 'NS' else h, 'M5' if f in 'NS' else 'M4'))
        assert n >= len(b), (key, f, n, len(b))
    pins, tcl = [], ['# A2-F pilot (%s): M4 W/E, M5 N/S, .012 mod .048 tracks.' % c['top']]
    for f, b in bits.items():
        layer = 'M5' if f in 'NS' else 'M4'
        s = sites(w if f in 'NS' else h, layer)
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
    (OUT / f'{c["top"]}.pins.json').write_text(json.dumps(dict(
        schema='opentallas.s81.assigned_pins.v1', master=c['top'], outline_um=[w, h], source=SRC,
        source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(), port_bits=sum(widths.values()),
        clock_entries={'stream': [c['clock']]}, reset_entries=[c['reset']], face_bits={f: len(b) for f, b in bits.items()},
        pins=pins, scope='A2F_PILOT_OUTLINE_MEASUREMENT_NOT_ADOPTED'), indent=1) + '\n')
    benches = [dict(name=f'a2f_{key}_equiv', cmd=GATE % 'gold', expect='pass', threads=1, peak_ram_gb=4,
                    needs=['iverilog'], pass_regex=r'A2F_EQUIV PASS gold'),
               dict(name=f'a2f_{key}_mut_sel', cmd=GATE % 'S81_A2F_MUT_SEL_SWAP', expect='fail', threads=1,
                    peak_ram_gb=4, needs=['iverilog'], fail_regex=r'A2F_EQUIV FAIL S81_A2F_MUT_SEL_SWAP')]
    spec = dict(
        name=f'{c["top"]}_pilot_1015_r1', top=c['top'], kind='tile', sources=DEPS + [SRC], clock_port=c['clock'],
        reset_ports=[c['reset']], outline=dict(w=w, h=h, exact=True),
        pins={f: list(dict.fromkeys(e.split(':')[0] for e in n)) for f, n in c['faces'].items() if n},
        io_tcl=str((OUT / f'{c["top"]}.tcl').relative_to(ROOT)), macros=[],
        route=dict(pd=.4, threads=8, peak_ram_gb=16, period_ps=770, hold_margin_ns=.03), recipe=2,
        io_flop_at_pins=dict(cols=4, allow_none=True), inhold=True, outhold=True, keep_pin_regs=True, pin_reg_split=True,
        hold_pad=dict(cell='HB2xp67_ASAP7_75t_R'),
        structural_change=(f'{c["top"]}: A2-F field-major write front master (four quarter copies merged, shared input '
                           'pipeline); pilot measures the planned outline; cycle-exact to A2, zero added cycles.'),
        slot_change_request=dict(contract='S81 VM A2-F front geometry candidate', version='a2f-1015',
                                 why='new hardened leaf; VM parent plan a2f_route_plan.py'),
        job=dict(owner='claude:S-VM A2-F', branch=BRANCH, tag='pilot1',
                 extra_paths=['tools/s81_vm', 'physical/s81_vm_a2f_1015'],
                 purpose='A2-F pilot: measured area/closure of the planned outline (cut screen input).',
                 benches=benches, cycles_added=0))
    path = SPECS / f'{c["top"]}.json'
    path.write_text(json.dumps(spec, indent=1) + '\n')
    subprocess.run(['python3', str(ROOT / 'tools/ref_tile/ref_tile.py'), 'gen', str(path)], cwd=ROOT, check=True)
    print(json.dumps(dict(leaf=key, outline=[w, h], pins=len(pins), faces={f: len(b) for f, b in bits.items()})))


for k in (sys.argv[1:] or list(LEAVES)):
    build(k)
