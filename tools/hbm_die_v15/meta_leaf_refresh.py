#!/usr/bin/env python3
"""Adopt source-bound routed IDX metadata pins into its sixteen existing leaf slots.

This updates the independent leaves only. It does not qualify scorer packing,
parent timing, relay homes or the die. No pin coordinate is scaled from an old view.
"""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MASTER = 'hidx_meta_w25_d123_r0'
LEF = f'physical/ref_tile/hidx_meta_static_1015c/views/{MASTER}/{MASTER}.lef'
SOURCE = 'rtl/hbm_accel/index/hidx_meta_w25_d123_r0.sv'
EXPECTED = {'clk', 'rst_n'} | {f'{n}[{i}]' for n in ('d', 'q') for i in range(25)}


def read_at(ref, name):
    return subprocess.check_output(['git', '-C', str(ROOT), 'show', f'{ref}:{name}'])


def routed_pins(raw):
    txt = raw.decode()
    size = re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)\s*;', txt)
    w, h = map(float, size.groups())
    if (w, h) != (68.04, 68.04):
        raise ValueError(f'expected actual 68.04-square successor, got {w} x {h}')
    pins = []
    for m in re.finditer(r'^  PIN (\S+)\n(.*?)^  END \1$', txt, re.M | re.S):
        name, body = m.groups()
        if name not in EXPECTED:
            continue
        shapes = re.findall(r'LAYER\s+(\w+)\s*;\s*RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*;', body)
        if len(shapes) != 1:
            raise ValueError(f'{name}: expected one physical pin rectangle, got {len(shapes)}')
        layer, *coords = shapes[0]
        x0, y0, x1, y1 = map(float, coords)
        face = 'S' if name.startswith('q[') else 'N'
        if layer != 'M5' or not (0 <= x0 < x1 <= w and 0 <= y0 < y1 <= h):
            raise ValueError(f'{name}: invalid M5 rectangle')
        if (face == 'N' and abs(y1 - h) > .001) or (face == 'S' and abs(y0) > .001):
            raise ValueError(f'{name}: routed rectangle does not touch assigned {face} face')
        pins.append(dict(name=name, face=face, layer=layer, offset=round((x0+x1)/2, 6),
                         span_um=[x0, x1], bbox_um=[x0,y0,x1,y1], offset_pending_view=False))
    if len(pins) != len(EXPECTED) or {p['name'] for p in pins} != EXPECTED:
        raise ValueError('view must contain every one of the exact 52 signal pins once')
    return pins


def apply(contract, raw, rtl, view_ref, source_ref):
    pins = routed_pins(raw)
    view_hashes = {n: hashlib.sha256(read_at(view_ref,str(Path(LEF).parent/n))).hexdigest()
        for n in (f'{MASTER}.lef',f'{MASTER}_tt.lib',f'{MASTER}_ff.lib','insertion.json')}
    parents = {s['name']: s for s in contract['slots']}
    leaves = [s for s in contract['slots'] if s.get('cell') == MASTER]
    if len(leaves) != 16:
        raise ValueError(f'expected sixteen existing metadata slots, got {len(leaves)}')
    for s in leaves:
        parent = parents[s['parent']]
        x, y = s['origin']['x'], s['origin']['y']
        if x < 0 or y < 0 or x+68.04 > parent['outline']['w'] or y+68.04 > parent['outline']['h']:
            raise ValueError(f'{s["name"]}: successor escapes parent outline')
        for other in contract['slots']:
            if other['name'] == s['name'] or other.get('parent') != s['parent']:
                continue
            ox, oy = other['origin']['x'], other['origin']['y']
            ow = 68.04 if other.get('cell') == MASTER else other['outline']['w']
            oh = 68.04 if other.get('cell') == MASTER else other['outline']['h']
            if x < ox+ow and ox < x+68.04 and y < oy+oh and oy < y+68.04:
                raise ValueError(f'{s["name"]}: overlaps {other["name"]}')
        s.update(outline=dict(w=68.04,h=68.04), pins=pins, source_sha256=hashlib.sha256(rtl).hexdigest(),
                 source_prerequisite=source_ref, assigned_pin_file=LEF,
                 assigned_pin_file_sha256=hashlib.sha256(raw).hexdigest(), assigned_pin_file_ref=view_ref,
                 pin_status='EXACT_ROUTED_68.04_LEF_IO; source-bound RF-delay successor',
                 measured_std_um2=2125, version=3,
                 reservation_basis='existing 216 um-spaced scorer footer slots; 68.04-square sibling and outline checks pass; full scorer packing remains OPEN',
                 qualification_scope='independent routed leaf only; complete source-exact scorer placement, registered seams, clock and die timing remain OPEN')
        clk = next(p for p in pins if p['name']=='clk')
        s['clock_entry'].update(face=clk['face'],layer=clk['layer'],offset=clk['offset'])
        s.pop('measured_ff', None)  # old 3,075-flop shift count is not the RF successor's count
        s['source_dependencies_sha256'] = {p: hashlib.sha256(read_at(source_ref,p)).hexdigest()
            for p in (SOURCE,'rtl/hdc/ot_hdc_delay_rf.sv','rtl/hdc/ot_hdc_delay.sv')}
        s['view_files_sha256'] = view_hashes
    contract['metadata_leaf_refresh_1319'] = dict(view_ref=view_ref, source_ref=source_ref, instances=16,
        old_outline_um=[51.84,51.84], new_outline_um=[68.04,68.04], added_area_mm2=round(16*(68.04**2-51.84**2)/1e6,9),
        added_cycles=0, parent_and_die_qualified=False)
    return contract


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--contract',type=Path,required=True)
    ap.add_argument('--view-ref',default='c61a97405')
    ap.add_argument('--source-ref',default='bed3d6968')
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args()
    c=apply(json.loads(a.contract.read_text()),read_at(a.view_ref,LEF),read_at(a.source_ref,SOURCE),a.view_ref,a.source_ref)
    a.out.write_text(json.dumps(c,indent=1)+'\n')
    print(json.dumps(c['metadata_leaf_refresh_1319']))


if __name__=='__main__': main()
