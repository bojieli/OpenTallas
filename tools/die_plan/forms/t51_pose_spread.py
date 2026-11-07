#!/usr/bin/env python3
"""Default-off physical T51 FT7 ring row spread. Same RTL and PIN cycles."""
import argparse,collections,hashlib,json,re
from pathlib import Path

def spread(text):
    rx=re.compile(r'^( \{([^\n]+)\} \{)([0-9.]+) ([0-9.]+) ([0-9.]+) ([0-9.]+) (\S+) (\S+)(\} \\\n)',re.M)
    cells=[]
    for m in rx.finditer(text):
        prefix,n,x,y,w,h,o,master,suffix=m.groups()
        cells.append(dict(name=n,x=float(x),y=float(y),w=float(w),h=float(h),orient=o,master=master,match=m))
    targets=[c for c in cells if c['name'].startswith('u_bound.u_cland_ft7_i/u_ring.') and 1160 <= c['y'] <= 1188]
    if len(targets)!=1417:raise ValueError(f'exact E FT7 ring cohort expected1417, got{len(targets)}')
    names={c['name'] for c in targets}; rows=collections.defaultdict(list)
    for c in cells:
        if c['name'] not in names:rows[round(c['y']/0.27)].append((c['x'],c['x']+c['w'],c['name']))
    moves={}; maxdis=0
    for c in sorted(targets,key=lambda c:(-c['y'],c['x'],c['name'])):
        desired=round((1188+2*(c['y']-1188))/0.27)
        candidates=sorted(range(round(1130/.27),round(1190/.27)+1),key=lambda y:(abs(y-desired),y))
        for row in candidates:
            if all(min(c['x']+c['w'],x1)<=max(c['x'],x0)+1e-6 for x0,x1,_ in rows[row]):break
        else:raise ValueError('no legal native-pose row for '+c['name'])
        ny=round(row*.27,6); orient='R0' if row%2==0 else 'MX'
        rows[row].append((c['x'],c['x']+c['w'],c['name']))
        moves[c['name']]={k:c[k] for k in ('x','y','w','h')};moves[c['name']].update(new_y=ny,new_orient=orient)
        maxdis=max(maxdis,abs(ny-c['y']))
    if maxdis>40:raise ValueError('spread exceeded estimated40um physicalreach budget')
    def replace(m):
        prefix,n,x,y,w,h,o,master,suffix=m.groups()
        if n not in moves:return m.group(0)
        p=moves[n];return f'{prefix}{x} {p["new_y"]:.6f} {w} {h} {p["new_orient"]} {master}{suffix}'
    result=rx.sub(replace,text)
    return result,{'schema':'t51_ft7_pose_spread.v1','source_sha256':hashlib.sha256(text.encode()).hexdigest(),'target_count':len(targets),'untargeted_count':len(cells)-len(targets),'untargeted_unchanged':True,'native_pose_target_collisions':0,'max_added_vertical_reach_um':maxdis,'RTL_changes':0,'PIN_cycles_added':0,'moves':moves}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('destination',type=Path);p.add_argument('--receipt',type=Path,required=True);a=p.parse_args()
    if a.destination.exists() or a.receipt.exists():raise SystemExit('refusing overwrite')
    out,receipt=spread(a.source.read_text());a.destination.write_text(out);a.receipt.write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:v for k,v in receipt.items()if k!='moves'},indent=2))
if __name__=='__main__':main()
