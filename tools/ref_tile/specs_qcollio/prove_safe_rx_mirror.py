#!/usr/bin/env python3
"""Exact immutable-view proof for the scoped 24-nm RX mirror origin waiver."""
import hashlib
import json
import sys
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools'))
import check_macro_track_alignment as C

def shape_access(m,x):
    result={}
    for p in m['pins']:
        kind='PG' if p['use'] in ('POWER','GROUND') else 'CLOCK' if p['name'] in ('wck','rck') else 'SIGNAL'
        r=result.setdefault(kind,dict(shapes=0,inaccessible=0,pins=0))
        r['pins']+=1
        for layer,rect in p['rects']:
            if layer not in C.ASAP7_TRACKS_NM:continue
            q=C.transform_rect(rect,'MY',m['W'],m['H'])
            axis='y' if C.ASAP7_LAYERS[layer][0]=='H' else 'x'
            low,high=(q[1]+302400,q[3]+302400) if axis=='y' else (q[0]+x,q[2]+x)
            period,tracks=C.track_residues(C.ASAP7_TRACKS_NM[layer],axis)
            # Access uses a full-width routing track, not a point on an edge.
            half=C.ASAP7_LAYERS[layer][1]/2
            fits=any(low+half<=t+n*period<=high-half
                     for t in tracks for n in range(int(low//period)-1,int(high//period)+2))
            r['shapes']+=1;r['inaccessible']+=not fits
    return result

def main():
    leaf=ROOT/'physical/ref_tile/qfd_static_ch546/views/qfd_static_ch546/qfd_static_ch546.lef'
    baseline='17ac09ab3'
    checked={}
    for path in [leaf,ROOT/'rtl/physical/ot_qfd_static_transport.sv']:
        rel=str(path.relative_to(ROOT))
        old=subprocess.check_output(['git','show',baseline+':'+rel],cwd=ROOT)
        assert old==path.read_bytes(),rel+' changed'
        checked[rel]=hashlib.sha256(old).hexdigest()
    m=C.parse_lef(leaf.read_text())[0]
    floor=json.loads((ROOT/'physical/ref_tile/qfd_coll_face_s1_safe/floorplan.json').read_text())
    r=dict(schema='opentallas.safe_collective.rx_mirror_track_waiver.v1',
           authority='ROOT scoped candidate acceptance, 2026-10-19; final visual/DRC/native approval pending',
           baseline_commit=baseline,unchanged_sha256=checked,child_view_unchanged=True,child_rtl_unchanged=True,lef=str(leaf.relative_to(ROOT)),
           lef_sha256=hashlib.sha256(leaf.read_bytes()).hexdigest(),
           transform='MY: (x,y)->(W-x,y); then translate by actual origin',
           nominal_origin_um=[129.6,302.4],actual_origin_um=[129.624,302.4],waiver_delta_nm=[24,0],
           nominal=C.check_placement(m,'MY',129600,302400),
           actual=C.check_placement(m,'MY',129624,302400),
           nominal_shape_access=shape_access(m,129600),actual_shape_access=shape_access(m,129624),
           all_other_origins_on_43_2=all(all(abs(b[k]/43.2-round(b[k]/43.2))<1e-8 for k in ('x','y'))
                  for b in floor['blocks'] if b['inst']!='*u_rx'))
    assert r['all_other_origins_on_43_2']
    assert sum(v['offtrack'] for v in r['nominal']['layers'].values())>0
    assert sum(v['offtrack'] for v in r['actual']['layers'].values())==0
    assert all(v['inaccessible']==0 for v in r['actual_shape_access'].values())
    r['verdict']='PASS_TRACK_PROOF_ONLY'
    dest=ROOT/'results/rtl/qwen_coll_safe_1019/rx_mirror_track_proof.json'
    dest.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(r,indent=2))

if __name__=='__main__':main()
