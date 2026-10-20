import json,re,itertools,hashlib
from pathlib import Path
import argparse
ap=argparse.ArgumentParser();ap.add_argument('--pins',required=True);ap.add_argument('--lef',required=True);ap.add_argument('--out',required=True);args=ap.parse_args()
pp=Path(args.pins);lp=Path(args.lef)
pins={n:(float(x),float(y)) for n,x,y in re.findall(r'place_pin -pin_name \{([^}]+)\}.*?-location \{([\d.]+) ([\d.]+)\}',pp.read_text())};mp={}
for n,body in re.findall(r'  PIN (\S+)\n(.*?)\n  END \1',lp.read_text(),re.S):
 r=re.search(r'RECT ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)',body)
 if r:a,b,c,d=map(float,r.groups());mp[n]=((a+c)/2,(b+d)/2)
def qport(j,p):
 for port,width in [('k_we',1),('k_addr',30),('k_len',4),('k_tag',17),('k_wstrb',32),('k_wdata',256)]:
  if j<width:return f'{port}[{p*width+j}]'
  j-=width
def rport(j,p):
 if j<4:return f'kr_beat[{p*4+j}]'
 if j<21:return f'kr_tag[{p*17+j-4}]'
 return f'kr_data[{p*256+j-21}]'
variants=[]
for swap in [False,True]:
 for oq,orr in itertools.product(['R0','MX','MY','R180'],repeat=2):
  rows=[]
  for p in range(2):
   for kind,width,y,o in [('q',340,43.2 if swap else 172.8,oq),('r',277,172.8 if swap else 43.2,orr)]:
    mx=[86.4,345.6][p]
    for j in range(width):
     vin=f'rq[{p*341+j+1}]' if kind=='q' else rport(j,p)
     vout=qport(j,p) if kind=='q' else f'rd[{p*280+(273+j if j<4 else 256+j-4 if j<21 else j-21)}]'
     for leg,pn,port in [('write',f'wd_in[{j}]',vin),('read',f'rd_out[{j}]',vout)]:
      x,z=mp[pn]
      if o in ['MY','R180']:x=114.480-x
      if o in ['MX','R180']:z=100.710-z
      a,b=pins[port];length=abs(mx+x-a)+abs(y+z-b)
      rows.append({'pc':p,'fifo':kind,'leg':leg,'bit':j,'port':port,'macro_pin':pn,'manhattan_um':round(length,3)})
  rows.sort(key=lambda r:-r['manhattan_um']);variants.append({'swap_rows':swap,'q_orient':oq,'r_orient':orr,'max_manhattan_um':rows[0]['manhattan_um'],'over405':sum(r['manhattan_um']>405 for r in rows),'worst8':rows[:8]})
variants.sort(key=lambda r:r['max_manhattan_um']);out={'scope':'pre-gate per-bit macro LEF data-pin to corresponding IO-flop anchor; Manhattan planning, no routed reach claim; add inward anchor margin separately','legs':2468,'pinplan_sha256':hashlib.sha256(pp.read_bytes()).hexdigest(),'lef_sha256':hashlib.sha256(lp.read_bytes()).hexdigest(),'variants':variants};Path(args.out).write_text(json.dumps(out,indent=1)+'\n');print(variants[:4])
