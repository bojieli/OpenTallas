#!/usr/bin/env python3
"""Place exact CLOSED SPR R0 bodies inside the existing HEAD reserves."""
import argparse,hashlib,importlib.util,json
from pathlib import Path

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--plan',required=True);ap.add_argument('--out',required=True);ap.add_argument('--checker',required=True);a=ap.parse_args()
 src=Path(a.plan);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
 view='physical/ref_tile/s81hd_spr_m4/views/ot_s81hd_spr';lef=Path(view)/'ot_s81hd_spr.lef'
 spec=importlib.util.spec_from_file_location('frozen_tracks',a.checker);C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C)
 m=C.parse_lef(lef.read_text())[0];assert m['W']==m['H']==216000
 p=json.loads(src.read_text());rows=[];windows={}
 for base in ['i','iw','ie','o']:
  rs=[r for pin in m['pins'] if pin['name'].startswith(base+'[') for _,r in pin['rects']]
  assert len(rs)==565,(base,len(rs))
  windows[base]=[min(r[0] for r in rs),min(r[1] for r in rs),max(r[2] for r in rs),max(r[3] for r in rs)]
 for bi,b in enumerate(p['blocks']):
  if b['master']!='ot_s81hd_spr':continue
  reserve=dict(b);assert b['orient'] in ['R0','MX'] and b['w']==216 and b['h']==648
  b['orient']='R0';p['facts']['instance_orientations'][b['name']]='R0'
  b['y']+=216;b['h']=216
  check=C.check_placement(m,'R0',round(b['x']*1000),round(b['y']*1000))
  assert all(v['offtrack']==0 for v in check['layers'].values()),check
  assert round(b['x']*1000)%C.SITE_X_NM==0 and round(b['y']*1000)%C.ROW_Y_NM==0
  for link in p['links']:
   for endpoint in link['e']:
    if endpoint[0]!=bi:continue
    r=windows[endpoint[1]]
    endpoint[2]=round(b['x']+(r[0]+r[2])/2000,4);endpoint[3]=round(b['y']+(r[1]+r[3])/2000,4)
    # Project the rectangle window to the declared face; finite pin-window
    # extent is retained separately for physical reach/STA, never a new stage.
    face={'i':'N','iw':'W','ie':'E','o':'S'}[endpoint[1]]
    link['endpoint_faces'][link['e'].index(endpoint)]=face
    if face in ['W','E']:endpoint[2]=b['x']+(216 if face=='E' else 0)
    else:endpoint[3]=b['y']+(216 if face=='N' else 0)
  rows.append(dict(instance=b['name'],reserve=reserve,body=dict(b),track_check=check))
 assert len(rows)==13
 p['facts']['spr_closed']=dict(source='bb8dd356c',record='33ea29537',view=view,module='ot_s81hd_spr',params={},
  orientation='R0',body_um=[216,216],reserve_um=[216,648],clock_pin_face='S',reset_stages=2,
  stream_cycles=2,added_data_cycles=0,registered_comparison_unchanged=True,
  lef_sha256=hashlib.sha256(lef.read_bytes()).hexdigest(),pin_windows_nm=windows,
  caveat='Exact exported R0 body inside existing reserve. Static track/window proof only; actual parent GEN/GRT/STA/CLK still decides boundary timing.')
 p['facts']['physical72']['design']='S81 HEAD H4 selected CLOSED SPR; remaining source-view debts retained'
 (out/'plan_unrouted_h4.json').write_text(json.dumps(p,indent=1)+'\n')
 receipt=dict(source_plan=str(src),source_plan_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),
  selected=p['facts']['spr_closed'],checker_sha256=hashlib.sha256(Path(a.checker).read_bytes()).hexdigest(),
  scope='Existing published check_macro_track_alignment check_placement for every signal RECT on actual proposed R0 origins; static row/site and track centres only, not routed parent proof',instances=rows)
 (out/'spr_closed_placement.json').write_text(json.dumps(receipt,indent=1)+'\n')
 print('HEAD_H4 closed_SPR=13 R0=13 offtrack=0 existing_reserve_fit=13 remaining_source_views=diagnostic')
if __name__=='__main__':main()
