#!/usr/bin/env python3
"""Prepare isolated RECIP/ZH geometry patches; no CAD or canonical view changes."""
import argparse
import hashlib
import importlib.util
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]


def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def native_shapes(path):
    out = {}
    for m in re.finditer(r'^\s*PIN\s+(\S+)\s*\n(.*?)^\s*END\s+\1\s*$', path.read_text(), re.M | re.S):
        if re.search(r'USE\s+(POWER|GROUND)', m[2]):
            continue
        layers = set(re.findall(r'LAYER\s+(M\d+)\s*;', m[2]))
        assert len(layers) == 1
        out[m[1]] = (next(iter(layers)), [list(map(float, r)) for r in re.findall(r'RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s*;', m[2])])
    return out


def prepare(kit, out, leaf):
    kit, out = Path(kit), Path(out)
    out.mkdir(parents=True, exist_ok=False)
    core = json.loads((kit/'core.json').read_text())
    old = json.loads((kit/'pins.json').read_text())
    assert isinstance(old, list)
    w, h = (216., 138.24) if leaf == 'recip' else (151.2, 151.2)
    module = 'ot_qkh_recip_leaf' if leaf == 'recip' else 'ot_nhb_zh'
    assert core['module'] == module and len(old) == (69 if leaf == 'recip' else 338)
    die = re.search(r'^export DIE_AREA = (.*)$', (kit/'config.mk').read_text(), re.M)
    assert die and list(map(float, die[1].split())) == [0.,0.,w,h]
    ref = ROOT/'physical/ref_tile'/('qkh_recip_ref' if leaf == 'recip' else 'ot_nhb_zh_m5')/'views'/module/(module+'.lef')
    assert digest(ref) == core['native_pin_contract']['source_lef_sha256']
    native = native_shapes(ref)
    name = lambda p: p['bus'] if p['bit'] is None else f"{p['bus']}[{p['bit']}]"
    pins = [dict(name=name(p), layer=p['layer'], x=p['x'], y=p['y']) for p in old]
    assert set(native) == {p['name'] for p in pins}
    moved = []
    if leaf == 'zh':
        south = sorted((p for p in pins if p['y'] == 0), key=lambda p: p['x'])
        assert len(south) == 268
        for i, p in enumerate(south):
            before = p['x']
            p['x'] = round(.012 + .048*round((2.16+i*(w-4.32)/(len(south)-1)-.012)/.048), 6)
            moved.append(dict(pin=p['name'], old_x=before, new_x=p['x']))
        assert min(b['x']-a['x'] for a,b in zip(south,south[1:])) >= .527999
    spec = importlib.util.spec_from_file_location('q6_normal_backend', HERE/'gen_core_kit_kv.py')
    backend = importlib.util.module_from_spec(spec); spec.loader.exec_module(backend)
    backend.PIN_LEN_UM = .084  # exact native contract, process local
    io, rows = backend.io_tcl(pins, w, h, module)
    ordinary = re.findall(r'^place_pin.*$', io, re.M)
    prior = re.findall(r'^place_pin.*$', (kit/'io.tcl').read_text(), re.M)
    if leaf == 'recip':
        assert ordinary == prior, 'compact primary placement must stay exact'
    else:
        assert {s for s in ordinary if not re.search(r'-location \{[\d.]+ 0\.0420\}', s)} == {s for s in prior if not re.search(r'-location \{[\d.]+ 0\.0420\}', s)}, 'non-south pins must remain exact'
    boxes = {}; extra = ['set nb [ord::get_db_block]', 'set nu [[ord::get_db_tech] getDbUnitsPerMicron]']
    for p in pins:
        layer, rects = native[p['name']]
        assert layer == p['layer']
        along = p['x'] if layer == 'M5' else p['y']
        assert abs((along-.012)/.048-round((along-.012)/.048)) < 1e-6, 'native track phase must remain exact'
        a = rects[0]; oldcx, oldcy = (a[0]+a[2])/2, (a[1]+a[3])/2
        x, y = p['x'], p['y']
        cx = .042 if x == 0 else w-.042 if x == w else x
        cy = .042 if y == 0 else h-.042 if y == h else y
        dx, dy = cx-oldcx, cy-oldcy
        rs = [[round(v+(dx if i%2 == 0 else dy), 6) for i,v in enumerate(r)] for r in rects]
        for r in rs:
            assert 0 <= r[0] < r[2] <= w and 0 <= r[1] < r[3] <= h, (p['name'], r)
        for r in rs[1:]:
            assert max(rs[0][0],r[0]) < min(rs[0][2],r[2]) and max(rs[0][1],r[1]) < min(rs[0][3],r[3]), 'secondary access must retain overlap with its primary'
            coords = ' '.join('[expr {round('+str(v)+' * $nu)}]' for v in r)
            extra += ['set nt [$nb findBTerm {'+p['name']+'}]', 'if {$nt eq "NULL"} {error "native pin absent"}', 'set nr [list '+coords+']', 'set nh 0', 'foreach pp [$nt getBPins] {foreach bb [$pp getBoxes] {', 'if {[list [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax]] eq $nr && [[$bb getTechLayer] getName] eq {'+layer+'}} {set nh 1}', '}}', 'if {!$nh} {', 'set np [lindex [$nt getBPins] 0]', 'if {$np eq "NULL" || $np eq ""} {error "native primary pin absent"}', '$np setPlacementStatus FIRM', 'odb::dbBox_create $np [[ord::get_db_tech] findLayer {'+layer+'}] '+coords, '}']
        boxes[p['name']] = dict(layer=layer, rectangles=rs)
    (out/'io.tcl').write_text(io+'\n'.join(extra)+'\n')
    (out/'pins.json').write_text(json.dumps(rows,indent=2)+'\n')
    (out/'pins_plan.json').write_text(json.dumps(dict(pins=pins),indent=2)+'\n')
    (out/'actual_generated_shapes.json').write_text(json.dumps(boxes,indent=2)+'\n')
    report = dict(status='PREP_ONLY_NOT_A_RUNNABLE_KIT', leaf=leaf, outline_um=[w,h], macros=[], signals=len(pins), moved_south=moved, source_files={n:digest(kit/n) for n in ['io.tcl','pins.json','core.json','config.mk']}, native_lef_sha256=digest(ref), normal_generator_sha256=digest(HERE/'gen_core_kit_kv.py'), rtl_change=False, cycles_added=0, clock_reset_roles=core['boundary_role'], all_shapes_contained=True, all_secondary_shapes_preserved=True, all_secondary_shapes_overlap=True)
    (out/'geometry_patch.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--kit',required=True);p.add_argument('--out',required=True);p.add_argument('--leaf',choices=['recip','zh'],required=True)
    a=p.parse_args();r=prepare(a.kit,a.out,a.leaf);print(r['status'],a.leaf,r['signals'])
