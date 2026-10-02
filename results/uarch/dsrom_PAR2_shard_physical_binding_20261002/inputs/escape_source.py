#!/usr/bin/env python3
"""Bounded source-backed escape hypotheses, without routing or full-DRC claims."""
import argparse
from collections import Counter
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import re
import w10_allport_access_audit as prior

ROOT = Path(__file__).resolve().parents[1]
OUT = Path('results/uarch/w10_connected_escape_prerequisite')


def nm(v):
    return int(Decimal(v)*1000)


def layer(text, name):
    return re.search(r'^LAYER '+name+r'\n(.*?)^END '+name+r'\s*$', text, re.M|re.S)[1]


def parse_rules(text):
    result = {}
    for name in ('M4', 'M5'):
        body = layer(text, name)
        eol = re.search(r'SPACING ([\d.]+) ENDOFLINE ([\d.]+) WITHIN ([\d.]+) ENDTOEND ([\d.]+)', body)
        widths = re.findall(r'WIDTH ([\d.]+)\s+([\d.]+)', body.split('DIRECTION')[0])
        if not eol or len(widths) != 2:
            raise ValueError('unsupported EOL/PRL grammar')
        result[name] = dict(width_nm=nm(re.search(r'\bWIDTH ([\d.]+) ;', body)[1]),
            area_nm2=int(Decimal(re.search(r'AREA ([\d.]+) ;', body)[1])*1000000),
            eol=dict(zip(['spacing_nm','width_threshold_nm','within_nm','endtoend_nm'], map(nm,eol.groups()))),
            prl_rows=[dict(width_nm=nm(w), spacing_nm=nm(s)) for w,s in widths],
            note='PRL length breakpoint zero; max wire width selects row. EOL narrow width condition <25nm includes 24nm.',
            other_properties=re.findall(r'PROPERTY (LEF58_\w+)',body))
    v4 = layer(text,'V4')
    table = re.search(r'PROPERTY LEF58_SPACINGTABLE "(.*?)"',v4,re.S)[1]
    if any(any(t != '-' for t in l.split()[1:]) for l in table.splitlines() if l.strip().startswith('Vx')):
        raise ValueError('unsupported explicit cut table override')
    result['V4'] = dict(default_edge_spacing_nm=nm(re.search(r'DEFAULT ([\d.]+)',table)[1]),
        classes={name:(nm(w),nm(h)) for name,w,h in re.findall(r'CUTCLASS (Vx\S*) WIDTH ([\d.]+) LENGTH ([\d.]+)',v4)},
        ordinary_enclosure_nm=[nm(v) for v in re.search(r'ENCLOSURE CUTCLASS Vx ([\d.]+) ([\d.]+)',v4).groups()],
        EOL_enclosure_source=re.search(r'ENCLOSURE CUTCLASS Vx EOL[^;]+;',v4)[0],
        scope='All class-pair entries inherit DEFAULT; edge based, no same-net/same-via exception in loaded rule flags')
    return result


def validate_source_rules(rules, log):
    if 'RULE|EXPORT_COMPLETE' not in log or 'RULE|COMPLETE' not in log:
        raise ValueError('incomplete loaded database rule export')
    for name in ('M4','M5'):
        for field, value in [('getEolSpace',24),('getEolWidth',25),('getEolWithin',40),('getEndToEndSpace',40)]:
            if f'RULE|FIELD|{name}|getTechLayerSpacingEolRules|0|{field}|{value}' not in log:
                raise ValueError('EOL source/loaded rule mismatch')
        if rules[name]['eol'] != dict(spacing_nm=24,width_threshold_nm=25,within_nm=40,endtoend_nm=40):
            raise ValueError('unsupported changed EOL policy')
    if rules['V4']['ordinary_enclosure_nm'] != [11,0] or 'RULE|FIELD|V4|getTechLayerCutEnclosureRules|0|getFirstOverhang|11' not in log:
        raise ValueError('ordinary enclosure source/loaded rule mismatch')
    if rules['V4']['default_edge_spacing_nm'] != 34 or 'RULE|FIELD|V4|getTechLayerCutSpacingTableDefRules|0|getDefault|34' not in log:
        raise ValueError('cut source/loaded rule mismatch')
    for flag in ['isSameNet','isSameMetal','isSameVia','isLayerValid','isCenterToCenterValid','isCenterAndEdgeValid','isPrlValid']:
        if f'RULE|FIELD|V4|getTechLayerCutSpacingTableDefRules|0|{flag}|0' not in log:
            raise ValueError('unsupported cut exception or metric')


def escape_shapes(ports, dims, macros, tracks, via, lanes=2, pad_length=84):
    shapes = []
    for m in macros:
        placed = {n:prior.transform(r,dims,m) for n,r in ports.items()}
        for side in ('left','right'):
            group = sorted([(n,r) for n,r in placed.items() if (r[0] < (m['bbox_nm'][0]+m['bbox_nm'][2])/2)==(side=='left')],key=lambda v:v[1][1])
            for index,(name,pin) in enumerate(group):
                cx,cy = (pin[0]+pin[2])//2,(pin[1]+pin[3])//2
                yo,yp = tracks['M4','Y']; xo,xp=tracks['M5','X']
                y=yo+round((cy-yo)/yp)*yp
                # Fixed predeclared hypothesis, no iterative coordinate search.
                distance=96+(index%lanes)*96
                if side=='left':
                    x=xo+math.floor((pin[0]-distance-xo)/xp)*xp
                    metal4=(x-23,y-12,pin[2],y+12)
                else:
                    x=xo+math.ceil((pin[2]+distance-xo)/xp)*xp
                    metal4=(pin[0],y-12,x+23,y+12)
                metal5=(x-12,y-pad_length//2,x+12,y+pad_length//2)
                cut=(x-12,y-12,x+12,y+12)
                landings={l:tuple(v+(x if i%2==0 else y) for i,v in enumerate(r)) for l,r in via.items()}
                shapes.append(dict(macro=m['name'],orientation=m['orientation'],port=name,side=side,
                    pin_nm=pin,via_center_nm=[x,y],rects={'M4':metal4,'M5':metal5,'V4':cut},via_landings=landings,
                    macro_bbox_nm=m['bbox_nm']))
    return shapes


def width(rect):
    return min(rect[2]-rect[0],rect[3]-rect[1])


def prl_spacing(a,b,rules):
    w=max(width(a),width(b))
    return max(r['spacing_nm'] for r in rules['prl_rows'] if w>=r['width_nm'])


def evaluate(lef,inspection,tech,rule_log,lanes=2,pad_length=84):
    rules=parse_rules(tech); validate_source_rules(rules,rule_log)
    dims,ports,obs=prior.parse_lef(lef)
    macros,via,tracks,_,pg=prior.read_inspection(inspection)
    shapes=escape_shapes(ports,dims,macros,tracks,via,lanes,pad_length)
    pg_by={l:[p for p in pg if p['layer']==l] for l in ('M4','M5','V4')}
    records=[]
    for i,s in enumerate(shapes):
        checks={}
        checks['pin_connected_positive_overlap']=prior.check(prior.overlap(s['pin_nm'],s['rects']['M4']),pin_nm=s['pin_nm'],patch_nm=s['rects']['M4'])
        for l in ('M4','M5'):
            r=s['rects'][l]; area=(r[2]-r[0])*(r[3]-r[1])
            cut=s['rects']['V4']
            side=min(cut[0]-r[0],r[2]-cut[2]); end=min(cut[1]-r[1],r[3]-cut[3])
            first,second=rules['V4']['ordinary_enclosure_nm']
            ordinary_ok=(end>=first and side>=second) or (end>=second and side>=first)
            checks[l+'_ordinary_Vx_enclosure_overhang']=prior.check(ordinary_ok,side_nm=side,end_nm=end,
                required_nm=[first,second],scope='Exact-build ordinary class Vx rule: either axis ordering, both above and below; EOL collection excluded')
            checks[l+'_patch_area']=prior.check(area>=rules[l]['area_nm2'],area_nm2=area,required_nm2=rules[l]['area_nm2'])
            checks[l+'_VIA45_landing_containment']=prior.check(prior.contained(s['via_landings'][l],r),landing_nm=s['via_landings'][l],metal_nm=r,
                scope='ordinary Vx enclosure satisfied by containing actual default via landing; EOL-specific enclosure remains separate')
        obstacles=[prior.transform(r,dims,next(m for m in macros if m['name']==s['macro'])) for r in obs]
        checks['M4_macro_OBS_nonoverlap']=prior.check(not any(prior.overlap(s['rects']['M4'],r) for r in obstacles),obstacles_nm=obstacles)
        for l in ('M4','M5','V4'):
            r=s['rects'][l]
            conflicts=[]; missing_classes=[]
            peers=[dict(rect_nm=o['rects'][l],peer=o['macro']+':'+o['port'],kind='escape') for j,o in enumerate(shapes) if j!=i]
            peers += [dict(p,peer='PG:'+p['net']) for p in pg_by[l]]
            for p in peers:
                other=p['rect_nm']; gap=prior.gap(r,other)
                if l=='V4':
                    size=tuple(sorted((other[2]-other[0],other[3]-other[1])))
                    if size not in {tuple(sorted(v)) for v in rules['V4']['classes'].values()}:
                        missing_classes.append(p); continue
                    requirement=rules['V4']['default_edge_spacing_nm']
                else:
                    # Sufficient envelope for scalar/PRL and all EOL spacings;
                    # a refuted envelope alone does not prove an actual DRC violation.
                    requirement=max(prl_spacing(r,other,rules[l]),rules[l]['eol']['endtoend_nm'])
                if gap < requirement:
                    conflicts.append(dict(peer=p['peer'],rect_nm=other,gap_nm=gap,required_bound_nm=requirement,
                        overlap=prior.overlap(r,other)))
            checks[l+'_peer_PDN_spacing_bound']=prior.check(not conflicts,conflicts=conflicts,
                rule='V4 default edge spacing' if l=='V4' else 'max(PRL-width-selected spacing, EOL end-to-end), sufficient envelope',
                scope='All proposed patches plus surveyed archived PG; no detailed signal occupation')
            if missing_classes:
                checks['V4_PG_cut_class_applicability']=prior.missing('Unmapped cut dimensions: '+repr(missing_classes[:4]))
            if l!='V4':
                checks[l+'_EOL_width_applicability']=prior.check(width(r)<rules[l]['eol']['width_threshold_nm'],
                    end_width_nm=width(r),threshold_nm=rules[l]['eol']['width_threshold_nm'],
                    scope='Simple route rectangles; pin-connected union corner semantics separate')
        checks['patch_pin_union_rectangle_diagnostic']=prior.check(prior.contained(s['pin_nm'],s['rects']['M4']) or prior.contained(s['rects']['M4'],s['pin_nm']),
            pin_nm=s['pin_nm'],patch_nm=s['rects']['M4'],scope='Geometric union shape only; rule applicability to fixed macro pin remains unresolved')
        checks['Vx_EOL_enclosure_applicability']=prior.missing('Exact-build checker trace selects non-EOL collections by default; EOL collection and width0 clause remain separate. Full physical EOL-specific applicability to connected union is not discharged by the ordinary trace.')
        checks['pin_union_corner_keepout_rectonly']=prior.missing('Connected patch/pin union has partial overlap at mirrored pins; RECTONLY, corner spacing and EOL keepout on macro ports require explicit applicability proof, not an exemption assumption.')
        checks['detailed_signal_endpoints_SS_FF']=prior.missing('No final routed signal geometry, fixed capture/mux assignment, or contextual SS/FF abstract; no build authorized.')
        records.append(dict(**s,constraints=checks))
    counts={}
    for r in records:
        for k,v in r['constraints'].items(): counts.setdefault(k,Counter())[v['classification']]+=1
    return dict(schema='opentallas.w10.connected_escape.prerequisite.v1',
        verdict='BOUNDED_HYPOTHESIS_AUDIT_FULL_LEGAL_INTERFACE_PENDING',rules=rules,classifications=counts,
        hypothesis=dict(lanes=lanes,lane_spacing_nm=96,minimum_outward_distance_nm=96,M5_pad_length_nm=pad_length,
            no_search_or_tuning=True,interpretation='Fixed analytical witnesses, not a routed candidate or immutable placement recipe'),
        records=records,full_legal_access_proved=False,full_DRC_proved=False,adopted=False)


def main():
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    paths=[prior.LEF,prior.DIR/'inspection.log',OUT/'actual_db.lef',OUT/'applicable_rules.log']
    result=evaluate(*( (ROOT/p).read_text() for p in paths))
    old=json.loads((ROOT/prior.DIR/'audit.json').read_text())
    result['existing_model_costs']=old['model_composition']
    result['pricing_scope']=dict(no_generator_or_headline_change=True,local_added_cycles=0,
        two_lane_outward_envelope_max_nm=max(max(s['macro_bbox_nm'][0]-s['rects']['M4'][0],s['rects']['M4'][2]-s['macro_bbox_nm'][2]) for s in result['records']),
        prior_edge_reserve_nm=13824,
        warning='Geometry subset of reserved strip does not prove spare contiguous tracks or endpoint reach; no additional modeled clock gain.')
    result['source_checker_trace'] = json.loads((ROOT/OUT/'router_source_witnesses.json').read_text())
    paths += [OUT/'router_source_lookup.json',OUT/'router_source_files.json',OUT/'router_source_witnesses.json',OUT/'applicable_rules.tcl',OUT/'export_rules.tcl',OUT/'export_rules.log',OUT/'image_reference_tech.lef',
        Path('tools/w10_connected_escape_audit.py'),Path('tests/test_w10_connected_escape_audit.py'),
        Path('tools/uarch_model.py'),prior.DIR/'audit.json',prior.DIR/'database.sha256']
    result['source_sha256']={str(p):prior.sha(ROOT/p) for p in paths}
    result['base_commit']='8b0837058'
    records=result.pop('records'); header=json.dumps(result,indent=2)[:-2]
    a.output.write_text(header+',\n  "records": [\n'+',\n'.join('    '+json.dumps(r,separators=(',',':')) for r in records)+'\n  ]\n}\n')


if __name__=='__main__': main()
