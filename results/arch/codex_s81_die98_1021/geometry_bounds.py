#!/usr/bin/env python3
"""Source-sized lower bounds; not a placement, capacity receipt, or release adoption."""
import argparse, hashlib, json
from pathlib import Path
ap=argparse.ArgumentParser()
ap.add_argument('--frrst',type=Path,required=True)
ap.add_argument('--slice',type=Path,required=True)
ap.add_argument('--end',type=Path,required=True)
a=ap.parse_args()
def spec(path):
    b=path.read_bytes(); d=json.loads(b)
    return dict(path=str(path),sha256=hashlib.sha256(b).hexdigest(),top=d['top'],outline=d['outline'],children=len(d.get('children',[])))
h9=spec(a.frrst/'s81frame_col_h9_rf3rl/spec.json')
h10=spec(a.frrst/'s81frame_col_h10_rf3rl/spec.json')
sl=spec(a.slice); en=spec(a.end)
fw=h9['outline']['w']; sh=sl['outline']['h']; ew=en['outline']['w']
assert fw==h10['outline']['w']
body=5*h9['outline']['h']+2*h10['outline']['h']
def width(n): return 840+n*(fw+8.7)+6*(sl['outline']['w']+50)+2*(ew+50)
out=dict(scope='GEOMETRY LOWER BOUNDS ONLY; no route, source bind, capacity or release adoption',
         sources=dict(h9=h9,h10=h10,slice=sl,end=en),reticle_legal_die_um=[32000,25000],margin_um=500,
         capacity_inventory=dict(plan_sha256='6c1d6d930c6b9d44850946e08862476f8cc9bd3c8dd0d24f3e216d375d75fd2f',
           frame98_sorted_names_sha256='653badb6086c78fbb905d0c1d5c5df75d996ec28037b12cb228748a197a2fc0e',
           frame_columns=14,h9_per_column=5,h10_per_column=2,frames=98),
         current98_stack=dict(body_height_um=body,two_ring_streets_um=760,top_allowance_um=250,
           minimum_height_before_south_band_um=body+760+250,width_with_actual_end_um=round(width(14),3),
           verdict='FAIL conventional stack under actual selected outlines'),
         current84_inventory=dict(frame_columns=12,frames_per_column=7,frames=84,
           minimum_height_before_south_band_um=body+760+250,verdict='same vertical failure; not a six-row vehicle'),
         lower_count_comparison=dict(frames=72,frame_columns=12,frames_per_column=6,
           assumed_h9_per_column=5,assumed_h10_per_column=1,
           frame_and_street_height_plus_1700_band_and_250_top_um=5*h9['outline']['h']+h10['outline']['h']+760+1700+250,
           width_with_actual_end_um=round(width(12),3),
           verdict='CONDITIONAL arithmetic only; actual inventory, service placement, relay channels, source capacity and calendar UNPROVEN; NOT ADOPTED'),
         preserve98_options=[
           'Repack actual frame hard children and MU endpoints; new outlines require synthesis/physical closure and reset/clock qualification.',
           'Redistribute retained frames into slice-column voids with complete hard-child rectangles and relay channels; preserve logical inventory and arithmetic, reprice actual paths.'
         ],
         other_holds=['GU_PROP consumer-qualified source differs from running exact capacity source; transport/calendar unresolved.',
           'MU end parent embeds old 1252.8x5702.4 slice stand-in; selected normal slice is taller. Its own outline is not final.',
           'Actual 98 stage-map and source bind not qualified; no release chain launched on impossible geometry.'])
print(json.dumps(out,indent=2))
