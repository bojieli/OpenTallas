#!/usr/bin/env python3
"""S81 FILL-S2 (2026-10-15): ref_tile kits for not-started S81 die masters from the CURRENT die case (top-down).

Inputs: the die generator's case pin LEF (outline + every pin, GEN19b construction_pass2 on EPYC4
/srv/opentallas-scratch/claude/s81-die-r10/gen19b) and the master's real RTL (no stubs).  Per master this writes
  physical/s81_die_pins/fill2_gen19b/<master>.tcl   place_pin of every pin (the die tools' assignment for this unclosed master)
  tools/ref_tile/specs_s81_fill2/<name>.json         the ref_tile spec (recipe 2), exact bench + failing mutant
Shared fixes (owner rules / FILL-S verdict 10:00, 10:20):
  * outline = the generator slot snapped UP to the 2.16-um lattice (full-length M5 PG stripes, child_lint (b));
  * EVEN pin spread: each face's pins keep their generator ORDER but are spaced uniformly over the face (track-snapped,
    0.012 + 0.048 k), so no face exceeds the 12 b/um/layer pin-density limit the generator's 0.048-pitch packing broke;
    face cut = pins / face tracks reported (must be <= 0.6);
  * clock pin at its face centre (reset beside it), no output hold pads (outhold false), recipe-2 input hold + pin flops.
The die must adopt the spread coordinates (top-down rule: die tools assign pins of unclosed masters); the tcl is that
assignment.

  fill2_kits.py --lef P.lef.gz [--only NAME,..] [--gen]
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PIN_DIR = "physical/s81_die_pins/fill2_gen19b"
SPEC_DIR = "tools/ref_tile/specs_s81_fill2"
CASE = "GEN19b construction_pass2 (EPYC4 s81-die-r10/gen19b, pins.lef)"
EDGE = 2.16            # keep pins off the corner (core margin)
TRK0, TRK = 0.012, 0.048

BENCH = "tools/s81/fill2_cfg7_bench.sh"
CFG7_SRC = ["rtl/v41die/ot_s81_cfg7_seq.sv"]
CFG7_EXTRA = ["rtl/v41die", "physical/dsrom_qx10_parent_context/parent_loader",
              "physical/asap7_memory_macros_v2/ot_rom_4096x72_m8", "tools/s81/fill2_cfg7_bench.sh", PIN_DIR]

MASTERS = {
    "s81fill2_cfg7_seq": dict(
        master="ot_s81_cfg7_seq", top="ot_s81_cfg7_seq", params={"PQ": 1}, sources=CFG7_SRC, extra=CFG7_EXTRA,
        clock="clk", resets=["rst_n"], inst=1898,
        what="per-pair configuration sequencer (PQ 1 loader, as die.v.params.json binds it: the q element "
             "ot_v41_rom_elem_q_qxpq_w10 carries go_tag / sh_free / bank_free)",
        benches=[("lockstep_pq1", "pq1", "pass"), ("go_tag_mutant", "mut_tag", "fail")]),
    "s81fill2_cfg7_seq_bf": dict(
        master="ot_s81_cfg7_seq_bf", top="ot_s81_cfg7_seq_bf", params={}, sources=CFG7_SRC, extra=CFG7_EXTRA,
        clock="clk", resets=["rst_n"], inst=519,
        what="BF pair configuration sequencer (PQ 0 loader wrapper ot_s81_cfg7_seq_bf)",
        benches=[("lockstep_bf", "bf", "pass"), ("bank_select_mutant", "mut_bank_bf", "fail")]),
}


def lef_macro(lef: str, name: str) -> dict:
    m = re.search(r'^MACRO %s\n(.*?)^END %s' % (re.escape(name), re.escape(name)), lef, re.S | re.M)
    body = m.group(1)
    w, h = map(float, re.search(r'SIZE ([\d.]+) BY ([\d.]+)', body).groups())
    pins = []
    for pn, pb in re.findall(r'PIN (\S+)\n(.*?)END \1', body, re.S):
        r = re.search(r'LAYER (\S+)\s*;\s*RECT ([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+)', pb)
        x1, y1, x2, y2 = map(float, r.groups()[1:])
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        d = {'W': cx, 'E': w - cx, 'S': cy, 'N': h - cy}
        pins.append(dict(pin=pn, layer=r.group(1), x=cx, y=cy, face=min(d, key=d.get)))
    return dict(w=w, h=h, pins=pins)


def snap(v: float) -> float:
    return round(math.ceil(v / 2.16 - 1e-9) * 2.16, 3)


def trk(v: float) -> float:
    return round(TRK0 + TRK * round((v - TRK0) / TRK), 3)


def base(p: str) -> str:
    return re.sub(r'\[\d+\]$', '', p)


def spread(mac: dict, dw: float, dh: float, clock: str, resets: list):
    """per face: generator order kept, uniform pitch over [EDGE, L-EDGE]; clock (+resets) at the face centre"""
    faces = {}
    for p in mac['pins']:
        faces.setdefault(p['face'], []).append(p)
    out, rep = [], {}
    for f, ps in faces.items():
        along = (lambda p: p['x']) if f in 'NS' else (lambda p: p['y'])
        L = dw if f in 'NS' else dh
        ps = sorted(ps, key=along)
        ck = [p for p in ps if base(p['pin']) in [clock] + resets]
        data = [p for p in ps if p not in ck]
        n = len(data)
        pitch = (L - 2 * EDGE) / max(n, 1)
        coords = [trk(EDGE + pitch * (i + 0.5)) for i in range(n)]
        c = trk(L / 2)
        # the clock group sits at the centre: data pins within 0.2 um of it move off by one track pair
        cks = [trk(c + TRK * 2 * k) for k in range(len(ck))]
        taken = set(cks)
        for i, v in enumerate(coords):
            while any(abs(v - t) < 0.0955 for t in taken):
                v = trk(v + TRK * 2)
            coords[i] = v
            taken.add(v)
        assert len(set(coords + cks)) == n + len(ck), f
        tracks = int((L - 2 * EDGE) / TRK)
        rep[f] = dict(pins=n + len(ck), pitch_um=round(pitch, 4), b_per_um=round((n + len(ck)) / (L - 2 * EDGE), 2),
                      cut=round((n + len(ck)) / tracks, 3))
        for p, v in list(zip(data, coords)) + list(zip(ck, cks)):
            x, y = {'N': (v, dh), 'S': (v, 0.0), 'W': (0.0, v), 'E': (dw, v)}[f]
            out.append(dict(p, x=x, y=y))
    return out, rep


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--lef', required=True)
    ap.add_argument('--only')
    ap.add_argument('--owner', default='Claude:fill-s81-2')
    ap.add_argument('--branch', default='claude/el1015-fill-s2-1015')
    ap.add_argument('--tag', default='g1')
    ap.add_argument('--gen', action='store_true')
    a = ap.parse_args()
    lef = gzip.open(a.lef, 'rt').read() if a.lef.endswith('.gz') else Path(a.lef).read_text()
    (ROOT / PIN_DIR).mkdir(parents=True, exist_ok=True)
    (ROOT / SPEC_DIR).mkdir(parents=True, exist_ok=True)
    sel = set(a.only.split(',')) if a.only else set(MASTERS)
    for name, d in MASTERS.items():
        if name not in sel:
            continue
        mac = lef_macro(lef, d['master'])
        dw, dh = snap(mac['w']), snap(mac['h'])
        pins, rep = spread(mac, dw, dh, d['clock'], d['resets'])
        assert all(r['cut'] <= 0.6 for r in rep.values()), rep
        scalar = {base(p['pin']) for p in mac['pins'] if p['pin'].endswith('[0]')} - \
                 {base(p['pin']) for p in mac['pins'] if re.search(r'\[[1-9]\d*\]$', p['pin'])}
        tcl = [f'# {d["master"]} ({name}): pins of {CASE}, generator order kept per face, EVEN spread over the face '
               f'(track-snapped), clock {d["clock"]} at its face centre; outline {dw} x {dh} (generator slot '
               f'{mac["w"]} x {mac["h"]} snapped up to 2.16). Face report: {json.dumps(rep)}']
        faces = {}
        for p in sorted(pins, key=lambda p: (p['face'], p['pin'])):
            pname = base(p['pin']) if base(p['pin']) in scalar else p['pin']
            tcl.append(f'place_pin -pin_name {{{pname}}} -layer {p["layer"]} -location {{{p["x"]:.3f} {p["y"]:.3f}}} '
                       f'-force_to_die_boundary')
            faces.setdefault(p['face'], set()).add(base(p['pin']))
        (ROOT / PIN_DIR / f'{d["master"]}.tcl').write_text('\n'.join(tcl) + '\n')
        benches = [{'name': bn, 'cmd': f'bash {BENCH} {mode} {{RUN}}/bench_{mode}', 'expect': exp,
                    **({'pass_regex': f'CFG7 BENCH PASS {mode}'} if exp == 'pass' else {'fail_regex': f'CFG7 BENCH FAIL {mode}'}),
                    'threads': 4, 'peak_ram_gb': 4, 'needs': ['verilator']} for bn, mode, exp in d['benches']]
        spec = {
            'name': name, 'top': d['top'], 'kind': 'tile', 'sources': d['sources'], 'params': d['params'],
            'clock_port': d['clock'], 'reset_ports': d['resets'],
            'outline': {'w': dw, 'h': dh, 'exact': True}, 'layer_cap': 'M5',
            'pins': {f: sorted(v) for f, v in sorted(faces.items())},
            'io_tcl': f'{PIN_DIR}/{d["master"]}.tcl', 'recipe': 2, 'outhold': False,
            'route': {'pd': 0.5, 'threads': 4, 'peak_ram_gb': 8, 'pin_h': 'M4', 'pin_v': 'M3 M5', 'm5_pg_pitch': 2.7},
            'structural_change': (f'First hardening of the S81 die master {d["master"]} ({d["inst"]} die instances, '
                                  f'{d["what"]}); real RTL {d["sources"][0]} (exact lockstep gate '
                                  f'rtl/v41die/test/tb_ot_s81_cfg7_seq.sv); 0 cycles; pins = {CASE} order with the '
                                  f'shared fixes: even per-face spread (generator packed W-face M4 pins at 0.048 um = '
                                  f'20.8 b/um/layer > 12), clock at face centre, no output hold pads; outline '
                                  f'{mac["w"]}x{mac["h"]} -> {dw}x{dh} (2.16 lattice). Face report {json.dumps(rep)}.'),
            'job': {'owner': a.owner, 'branch': a.branch, 'tag': a.tag,
                    'purpose': f'S81 FILL-S2: die master {d["master"]} ({d["inst"]} replicas, hardened once): exact '
                               f'lockstep bench + failing mutant; recipe 2, M5 cap, GEN19b pins evenly spread',
                    'views_to': f'physical/ref_tile/{name}/views', 'record_to': f'results/rtl/ref_tile/{name}',
                    'extra_paths': d['extra'], 'benches': benches},
        }
        p = ROOT / SPEC_DIR / f'{name}.json'
        p.write_text(json.dumps(spec, indent=1) + '\n')
        print(name, d['master'], f'{mac["w"]}x{mac["h"]} -> {dw}x{dh}', json.dumps(rep))
        if a.gen:
            r = subprocess.run([sys.executable, str(ROOT / 'tools/ref_tile/ref_tile.py'), 'gen', str(p)],
                               capture_output=True, text=True, cwd=ROOT)
            print(' gen rc', r.returncode, ((r.stdout + r.stderr).strip().splitlines() or [''])[-1][:300])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
