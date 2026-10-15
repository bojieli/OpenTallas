#!/usr/bin/env python3
"""S81 FILL (2026-10-15): common-clock die stations dsfd_hstnh_<W> / dsfd_hstnv_<W> of the CURRENT die case as real
hard tiles (tools/ref_tile), one kit per distinct master (replicas share the one hardened view).

Inputs are the die generator's own outputs (top-down): the case glue (die_glue.sv, the RTL the die netlist binds) and
the case pin LEF (outline + every pin centre).  For each master this writes
  rtl/dsrom_sys/s81_station_native/gen18r/<master>.sv   the glue module text, byte-identical (sha recorded)
  physical/s81_die_pins/v22_gen18r_stations/<master>.tcl  place_pin of every pin at the generator's centre
  tools/ref_tile/specs_s81_station_gen18r/<name>.json    the ref_tile spec (recipe 2), bench + 2 mutants
Outline: the generator's slot when the recipe-2 content fits at util <= UTIL_MAX; otherwise the slot grows in DEPTH
only (perpendicular to the two data faces: hstnh wider, hstnv taller) so every data-pin coordinate along its face is
unchanged, and the spec carries a slot_change_request for the die lead (Codex 203851bc0 measured the 1024-b slot at
135 % of its row area once the recipe-2 pin hold cells are in).

  station_kits_gen18.py --glue G.sv --lef P.lef.gz --counts inst_counts.txt [--only M1,M2] [--gen]
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RTL_DIR = "rtl/dsrom_sys/s81_station_native/gen18r"
PIN_DIR = "physical/s81_die_pins/v22_gen18r_stations"
SPEC_DIR = "tools/ref_tile/specs_s81_station_gen18r"
MARGIN = 2.16          # ref_tile core margin each side
# recipe-2 std area a bit: flop + share of the clock inverter / buffers (Codex 1024-b synthesis 354.1 um2 / 1024 b) +
# input hold (BUFx4f + HB2) + output min delay (BUF-HB-BUF) = Codex's logged insertions 2 HB2 + 3 BUFx4f a bit
AREA_BIT = 354.13362 / 1024 + 2 * 0.0729 + 3 * 0.11664
AREA_FIX = 6.0         # clock root buffer, tie cells
UTIL_MAX = 0.55
GRID = 0.216           # outline growth step (4 placement sites)


def modules(glue: str) -> dict:
    out = {}
    for m in re.finditer(r'^module (\w+) \(.*?^endmodule\n', glue, re.S | re.M):
        out[m.group(1)] = m.group(0)
    return out


def lef_macros(lef: str) -> dict:
    out = {}
    for m in re.finditer(r'^MACRO (\S+)\n(.*?)^END \1', lef, re.S | re.M):
        body = m.group(2)
        w, h = map(float, re.search(r'SIZE ([\d.]+) BY ([\d.]+)', body).groups())
        pins = []
        for pn, pb in re.findall(r'PIN (\S+)\n(.*?)END \1', body, re.S):
            r = re.search(r'LAYER (\S+)\s*;\s*RECT ([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+)', pb)
            if not r:
                continue
            x1, y1, x2, y2 = map(float, r.groups()[1:])
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            d = {'W': cx, 'E': w - cx, 'S': cy, 'N': h - cy}
            pins.append(dict(pin=pn, layer=r.group(1), x=cx, y=cy, face=min(d, key=d.get)))
        out[m.group(1)] = dict(w=w, h=h, pins=pins)
    return out


def size(master: str, w_bits: int, mac: dict):
    horiz = master.startswith(('dsfd_hstnh_', 'dsfd_stnh_'))
    w, h = mac['w'], mac['h']
    need = (AREA_BIT * w_bits + AREA_FIX) / UTIL_MAX
    face = (h if horiz else w) - 2 * MARGIN
    depth = (w if horiz else h) - 2 * MARGIN
    if face * depth >= need:
        return w, h, None
    d_new = math.ceil((need / face + 2 * MARGIN) / GRID - 1e-9) * GRID
    d_new = round(d_new, 3)
    return (d_new, h, 'w') if horiz else (w, d_new, 'h')


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--glue', required=True)
    ap.add_argument('--lef', required=True)
    ap.add_argument('--counts', required=True, help='"<n> <master>" lines (die instance census of the same case)')
    ap.add_argument('--case', default='GEN18r construction_pass0 (EPYC4 s81-die-r10/gen18r)')
    ap.add_argument('--only', help='comma list of masters')
    ap.add_argument('--owner', default='Claude:fill-s81')
    ap.add_argument('--branch', default='claude/el1015-fill-1015')
    ap.add_argument('--tag', default='f1')
    ap.add_argument('--gen', action='store_true')
    a = ap.parse_args()
    glue_txt = Path(a.glue).read_text()
    glue_sha = hashlib.sha256(glue_txt.encode()).hexdigest()
    mods = modules(glue_txt)
    lef_txt = gzip.open(a.lef, 'rt').read() if a.lef.endswith('.gz') else Path(a.lef).read_text()
    macs = lef_macros(lef_txt)
    counts = {ln.split()[1]: int(ln.split()[0]) for ln in Path(a.counts).read_text().splitlines() if ln.strip()}
    want = [m for m in sorted(mods) if re.fullmatch(r'dsfd_hstn[hv]_\d+|dsfd_stn[hv]_\d+x1', m)]
    if a.only:
        sel = set(a.only.split(','))
        want = [m for m in want if m in sel]
        assert len(want) == len(sel), sorted(sel - set(want))
    for d in (RTL_DIR, PIN_DIR, SPEC_DIR):
        (ROOT / d).mkdir(parents=True, exist_ok=True)
    summary = []
    for mst in want:
        txt = mods[mst]
        wb = int(re.search(r'input wire \[(\d+):0\] di', txt).group(1)) + 1
        fwd = mst.startswith(('dsfd_stnh_', 'dsfd_stnv_'))
        if fwd:      # forwarded-clock station: one fi0 -> negedge stage(s), fo0 = the kept forwarding INV of slice 0
            assert '.fclk_i(fi0[0])' in txt and '.fclk_o(fo0[0])' in txt and 'fi1' not in txt, mst
        else:
            assert 'ot_fwd_clk_inv u_ck (.a(ck[0])' in txt, mst      # common-clock form (kept INV, negedge stage)
            # harden the --hstn-posedge form (tools/dsrom_s81_fulldie.py, same header, body = plain posedge flops on ck):
            # the INV + negedge sinks defeat the tile IO reference (gate 722a9747a: OT_LINK_BUDGET no latency for core_clk)
            head = txt[:txt.index('    wire fck;')]
            txt = (head + f'    reg [{wb - 1}:0] q;   // common-clock station: every di bit captured at the rising edge of ck\n'
                   '    always @(posedge ck[0]) q <= di;\n    assign dq = q;\nendmodule\n')
        mac = macs[mst]
        dw, dh, grown = size(mst, wb, mac)
        sha = hashlib.sha256(txt.encode()).hexdigest()
        (ROOT / RTL_DIR / f'{mst}.sv').write_text(txt)
        horiz = mst.startswith(('dsfd_hstnh_', 'dsfd_stnh_'))
        tcl = [f'# {mst}: die generator pin centres ({a.case}, pins.lef); outline {dw} x {dh}'
               + (f' (slot {mac["w"]} x {mac["h"]} grown in depth)' if grown else ' (= generator slot)')]
        faces = {}
        scalar = set(re.findall(r'wire \[0:0\] (\w+)', txt))     # 1-bit vectors are scalars after synthesis (PPL-0061)
        for p in mac['pins']:
            x, y = p['x'], p['y']
            if grown == 'w' and p['face'] == 'E':
                x = dw - (mac['w'] - x)
            if grown == 'h' and p['face'] == 'N':
                y = dh - (mac['h'] - y)
            pname = re.sub(r'\[0\]$', '', p['pin']) if re.sub(r'\[\d+\]$', '', p['pin']) in scalar else p['pin']
            tcl.append(f'place_pin -pin_name {{{pname}}} -layer {p["layer"]} -location {{{x:.6f} {y:.6f}}} -force_to_die_boundary')
            faces.setdefault(p['face'], set()).add(re.sub(r'\[\d+\]$', '', p['pin']))
        # a glue port the case LEF has no pin for (dsfd_stnv_566x1.fn0, the non-inverted forwarded clock tap): placed on
        # fo0's face 0.192 um beside it and reported to the die lead (the die generator must add the LEF pin)
        ports = re.findall(r'(?:input|output) wire \[\d+:0\] (\w+)', txt)
        missing = [q for q in ports if not any(re.sub(r'\[\d+\]$', '', p['pin']) == q for p in mac['pins'])]
        for q in missing:
            assert q == 'fn0', (mst, missing)
            fo = next(p for p in mac['pins'] if p['pin'].startswith('fo0'))
            x, y = fo['x'], fo['y']
            if grown == 'h' and fo['face'] == 'N':
                y = dh - (mac['h'] - y)
            if fo['face'] in 'NS':
                x += 0.192
            else:
                y += 0.192
            tcl.append(f'# {q}: NOT in the case pins.lef (die generator owes the pin); placed beside fo0 on face {fo["face"]}')
            tcl.append(f'place_pin -pin_name {{{q}}} -layer {fo["layer"]} -location {{{x:.6f} {y:.6f}}} -force_to_die_boundary')
            faces.setdefault(fo['face'], set()).add(q)
        (ROOT / PIN_DIR / f'{mst}.tcl').write_text('\n'.join(tcl) + '\n')
        name = f's81fill_{mst[5:]}'
        layers = sorted({p['layer'] for p in mac['pins']})
        n = counts.get(mst, 0)
        bench = 'tools/s81_station_native/run_' + ('fwd_' if fwd else '') + 'station_gate.sh'
        edge = 'fwd_negedge' if fwd else 'top_posedge'
        spec = {
            'name': name, 'top': mst, 'kind': 'tile',
            'sources': ['rtl/common/ot_fwd_link_stage.sv', f'{RTL_DIR}/{mst}.sv'],
            'params': {}, 'clock_port': 'fi0' if fwd else 'ck', 'reset_ports': [],
            **({'forwarded_clock': True} if fwd else {}),
            'outline': {'w': dw, 'h': dh, 'exact': True},
            'layer_cap': 'M5',
            'pins': {f: sorted(v) for f, v in sorted(faces.items())},
            'io_tcl': f'{PIN_DIR}/{mst}.tcl',
            'recipe': 2,
            'route': {'pd': 0.5, 'threads': 4, 'peak_ram_gb': 8 if wb <= 1100 else 16, 'pin_h': 'M4', 'pin_v': 'M3 M5',
                      'm5_pg_pitch': 2.7},
            'structural_change': ((f'First hardening of the GEN18r generated forwarded-clock station {mst} ({n} die instances): '
                                   f'capture on the falling edge of the forwarded fi0, fo0 = kept forwarding INV, {wb} b, no reset, 0 cycles; ')
                                  if fwd else
                                  (f'First hardening of the GEN18r common-clock station {mst} ({n} die instances) in the '
                                   f'--hstn-posedge form: plain posedge flops on ck (the glue INV + negedge stage is the same '
                                   f'function but its inverted sinks failed the IO reference in every gate, OT_LINK_BUDGET no '
                                   f'latency for core_clk), {wb} b, no reset, 0 cycles; '))
                                  + (
                                  f'RTL = ' + ('the case glue module byte-identical' if fwd else 'the generator --hstn-posedge emission of the case glue header') + f' (module sha256 {sha[:16]}, glue {glue_sha[:16]}); '
                                  'pins at the generator centres. '
                                  + (f'Slot {mac["w"]} x {mac["h"]} holds {face_area(mac, horiz):.0f} um2 of core vs '
                                     f'{AREA_BIT * wb + AREA_FIX:.0f} um2 recipe-2 content (input hold + output min delay '
                                     f'cells a bit) -> depth grown to {dw} x {dh} (data-pin coordinates unchanged).'
                                     if grown else 'Generator slot kept.')),
            'job': {
                'owner': a.owner, 'branch': a.branch, 'tag': a.tag,
                'purpose': (f'S81 FILL: GEN18r die station {mst} ({n} replicas, hardened once): exact phase/basis/random '
                            'bench + wrong-edge and payload mutants; recipe 2, M5 cap, generator pins'),
                'views_to': f'physical/ref_tile/{name}/views',
                'record_to': f'results/rtl/ref_tile/{name}',
                'extra_paths': ['rtl/common', RTL_DIR, 'tools/s81_station_native', PIN_DIR,
                                'physical/hbm_accel_die_views/stations/bench']
                               + (['physical/hbm_w2_rb_station_20261006/forwarded_subtree.tcl'] if fwd else []),
                'benches': [
                    {'name': 'phase_words', 'cmd': f'bash {bench} pass {mst} {wb} {{RUN}}/bench_p', 'expect': 'pass',
                     'pass_regex': f'STATION PASS 20000 words {wb} bits {edge}', 'threads': 2, 'peak_ram_gb': 4},
                    {'name': 'wrong_clock_edge_mutant', 'cmd': f'bash {bench} clock_mutant_raw {mst} {wb} {{RUN}}/bench_c',
                     'expect': 'fail', 'fail_regex': 'STATION FAIL', 'threads': 2, 'peak_ram_gb': 4},
                    {'name': 'payload_bit_mutant', 'cmd': f'bash {bench} data_mutant_raw {mst} {wb} {{RUN}}/bench_d',
                     'expect': 'fail', 'fail_regex': 'STATION FAIL', 'threads': 2, 'peak_ram_gb': 4},
                ],
            },
        }
        if grown:
            spec['slot_change_request'] = {
                'reason': (f'recipe-2 content {AREA_BIT * wb + AREA_FIX:.0f} um2 exceeds util {UTIL_MAX} of the generator '
                           f'slot core {face_area(mac, horiz):.0f} um2; depth-only growth keeps every data pin coordinate'),
                'outline': [dw, dh], 'generator_slot': [mac['w'], mac['h']]}
        p = ROOT / SPEC_DIR / f'{name}.json'
        p.write_text(json.dumps(spec, indent=1) + '\n')
        summary.append((mst, wb, n, mac['w'], mac['h'], dw, dh, bool(grown), layers))
        if a.gen:
            r = subprocess.run([sys.executable, str(ROOT / 'tools/ref_tile/ref_tile.py'), 'gen', str(p)],
                               capture_output=True, text=True, cwd=ROOT)
            last = (r.stdout + r.stderr).strip().splitlines()[-1:] or ['']
            print(mst, 'gen rc', r.returncode, last[0][:200])
    for s in summary:
        print('%-18s W=%-5d n=%-4d slot %.3fx%.3f -> %.3fx%.3f %s %s' % (*s[:7], 'GROWN' if s[7] else '', s[8]))
    return 0


def face_area(mac, horiz):
    return (mac['w'] - 2 * MARGIN) * (mac['h'] - 2 * MARGIN)


if __name__ == '__main__':
    raise SystemExit(main())
