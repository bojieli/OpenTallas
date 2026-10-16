#!/usr/bin/env python3
"""Apply the die-owned DMA cluster layer/identity and universal calendar grants.

This allocates real candidate rectangles; it does not adopt a physical view or
claim complete VM hub packing, host programming, or native die qualification.
"""
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / 'results/arch/hier_contract_1015/hbm_v15.json'
HOST = ROOT / 'tools/hbm_die_v15/v16_specs/host_misc.json'
SOURCE_REF = '53ece5c68'


def overlap(a, b):
    return (a[0] < b[2] and b[0] < a[2] and
            a[1] < b[3] and b[1] < a[3])


def box(slot):
    p, o = slot['origin'], slot['outline']
    return (p['x'], p['y'], p['x'] + o['w'], p['y'] + o['h'])


def main():
    import sys
    sys.path.insert(0, str(ROOT / 'tools'))
    import hbm_die_views as views
    g = json.loads(CONTRACT.read_text())
    host = json.loads(HOST.read_text())
    plan = json.loads((ROOT / g['floorplan']['file']).read_text())
    slots = {s['name']: s for s in g['slots']}
    # Preserve every existing assigned DMA pin. Add the stack strap in the
    # E-face free margin. Grow away from the die centre for actual child halos.
    for qid, q in enumerate(('SW', 'SE', 'NW', 'NE')):
        s = slots['hb_dbk_' + q]
        previous_width = s['outline']['w']
        if q in ('SW', 'NW'):
            s['origin']['x'] = round(s['origin']['x'] - (511.92 - previous_width), 6)
        s['outline'] = dict(w=511.92, h=360.72)
        s.update(pg_layer='M7', strap_layer='M8', signal_max_layer='M6',
                 layer_cap='M6', params={},
                 identity_straps={'stk': qid},
                 grant='wires_only_cluster_v7_hardening_2330')
        s['pins'] = [p for p in s['pins'] if p['name'].split('[')[0] != 'stk']
        # The original consecutive bus packing has no gap after rst_n. Put
        # stk in the otherwise unused E-face margin instead of moving pins.
        lo = max(p['span_um'][1] for p in s['pins'] if p['face'] == 'E') + .192
        assert lo + .192 < s['outline']['h'] - 2
        s['pins'].append(dict(name='stk[1:0]', face='E', layer='M4',
                              span_um=[round(lo, 6), round(lo + .192, 6)],
                              offset=round(lo + .096, 6),
                              note='Registered compile-time stack identity; existing pins preserved.'))
        s['controller_binding_status'] = ('Registered stk port source 49705ce8a; '
            'one configured controller master required. Old STK0 view is historical '
            'and cannot qualify this new source or the parent.')
        s['parent_qualified'] = False
        for child in s.get('children', []):
            if child['inst'] == 'u_control':
                child['at'] = [347.76, 239.76]
                child['view'] = 'physical/ref_tile/hv15_dbk_vp4_ctl/views/ot_hgi_dma_back_static_vp4_controller'
                child['dedupe'] = 'One source/master; registered stk[1:0] identity. Fresh view required.'
            else:
                b = int(child['inst'].split('[')[1].split(']')[0]) if '[' in child['inst'] else int(child['inst'].split('u_bank')[1])
                child['at'] = [[23.76, 23.76], [185.76, 23.76], [347.76, 23.76],
                               [23.76, 131.76], [185.76, 131.76], [347.76, 131.76],
                               [23.76, 239.76], [185.76, 239.76]][b]
            cw, ch = (69.12, 69.12) if child['inst'] == 'u_control' else (140.4, 87.48)
            cx, cy = child['at']
            assert cx >= 20 and cy >= 20 and cx + cw + 20 <= 511.92 and cy + ch + 20 <= 360.72
        for other in g['slots']:
            if other['name'] != s['name'] and other.get('parent') == 'die' and other.get('origin') and other.get('outline'):
                assert not overlap(box(s), box(other)), (s['name'], other['name'])
    source = 'rtl/hbm_accel/generic/vm/static/hfd_hgi_vm_calendar.sv'
    raw = subprocess.check_output(['git', '-C', str(ROOT), 'show', SOURCE_REF + ':' + source])
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / 'calendar.sv'
        p.write_bytes(raw)
        ports = views.L.parse_module(str(p), 'hfd_hgi_vm_calendar')['ports']
    spec = json.loads(subprocess.check_output(['git', '-C', str(ROOT), 'show',
        SOURCE_REF + ':physical/ref_tile/hv15_vm_cal_u/spec.json']))
    calendars = []
    for q in ('SW', 'SE', 'NW', 'NE'):
        name = 'calendar_' + q
        reserved = plan['vmh_' + q]
        w, h = 220.32, 116.64
        # Dedicated lower-left home inside the existing VM-hub planning box;
        # other hub children are still unplaced and must fit around this home.
        x = reserved['x'] + 20
        blockers = [box(s) for s in g['slots'] if s['name'] != name
                    and s.get('parent') == 'die' and s.get('origin') and s.get('outline')]
        blockers += [(b['x'], b['y'], b['x'] + b['w'], b['y'] + b['h'])
                     for pn, b in plan.items() if isinstance(b, dict) and 'x' in b
                     and pn != 'vmh_' + q]
        y = reserved['y'] + 20
        while any(overlap((x, y, x + w, y + h), b) for b in blockers):
            y += 21.6
        candidate = dict(name=name, cell='hfd_hgi_vm_calendar', instance=name,
            source=source, source_prerequisite=SOURCE_REF, kind='tile', parent='die',
            version=7, grant='universal_calendar_candidate_2330',
            origin=dict(x=round(x, 6), y=round(y, 6), orient='R0'),
            outline=dict(w=w, h=h), pg_layer='M5', strap_layer='M6',
            signal_max_layer='M5', layer_cap='M5', params={},
            clock_entry=dict(port='clk', face='W', layer='M4'), pins=[],
            planning_group='vmh_' + q, qualified=False,
            notes='Source universal W187; compact candidate slot only (174.744x70.488 SRAM, '
                'at least20um edge channels, target51.9% total fill). Fresh view, host '
                'programming, complete hub packing, incident pin hops and native '
                'die timing remain OPEN. Universal output low slices are explicit in consumers.')
        assert x + w + 20 <= reserved['x'] + reserved['w']
        assert y + h + 20 <= reserved['y'] + reserved['h']
        for face, names in spec['pins'].items():
            extent = w if face in 'NS' else h
            total = sum(ports[n][1] for n in names)
            pitch = .096
            pos = round((extent - pitch * total) / 2 / .048) * .048
            for n in names:
                width = ports[n][1]
                candidate['pins'].append(dict(name=n if width == 1 else f'{n}[{width-1}:0]',
                    face=face, layer='M5' if face in 'NS' else 'M4',
                    span_um=[round(pos, 6), round(pos + width * pitch, 6)],
                    offset=round(pos + width * pitch / 2, 6)))
                pos += width * pitch
        for other in g['slots']:
            if other['name'] == name or not other.get('origin') or not other.get('outline'):
                continue
            if other.get('parent') == 'die':
                assert not overlap(box(candidate), box(other)), (name, other['name'])
        for pname, other in plan.items():
            if not isinstance(other, dict) or 'x' not in other or pname == 'vmh_' + q:
                continue
            pb = (other['x'], other['y'], other['x'] + other['w'], other['y'] + other['h'])
            assert not overlap(box(candidate), pb), (name, pname)
        slots[name] = candidate
        calendars.append(candidate)
    # Actual v16 generator consumes these static straps, rather than parameter
    # variants or case analysis. Keep unrelated logical straps unchanged.
    host['straps'] = [s for s in host.get('straps', [])
                      if not (s['inst'].startswith('hb_dbk_') and s['port'] == 'stk')]
    for qid, q in enumerate(('SW', 'SE', 'NW', 'NE')):
        host['straps'].append(dict(inst='hb_dbk_' + q, port='stk', lo=0, hi=2,
                                  value=qid, reason='Registered physical stack identity; no runtime selection.'))
    for instance in host['instances']:
        if instance['name'].startswith('hb_dbk_'):
            instance['params'] = {}
            instance['note'] = 'One vp4 bank-cluster master; registered stk strap and eight bank clock entries.'
        if instance['name'].startswith('calendar_'):
            instance.update(master='hfd_hgi_vm_calendar', source=source,
                            slot=instance['name'])
            instance['note'] = 'Universal W187 master; compiler --universal required; host-loader gap remains OPEN.'
    g['slots'] = list(slots.values())
    g['hardening_grants_2330'] = dict(source=SOURCE_REF, parent_qualified=False,
        dma='Four 511.92x360.72 homes: PG M7, signal cap M6, registered stk identity; '
            '23.76um width growth away from centre provides actual child edge channels.',
        calendars=[s['name'] for s in calendars],
        scope='Candidate slot and source binding only; no inherited view/native or full die qualification.')
    CONTRACT.write_text(json.dumps(g, indent=1) + '\n')
    HOST.write_text(json.dumps(host, indent=1) + '\n')
    print('PASS: four DMA identities, unchanged homes/pins, four nonoverlapping calendar candidate homes')


if __name__ == '__main__':
    main()
