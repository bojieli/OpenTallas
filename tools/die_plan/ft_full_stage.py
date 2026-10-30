"""Opt-in complete existing normal-FT placement. Old bit_sites indexing is unchanged."""
import json
import math
from pathlib import Path


def validate(t, doc):
    if doc.get('schema') != 'opentallas.ft_full_stage.v1':
        raise ValueError('full-stage FT: unsupported schema')
    if doc.get('module') != t['module'] or doc.get('outline_um') != t['outline_um']:
        raise ValueError('full-stage FT: stale module/outline')
    slots = {s['name']: s for s in t.get('ft_slots', [])}
    names = set()
    if not doc.get('slots'):
        raise ValueError('full-stage FT: empty slots')
    for name, packet in doc['slots'].items():
        s = slots[name]
        for key in ('stations', 'width', 'in_face', 'out_face'):
            if packet[key] != s[key]:
                raise ValueError(f'full-stage FT {name}: stale {key}')
        if s.get('bit_sites_um'):
            raise ValueError('full-stage FT: conflicting old bit_sites_um')
        k, width = s['stations'], s['width'] + 1
        rows = packet['targets']
        expected = {(j, b) for j in range(k) for b in range(width)}
        if len(rows) != len(expected) or {(r['stage'], r['bit']) for r in rows} != expected:
            raise ValueError('full-stage FT: incomplete/duplicate stage-bit inventory')
        for r in rows:
            if r['name'] in names or not r['name'] or not r['master']:
                raise ValueError('full-stage FT: duplicate/missing actual cell identity')
            names.add(r['name'])
            for key in ('xy', 'size'):
                if len(r[key]) != 2 or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in r[key]):
                    raise ValueError('full-stage FT: invalid coordinates/size')
            x, y = r['xy']; w, h = r['size']
            if min(x, y) < 0 or min(w, h) <= 0 or x+w > t['outline_um'][0]+1e-6 or y+h > t['outline_um'][1]+1e-6:
                raise ValueError('full-stage FT: footprint outside outline')
        by = {(r['stage'], r['bit']): r for r in rows}
        for b in range(width):
            for j in range(k-1):
                a, z = by[j,b], by[j+1,b]
                distance = sum(abs(a['xy'][i]+a['size'][i]/2-z['xy'][i]-z['size'][i]/2) for i in (0,1))
                if distance > 405+1e-6:
                    raise ValueError('full-stage FT: internal hop exceeds 405um')
    return doc


def tq(value):
    # Tcl quoted word, preserving literal synthesized brackets/backslashes/$.
    return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"').replace('$', '\\$').replace('[', '\\[').replace(']', '\\]') + '"'


def install(t, plan_path, kd):
    pointer = t.get('ft_full_stage_placement_file')
    if not pointer:
        return
    p = Path(pointer)
    if not p.is_absolute():
        p = Path(plan_path).parent / p
    doc = validate(t, json.loads(p.read_text()))
    lines = ['set ff_full_slots {}', 'set ff_full_targets {}', 'set ff_full_outline [list ' + ' '.join(tq(v) for v in t['outline_um']) + ']']
    for slot, packet in doc['slots'].items():
        lines.append(f'dict set ff_full_slots {tq(slot)} {packet["stations"]}')
        for r in packet['targets']:
            values = [slot, r['stage'], r['bit'], r['name'], r['master'], *r['xy'], *r['size']]
            lines.append('lappend ff_full_targets [list ' + ' '.join(tq(v) for v in values) + ']')
    (kd/'ft_full_stage_data.tcl').write_text('\n'.join(lines)+'\n')
    (kd/'ft_full_stage.json').write_text(json.dumps(doc, indent=1)+'\n')
    (kd/'ft_full_stage.tcl').write_text(Path(__file__).with_suffix('.tcl').read_text())
    hook = kd/'face_flops.tcl'
    text = hook.read_text()
    text = text.replace('set ff_done {}', 'source /work/ft_full_stage_data.tcl\nset ff_done {}', 1)
    text = text.replace('set nm [$bt getName]', 'set nm [$bt getName]\n    if {[info exists ff_full_slots] && ([dict exists $ff_full_slots [ff_slot_of $nm _i]] || [dict exists $ff_full_slots [ff_slot_of $nm _o]])} continue', 1)
    text = text.replace('if {$slot eq ""} continue', 'if {$slot eq ""} continue\n  if {[info exists ff_full_slots] && [dict exists $ff_full_slots $slot]} continue', 1)
    hook.write_text(text+'\nsource /work/ft_full_stage.tcl\n')
    # These sites are already legal and obstacle-checked; subsequent DPL must preserve them.
    release = kd/'face_flops_release.tcl'
    release.write_text(release.read_text()+'\nsource /work/ft_full_stage.tcl\n')


def load(P, tn):
    """Validated exact rows indexed by slot and (stage, bit); absent opt-in is {}."""
    t = P.types[tn]
    pointer = t.get('ft_full_stage_placement_file')
    if not pointer:
        return {}
    p = Path(pointer)
    if not p.is_absolute():
        p = Path(getattr(P, 'path', None) or Path.cwd()/'plan.json').parent / p
    doc = validate(t, json.loads(p.read_text()))
    return {slot: {(r['stage'], r['bit']): r for r in packet['targets']}
            for slot, packet in doc['slots'].items()}


def centre(row):
    return tuple(row['xy'][i]+row['size'][i]/2 for i in (0,1))
