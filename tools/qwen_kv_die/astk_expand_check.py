#!/usr/bin/env python3
"""KVR-VIEWS 2026-10-19: frame-local proof of the production ASTK expansion (kv_expand --astk-static) without a die case.

Builds a minimal run directory holding ONE die module with the two ASTK frames (qkd_astk, qkd_astk_n) at the native
328.32-um envelope, every die port of the frame on its own die wire (widths from the BINDINGS convention against the
elaborated qkd_astk_strip_er_die), and runs kv_expand.main(--astk-static) on it: the same code path, leaf views, face-land
alias (OT_KV_FACE_LAND), placement plan and fail-closed connectivity checks (undriven child inputs, multiple drivers,
unbound parent inputs, overlaps, leaf outside frame) as the die prep.  Prints the per-frame counts and the leaf views bound.
Needs yosys (fleet).  Use while the die case itself cannot be built (relay placement owned by KVR-PLACE).

    OT_KV_STATIC_DIE=1 ... OT_KV_FACE_LAND=astk_rly_296 python3 tools/qwen_kv_die/astk_expand_check.py --out DIR
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tools' / 'qwen_kv_die'))
import kv_die as K  # noqa: E402
import kv_expand as E  # noqa: E402
import kv_astk_expand as A  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args(argv)
    K._set_geometry(True, reserve_native_astk=True)
    views, rtl, sub, alias = dict(E.VIEWS), dict(E.RTL), dict(E.SUBLEVELS), {}
    A.configure(K, views, rtl, sub, alias)
    leaf = {}
    for mod, vd in views.items():
        lef = ROOT / vd / f'{mod}.lef'
        if lef.exists():
            nm, blk, sz, ports = E.lef_macro(lef)
            for r in ports.values():
                r['w'] = 1 if r['bits'] == {None} else max(r['bits']) + 1
            leaf[nm] = dict(size=sz, ports=ports)
    b = K.BINDINGS['qkd_astk']
    E.SUBLEVELS.update(sub)
    J = E.elaborate(b['module'], b['file'], leaf, b.get('parameters'))
    rtl_w = {p: len(v['bits']) for p, v in J['ports'].items()}
    dpw = {dp: sum(rtl_w[rp] for rp in rps) for dp, rps in b['ports'].items()}
    fw, fh = 328.32, 4 * (K.ENG_H + K.GY) + 237.6
    case = a.out / 'case_kv'
    (a.out / 'libs').mkdir(parents=True, exist_ok=True)
    case.mkdir(parents=True, exist_ok=True)
    wires, insts, place = [], [], []
    for k, (mst, x) in enumerate((('qkd_astk', 0.0), ('qkd_astk_n', 400.0))):
        inst = f'astk_{k}'
        conns = []
        for dp, w in dpw.items():
            wn = f'n_{inst}_{dp}'
            wires.append(f'  wire [{w - 1}:0] {wn};' if w > 1 else f'  wire {wn};')
            conns.append(f'.{dp}({wn})')
        insts.append(f'  {mst} {inst} ({", ".join(conns)});')
        place.append(f'ot_mts::place [$_blk findInst {inst}] {x:.3f} 0.000 R0')
    (case / 'die.v').write_text('module astk_check_die ();\n' + '\n'.join(wires) + '\n' + '\n'.join(insts) + '\nendmodule\n')
    place.append('ot_mts::place [$_blk findInst anchor_keep] 0.000 0.000 R0   ;# harness anchor (kv_expand appends after the last kept place line)')
    (case / 'place.tcl').write_text('\n'.join(place) + '\n')
    lef = ''.join(f'MACRO {m}\n  CLASS BLOCK ;\n  SIZE {fw} BY {fh} ;\nEND {m}\n' for m in ('qkd_astk', 'qkd_astk_n'))
    (case / 'elements.lef').write_text(lef + 'END LIBRARY\n')
    (a.out / 'libs' / 'views.json').write_text(json.dumps(dict(views={}, bound=[])) + '\n')
    rc = E.main(['--run', str(a.out), '--astk-static', '--only', 'qkd_astk,qkd_astk_n'])
    rep = json.loads((a.out / 'expand.json').read_text())
    dv = (case / 'die.v').read_text()
    out = dict(schema='opentallas.qwen_kv.astk_expand_check.v1', rc=rc, frame_um=[fw, fh],
               face_land=sorted(getattr(__import__('kv_static_die'), 'FACE_LAND_SEL', ())),
               frames={k: dict(instances=v['instances'], leaves=v['leaves_per_instance'], tie_pin_bits=v['tie_pin_bits'],
                               checks=v['connectivity_checks'], open_parent_inputs=v['open_parent_inputs'],
                               rtl_ports_without_die_port=v['rtl_ports_without_die_port']) for k, v in rep['frames'].items()},
               leaves=rep['leaves'], fl_instances=dv.count('qkd_astk_rly_296_fl '),
               plain_rly_instances=dv.count('  qkd_astk_rly_296 '), view_readiness=A.require_views(ROOT))
    (a.out / 'astk_expand_check.json').write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps({k: out[k] for k in ('rc', 'face_land', 'frames', 'fl_instances', 'plain_rly_instances')}))
    return rc


if __name__ == '__main__':
    sys.exit(main())
