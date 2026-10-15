#!/usr/bin/env python3
"""Native write-edge leaf kits (claude S81 VM F1, 2026-10-15): one closed hard master per write clock category.

  ck_write_header_t  -> dsfd_vm_static_w0_header          (1 root)
  ck_write_payload_t -> dsfd_vm_static_w0_payload         (4 roots, one master)
  ck_write_control_t -> dsfd_vm_static_wcontrol           (1 root)
  ck_write_dispatch_t-> dsfd_vm_static_wdispatch128_B{0,8,16,24}  (16 roots, 4 bank-base masters)
  ck_write_stage_t   -> dsfd_vm_static_wstage128_{E,W}    (128 roots, 2 pin-orientation masters)

Faces / outlines are Codex's write-edge candidates (physical/s81_vm_write_edge_1015/*.json, reach screen plan.json:
dispatch->stage max 83.5 um, 0 bits > 500 um).  Pins are re-snapped here onto the layers and tracks of the closed native
VM leaves (capture/scatter): N/S on M5, E/W on M4, centres .012 mod .048, pitch a multiple of .048 (>= .096, two tracks;
face use <= 0.5 of the tracks), centred with >= 4.32 um corner keep-out.  Same RTL, no stage added; outhold off (the
composed hold is carried by every receiver's input pad, as the composed-budget relay kits).
"""
import hashlib, json, math, subprocess, sys
from pathlib import Path
R = Path(__file__).resolve().parents[2]
CAND = R / 'physical/s81_vm_write_edge_1015'
OUT = CAND / 'native'
SPECS = R / 'tools/ref_tile/specs_s81vm_write_native_1015'
V = 'rtl/dsrom_sys/s81_ph/vm/'
BRANCH = 'claude/s81-vm-write-native-1015'

# kit -> (top, candidate pin json, sources, params-in-wrapper, bench leaf, clock category, roots)
KITS = [('dsfd_vm_write_header_native', 'dsfd_vm_static_w0_header', 'dsfd_vm_static_w0_header', [V + 'dsfd_vm_static_w0.sv'], 'header', 'ck_write_header_t', 1),
        ('dsfd_vm_write_payload_native', 'dsfd_vm_static_w0_payload', 'dsfd_vm_static_w0_payload', [V + 'dsfd_vm_static_w0.sv'], 'payload', 'ck_write_payload_t', 4),
        ('dsfd_vm_write_control_native', 'dsfd_vm_static_wcontrol', 'dsfd_vm_static_wcontrol', [V + 'dsfd_vm_static_wcontrol.sv'], 'control', 'ck_write_control_t', 1)]
KITS += [(f'dsfd_vm_write_dispatch_b{b}_native', f'dsfd_vm_static_wdispatch128_B{b}', 'dsfd_vm_static_wdispatch128',
          [V + 'dsfd_vm_static_wdispatch128.sv', V + 'dsfd_vm_static_wdispatch128_profiles.sv'], 'dispatch', 'ck_write_dispatch_t', 4) for b in (0, 8, 16, 24)]
KITS += [(f'dsfd_vm_write_stage_{o.lower()}_native', f'dsfd_vm_static_wstage128_{o}', 'dsfd_vm_static_wstage128_' + ('east' if o == 'E' else 'west'),
          [V + 'dsfd_vm_static_wstage128.sv', V + 'dsfd_vm_static_wstage128_profiles.sv'], 'stage', 'ck_write_stage_t', 64) for o in 'EW']


DISP_IN = {'i_v': 1, 'i_row': 14, 'i_mask': 4, 'i_data': 128, 'i_tag': 8, 'i_capture_lane': 2, 'i_storage_slot': 2}
DISP_OUT = {'o_v': 1, 'o_slot': 2, 'o_row': 14, 'o_mask': 4, 'o_data': 128, 'o_tag': 8}


def rename(top, name):
    """dispatch profiles split each bus by face: sources 0..26 -> *_n, 27..52 -> *_s; records 0..11 (banks +0..3) -> *_e,
    records 12..23 -> *_w (dsfd_vm_static_wdispatch128_profiles.sv)."""
    if not top.startswith('dsfd_vm_static_wdispatch128_B') or '[' not in name:
        return name
    base, idx = name[:-1].split('[')
    idx = int(idx)
    if base in DISP_IN:
        v = DISP_IN[base]
        return f'{base}_n[{idx}]' if idx // v < 27 else f'{base}_s[{idx - 27 * v}]'
    v = DISP_OUT[base]
    return f'{base}_e[{idx}]' if idx // v < 12 else f'{base}_w[{idx - 12 * v}]'


def snap_face(names, length):
    n = len(names)
    if not n:
        return []
    usable = length - 2 * 4.32
    pitch = .432 if n == 1 else min(.432, math.floor(usable / (n - 1) / .048 + 1e-9) * .048)
    assert pitch >= .096 - 1e-9, (names[0], n, length, pitch)
    span = (n - 1) * pitch
    start = .012 + math.floor(((length - span) / 2 - .012) / .048) * .048
    assert start >= 4.32 - 1e-9 and start + span <= length - 4.32 + 1e-9
    return [round(start + i * pitch, 6) for i in range(n)], pitch


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    SPECS.mkdir(parents=True, exist_ok=True)
    model = {'schema': 'opentallas.s81.vm-write-native-kits.v1', 'period_ps': 833.333, 'route_period_ps': 770, 'kits': {}}
    for kit, top, cand, sources, leaf, cat, roots in KITS:
        c = json.loads((CAND / (cand + '.json')).read_text())
        w, h = c['outline_um']
        faces = {f: [rename(top, p['name']) for p in c['pins'] if p['face'] == f] for f in 'NSEW'}
        pins, pitches = [], {}
        for f in 'NSEW':
            if not faces[f]:
                continue
            length = w if f in 'NS' else h
            pos, pitch = snap_face(faces[f], length)
            pitches[f] = pitch
            for name, d in zip(faces[f], pos):
                layer = 'M5' if f in 'NS' else 'M4'
                x = d if f in 'NS' else (0.0 if f == 'W' else w)
                y = d if f in 'WE' else (h if f == 'N' else 0.0)
                size = '.024 .192' if f in 'NS' else '.192 .024'
                pins.append(dict(port=name, face=f, layer=layer, x_um=round(x, 6), y_um=round(y, 6), size=size))
        tcl = OUT / (top + '.tcl')
        tcl.write_text('# Native write-edge pin plan (claude S81 VM F1 2026-10-15): Codex candidate faces, closed-leaf layers/tracks.\n' +
                       ''.join(f"place_pin -pin_name {{{p['port']}}} -layer {p['layer']} -location {{{p['x_um']:.3f} {p['y_um']:.3f}}} "
                               f"-pin_size {{{p['size']}}} -force_to_die_boundary\n" for p in pins))
        (OUT / (top + '.json')).write_text(json.dumps(dict(top=top, outline_um=[w, h], candidate=str((CAND / (cand + '.json')).relative_to(R)),
                                                          face_pitch_um=pitches, pins=pins), indent=1) + '\n')
        bases = {f: [] for f in 'NSEW'}
        for p in pins:
            b = p['port'].split('[')[0]
            if b not in bases[p['face']]:
                bases[p['face']].append(b)
        benches = [dict(name=f'exact_{leaf}_wsched53', cmd=f'bash tools/s81_write_edge/leaf_bench.sh {{RUN}}/bench/{leaf}_base {leaf} base',
                        expect='pass', pass_regex=f'WRITE_LEAF_BENCH PASS {leaf} base WRITE_ROOTS_RESULT sent=11024 got=11024 bad=0',
                        min_count_regex=r'sent=(\d+)', threads=4, peak_ram_gb=4, needs=['verilator']),
                   dict(name=f'mutant_actual_{leaf}', cmd=f'bash tools/s81_write_edge/leaf_bench.sh {{RUN}}/bench/{leaf}_mut {leaf} mutant',
                        expect='fail', fail_regex=f'WRITE_LEAF_BENCH FAIL {leaf} mutant WRITE_ROOTS_RESULT sent=11024 got=11024 bad=[1-9]',
                        min_count_regex=r'sent=(\d+)', threads=4, peak_ram_gb=4, needs=['verilator'])]
        if leaf in ('dispatch', 'stage'):
            benches += [dict(name='profile_equiv', cmd=f'python3 tools/s81_write_edge/profile_equiv.py {{RUN}}/bench/pe {top}', expect='pass',
                             pass_regex=f'PROFILE_EQUIV PASS {top} cycles 3000', min_count_regex=r'cycles (\d+)', threads=1, peak_ram_gb=2,
                             needs=['iverilog']),
                        dict(name='profile_equiv_mutant', cmd=f'python3 tools/s81_write_edge/profile_equiv.py {{RUN}}/bench/pem {top} --mutant',
                             expect='fail', fail_regex=f'PROFILE_EQUIV FAIL {top} cycles 3000 bad [1-9]', min_count_regex=r'cycles (\d+)',
                             threads=1, peak_ram_gb=2, needs=['iverilog'])]
        big = leaf in ('dispatch', 'payload')
        spec = dict(name=kit, top=top, kind='tile', sources=sources, clock='cts', clock_port='ck_control' if leaf == 'control' else 'ck',
                    reset_ports=['rst_n'], outline=dict(w=w, h=h, exact=True), pins=bases, io_tcl=str(tcl.relative_to(R)), params={},
                    layer_cap='M5', macros=[], route=dict(pd=.40, threads=16 if big else 8, peak_ram_gb=48 if leaf == 'dispatch' else 16,
                                                         hold_margin_ns=.030),
                    recipe=2, io_flop_at_pins=dict(cols=4, allow_none=True), inhold=True, outhold=False, keep_pin_regs=True, pin_reg_split=True,
                    hold_pad=dict(cell='HB2xp67_ASAP7_75t_R'),
                    structural_change=('Native write-edge leaf: the scalar 29,203-sink W0/wsched register is split into 150 independently '
                                       'clocked actual leaves (control1/header1/payload4/dispatch16/stage128); same RTL, fixed edges W0 P, '
                                       'dispatch P+1/P+2, storage P+3, scatter P+4+lane; no ready/credit/stage added. Pins on closed-leaf '
                                       'M5/M4 tracks; outhold off (receivers carry the composed hold pad).'),
                    slot_change_request=dict(contract='S81 static VM write-edge native option', version='101a4e629/a60002977',
                                             why='New native write leaves: per-category clock roots need closed views with measured R; '
                                                 'parent geometry adoption by S-DIE'),
                    job=dict(owner='claude:S81 VM F1 write-edge', branch=BRANCH, tag='wn1',
                             purpose=f'Actual {top} native leaf for {cat} ({roots} roots): TT setup/FF hold/DRC0, native face IO, measured R',
                             extra_paths=['rtl/dsrom_sys/s81_ph/vm', 'rtl/dsrom_sys/s81_ph/test', 'tools/s81_write_edge', 'physical/s81_vm_write_edge_1015'],
                             benches=benches))
        path = SPECS / (kit + '.json')
        path.write_text(json.dumps(spec, indent=1) + '\n')
        subprocess.run([sys.executable, str(R / 'tools/ref_tile/ref_tile.py'), 'gen', str(path)], cwd=R, check=True)
        model['kits'][kit] = dict(top=top, category=cat, roots=roots, outline_um=[w, h], signal_pins=len(pins), face_pitch_um=pitches,
                                  sources={s: hashlib.sha256((R / s).read_bytes()).hexdigest() for s in sources})
    (OUT / 'model.json').write_text(json.dumps(model, indent=1) + '\n')


if __name__ == '__main__':
    main()
