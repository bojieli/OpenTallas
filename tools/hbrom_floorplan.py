#!/usr/bin/env python3
"""HBROM rectangular inventory and routing screen; never physical closure.

Consumes hbrom_model sweep (best) and its inputs. Physical dimensions absent
from inputs.physical_floorplan remain explicit blockers. --svg is opt-in.
"""
from __future__ import annotations
import argparse
import hashlib
import html
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROM = 'physical/asap7_memory_macros_v2/ot_rom_4096x274_m8/ot_rom_4096x274_m8.lef'
PHY = 'physical/asap7_memory_macros_v2/ot_hbm3e_phy_v41x_aw30/ot_hbm3e_phy_v41x_aw30.lef'


def lef(path):
    text = path.read_text()
    w, h = map(float, re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', text).groups())
    return dict(width=w, height=h, sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                obs_layers=re.findall(r'LAYER (\w+)', text.split('  OBS')[-1]))


def overlap(a, b):
    return a['x'] < b['x'] + b['w'] - 1e-7 and b['x'] < a['x'] + a['w'] - 1e-7 and a['y'] < b['y'] + b['h'] - 1e-7 and b['y'] < a['y'] + a['h'] - 1e-7


def check_rectangles(rectangles, die):
    errors = []
    names = set()
    active = []
    for r in sorted(rectangles, key=lambda z: z['x']):
        if r['name'] in names:
            errors.append('duplicate instance: ' + r['name'])
        names.add(r['name'])
        if r['w'] <= 0 or r['h'] <= 0 or r['x'] < 0 or r['y'] < 0 or r['x'] + r['w'] > die[0] + 1e-7 or r['y'] + r['h'] > die[1] + 1e-7:
            errors.append('outside die or nonpositive: ' + r['name'])
        active = [a for a in active if a['x'] + a['w'] > r['x'] + 1e-7]
        for a in active:
            if overlap(a, r):
                errors.append('overlap: ' + a['name'] + ' / ' + r['name'])
        active.append(r)
    return errors


def derive(selected, inputs, root=ROOT):
    if 'best' in selected:
        selected = selected['best']
    if not selected:
        raise ValueError('no selected analytical model candidate')
    p = inputs.get('physical_floorplan', {})
    rom, phy = lef(root / ROM), lef(root / PHY)
    die = p.get('die_um', [25600, 31800])
    hub = p.get('hub_um', [8000, 5000])
    edge, gap, halo = p.get('edge_um', 200), p.get('cluster_gap_um', 40), p.get('macro_halo_um', 2)
    capture = p.get('capture_strip_um', 8.64)
    nphy = p.get('hbm_phy_count', 4)
    if nphy not in (0, 2, 4):
        raise ValueError('symmetric shoreline supports 0,2,4 PHYs')
    geom, cand = selected['geometry'], selected['candidate']
    nc, nt, pairs = geom['clusters_per_die'], cand['tiles_per_cluster'], cand['pairs_per_tile']
    if any(not isinstance(v, int) or isinstance(v, bool) or v <= 0 for v in (nc, nt, pairs)):
        raise ValueError('cluster/tile/pair counts must be positive integers')
    blockers = []
    compute = p.get('compute_tile_um')
    if compute is None:
        area = inputs['compute']['area_mm2'] * 1e6
        compute = [math.sqrt(area), math.sqrt(area)]
        blockers.append('compute tile shape is area-derived square, no hardened abstract')
    if 'hub_um' not in p:
        blockers.append('8x5mm hub is assumed reservation; full dedicated-unit inventory missing')
    if 'hbm_phy_count' not in p:
        blockers.append('four HBM PHYs assumed; selected topology inventory required')
    if not p.get('compute_tile_includes_sram_inventory', False):
        blockers.append('compute tile SRAM instance inventory not bound')
    if not p.get('hub_inventory_complete', False):
        blockers.append('hub HE/quantizer/attention/index/VM inventory incomplete')
    if nc % 4:
        blockers.append('selected cluster count not multiple of four; quadrant occupancy asymmetric')
    outputs = inputs['networks'][str(pairs)]['output_streams_per_tile']
    tracks = outputs * 274 + 12 + 8 + 3
    # M6 and M8 only; M1-M4 obstructed by macros. Source v41_floorplan_pack.
    tracks_per_um = .5 * ((1 - .672 / 4.32) / .064 + .75 / .080)
    escape = math.ceil(tracks / tracks_per_um / 2.16) * 2.16
    shore = phy['height'] + gap if nphy else 0
    qw = (die[0] - 2 * edge - hub[0]) / 2
    qh = (die[1] - 2 * edge - 2 * shore - hub[1]) / 2
    if min(qw, qh) <= 0:
        raise ValueError('hub and shoreline leave no quadrants')
    total_macros = pairs * 2 * nt
    options = []
    # Each tile has its own ROM block, local capture strips, escape, compute.
    for cols in range(1, min(256, pairs * 2) + 1):
        rows = math.ceil(pairs * 2 / cols)
        rw = cols * (rom['width'] + 2 * halo + capture)
        rh = rows * (rom['height'] + 2 * halo)
        tw = max(rw, compute[0])
        mux_h = inputs['networks'][str(pairs)]['area_mm2'] * 1e6 / tw
        th = rh + escape + compute[1] + mux_h
        # Tiles arranged vertically within a cluster; intentional explicit choice.
        cw, ch = tw + gap, nt * th + gap
        slots = math.floor(qw / cw) * math.floor(qh / ch)
        options.append((slots, -(cw * ch), cols, rows, cw, ch, tw, th, rw, rh))
    slots, _, cols, rows, cw, ch, tw, th, rw, rh = max(options)
    rects = []
    def add(name, kind, x, y, w, h, **kw):
        rects.append(dict(name=name, kind=kind, x=x, y=y, w=w, h=h, **kw))
    add('hub', 'hub_reservation', (die[0]-hub[0])/2, (die[1]-hub[1])/2, *hub)
    for i in range(nphy):
        x = edge if i % 2 == 0 else die[0]-edge-phy['width']
        y = edge if i < 2 else die[1]-edge-phy['height']
        add(f'phy_{i}', 'phy_macro', x, y, phy['width'], phy['height'], master=PHY)
    xorig = [edge, (die[0]+hub[0])/2]
    yorig = [edge+shore, (die[1]+hub[1])/2]
    placed = min(nc, slots * 4)
    if placed != nc:
        blockers.append(f'rectangular cluster capacity {slots*4} below selected {nc}')
    ncol = math.floor(qw / cw)
    for c in range(placed):
        quadrant, local = c % 4, c // 4
        x0 = xorig[quadrant%2] + (local % ncol) * cw
        y0 = yorig[quadrant//2] + (local // ncol) * ch
        for t in range(nt):
            yy = y0 + t * th
            prefix = f'cluster{c}/tile{t}'
            for b in range(pairs*2):
                xx = x0 + (b%cols)*(rom['width']+2*halo+capture)
                by = yy + (b//cols)*(rom['height']+2*halo)
                add(f'{prefix}/rom{b}', 'rom_macro', xx+halo, by+halo, rom['width'], rom['height'], master=ROM)
                add(f'{prefix}/capture{b}', 'capture_reservation', xx+2*halo+rom['width'], by, capture, rom['height']+2*halo)
            add(f'{prefix}/escape', 'pin_corridor', x0, yy+rh, tw, escape, tracks_needed=tracks, tracks_available=escape*tracks_per_um)
            add(f'{prefix}/compute_sram', 'compute_sram_reservation', x0, yy+rh+escape, *compute)
            add(f'{prefix}/mux', 'mux_reservation', x0, yy+rh+escape+compute[1], tw, inputs['networks'][str(pairs)]['area_mm2']*1e6/tw)
    errors = check_rectangles(rects, die)
    if die[0]>26000 or die[1]>33000 or die[0]*die[1]/1e6>815:
        errors.append('reticle/project envelope exceeded')
    required_rom = nc*total_macros
    inventory = {kind:sum(r['kind']==kind for r in rects) for kind in sorted({r['kind'] for r in rects})}
    if inventory.get('rom_macro',0) != required_rom:
        errors.append('ROM instance inventory incomplete')
    if compute[0]*compute[1] + 1e-6 < inputs['compute']['area_mm2']*1e6:
        errors.append('compute tile rectangle smaller than modeled area')
    capture_area = pairs*2*capture*(rom['height']+2*halo)/1e6
    if capture_area < inputs['macro'].get('capture_area_per_pair_mm2', 0)*pairs:
        errors.append('capture strip area below bare capture-flop area')
    blockers.extend(['capture CTS/enables/clock routing not placed','shared mux and clock-cell fit unmeasured','macro pin access/OBS track preflight not run','SS setup / FF hold / contextual route / PG not qualified'])
    return dict(schema='opentallas.hbrom.floorplan.v1', status='rectangular_screen_not_physical_closure',
                candidate=cand, die_um=die, hub_um=hub, quadrant_um=[qw,qh], cluster_um=[cw,ch],
                clusters_requested=nc, clusters_placed=placed, cluster_slots=slots*4,
                rom_columns_per_tile=cols, rom_rows_per_tile=rows, inventory=inventory,
                required_rom_instances=required_rom, rectangles=rects, geometric_errors=errors,
                geometric_fit=not errors and placed==nc, complete_inventory=False,
                qualification_blockers=blockers, qualified=False,
                source_pins={ROM:rom['sha256'], PHY:phy['sha256']},
                routing=dict(horizontal_layers=['M6','M8'], macro_obs=rom['obs_layers'],
                             tracks_needed=tracks, channel_um=escape, tracks_available=escape*tracks_per_um,
                             clock_shield_tracks=3, source='tools/v41_floorplan_pack.py'))


def svg(result):
    w,h=result['die_um']
    colors={'rom_macro':'#739ac5','capture_reservation':'#c79148','pin_corridor':'#ddd','compute_sram_reservation':'#78ab83','hub_reservation':'#ad8abe','phy_macro':'#ba6c6c','mux_reservation':'#dab471'}
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}">',f'<rect width="{w}" height="{h}" fill="white" stroke="black"/>']
    for r in result['rectangles']:
        out.append(f'<rect x="{r["x"]}" y="{r["y"]}" width="{r["w"]}" height="{r["h"]}" fill="{colors[r["kind"]]}"><title>{html.escape(r["name"])}</title></rect>')
    out.append('</svg>')
    return '\n'.join(out)+'\n'


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--model',type=Path,required=True);ap.add_argument('--inputs',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True);ap.add_argument('--svg',type=Path)
    a=ap.parse_args();r=derive(json.loads(a.model.read_text()),json.loads(a.inputs.read_text()))
    r['source_pins'].update({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (a.model,a.inputs,Path(__file__))})
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,indent=2)+'\n')
    if a.svg:
        a.svg.parent.mkdir(parents=True,exist_ok=True);a.svg.write_text(svg(r))

if __name__=='__main__': main()
