import re,json,math,statistics,hashlib
from pathlib import Path
root=Path('/srv/opentallas-scratch/claude/s81-mu5')
def lef(p):
 s=p.read_text();sz=tuple(map(float,re.search(r'SIZE ([\d.]+) BY ([\d.]+)',s).groups()));out={}
 for m in re.finditer(r'^  PIN (\S+)\n(.*?)^  END \1$',s,re.M|re.S):
  rr=re.search(r'RECT ([\d.-]+) ([\d.-]+) ([\d.-]+) ([\d.-]+)',m[2])
  if rr:
   a,b,c,d=map(float,rr.groups());out[m[1]]=((a+c)/2,(b+d)/2)
 return sz,out
out={}
for v in ['mu5r','mu5k']:
 p=root/f'case_{v}';ver=(p/'die.v').read_text();place=(p/'place.tcl').read_text();loc={}
 for m in re.finditer(r'place_inst -name (\S+) -location \{([\d.]+) ([\d.]+)\} -orientation (\S+)',place):loc[m[1]]=(float(m[2]),float(m[3]),m[4])
 phy_path=p/'views'/('rv_phy_hbm.lef' if v=='mu5r' else 'ot_hbm3e_phy_v41x_aw30_e8p5_k.lef');phy_sz,phy=lef(phy_path)
 def xy(name,pin,sz):
  x,y,o=loc[name];a,b=pin;w,h=sz
  if o=='MX': b=h-b
  elif o=='MY': a=w-a
  elif o=='R180':a,b=w-a,h-b
  elif o!='R0':raise ValueError(o)
  return x+a,y+b
 rows=[];groups={}
 for i in range(16):
  name=f'u_ctrl_{i:02d}';line=next(l for l in ver.splitlines() if ' '+name+' (' in l);sz,pins=lef(p/'views'/f'rv_ctrl_{i:02d}.lef')
  for m in re.finditer(r'\.(k_\w+|kr_\w+)\(a_phy_hbm_\w+\[(\d+):(\d+)\]\)',line):
   port,hi,lo=m[1],int(m[2]),int(m[3])
   for b in range(hi-lo+1):
    pp=f'{port}[{lo+b}]';cp=f'{port}[{b}]'
    if pp not in phy or cp not in pins:continue
    a=xy('u_phy_hbm',phy[pp],phy_sz);z=xy(name,pins[cp],sz);d=abs(a[0]-z[0])+abs(a[1]-z[1]);r={'port':port,'phy_pin':pp,'ctrl':name,'ctrl_pin':cp,'phy_xy':a,'ctrl_xy':z,'um':round(d,3),'registered_hops_lower_bound':max(0,math.ceil(d/405)-1)};rows.append(r);groups.setdefault(port,[]).append(d)
 out[v]={'case_die_sha256':hashlib.sha256((p/'die.v').read_bytes()).hexdigest(),'phy_lef_sha256':hashlib.sha256(phy_path.read_bytes()).hexdigest(),'bits':len(rows),'over405':sum(r['um']>405 for r in rows),'worst':sorted(rows,key=lambda x:x['um'],reverse=True)[:20],'ports':{k:{'bits':len(a),'min_um':round(min(a),2),'median_um':round(statistics.median(a),2),'max_um':round(max(a),2),'over405':sum(x>405 for x in a),'max_extra_registered_hops_lb':max(0,math.ceil(max(a)/405)-1)}for k,a in groups.items()}}
import csv,sys
writer=csv.writer(sys.stdout);writer.writerow(['ctrl','ctrl_pin','phy_pin','phy_x_um','phy_y_um','ctrl_origin_x_um','ctrl_origin_y_um','ctrl_orientation','matching_south_x_local_um','south_gap_um','synthetic_ctrl_x_um','synthetic_ctrl_y_um'])
for r in rows:
 x,y,o=loc[r['ctrl']];writer.writerow([r['ctrl'],r['ctrl_pin'],r['phy_pin'],*r['phy_xy'],x,y,o,r['phy_xy'][0]-x,y-r['phy_xy'][1],*r['ctrl_xy']])
