#!/usr/bin/env python3
"""Build an explicit, unadopted owned-capture parent geometry from a real contract.
No grant, timing, pin/hop, clock or routing qualification is implied.
"""
import argparse, copy, hashlib, json
from pathlib import Path

def build(base):
    c=copy.deepcopy(base)
    layout=c['sub_layouts']['ot_s81_hc_cth']
    cap=[r for r in layout['rows'] if r['tile']=='ctfx']
    assert len(cap)==1
    old_h=cap[0]['h']; delta=round(51.84-old_h,3)
    assert delta>0, 'requires an existing smaller capture reservation'
    boundary=cap[0]['y']
    for row in layout['rows']:
        if row['y']>boundary: row['y']=round(row['y']+delta,3)
    cap[0].update(cell='ot_s81_hc_ctfx_cap',h=51.84)
    layout['outline']['h']=round(layout['outline']['h']+delta,3)
    receipt={'status':'UNADOPTED_PARENT_GEOMETRY_ONLY','old_capture_height_um':old_h,'new_capture_height_um':51.84,'growth_per_cth_um':delta,'sub_layout':layout,'parents':{},'remaining':['actual canonical source/child binding','assigned parent and leaf pin regeneration','exact peer hops/reset/control and internal wire/PG/cuts','mapped source equivalence and native TT/FF/DRC0']}
    for name,count in [('sp_hc_s',10),('sp_hc_t',12)]:
        parent=next(s for s in c['slots'] if s['name']==name)
        growth=round(count*delta,3)
        parent['origin']['y']=round(parent['origin']['y']-growth,3)
        parent['outline']['h']=round(parent['outline']['h']+growth,3)
        for pin in parent.get('pins',[]):
            if pin.get('face') in ('W','E'):pin['offset']=round(pin['offset']+growth,4)
        children=[s for s in c['slots'] if s.get('parent')==name]
        for child in children:child['origin']['y']=round(child['origin']['y']+growth,3)
        tiles=[s for s in children if s.get('cell')=='ot_s81_hc_cth']
        for x in sorted({s['origin']['x'] for s in tiles}):
            column=sorted([s for s in tiles if s['origin']['x']==x],key=lambda s:-s['origin']['y'])
            assert 0<len(column)<=count,(name,x,len(column),count)
            for i,tile in enumerate(column):
                tile['outline']['h']=round(tile['outline']['h']+delta,3)
                tile['origin']['y']=round(tile['origin']['y']-(i+1)*delta,3)
        receipt['parents'][name]={'growth_down_um':growth,'origin':parent['origin'],'outline':parent['outline'],'cth_instances':len(tiles),'childplan':[{'name':t['name'],'origin':t['origin'],'outline':t['outline']} for t in tiles]}
    c['norm_capture_margin_candidate']=receipt
    return c,receipt

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--receipt',type=Path,required=True);a=p.parse_args()
    text=a.input.read_bytes();c,r=build(json.loads(text));r['input_sha256']=hashlib.sha256(text).hexdigest();r['input']=str(a.input)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(c,indent=1)+'\n');a.receipt.write_text(json.dumps(r,indent=1)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ['sub_layout','parents']},indent=1));print(json.dumps({k:{q:v for q,v in r.items() if q!='childplan'} for k,r in r['parents'].items()},indent=1))
if __name__=='__main__':main()
