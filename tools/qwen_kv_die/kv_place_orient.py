#!/usr/bin/env python3
"""KV-GEN8 10-19: qualify EVERY die placement orientation against the actual LEF pin lattice before the real case.

GEN7 (kvs14r-4db097403-codexmub) and every kvs14r MU real case since 10-19 08:00 (219049242-mu, 99e646e98-mu,
0f1b1ed67-mu) died in PLACE after ~18 min: 'ot_mts: qkd_astk_ep_s MY x has no legal origin on this track grid'.
The expanded ASTK strip of the east stacks (ES/EN) is X-mirrored, so kv_expand composes MY onto its closed leaves.
qkd_astk_ep_s carries its 1,304-bit zi face bus on BOTH vertical layers (652 pins M3 at x%36==9, 652 pins M5 at
x%48==12).  Under an X mirror a pin centre c becomes W - c, so an origin O must satisfy O + W == 18 (mod 36) and
O + W == 24 (mod 48): 18 != 24 (mod 12) -- no origin exists for ANY outline width.  No X-mirrored placement of a
view with on-track M3 AND M5 pins is legal on the ASAP7 track set; only that master's pins can change it.

kv_lane_orientation.adapt already does the correct, reported thing for forwarded-lane relays (keep the Y sense and
the frame, drop only an illegal X mirror: MY -> R0, R180 -> MX).  This pass applies the SAME rule to every
`ot_mts::place` line whose master's closed LEF is in case_kv/elements.lef, so the illegality is caught in prep
(seconds), not 18 min into the real case.  It runs right after kv_expand, before rst_regional / rly_std / fwd_lanes
stations + the reach gate, so every downstream geometry check and the real case use the adapted orientations.
Every change is reported (instance, master, before, after, worst pin x displacement = macro width); nothing else
moves.  A placement with no legal orientation at all FAILS (exit 1).  Masters without a LEF block are left alone
(ot_mts remains the authority).  Structural successor owned separately: an ep_s re-pin with the zi bus on ONE
vertical layer (M5 only: O = 54k, k = 4 mod 8 is legal under MY) removes the adaptation.

  kv_place_orient.py --case RUN/case_kv [--report RUN/case_kv/place_orientations.json] [--check-only]
"""
import argparse
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_macro_track_alignment as C  # noqa: E402
from kv_lane_orientation import origin_rules  # noqa: E402

PLACE = re.compile(r'^(ot_mts::place \[\$_blk findInst (\S+)\] \S+ \S+ )(R0|MX|MY|R180)(\s*)$')
INST = re.compile(r'^\s*([A-Za-z_]\w*)\s+(?:#\s*\(.*?\)\s*)?\\?([^\s(]+)\s*\(', re.S)
KEEP_Y = {'MY': 'R0', 'R180': 'MX', 'R0': 'MY', 'MX': 'R180'}


def masters_of(die_v_text, wanted):
    out = {}
    for line in die_v_text.split('\n'):
        m = INST.match(line)
        if m and m.group(2) in wanted:
            out[m.group(2)] = m.group(1)
    return out


def lef_blocks(lef_text, names):
    blocks = {}
    for n in names:
        m = re.search(rf'^MACRO {re.escape(n)}\s*$.*?^END {re.escape(n)}\s*$', lef_text, re.M | re.S)
        if m:
            blocks[n] = m.group(0)
    return blocks


def legal(rules):
    return all(v['legal_origins_mod_joint_nm'] for v in rules.values())


def adapt(place_text, inst_master, macros):
    """place_text: place.tcl; inst_master: instance -> master; macros: master -> parsed LEF macro."""
    cache, changes, refused, checked = {}, [], [], 0

    def ok(name, o):
        if (name, o) not in cache:
            cache[name, o] = legal(origin_rules(macros[name], o))
        return cache[name, o]

    def sub(mt):
        nonlocal checked
        prefix, inst, old, suffix = mt.groups()
        name = inst_master.get(inst)
        if name not in macros:
            return mt[0]
        checked += 1
        if ok(name, old):
            return mt[0]
        new = KEEP_Y[old]
        if not ok(name, new):
            refused.append(dict(instance=inst, master=name, orient=old))
            return mt[0]
        changes.append(dict(instance=inst, master=name, before=old, after=new,
                            max_pin_x_displacement_um=round(macros[name]['W'] / 1000, 3)))
        return prefix + new + suffix

    text = '\n'.join(PLACE.sub(sub, ln) for ln in place_text.split('\n'))
    per = {}
    for c in changes:
        k = f"{c['master']} {c['before']}->{c['after']}"
        per[k] = per.get(k, 0) + 1
    rep = dict(schema='opentallas.kv_place_orient.v1', checked=checked, changes=changes, refused=refused,
               per_master=per, verdict='FAIL' if refused else 'PASS',
               rule='keep Y sense and frame; drop only an X mirror the closed LEF pin lattice cannot take (as kv_lane_orientation)',
               note='Adapted instances have their pins on the opposite X face (<= macro width); reach/route/STA measure them.')
    return text, rep


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--case', required=True, type=Path)
    ap.add_argument('--report', type=Path)
    ap.add_argument('--check-only', action='store_true', help='report only; do not rewrite place.tcl')
    a = ap.parse_args(argv)
    case = a.case
    place = (case / 'place.tcl').read_text()
    insts = {m.group(2) for m in (PLACE.match(ln) for ln in place.split('\n')) if m and m.group(3) in ('MY', 'R180', 'R0', 'MX')}
    im = masters_of((case / 'die.v').read_text(), insts)
    lef = (case / 'elements.lef').read_text()
    blocks = lef_blocks(lef, set(im.values()))
    macros = {}
    for n, b in blocks.items():
        for m in C.parse_lef(b + '\n'):
            if m['name'] == n:
                macros[n] = m
    text, rep = adapt(place, im, macros)
    rep.update(case=str(case), instances_placed=len(insts), masters_with_lef=len(macros),
               masters_without_lef=sorted(set(im.values()) - set(macros))[:40])
    out = a.report or case / 'place_orientations.json'
    out.write_text(json.dumps(rep, indent=1) + '\n')
    if rep['changes'] and not a.check_only:
        if not (case / 'place.tcl.preorient').exists():
            shutil.copy(case / 'place.tcl', case / 'place.tcl.preorient')
        (case / 'place.tcl').write_text(text)
    print(f"KV_PLACE_ORIENT {rep['verdict']} checked {rep['checked']} changed {len(rep['changes'])} "
          f"refused {len(rep['refused'])} {rep['per_master']} -> {out}")
    return 1 if rep['refused'] else 0


if __name__ == '__main__':
    sys.exit(main())
