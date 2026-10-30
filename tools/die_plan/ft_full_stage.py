"""Opt-in complete existing normal-FT placement. Old bit_sites indexing is unchanged."""
import json
import math
import re
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
    preserve = t.get('ft_full_stage_preserve_ff_families', False)
    if type(preserve) is not bool:
        raise ValueError('full-stage FT: preserve_ff_families must be boolean')
    pointer = t.get('ft_full_stage_placement_file')
    if not pointer:
        if preserve:
            raise ValueError('full-stage FT: family preservation needs complete native target packet')
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
    if preserve:
        install_family_preservation(doc, kd)



def install_family_preservation(doc, kd):
    """Exclude entire target FF families as NEW physical optimizer choices.

    Existing instances stay touchable. Library-wide scope also covers unrelated
    FFs of these same families in this TYPE; this is an explicit opt-in tradeoff.
    Both required x1 and x2 survive because neither is a new sizing candidate.
    """
    families = set()
    for packet in doc['slots'].values():
        for row in packet['targets']:
            m = row['master']
            if not re.fullmatch(r'DFF[A-Za-z0-9_]*x[0-9][A-Za-z0-9]*_ASAP7_75t_[RL]', m):
                raise ValueError(f'full-stage FT: unsupported sequential master family {m}')
            families.add(re.sub(r'x[0-9][0-9A-Za-z]*(_ASAP7_.*)$', r'x*\1', m))
    if not families:
        raise ValueError('full-stage FT: empty family inventory')
    hook = kd/'ft_family_preserve.tcl'
    hook.write_text('# Physical-process only; existing FFs remain touchable.\n'
                    'if {![info exists ::env(DONT_USE_CELLS)]} {set ::env(DONT_USE_CELLS) {}}\n' +
                    'foreach family [list ' + ' '.join(tq(x) for x in sorted(families)) + '] {\n'
                    '  if {$family ni $::env(DONT_USE_CELLS)} {lappend ::env(DONT_USE_CELLS) $family}\n'
                    '}\n'
                    'puts "OT_FT_FAMILY_PRESERVE physical new-master exclusions $::env(DONT_USE_CELLS)"\n')
    # Native ORFS calls PRE hook BEFORE set_dont_use in each fresh physical
    # process. The synthesis environment/config DONT_USE_CELLS is untouched.
    gpl = kd/'face_flops.tcl'
    gpl.write_text(gpl.read_text()+'\nsource /work/ft_family_preserve.tcl\n')
    config=kd/'config.mk';text=config.read_text()
    previous=re.findall(r'^export\s+PRE_RESIZE_TCL\s*=\s*(\S+)\s*$',text,re.M)
    assignments=re.findall(r'^export\s+PRE_RESIZE_TCL\s*[^\n]*',text,re.M)
    if len(assignments) != len(previous):
        raise ValueError('full-stage FT: unsupported PRE_RESIZE_TCL assignment; chain explicitly')
    if len(previous)>1 or (previous and not previous[0].startswith('/work/')):
        raise ValueError('full-stage FT: unsupported existing PRE_RESIZE_TCL; chain explicitly')
    resize=kd/'ft_family_pre_resize.tcl'
    resize.write_text((('source '+tq(previous[0])+'\n') if previous else '') +
                      'source /work/ft_family_preserve.tcl\n')
    text=re.sub(r'^export\s+PRE_RESIZE_TCL\s*=.*\n?', '',text,flags=re.M)
    config.write_text(text+'\nexport PRE_RESIZE_TCL = /work/ft_family_pre_resize.tcl\n')


def load(P, tn):
    """Validated exact rows indexed by slot and (stage, bit); absent opt-in is {}."""
    if P is None:  # Legacy standalone wire-terminal helper has no Plan.
        return {}
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


def lane_hops(P, lid):
    """Every bit, actual plan pin positions and exact full-stage centres.

    Unselected slots retain their documented legacy analytic estimates. This is
    a geometric lower bound, never a placed/route qualification receipt.
    """
    from die_hop_scan import type_tables, md
    import schema as S
    tabs = {}
    def table(part):
        tn = P.parts[part]['type']
        if tn not in tabs:
            tabs[tn] = type_tables(P, tn)
        return tabs[tn]
    def pin(pid, side, bit):
        endpoint = P.ports[pid][side]
        part = endpoint['part']
        if part == S.DIE_PART:
            return P.port_point(pid)
        return P.to_die(part, table(part)[0][endpoint['bus']][bit][:2])
    ports = P.lanes[lid]['ports']
    hops = []
    for bit in range(S.port_pins_count(P.ports[ports[0]])):
        previous = pin(ports[0], 'src', bit)
        distance = 0
        for part, slot, a, b in P.lane_crossings(lid):
            pa, pb = pin(a, 'dst', bit), pin(b, 'src', bit)
            distance += md(previous, pa)
            previous = pa
            for xy in table(part)[1][slot][bit]:
                point = P.to_die(part, xy)
                distance += md(previous, point)
                hops.append(distance)
                distance = 0
                previous = point
            distance += md(previous, pb)
            previous = pb
        distance += md(previous, pin(ports[-1], 'dst', bit))
        hops.append(distance)
    return hops
