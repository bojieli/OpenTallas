"""Disabled actual-mapped-FF row candidate, not a placed native view or clock proof."""
import argparse
import csv
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/die_trial'))
from legal_sites import RowAllocator


def main():
    p=argparse.ArgumentParser();p.add_argument('--mapped',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    s=a.mapped.read_text();ff=re.findall(r'^  (DFF\S+) (\S+)\s*\(',s,re.M)
    assert len(ff)==21930 and {t for t,_ in ff}=={'DFFHQNx1_ASAP7_75t_R'}
    W,H=604.8,803.52
    macros=[]
    for i in range(44):
        row,col=divmod(i,5);x,y=17.28+col*113.832,17.28+row*86.94
        macros.append(dict(name=f'g_leaf[{i//4}].u_leaf.g_page[{i%4}].u_program',leaf=i//4,
                           rect_um=[x,y,x+96.552,y+69.66]))
    blocked=[[x-4.32,y-4.32,X+4.32,Y+4.32]for x,y,X,Y in [m['rect_um']for m in macros]]
    alloc=RowAllocator([4.32,4.32,W-4.32,H-4.32],blocked,cell_size=(1.404,.27),column_pitch=2.16,row_pitch=.27)
    ports=json.loads((ROOT/'results/hbm_programme_native_intake_0450/model.json').read_text())['ports']
    outs=[q['name']+(f'[{b}]'if q['is_vector']else'')for q in ports if q['direction']=='output'for b in range(q['width'])]
    tracks=[.024+i*.048 for i in range(17000) if 17.28<=.024+i*.048<=H-17.28]
    pins={n:[W-.024,tracks[round(i*(len(tracks)-1)/(len(outs)-1))]]for i,n in enumerate(outs)}
    rows=[];rest=defaultdict(list);stats={};max_pin_hop=0
    for typ,name in ff:
        logical=name.lstrip('\\').split('$_')[0]
        if logical in pins:
            pin=pins[logical];pts,st=alloc.allocate([W-4.32,pin[1]],1,80.)
            x,y=map(float,pts[0]);hop=abs(x-pin[0])+abs(y-pin[1]);max_pin_hop=max(max_pin_hop,hop)
            rows.append([name.lstrip('\\'),typ,'native_output_capture',x,y,pin[0],pin[1]])
        else:
            m=re.search(r'g_leaf\[(\d+)\]\.u_leaf',name)
            rest['leaf'+m[1]if m else'top_other'].append((typ,name))
    assert len(rows)==2282
    for group,cells in sorted(rest.items(),key=lambda kv:(kv[0]=='top_other',kv[0])):
        if group=='top_other':target=[8.64,H/2]
        else:
            mm=[m['rect_um']for m in macros if m['leaf']==int(group[4:])]
            target=[(min(r[0]for r in mm)+max(r[2]for r in mm))/2,
                    (min(r[1]for r in mm)+max(r[3]for r in mm))/2]
        pts,st=alloc.allocate(target,len(cells),160.)
        stats[group]=dict(target_um=target,**st)
        for (typ,name),(x,y)in zip(sorted(cells),pts):rows.append([name.lstrip('\\'),typ,group,float(x),float(y),'',''])
    assert len(rows)==21930 and len({(r[3],r[4])for r in rows})==21930
    with(a.out/'actual_mapped_FF_row_candidate.csv').open('w')as f:
        w=csv.writer(f);w.writerow(['cell','master','ownership','x_um','y_um','planned_output_pin_x_um','planned_output_pin_y_um']);w.writerows(rows)
    receipt=dict(status='PASS_DISABLED_CONSERVATIVE_FF_ROWS_ONLY',mapped_sha256=hashlib.sha256(s.encode()).hexdigest(),
      source_snapshot='63eef4b8a5f43cf69152650bbb2c80a0f437387d',outline_um=[W,H],macro_streets_um=17.28,
      macros=macros,soft_FF=21930,output_capture_FF=2282,other_FF_groups=stats,
      conservative_FF_footprint_um=[1.404,.27],column_pitch_um=2.16,row_pitch_um=.27,
      macro_halo_um=4.32,unique_nonoverlap_row_sites=True,max_output_FF_to_proposed_pin_um=max_pin_hop,
      held=['No physical placement/CTS/route/STA performed','Combinational logic rows unplaced',
            'Actual macro-pin→FF and internal FF→FF timing/reach notqualified',
            'Actual clock/reset/START66 contacts and programme collar rows unplaced',
            'Parent existing5106XO/new2304upstream and preserved4434wrappercapture FF rows/pricing unjoined',
            'No native source-view/physical/current-parent adoption'],release_eligible=False)
    (a.out/'row_candidate.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print('PASS_DISABLED_FF_ROWS',len(rows),'outputpinmax',round(max_pin_hop,3))


if __name__=='__main__':main()
