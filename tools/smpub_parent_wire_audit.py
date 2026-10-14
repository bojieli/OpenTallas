#!/usr/bin/env python3
"""Actual synthesized wires-only publication parent net-to-LEF placement audit.
Pending views are explicitly marked, never qualification credit.
"""
import json,re,subprocess,itertools,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/rtl/hgi_sm_pub_parent_stations_20261013'
def lef(path):
 s=path.read_text();size=tuple(map(float,re.search(r'SIZE\s+(\S+)\s+BY\s+(\S+)',s).groups()));pins={}
 for m in re.finditer(r'  PIN (\S+)\n(.*?)  END \1\n',s,re.S):
  rect=re.search(r'RECT\s+([-\d.e]+)\s+([-\d.e]+)\s+([-\d.e]+)\s+([-\d.e]+)',m[2]);
  if rect:
   a,b,c,d=map(float,rect.groups());pins[m[1]]=((a+c)/2,(b+d)/2)
 return size,pins

def netlist(out):
 src=(ROOT/'rtl/hbm_accel/generic/peers/ot_hgi_sm_pub.sv').read_text();decl=[]
 for m in re.finditer(r'^module\s+(\w+)\b.*?^endmodule',src,re.M|re.S):
  t=m[0];decl.append(t if m[1]=='ot_hgi_sm_pub_parent' else '(* blackbox *) '+t[:t.index(');')+2]+'\nendmodule')
 (out/'wires.sv').write_text('\n'.join(decl));ys='/home/ubuntu/.local/opentallas-tools/yosys-0.68/bin/yosys'
 with (out/'yosys.log').open('w') as log:subprocess.run([ys,'-Q','-T','-p',f'read_verilog -sv -DSYNTHESIS -DOT_HGI_PUB_HIER_DEF=0 {out}/wires.sv; hierarchy -top ot_hgi_sm_pub_parent; proc; opt_clean; write_json {out}/net.json'],stdout=log,stderr=log,check=True)
 return json.loads((out/'net.json').read_text())['modules']['ot_hgi_sm_pub_parent']
def placements(nl):
 p={}
 for n,c in nl['cells'].items():
  typ=c['type'];nums=list(map(int,re.findall(r'\[(\d+)\]',n)));o='R0'
  if n.startswith('g_s'):k=nums[0];x,y,o=129.6+432*(k%4),907.2 if k<4 else 43.2,'R0' if k<4 else 'MX'
  elif n.startswith('g_credit'):k=nums[0];x,y,o=43.2+432*(k%4),1209.6 if k<4 else 43.2,'R0' if k<4 else 'MX'
  elif n.startswith('g_c['):
   k=nums[0]
   if n.endswith('u_core'):x,y=[129.6,475.2,1166.4,1425.6][k],432
   else:x,y=25.92 if k<2 else 1676.16,432 if k%2==0 else 561.6
   o='R0' if k<2 else 'MY'
  elif n.startswith('g_cmd'):x,y=[0,518.4,1036.8,1468.8][nums[0]],708.48
  elif n.startswith('g_ret'):
   k,j=nums;c=k%4;t=c-j;x=172.8+432*t+43.2*j;y=(561.6 if t==1 else 604.8) if k<4 else(717.12 if t==1 else 648)
  elif n.startswith('g_l'):
   level,k=nums
   x,y=(345.6+432*k,648) if level==1 else((518.4,777.6) if k==0 else(1296,648)) if level==2 else(924.48,648)
  elif n.startswith('g_rst_region'):
   k=nums[0]
   if '.g_h.' in n:x,y=[0,561.6,993.6,1425.6][k],648
   else:x,y=172.8+432*k,1036.8 if n.endswith('u_n') else 302.4
  elif n=='u_rst':x,y=155.52,734.4
  elif n=='u_cmd':x,y=43.2,691.2
  elif n=='u_stream_relay':x,y=604.8,604.8
  elif n=='u_stream_port':x,y=95.04,604.8
  else:raise ValueError(n)
  p[n]=dict(master=typ,x=x,y=y,orient=o)
 return p

def views(nl):
 v={};pending=[]
 for typ in {c['type'] for c in nl['cells'].values()}:
  paths=list((ROOT/'physical/ref_tile').glob('*/views/'+typ+'/'+typ+'.lef'))
  if not paths and typ=='ot_hgi_sm_pub_cmd_quiet':paths=list((ROOT/'physical/ref_tile').glob('smpub_cmd/views/ot_hgi_sm_pub_cmd/ot_hgi_sm_pub_cmd.lef'));pending.append(typ)
  if not paths and typ=='ot_hgi_sm_pub_reset_hop':v[typ]=((21.6,21.6),{'clk':(.042,12),'i_rn':(.042,10),'o_rn':(21.558,10)});pending.append(typ);continue
  if not paths:raise ValueError('missing '+typ)
  size,pins=lef(paths[0])
  lint=paths[0].parent/'child_lint.json'
  if not lint.exists() or json.loads(lint.read_text()).get('verdict')!='PASS':pending.append(typ)
  if typ=='ot_hgi_sm_pub_vmcore' and size[0]>90:pins={k:(x-86.4 if x>100 else x,y) for k,(x,y) in pins.items()};size=(86.4,size[1]);pending.append(typ)
  v[typ]=(size,pins)
 return v,pending

def point(p,size,pin):
 x,y=pin;w,h=size
 if p['orient']=='MX':y=h-y
 if p['orient']=='MY':x=w-x
 return p['x']+x,p['y']+y

def audit(nl,p,v,pending):
 nets={};missing=[]
 for n,c in nl['cells'].items():
  size,pins=v[c['type']]
  for port,bits in c['connections'].items():
   for i,bit in enumerate(bits):
    if not isinstance(bit,int):continue
    pin=port if len(bits)==1 else f'{port}[{i}]'
    if pin not in pins:missing.append(n+'.'+pin);continue
    xy=point(p[n],size,pins[pin]);nets.setdefault(bit,[]).append((n,pin,*xy,c['port_directions'][port]))
 edges=[]
 for bit,ends in nets.items():
  for a,b in itertools.combinations(ends,2):
   if a[0]==b[0] or (a[4]!='output' and b[4]!='output'):continue
   dist=abs(a[2]-b[2])+abs(a[3]-b[3]);edges.append(dict(net=bit,a=a,b=b,manhattan_um=round(dist,3)))
 edges.sort(key=lambda e:e['manhattan_um'],reverse=True);channels=[]
 for a,b in itertools.combinations(p,2):
  aa=p[a];bb=p[b];aw,ah=v[aa['master']][0];bw,bh=v[bb['master']][0]
  dx=max(aa['x']-bb['x']-bw,bb['x']-aa['x']-aw,0);dy=max(aa['y']-bb['y']-bh,bb['y']-aa['y']-ah,0)
  if dx<20-1e-6 and dy<20-1e-6:channels.append(dict(a=a,b=b,x_gap_um=round(dx,3),y_gap_um=round(dy,3)))
 return dict(schema='opentallas.smpub.actual-net-pin-candidate.v1',qualification='UNQUALIFIED candidate geometry; actual parent routed parasitics, child access, reset recovery/removal and native context remain required',pending_actual_views=pending,child_count=len(p),outline_um=[1814.4,1296],placements=p,missing_pins=missing,edge_count=len(edges),over_500_um=[e for e in edges if e['manhattan_um']>500],channel_violations=channels,max_edge_um=edges[0]['manhattan_um'],edges=edges)
if __name__=='__main__':
 out=Path(sys.argv[1]) if len(sys.argv)>1 else Path('/tmp/smpub-parent-wire-audit');out.mkdir(parents=True,exist_ok=True);nl=netlist(out);p=json.loads((OUT/'parent_placements.json').read_text()) if (OUT/'parent_placements.json').exists() else placements(nl);v,pending=views(nl);d=audit(nl,p,v,pending);(OUT/'parent_wire_audit_candidate.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps({k:d[k] for k in ['child_count','pending_actual_views','missing_pins','max_edge_um','edge_count','channel_violations']},indent=2));print('over500',len(d['over_500_um']));print(json.dumps(d['over_500_um'][:20],indent=2))
