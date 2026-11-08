#!/usr/bin/env python3
"""Private T51 signal-layer/whole-stage pose form; default off, zero RTL cycles."""
import argparse,collections,hashlib,json,re
from pathlib import Path
SOURCE_SHA='1fcdd30c1328b2c459c9f8555fdf9bdabad49565ff2246b694adde63a0383e39'
OFFSETS={'u_bound.u_ft_ft11_o_2/':-17.28,'u_bound.u_ft_ft12_o_2/':8.64}
RX=re.compile(r'^( \{([^\n]+)\} \{)([0-9.]+) ([0-9.]+) ([0-9.]+) ([0-9.]+) (\S+) (\S+)(\} \\\n)',re.M)
def transform(text):
 if hashlib.sha256(text.encode()).hexdigest()!=SOURCE_SHA:raise ValueError('unreviewed native-pose input')
 cells=[]
 for m in RX.finditer(text):
  pre,n,x,y,w,h,o,master,suf=m.groups();cells.append(dict(n=n,x=float(x),y=float(y),w=float(w),h=float(h),o=o,m=master))
 def shift(n):return next((v for k,v in OFFSETS.items()if n.startswith(k)),0)
 counts={k:sum(c['n'].startswith(k)for c in cells)for k in OFFSETS}
 if set(counts.values())!={513}:raise ValueError(f'whole-stage data+control count differs:{counts}')
 rows=collections.defaultdict(list);collisions=[];groups=collections.defaultdict(dict)
 for c in cells:
  y=round(c['y']+shift(c['n']),6)
  for q in rows[round(y/.27)]:
   if min(c['x']+c['w'],q['x']+q['w'])>max(c['x'],q['x'])+1e-6 and (shift(c['n'])or shift(q['n'])):collisions.append([c['n'],q['n']])
  rows[round(y/.27)].append({**c,'y':y})
  m=re.match(r'u_bound\.u_ft_(ft(?:11|12)_o)_(\d+)/q\[(\d+)\]',c['n'])
  if m:groups[m[1],int(m[2])][int(m[3])]=(c['x']+c['w']/2,y+c['h']/2)
 if collisions:raise ValueError(f'native fixed-pose collision:{collisions[:3]}')
 hops={}
 for name in ('ft11_o','ft12_o'):
  for stage in range(4):
   a,b=groups[name,stage],groups[name,stage+1];bits=a.keys()&b.keys()
   if len(bits)!=512:raise ValueError('incomplete actual bit-level hop cohort')
   spans=[abs(a[i][0]-b[i][0])+abs(a[i][1]-b[i][1])for i in bits]
   hops[f'{name}:{stage}']={'bits':512,'max_planned_center_span_um':max(spans)}
 def replace(m):
  pre,n,x,y,w,h,o,master,suf=m.groups();dy=shift(n)
  if not dy:return m.group(0)
  return f'{pre}{x} {float(y)+dy:.6f} {w} {h} {o} {master}{suf}'
 return RX.sub(replace,text),dict(source_sha256=SOURCE_SHA,changed_cells=1026,other_native_poses_unchanged=len(cells)-1026,offsets_um=OFFSETS,native_pose_collisions=0,hops=hops,RTL_changes=0,PIN_cycles_added=0,signal_layers='M4-M6',wire_repair_um=120)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('kit',type=Path);p.add_argument('--enable',action='store_true');a=p.parse_args()
 if not a.enable:print('DEFAULT OFF: no kit writes');return
 k=a.kit;pose=k/'native_ff_pose.tcl';backup=k/'native_ff_pose.parent_m5_vB.tcl';receipt=k/'T51_M4_STAGGER.json'
 if backup.exists()or receipt.exists():raise SystemExit('refusing overwrite of prior form')
 if any((k/'run/results/asap7').glob('*/base/[2-6]_*.odb')):raise SystemExit('new form requires fresh floorplan/PLACE; source checkpoints retained separately')
 text=pose.read_text();out,report=transform(text);config=(k/'config.mk').read_text();new,n=re.subn(r'^override export MIN_ROUTING_LAYER = M5$', 'override export MIN_ROUTING_LAYER = M4',config,flags=re.M)
 if n!=1:raise SystemExit('unexpected layer envelope; refusing ambiguous form')
 backup.write_text(text);pose.write_text(out);(k/'config.mk').write_text(new+'\n# Private M4-M6/stagger form; same RTL/pins/outline/cycles. Fresh floorplan required.\n');receipt.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
