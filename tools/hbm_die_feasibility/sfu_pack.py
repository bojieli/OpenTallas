#!/usr/bin/env python3
"""Tight full SW SFU geometry prototype, never a placement/pin/tap grant."""
import argparse,json,subprocess
from pathlib import Path
from report import area,box,overlaps,digest


def propose(candidate,slot,body_lef_sha):
    x0,y0=slot['origin']['x'],slot['origin']['y'];rows=[]
    def put(name,master,x,y,w,h,kind):
        r={'instance':name,'master':master,'kind':kind,'xy_um':[round(x0+x,6),round(y0+y,6)],'w_um':w,'h_um':h,'orientation':'R0','assigned':False}
        rect=box(r)
        if any(area(rect,box(p))>1e-6 for p in rows):raise ValueError('trial packing collision')
        hit=overlaps(rect,candidate['children'])
        forbidden=[q['name'] for q in candidate['routing_corridor_reservations']+candidate['ring_device_column_reservations'] if area(rect,q['rect_um'])>1e-6]
        if hit['count'] or forbidden:raise ValueError('existing child or corridor collision')
        r['existing_child_overlap']=hit;r['forbidden_corridor_overlap']=forbidden;rows.append(r)
    for i in range(16):put(f'lane{i}','ot_su12_sfu',(i%8)*218.16,(i//8)*332.64,216,330.48,'selected CLOSED frozen body, unchanged')
    for i in range(4):put(f'control{i}',['ot_hgi_sfu_ctl75lo','ot_hgi_sfu_ctl75hi','ot_hgi_sfu_ctl60lo','ot_hgi_sfu_ctl60hi'][i],1745.28,i*174.96,216,172.8,'new unqualified control')
    for i in range(16):put(f'mapper{i}','ot_hgi_sfu_lane_map',i*105.84,665.28,103.68,54,'new requested mapper,26 prior setup failures')
    return {'schema':'opentallas.sfu.full_geometry_prototype.v1','qualified':False,'assigned':False,'source_quarter_to_SW_proven':False,'selected_body_LEF_sha256':body_lef_sha,'prototype_gap_um':2.16,'perimeter_margin_um':0,'nearest_ring_clearance_um':1.44,'master_count':36,'children':rows,'unknowns':['literal pin tracks/routing cuts and per-bit intrinsic+wire budgets','PG access for selected M6 body and new M5 children','actual source root/reset driver/tap graph','source quarter geographic binding','outer cache/VM/credit/price integration'],'no_closure_or_grant':True}

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--revision',required=True);a.add_argument('--body-repo',type=Path,required=True);a.add_argument('--output',type=Path,required=True);p=a.parse_args()
    raw=subprocess.check_output(['git','show',p.revision+':results/arch/hbm_native_1013/die_v13/candidate.json']);c=json.loads(raw)
    contractraw=subprocess.check_output(['git','show',p.revision+':results/arch/hier_contract_1011/r25gq.json']);slot=next(s for s in json.loads(contractraw)['slots'] if s['name']=='hb_sfu_SW')
    path='physical/ref_tile/sfu_lane_ring3_rt/views/ot_su12_sfu/ot_su12_sfu.lef';leaf=(p.body_repo/path).read_bytes();sha=digest(leaf)
    if sha!='414fdd99a70a45fdb7c73440a7dabc9d4699d7c84c2be1a4dcf3d5902e4de9f3':raise ValueError('selected frozen view mismatch')
    result=propose(c,slot,sha);result.update(geometry_revision=p.revision,geometry_sha256=digest(raw),published_contract_sha256=digest(contractraw),selected_body_LEF_path=path)
    p.output.write_text(json.dumps(result,indent=2)+'\n')
