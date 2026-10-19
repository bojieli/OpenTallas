#!/usr/bin/env python3
"""Finite model audit only. No views, timings or routing are generated."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from check_s81_sc2_terminal_protection_1019 import covered, grow


def overlap(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def contains(a, b):
    return all(a[k] <= b[k] for k in (0, 1)) and all(a[k] >= b[k] for k in (2, 3))


def shifted(r, dx, dy):
    return [r[0]+dx, r[1]+dy, r[2]+dx, r[3]+dy]


def area_union(rects):
    xs = sorted({r[k] for r in rects for k in (0, 2)})
    area = 0
    for lo, hi in zip(xs, xs[1:]):
        intervals = sorted((r[1], r[3]) for r in rects if r[0] <= lo and r[2] >= hi)
        length = 0
        end = -10**12
        for a, b in intervals:
            length += max(0, b-max(a, end))
            end = max(end, b)
        area += (hi-lo)*length
    return area


def candidate(m, dy=-9, dx=-12):
    out = []
    for old in m['paths']:
        p = copy.deepcopy(old)
        for s in p['shapes']:
            s['rect_nm'] = shifted(s['rect_nm'], dx if s['layer']=='M5' else 0, dy)
            # M4 must still fully contain the shifted VIA45 enclosure.
            if s['layer']=='M4':
                for v in old['vias']:
                    if contains(next(t['rect_nm'] for t in old['shapes'] if t['role']==s['role']), v['m4_rect_nm']):
                        # Move the column end, including its exact enclosure;
                        # do not retain a needless old-column 12nm end stub.
                        if s['rect_nm'][0]==v['m4_rect_nm'][0]: s['rect_nm'][0] += dx
                        if s['rect_nm'][2]==v['m4_rect_nm'][2]: s['rect_nm'][2] += dx
        for v in p['vias']:
            v['center_nm'] = [v['center_nm'][0]+dx, v['center_nm'][1]+dy]
            for key in ('cut_rect_nm', 'm4_rect_nm', 'm5_rect_nm'):
                v[key] = shifted(v[key], dx, dy)
        p['retained_pads'] = [dict(layer='M4', rect_nm=[x-12,y-12,x+12,y+12], role=role)
                              for role,(x,y) in [('source_pad',old['preserved_anchor_nm']),('terminal_pad',old['terminal_nm'])]]
        out.append(p)
    return out


def audit(paths):
    errors = []
    counts = dict(paths=len(paths), connected=0, long_rectangles=0, vias=0, retained_pads=0)
    pad_overlap_heights = []
    min_patch_area = {'M4':10**12, 'M5':10**12}
    for p in paths:
        shapes = p['shapes'] + p['retained_pads']
        edges = {i:set() for i in range(len(shapes))}
        for i, a in enumerate(shapes):
            for j, b in enumerate(shapes):
                if a['layer']==b['layer'] and overlap(a['rect_nm'], b['rect_nm']):
                    edges[i].add(j)
        for s in p['shapes']:
            counts['long_rectangles'] += 1
            r = s['rect_nm']; phase = (r[1]+r[3])//2 if s['layer']=='M4' else (r[0]+r[2])//2
            if phase%48 != (3 if s['layer']=='M4' else 0):
                errors.append([p['pin'],'LONG_CENTER_PHASE',s['layer'],phase%48])
        for v in p['vias']:
            counts['vias'] += 1
            hits = []
            for layer,key in [('M4','m4_rect_nm'),('M5','m5_rect_nm')]:
                found = [i for i,s in enumerate(shapes) if s['layer']==layer and contains(s['rect_nm'],v[key])]
                if not found: errors.append([p['pin'],'VIA_ENCLOSURE',layer])
                hits += found
            for i in hits: edges[i].update(hits)
        reached = {0}; pending = [0]
        while pending:
            for j in edges[pending.pop()]-reached:
                reached.add(j); pending.append(j)
        if len(reached)==len(shapes): counts['connected'] += 1
        else: errors.append([p['pin'],'DISCONNECTED'])
        for pad in p['retained_pads']:
            counts['retained_pads'] += 1
            hits = [s['rect_nm'] for s in p['shapes'] if s['layer']=='M4' and overlap(s['rect_nm'],pad['rect_nm'])]
            if hits:
                pad_overlap_heights.append(max(min(r[3],pad['rect_nm'][3])-max(r[1],pad['rect_nm'][1]) for r in hits))
            else: errors.append([p['pin'],'PAD_DISCONNECTED'])
        # Each same-layer connected component must independently meet AREA.
        remaining = set(range(len(shapes)))
        while remaining:
            component = {next(iter(remaining))}; pending = list(component)
            while pending:
                i = pending.pop()
                for j in edges[i]-component:
                    if shapes[j]['layer']==shapes[i]['layer']:
                        component.add(j); pending.append(j)
            remaining -= component
            layer = shapes[next(iter(component))]['layer']
            area = area_union([shapes[i]['rect_nm'] for i in component])
            min_patch_area[layer] = min(min_patch_area[layer], area)
            if area < 2000: errors.append([p['pin'],'CONNECTED_MIN_AREA',layer,area])
    return dict(status='PASS' if not errors else 'FAIL', counts=counts, errors=errors,
                minimum_pad_overlap_height_nm=min(pad_overlap_heights,default=0),
                minimum_connected_patch_area_nm2=min_patch_area)


def scalar_screen(paths, m):
    shapes = [s for p in paths for s in p['shapes']+p['retained_pads']]
    minimum = dict(M4=10**12,M5=10**12,PG_M4=10**12)
    under_old_48 = []
    for i,s in enumerate(shapes):
        r=s['rect_nm']; layer=s['layer']
        for t in shapes[i+1:]:
            # Retained pads have no net member; recover identity below.
            if t.get('net')==s.get('net') or t['layer']!=layer: continue
            q=t['rect_nm']; gap=max(max(r[k]-q[k+2],q[k]-r[k+2],0) for k in (0,1))
            minimum[layer]=min(minimum[layer],gap)
            if gap<48 and len(under_old_48)<8: under_old_48.append([s.get('net'),t.get('net'),gap])
        for pg in m['pg_rectangles']:
            if pg['layer']!=layer: continue
            q=pg['rect_nm']; gap=max(max(r[k]-q[k+2],q[k]-r[k+2],0) for k in (0,1))
            minimum['PG_M4']=min(minimum['PG_M4'],gap)
    return dict(minimum_axis_gaps_nm=minimum,old_scalar48_underexamples=under_old_48,
                conclusion='Scalar gaps only; no native EOL/corner/union-width interpretation or DRC verdict.')


def obstruction_screen(paths,m):
    obs={layer:[o['rect_nm'] for o in m['proposed_obstruction_rectangles'] if o['layer']==layer] for layer in ('M4','M5')}
    errors=[]; enclosures=0; protected=0
    for p in paths:
        x,y=p['terminal_nm']; pin=[x-12,y-12,x+12,y+12]
        for s in p['shapes']:
            boxes=obs[s['layer']]
            if not covered(s['rect_nm'],boxes):
                if s['layer']!='M4' or not covered(s['rect_nm'],[grow(o,24) for o in boxes]+[grow(pin,24)]):
                    errors.append([p['pin'],'NECK_HALO'])
        for v in p['vias']:
            for layer,key in [('M4','m4_rect_nm'),('M5','m5_rect_nm')]:
                enclosures+=1
                if covered(v[key],obs[layer]):protected+=1
                else:errors.append([p['pin'],'VIA_OBS',layer])
    return dict(status='PASS' if not errors else 'FAIL',errors=errors,via_enclosures=enclosures,protected_enclosures=protected,
                scope='Existing abstract OBS plus native24nm spacing halo; conditional approach local union remains unqualified.')


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--root',required=True); a = ap.parse_args()
    root = Path(a.root); base = root/'results/rtl/s81_coll_wide_pitch_1019'
    model_path = base/'access_model/model.json'; m = json.loads(model_path.read_text())
    tech = base/'access_model/asap7_tech.lef'
    assert hashlib.sha256(tech.read_bytes()).hexdigest()=='7694bf4f8ef2f9745e4579f454788a0cf048e8605320f32d1d83ec540ed4ca41'
    paths = candidate(m); positive = audit(paths)
    for p in paths:
        for s in p['retained_pads']: s['net']=p['pin']
    scalar = scalar_screen(paths,m)
    obstruction=obstruction_screen(paths,m)
    assert obstruction['status']=='PASS'
    mutants = {'original_phase':audit(candidate(m,0,0)), 'lost_contact':audit(candidate(m,-33,-12))}
    assert positive['status']=='PASS' and positive['counts']['connected']==437
    assert all(x['status']=='FAIL' for x in mutants.values())
    width,height = m['outline_nm']
    transforms=[]
    for orientation,sx,sy in [('N',1,1),('FN',-1,1),('FS',1,-1),('S',-1,-1)]:
        # x'=origin_x+(x if sx=1 else W-x), likewise y.
        px = 0 if sx==1 else width%48
        py = 3 if sy==1 else (height-3)%48
        transforms.append(dict(orientation=orientation, required_origin_mod48_nm=[(-px)%48,(3-py)%48],
                               default_R0_parent_tracks_match_at_43p2_lattice=px==0 and py==3))
    report = dict(status='MODEL_ONLY_HOLD_NATIVE_UNION_AND_PARENT_APPLICABILITY',
        source_sha256={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [model_path,tech,Path(__file__)]},
        units=dict(database_units_per_micron=1000,manufacturing_grid_nm=1),
        long_center_phases_nm=dict(original_M4=12,original_M5=12,candidate_M4=3,candidate_M5=0,pitch=48),
        transform_convention='Origin is lower-left of oriented bounding box. LEF has implicit ORIGIN 0 0; SYMMETRY X Y. Actual DEF transforms must be bound separately.',
        conditional_transform_table=transforms, positive=positive, mutants=mutants,
        candidate_scalar_screen=scalar,
        candidate_obstruction_screen=obstruction,
        immutable=dict(outline_nm=m['outline_nm'],PG_rectangles=len(m['pg_rectangles']),source_contacts=437,outer_contacts=437,actual_generated_views_changed=False),
        qualifications=dict(native_rule_interpreter=False,parent_TRACKS_bound=False,parent_PG_escape=False,union_RECTONLY_WIDTHTABLE=False,Liberty_generation=False,FF_MIN_evidence=False),
        local_union=dict(overlap_nm=15,union_height_nm=33,notch_step_nm=9,warning='24nm primitive widths do not establish native union legality; 33nm bbox is not itself a justified WIDTHTABLE violation.'),
        next='Native interpreter/source applicability for local contact unions; exact transformed master placement and parent TRACKS/AP/PG before selecting corrected generation.')
    (base/'native_grid/audit.json').write_text(json.dumps(report,indent=2)+'\n')
    (base/'native_grid/candidate_paths.json').write_text(json.dumps(paths,separators=(',',':'))+'\n')
    print(json.dumps(dict(positive=positive,mutants={k:dict(status=v['status'],errors=len(v['errors'])) for k,v in mutants.items()},transforms=transforms)))


if __name__=='__main__': main()
