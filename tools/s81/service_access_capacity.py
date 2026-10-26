#!/usr/bin/env python3
"""Whole-column canonical alternative exposing a real SW service-access spine.

Preserves every root/pair/type/packed child identity. Actual generator stations,
clock/reset, aggregate cuts and native routing remain to be constructed.
"""
import argparse,copy,hashlib,json
from pathlib import Path

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--input',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--shift',type=float,default=64.8);a=ap.parse_args()
 base=json.loads(a.input.read_text());p=copy.deepcopy(base)
 assert p['pair_count']==2417 and p['bf_pairs']==519 and p['root_count']==128
 cols=sorted(p['columns'],key=lambda q:q['x_um']);col=cols[10];before=col['x_um'];dx=a.shift
 selected=[f for f in p['placements'] if abs(f['origin_um'][0]-before)<1e-6]
 assert len(selected)==col['roots']==6
 col['x_um']=round(before+dx,6)
 for f in selected:f['origin_um'][0]=col['x_um']
 width=selected[0]['outline_um'][0];x0=round(cols[9]['x_um']+width,6);x1=col['x_um']
 p['service_access_corridors']=[dict(name='SW_service_access',rect_um=[x0,20.,x1,24604.],between_columns=[9,10])]
 p['status']='COARSE_FULL2417_SERVICE_SPINE_CANDIDATE_NOT_NATIVE'
 p['changes'].append(f'Translate entire physical W innercolumn10 +{dx}um, preserving6typedframes and everypair/root; expose{x1-x0:.3f}um actualgap for q/a/ix/co service routing')
 p['service_access_provenance']=dict(source_capacity_sha256=hashlib.sha256(a.input.read_bytes()).hexdigest(),generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),moved_roots=[f['root'] for f in selected],translation_um=[dx,0],old_gap_um=8.64,new_gap_um=round(x1-x0,6),service_return_station_um=[54.84,17.256],station_side_clearance_if_centered_um=round((x1-x0-54.84)/2,6),q514_a1026_combined_bits=1540,
   isolated_a1026_cut_diagnostic=1026/((x1-x0)*31.510416666666668),isolated_q514_plus_a1026_cut_diagnostic=1540/((x1-x0)*31.510416666666668),all_q_a_ix_co_bits=2568,all_q_a_ix_co_cut_diagnostic=2568/((x1-x0)*31.510416666666668),
   warning='These are necessary wire-count screens only. All q/a/ix/co traffic must share actual routing windows with clock/reset/control and real PG/obstructions; full generator occupancy, native pin reach and aggregate cuts remain required. Narrow73.44um comparison fails q+a combined0.60; broad155.52um carries declared2568bits at0.524 before extra traffic.')
 def overlap(a,b):return a[0]<b[0]+b[2]-1e-6 and a[0]+a[2]>b[0]+1e-6 and a[1]<b[1]+b[3]-1e-6 and a[1]+a[3]>b[1]+1e-6
 boxes=[(f['root'],[*f['origin_um'],*f['outline_um']]) for f in p['placements']]
 obstacles=[(q[0],[q[1],q[2],q[3],q[4]]) for q in p['hard_fixed_boxes']]+[(h['name'],[*h['at_um'],h['outline']['w'],h['outline']['h']]) for h in p['hcp_homes']]
 collisions=[(i,j) for i,b in boxes for j,c in obstacles if overlap(b,c)]
 collisions.extend((i,j) for k,(i,b) in enumerate(boxes) for j,c in boxes[k+1:] if overlap(b,c))
 assert not collisions,collisions
 assert all(b[0]>=20 and b[1]>=20 and b[0]+b[2]<=32980 and b[1]+b[3]<=25980 for _,b in boxes)
 p['service_access_provenance']['coarse_collisions']=collisions
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(p,indent=1)+'\n');print(json.dumps(p['service_access_provenance']))
if __name__=='__main__':main()
