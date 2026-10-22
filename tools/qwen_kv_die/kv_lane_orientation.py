#!/usr/bin/env python3
"""Adapt forwarded-lane placements to the actual closed LEF pin lattices.

A relay's MY cannot be inherited by a replacement whose M3 and M5 clock/
strap pins require incompatible X residues. Keep its Y sense and frame,
remove only an illegal X mirror, and report the changed pin geometry.
The real ot_mts placement and on-track assertions remain mandatory.
"""
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_macro_track_alignment as C


def origin_rules(m, orient):
    """Python counterpart of ot_mts::rule + site grid, including pin_track_shapes."""
    cons = {'x': (1, {0}), 'y': (1, {0})}
    for pin in m['pins']:
        if pin['use'] in ('POWER', 'GROUND'):
            continue
        shapes = []
        for layer, r in pin['rects']:
            if layer not in C.ASAP7_TRACKS_NM:
                continue
            axis = 'y' if C.ASAP7_LAYERS[layer][0] == 'H' else 'x'
            q = C.transform_rect(r, orient, m['W'], m['H'])
            along, across = ((q[2]-q[0], q[3]-q[1]) if axis == 'y' else (q[3]-q[1], q[2]-q[0]))
            shapes.append((layer, axis, q, along, across))
        preferred = [s for s in shapes if s[3] >= s[4]]
        if preferred:
            narrow = {l: min(s[4] for s in preferred if s[0] == l) for l in {s[0] for s in preferred}}
            shapes = [s for s in preferred if s[4] == narrow[s[0]]]
        for layer, axis, q, _, _ in shapes:
            period, tracks = C.track_residues(C.ASAP7_TRACKS_NM[layer], axis)
            lo, hi = (q[1], q[3]) if axis == 'y' else (q[0], q[2])
            legal = C.legal_origins([(lo, hi)], period, tracks, 'center')
            old_p, old_s = cons[axis]
            joint = math.lcm(old_p, period)
            cons[axis] = joint, {v for v in range(joint) if v % old_p in old_s and v % period in legal}
    return {axis: C.joint_grid(s, p, C.SITE_X_NM if axis == 'x' else C.ROW_Y_NM)
            for axis, (p, s) in cons.items()}


def adapt(place, replacements, macros):
    rules = {name: {o: origin_rules(m, o) for o in C.MIRROR_SET} for name, m in macros.items()}
    legal = lambda name, o: all(v['legal_origins_mod_joint_nm'] for v in rules[name][o].values())
    changes, seen = [], set()
    pattern = re.compile(r'^(ot_mts::place \[\$_blk findInst (\S+)\] \S+ \S+ )(R0|MX|MY|R180)(\s*)$')

    def replace(match):
        prefix, inst, old, suffix = match.groups()
        if inst not in replacements:
            return match[0]
        seen.add(inst)
        name = replacements[inst][0]
        if name not in macros:
            raise ValueError(f'{name}: missing closed LEF for orientation qualification')
        if legal(name, old):
            return match[0]
        new = {'MY': 'R0', 'R180': 'MX'}.get(old)
        if new is None or not legal(name, new):
            raise ValueError(f'{inst} {name}: no legal orientation preserving Y sense from {old}')
        changes.append(dict(instance=inst, master=name, before=old, after=new,
                            max_pin_x_displacement_um=macros[name]['W'] / 1000))
        return prefix + new + suffix

    updated = '\n'.join(pattern.sub(replace, line) for line in place.split('\n'))
    if set(replacements) != seen:
        raise ValueError(f'lane placement missing: {sorted(set(replacements) - seen)[:8]}')
    return updated, dict(schema='opentallas.kv_lane_orientation.v1', rules=rules, changes=changes,
                        qualified_instances=len(seen),
                        note='Actual pins change sides on adapted instances; downstream reach, route and STA must use these placements.')
