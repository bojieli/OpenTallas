#!/usr/bin/env python3
"""Read-only necessary-predicate audit. No routing, DRC or access-sufficiency claim.

Coordinates are integer nanometres. Refuted predicates concern the explicitly
named unextended/centred hypotheses; they do not prove the macro inaccessible.
"""
import argparse
from collections import Counter
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DIR = Path('results/uarch/w10_allport_necessary_access')
LEF = Path('physical/asap7_memory_macros/ot_rom_4096x274_m8/ot_rom_4096x274_m8.lef')
EXPECTED = {'clk', 'ce_in', *(f'addr_in[{i}]' for i in range(12)),
            *(f'rd_out[{i}]' for i in range(274))}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rects(text):
    return [tuple(int(Decimal(v)*1000) for v in m.split())
            for m in re.findall(r'RECT\s+([\d. -]+)\s*;', text)]


def parse_lef(text):
    size = re.search(r'SIZE ([\d.]+) BY ([\d.]+)', text)
    dims = tuple(int(Decimal(v)*1000) for v in size.groups())
    ports = {}
    for name, body in re.findall(r'\bPIN (\S+)\n(.*?)\n  END \1\n', text, re.S):
        if name in {'VDD', 'VSS'}:
            continue
        if name in ports:
            raise ValueError('duplicate port ' + name)
        if re.findall(r'LAYER (\S+) ;', body) != ['M4'] or len(rects(body)) != 1:
            raise ValueError('unsupported port geometry ' + name)
        ports[name] = rects(body)[0]
    if set(ports) != EXPECTED:
        raise ValueError('port census mismatch: ' + repr(EXPECTED ^ set(ports)))
    obs = re.search(r'\bOBS\n(.*?)\n  END\n', text, re.S)[1]
    obstruction = rects(re.search(r'LAYER M4 ;(.*)', obs, re.S)[1])
    return dims, ports, obstruction


def transform(rect, dims, macro):
    x1, y1, x2, y2 = rect
    w, h = dims
    orient = macro['orientation']
    if orient not in {'R0', 'MX', 'MY', 'R180'}:
        raise ValueError('unsupported orientation ' + orient)
    if orient in {'MY', 'R180'}:
        x1, x2 = w-x2, w-x1
    if orient in {'MX', 'R180'}:
        y1, y2 = h-y2, h-y1
    bx, by, ex, ey = macro['bbox_nm']
    if (ex-bx, ey-by) != dims:
        raise ValueError('macro dimensions mismatch')
    return (bx+x1, by+y1, bx+x2, by+y2)


def contained(a, b):
    return b[0] <= a[0] and b[1] <= a[1] and b[2] >= a[2] and b[3] >= a[3]


def gap(a, b):
    # Axis-separation (L-infinity) predicate only; advanced DRC not evaluated.
    return max(max(a[0]-b[2], b[0]-a[2], 0),
               max(a[1]-b[3], b[1]-a[3], 0))


def overlap(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def check(ok, **witness):
    return dict(classification='PROVABLE' if ok else 'REFUTED', witness=witness)


def missing(reason):
    return dict(classification='MISSING', witness=dict(reason=reason))


def read_inspection(text):
    if 'AUDIT|COMPLETE' not in text.splitlines():
        raise ValueError('incomplete database extraction: missing completion marker')
    pg, macros, via, tracks, rules = [], [], {}, {}, {}
    for line in text.splitlines():
        p = line.split('|')
        if p[0] != 'AUDIT':
            continue
        if p[1] == 'PG':
            pg.append(dict(net=p[2], layer=p[3], rect_nm=list(map(int, p[4].split())), kind=p[5]))
        elif p[1] == 'MACRO':
            macros.append(dict(name=p[2], orientation=p[3], bbox_nm=list(map(int, p[4].split()))))
        elif p[1] == 'VIABOX':
            if p[2] != 'VIA45':
                raise ValueError('unpriced alternative via')
            via[p[3]] = tuple(map(int, p[4].split()))
        elif p[1] == 'TRACK':
            grid = list(map(int, p[4].split()))
            tracks[p[2], p[3]] = (grid[0], grid[1]-grid[0])
        elif p[1] == 'RULE' and p[3] in {'getWidth', 'getSpacing', 'getArea'}:
            rules[p[2], p[3]] = int(p[4])
    if Counter(m['orientation'] for m in macros) != Counter(['R0', 'MX', 'MY', 'R180']):
        raise ValueError('four-orientation census mismatch')
    if set(via) != {'M4', 'M5', 'V4'} or not pg:
        raise ValueError('incomplete via/PDN extraction')
    if 'AUDIT|MISSING_PG_VIA' in text or 'AUDIT|MISSING|' in text:
        raise ValueError('incomplete database extraction; keep failed evidence')
    return macros, via, tracks, rules, pg


def audit(lef, inspection):
    dims, ports, obs = parse_lef(lef)
    macros, via, tracks, rules, pg = read_inspection(inspection)
    records = []
    for macro in macros:
        placed = {n: transform(r, dims, macro) for n, r in ports.items()}
        obstacles = [transform(r, dims, macro) for r in obs]
        for name, rect in placed.items():
            cx, cy = (rect[0]+rect[2])//2, (rect[1]+rect[3])//2
            origin, pitch = tracks['M4', 'Y']
            near = origin + round((cy-origin)/pitch)*pitch
            xorigin, xpitch = tracks['M5', 'X']
            near_x = xorigin + round((cx-xorigin)/xpitch)*xpitch
            landing = {l: tuple(v + (cx if i%2 == 0 else cy) for i, v in enumerate(r))
                       for l, r in via.items()}
            ontrack_cut = tuple(v + (near_x if i%2 == 0 else near) for i, v in enumerate(via['V4']))
            area = (rect[2]-rect[0])*(rect[3]-rect[1])
            neighbour, distance = min(((n, gap(rect, r)) for n, r in placed.items() if n != name), key=lambda v: v[1])
            checks = dict(
                M4_track_intersects_port=check(rect[1] <= near <= rect[3], track_y_nm=near, rect_nm=rect),
                M5_track_intersects_port=check(rect[0] <= near_x <= rect[2], track_x_nm=near_x, rect_nm=rect),
                centered_M5_on_track_diagnostic=check(cx == near_x, center_x_nm=cx, nearest_track_x_nm=near_x,
                    note='Off-track centred hypothetical landing is not an implemented escape'),
                M4_center_on_track_diagnostic=check(cy == near, center_y_nm=cy, nearest_track_y_nm=near,
                    note='Center alignment is diagnostic, not a necessary full-access condition'),
                unextended_port_contains_centered_VIA45_M4=check(contained(landing['M4'], rect),
                    port_nm=rect, landing_nm=landing['M4']),
                unextended_port_contains_nearest_M4_M5_track_V4_cut=check(contained(ontrack_cut, rect),
                    port_nm=rect, cut_nm=ontrack_cut, M4_y_nm=near, M5_x_nm=near_x,
                    note='Nearest-track landing hypothesis only; port-track intersection is not via containment'),
                unextended_port_contains_centered_V4_cut=check(contained(landing['V4'], rect),
                    port_nm=rect, cut_nm=landing['V4']),
                isolated_port_satisfies_M4_routing_minarea=check(area >= rules['M4', 'getArea'],
                    area_nm2=area, minimum_nm2=rules['M4', 'getArea'],
                    note='Routing-patch hypothesis; no assertion that an abstract macro port must itself meet routing area'),
                port_pair_base_M4_spacing=check(distance >= rules['M4', 'getSpacing'], neighbour=neighbour,
                    separation_nm=distance, required_nm=rules['M4', 'getSpacing']),
                centered_M4_landing_avoids_macro_OBS=check(not any(overlap(landing['M4'], r) for r in obstacles),
                    landing_nm=landing['M4'], obstacles_nm=obstacles),
            )
            for layer in ['M4', 'M5', 'V4']:
                boxes = [b for b in pg if b['layer'] == layer]
                collisions = [b for b in boxes if overlap(landing[layer], b['rect_nm'])]
                checks[f'centered_{layer}_landing_PDN_nonoverlap'] = check(not collisions,
                    landing_nm=landing[layer], collisions=collisions,
                    scope='Only archived GRT power geometry in all macro-edge +/-2um strips; no signal occupancy')
                if layer in {'M4', 'M5'}:
                    conflicts = [b for b in boxes if gap(landing[layer], b['rect_nm']) < rules[layer, 'getSpacing']]
                    checks[f'centered_{layer}_landing_PDN_base_spacing'] = check(not conflicts,
                        required_nm=rules[layer, 'getSpacing'], conflicts=conflicts,
                        landing_nm=landing[layer], scope='Base scalar rule only; EOL/PRL not discharged')
            for key, reason in {
                'cut_spacing_and_enclosure_rules': 'Advanced cut/enclosure fields and rule applicability not fully discharged; V4 scalar spacing=0 is not a waiver',
                'EOL_PRL_spacing': 'Actual advanced rule objects exist; no complete shape/context evaluator',
                'extended_escape_minarea': 'No proposed escape conductor or connected metal union',
                'simultaneous_escape_and_signal_occupancy': 'GRT checkpoint lacks final detailed signal geometry; macro OBS and PG checks are insufficient',
                'capture_mux_endpoint_capacity': 'No fixed endpoints or all-bank channel proof',
                'contextual_SS_FF_and_final_abstract': 'c8 terminal FAIL; final routed artifacts absent',
            }.items():
                checks[key] = missing(reason)
            records.append(dict(macro=macro['name'], orientation=macro['orientation'], port=name,
                rect_nm=rect, failed_c8_net_witness=name in {'rd_out[171]', 'rd_out[254]'} and macro['orientation'] == 'MX',
                constraints=checks))
    counts = {}
    for record in records:
        for k, v in record['constraints'].items():
            counts.setdefault(k, Counter())[v['classification']] += 1
    return dict(schema='opentallas.w10.allport.necessary_access.v1', verdict='BOUNDED_AUDIT_COMPLETE_FULL_ACCESS_PENDING',
        port_instances=len(records), ports_per_macro=len(ports), classifications=counts, records=records,
        full_DRC_proved=False, full_legal_access_proved=False, root_cause_proved=False,
        semantics='Refutations apply only to named hypotheses; no macro impossibility or access adoption inferred')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit((ROOT/LEF).read_text(), (ROOT/DIR/'inspection.log').read_text())
    # Re-evaluate the already-integrated audit against current generator without editing it.
    import uarch_model
    inputs = json.loads((ROOT/'results/uarch/w10_wake_pinaccess_contract_review/inputs.json').read_text())
    captured, _, _, _, _ = read_inspection((ROOT/DIR/'inspection.log').read_text())
    expected = [{k: m[k] for k in ['name', 'orientation', 'bbox_nm']} for m in inputs['geometry']['macros']]
    if captured != expected or sha(ROOT/LEF) != inputs['geometry']['macro_lef_sha256']:
        raise ValueError('00e9 model and actual macro interface disagree; reprice before build')
    current_wake = json.loads((ROOT/'results/uarch/w10_baseline_wake/fullgoal_bound.json').read_text())
    if current_wake['elements'] != inputs['wake']['elements']:
        raise ValueError('current wake capacity differs from 00e9; parent reprice required')
    composed = uarch_model.w10_pinaccess_contract_review(inputs)
    advanced = []
    for line in (ROOT/DIR/'rules.log').read_text().splitlines():
        parts = line.split('|')
        if len(parts) == 7 and parts[0:2] == ['FIELDS', 'VALUE']:
            # Persist numeric values only; SWIG object addresses carry no rule semantics.
            if re.fullmatch(r'-?\d+', parts[6]):
                advanced.append(dict(layer=parts[2], rule_family=parts[3], index=int(parts[4]),
                    field=parts[5], value_nm_or_flag=int(parts[6])))
    result['advanced_rule_evidence'] = dict(extracted_numeric_fields=advanced,
        missing='Other fields, class applicability and complete context evaluation remain missing; zeros are not global waivers')
    result['model_composition'] = {k: composed[k] for k in ['capacity', 'fully_additive_contingency']}
    result['model_composition']['scope'] = 'Existing 00e9 conditional reservations; no new geometry or latency adopted. Local fit and rule-complete escapes remain pending.'
    files = [LEF, Path(__file__).resolve().relative_to(ROOT), DIR/'inspect.tcl', DIR/'inspection.log',
             DIR/'rules.tcl', DIR/'rules.log', Path('tools/uarch_model.py'),
             Path('results/uarch/w10_wake_pinaccess_contract_review/inputs.json'),
             Path('results/uarch/w10_wake_pinaccess_contract_review/review.json'),
             Path('results/uarch/w10_baseline_wake/fullgoal_bound.json'),
             Path('tests/test_w10_allport_access_audit.py')]
    result['source_sha256'] = {str(p): sha(ROOT/p) for p in files}
    result['base_commit'] = '952c5eb3ba4c0968bf2331422368aa706474c83d'
    result['database'] = dict(path=inputs['geometry']['actual_global_route_database'],
        sha256=(ROOT/DIR/'database.sha256').read_text().split()[0], state='terminal failed c8 GRT, not final route',
        query_image='sha256:af971398d91e5d154ec40d3df26554efd8790107268a4c7f1e6bb8f222979d34')
    records = result.pop('records')
    # One line per port keeps the immutable witness ledger bounded and iterable.
    header = json.dumps(result, indent=2)[:-2]
    args.output.write_text(header + ',\n  "records": [\n' +
        ',\n'.join('    '+json.dumps(r, separators=(',', ':')) for r in records) + '\n  ]\n}\n')


if __name__ == '__main__':
    main()
