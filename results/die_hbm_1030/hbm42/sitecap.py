import json,sys
from pathlib import Path
import numpy as np
T='/srv/opentallas-scratch2/claude/wt/die-hbm-42/tools/die_plan'
sys.path.insert(0,T); sys.path.insert(0,str(Path(T).parents[1]))
import schema as S
from tools.die_trial.legal_sites import RowAllocator
KEEPOFF=1.08; CELL=(1.404,.27)
raw=json.load(open(sys.argv[1]))
for tn in sys.argv[2].split(','):
    t=raw['partition_types'][tn]; w,h=t['outline_um']
    boxes=list(S.placed_macro_boxes(t,halo=KEEPOFF).values())
    def mk():
        al=RowAllocator((4.32,4.32,w-4.32,h-4.32),blocked=boxes,cell_size=CELL,column_pitch=2.16,row_pitch=.27,origin=(4.32,4.32))
        for s in t['ft_slots']:
            for st in s.get('bit_sites_um') or []:
                for x,y in st: al.reserve_rectangle((x,y,x+CELL[0],y+CELL[1]))
            if not s.get('bit_sites_um'):
                for x,y in s.get('regs_um') or []: al.reserve_rectangle((x-2,y-2,x+2,y+2))
        return al
    print(tn,'outline',w,h,'macros',len(boxes),'macro area frac',round(sum((b[2]-b[0])*(b[3]-b[1]) for b in boxes)/(w*h),3))
    for s in t['ft_slots']:
        nst=len(s.get('bit_sites_um') or s.get('regs_um') or [])
        if s['width']<15: continue
        line=[s['name'],'w',s['width'],'stages',nst,'bitsites',bool(s.get('bit_sites_um')),s.get('in_face'),s.get('out_face')]
        if s.get('bit_sites_um'):
            cs=[]
            for st in s['bit_sites_um']:
                c=np.mean([[x+CELL[0]/2,y+CELL[1]/2] for x,y in st],axis=0)
                caps=[]
                for R in (90,140,200):
                    al=mk()
                    try: al.allocate(c,100000,max_radius_um=R)
                    except ValueError as e: caps.append(int(str(e).split('legal sites')[0].replace('only','')))
                cs.append((tuple(np.round(c)),caps))
            line.append(cs)
        print('  ',*line)
