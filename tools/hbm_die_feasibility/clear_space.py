#!/usr/bin/env python3
"""Bounded geometry search; absence of candidates is not a global fit proof."""
import argparse,json,subprocess
from pathlib import Path
from report import area,box,digest


def search(candidate,width,height,bounds,step):
    xmin,ymin,xmax,ymax=bounds
    obstacles=[(c['instance'],box(c)) for c in candidate['children'] if c['xy_um'][0]<xmax+width and c['xy_um'][0]+c['w_um']>xmin and c['xy_um'][1]<ymax+height and c['xy_um'][1]+c['h_um']>ymin]
    obstacles += [(r['name'],r['rect_um']) for r in candidate['routing_corridor_reservations']+candidate['ring_device_column_reservations']]
    valid=[]
    for xi in range(int(xmin/step)+1,int(xmax/step)+1):
        for yi in range(int(ymin/step)+1,int(ymax/step)+1):
            x,y=round(xi*step,6),round(yi*step,6);rect=[x,y,x+width,y+height]
            if rect[2]>candidate['die_um'][0] or rect[3]>candidate['die_um'][1]:continue
            if not any(area(rect,b)>1e-6 for _,b in obstacles):valid.append({'xy_um':[x,y],'w_um':width,'h_um':height,'assigned':False,'source_peer_binding':None})
    return len(obstacles),valid

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--revision',required=True);a.add_argument('--output',type=Path,required=True);p=a.parse_args()
    raw=subprocess.check_output(['git','show',p.revision+':results/arch/hbm_native_1013/die_v13/candidate.json']);candidate=json.loads(raw)
    bounds=[13000,13500,17500,18000];n,valid=search(candidate,622.08,596.16,bounds,43.2)
    result={'schema':'opentallas.qdq_clear_space_screen.v1','geometry_revision':p.revision,'geometry_sha256':digest(raw),'qualified':False,'search_grid_um':43.2,'search_origin_range_um':bounds,'envelope_um':[622.08,596.16],'obstacles_considered':n,'clear_candidates':len(valid),'geometry_only_samples':valid[:10],'important_limits':['Bounded43.2um-grid absence is not global fit proof','No complete native master/child topology integration','No actual external rec/reset/ret peer anchors','No routing or PG access capacity','No clock/reset producer/tap assignment','No slot relocation semantic or throughput qualification']}
    p.output.write_text(json.dumps(result,indent=2)+'\n')
