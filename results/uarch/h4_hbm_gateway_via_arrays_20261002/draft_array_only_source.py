#!/usr/bin/env python3
"""Construct exact source PG arrays and macro clock escape pads in32SM context.

A successor to the existing gateway cut model. No installed PDN/CTS, electrical
power-current capacity, SS/FF closure or finite ownership timing is inferred.
"""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import re

BASE = Path(__file__).resolve().parents[1] / 'results/uarch/h4_hbm_gateway_via_arrays_20261002'
PIN = 'e5b3999bd2adf7bb2068783fc3f4f49a8ab462ebeb87e74750e0eabd12cc324f'

def canonical(x): return json.dumps(x, sort_keys=True, separators=(',', ':')).encode()
def sha(b): return hashlib.sha256(b).hexdigest()

def inputs():
    b = (BASE / 'input_manifest.json').read_bytes()
    if sha(b) != PIN: raise ValueError('manifest pin')
    out = {}
    for r in json.loads(b)['inputs']:
        p = (BASE / r['archive']).resolve()
        if not p.is_relative_to(BASE.resolve()): raise ValueError('archive origin')
        raw = p.read_bytes()
        if sha(raw) != r['sha256'] or len(raw) != r['bytes']: raise ValueError('source pin')
        out[p.name] = raw
    return out

def block(text, kind, name):
    return re.search(r'^' + kind + ' ' + name + r'\b(.*?)^END ' + name + r'\s*$', text, re.S | re.M)[1]

def array_rule(text, name, columns, rows, lower_width, upper_width):
    b = block(text, 'VIARULE', name)
    metals = re.findall(r'LAYER (M\d+)\s*;\s*ENCLOSURE ([.0-9]+) ([.0-9]+)', b)
    rect = list(map(float, re.search(r'RECT ([.0-9-]+) ([.0-9-]+) ([.0-9-]+) ([.0-9-]+)', b).groups()))
    pitch = list(map(float, re.search(r'SPACING ([.0-9]+) BY ([.0-9]+)', b).groups()))
    cut = re.search(r'LAYER (V\d+)', b)[1]
    cb = block(text, 'LAYER', cut)
    sp = re.search(r'^\s*SPACING ([.0-9]+)\s*;', cb, re.M)
    spacing = float(sp[1]) if sp else float(re.search(r'SPACINGTABLE\s+DEFAULT ([.0-9]+)', cb)[1])
    w, h = rect[2] - rect[0], rect[3] - rect[1]
    ext = [w + (columns - 1) * pitch[0], h + (rows - 1) * pitch[1]]
    metal = {}
    for layer, ex, ey in metals:
        metal[layer] = [round(ext[0] + 2 * float(ex), 6), round(ext[1] + 2 * float(ey), 6)]
    lower, upper = metals[0][0], metals[1][0]
    # M6/M8 horizontal; M7 vertical. Compare transverse metal widths.
    def transverse(layer, dims): return dims[1] if layer in ('M6', 'M8') else dims[0]
    envelope = [max(v[i] for v in metal.values()) for i in range(2)]
    ok = (columns > 0 and rows > 0 and min(pitch[0] - w, pitch[1] - h) + 1e-9 >= spacing
          and transverse(lower, metal[lower]) <= lower_width + 1e-9
          and transverse(upper, metal[upper]) <= upper_width + 1e-9
          and max(envelope) <= .544 + 1e-9)
    return dict(rule=name, lower=lower, upper=upper, cut_layer=cut, columns=columns, rows=rows,
                contacts=columns*rows, cut_size_um=[w, h], centre_pitch_um=pitch,
                edge_spacing_um=[round(pitch[0]-w,6), round(pitch[1]-h,6)],
                source_min_cut_spacing_um=spacing, metal_extent_um=metal,
                envelope_um=envelope, source_stripe_widths_um=[lower_width, upper_width],
                fits_existing_reserved_envelope=ok)

def clock_pads(text):
    result = {}
    for name in ('M4', 'M5', 'M6', 'M7'):
        b = block(text, 'LAYER', name)
        width = float(re.search(r'^\s*WIDTH ([.0-9]+)\s*;', b, re.M)[1])
        area = float(re.search(r'^\s*AREA ([.0-9]+)\s*;', b, re.M)[1])
        direction = re.search(r'DIRECTION (HORIZONTAL|VERTICAL)', b)[1]
        dims = [.128, width] if direction == 'HORIZONTAL' else [width, .128]
        result[name] = dict(width_um=width, length_um=.128, extent_um=dims,
                           source_min_area_um2=area, area_um2=math.prod(dims),
                           min_area_pass=math.prod(dims)+1e-12 >= area)
    return result

def overlap(a,b): return max(a[0],b[0]) < min(a[2],b[2]) and max(a[1],b[1]) < min(a[3],b[3])

def build():
    s=inputs();text=s['tech.lef'].decode();pdn=s['pdn.tcl'].decode()
    for token in ('-width {0.288} -spacing {0.096}', '-width {0.544} -spacing {0.096}', '-layers {M6 M7}', '-layers {M7 M8}'):
        if token not in pdn: raise ValueError('unchanged source PDN recipe')
    arrays=[array_rule(text,'M7_M6',7,3,.288,.544), array_rule(text,'M8_M7',7,7,.544,.544)]
    if not all(a['fits_existing_reserved_envelope'] for a in arrays): raise ValueError('PG array envelope FAIL')
    pads=clock_pads(text)
    if not all(p['min_area_pass'] for p in pads.values()): raise ValueError('clock pad min area FAIL')
    old=json.loads(gzip.decompress(s['constructor.json.gz']));models={}
    for name,ctx in old['models'].items():
        endpoints=[]
        for sm in ctx['clock_source_allocations']:
            all_e=sm['macro_clock_endpoints']
            bodies=[[h[0]+4,h[1]+4,h[2]-4,h[3]-4] for h in (e['source_halo_bbox_um'] for e in all_e)]
            for e in all_e:
                h=e['source_halo_bbox_um'];p=e['clock_pin_bbox_um'];driver=e['clock_driver_footprint_bbox_um']
                # Select the real left4um halo, not an unspecified pin-side
                # contact. Snap only the NEW contact centre to1nm source grid.
                cx=round(h[0]+3,3);cy=round(p[1],3)
                box=[cx-.064,cy-.064,cx+.064,cy+.064]
                via_conflicts=[i for i,b in enumerate(bodies) if overlap(box,b)]
                path=abs(driver[0]-cx)+abs(driver[1]+.135-cy)+abs(p[0]-cx)+abs(p[1]-cy)
                halo_fit=h[0]<=box[0] and box[2]<=h[0]+4 and h[1]<=box[1] and box[3]<=h[3]
                endpoints.append(dict(SM=sm['SM'],macro=e['macro'],master=e['master'],
                    pin_bbox_um=p,clock_contact_centre_um=[cx,cy],contact_bbox_um=box,
                    default_via_stack=['VIA45','VIA56','VIA67'],pad_layers=['M4','M5','M6','M7'],
                    source_pin_escape_um=abs(p[0]-cx)+abs(p[1]-cy),
                    passive_clock_last_leg_with_escape_um=path,existing_SS_last_leg_limit_um=215,
                    source_macro_body_conflicts=via_conflicts,inside_existing4um_halo=halo_fit,
                    local_contact_fit=halo_fit and not via_conflicts and path<=215))
        cuts=ctx['distributed_gateway_and_bank_cuts']+[c['cut'] for c in ctx['L2_controller_slots']]
        if not all(c['via_envelope_um']==[.544,.544] and c['via_spacing_envelope_um']==.096 for c in cuts):
            raise ValueError('source cut envelope mismatch')
        models[name]=dict(SMs=32,macro_clock_contacts=endpoints,macro_contacts=len(endpoints),
            clock_single_contacts=3*len(endpoints),existing_cut_count=len(cuts),
            existing_cut_capacity_and_demand_unchanged=True,
            all_contact_geometry_fits=all(e['local_contact_fit'] for e in endpoints),
            maximum_passive_last_leg_with_escape_um=max(e['passive_clock_last_leg_with_escape_um'] for e in endpoints),
            selected_L2_capacities=[c['cut']['signal_capacity_tracks'] for c in ctx['L2_controller_slots']],
            full_reserved_die_mm2=ctx['full_reserved_die_mm2'],
            clock_SS_bounds_reused_without_relaxation=True)
    return dict(schema='HBM_SOURCE_PG_ARRAY_CLOCK_ESCAPE_V1',models=models,PG_array_rules=arrays,
        clock_pad_source_rules=pads,via_array_size_is_selected_not_auto_PDN_generator=True,
        PG_stripe_intersections_require_selected_arrays=True,PG_cut_exclusions_recharged=False,
        extra_signal_tracks=0,extra_clock_buffer_area=0,automatic_latency_delta=False,
        source_geometry_pass=all(m['all_contact_geometry_fits'] for m in models.values()),
        installed_PDN=False,actual_route_DRC=False,IR_EM_current_capacity=None,installed_CTS=False,
        whole_operator_intervals=None,physical_wait_bounds=None,hardware_admitted=False,engine_build_allowed=False,
        SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,
        remaining=['implement exact selected PG array constraints; unconstrained PDN auto arrays are not admitted',
                   'clock branch and source slew enforcement; balanced source clock/FF hold',
                   'actual matrix/L2 owner connection and cache reservation exclusion',
                   'finite production-port contender/ACK/consumer/reverse bounds and whole-program composition'])

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--verify',action='store_true');a=p.parse_args()
    raw=gzip.compress(canonical(build()),mtime=0)
    if a.verify:
        if a.out.read_bytes()!=raw: raise ValueError('byte exact replay')
    else: a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_bytes(raw)
    print('PASS source array/clock escape replay; hardware admission remains FAIL')
if __name__=='__main__': main()
