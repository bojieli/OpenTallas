import json,re,math,hashlib,importlib.util,os
from pathlib import Path
B=Path(__file__).resolve().parent
ROOT=Path(os.environ.get('MODEL_REPO_ROOT',str(B.parents[2])))
LEFS=Path(os.environ.get('MODEL_LEF_DIR',str(B)))
spec=importlib.util.spec_from_file_location('RS',ROOT/'tools/qwen_kv_die/kv_rly_std.py');RS=importlib.util.module_from_spec(spec);spec.loader.exec_module(RS)
def lef(path):
 s=path.read_text();sz=re.search(r'SIZE ([\d.]+) BY ([\d.]+)',s);pins={};cur=None
 for line in s.splitlines():
  q=re.match(r'\s*PIN (\S+)',line)
  if q:cur=q[1]
  q=re.match(r'\s*RECT\s+([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)',line)
  if q and cur and cur not in pins:
   a,b,c,d=map(float,q.groups());pins[cur]=((a+c)/2,(b+d)/2)
 return tuple(map(float,sz.groups())),pins
D=json.load(open(Path(os.environ.get('MODEL_GEOMETRY',str(B.parent/'kv_ctl_central_1021/pre_relays_central.json')))));by={i['n']:i for i in D['insts']};src=by['slg_ES_6']
sz,GP=lef(LEFS/'qkd_kvs_grp_s6c.lef')
source=[(src['x']+sz[0]-GP[f'krsp[{j}]'][0],src['y']+GP[f'krsp[{j}]'][1]) for j in range(1062)]
fw,fh,reps=RS.layout(1062);row=[]
for std,dx,dy,role in reps:
 sw,sh=RS.dims(std);_,P=lef(LEFS/f'qkd_rlys_{std}.lef')
 for j in range(min(std,1062-len(row))):
  px,py=P[f'a[{j}]'];row.append((dx+px,dy+py))
assert len(row)==1062
x=src['x']-21.6-fw
out=[]
for orient in ('R0','MY'):
 pts=[(fw-px if orient=='MY' else px,py) for px,py in row]
 A=max(abs(x+px-sx)-(sy-py) for (px,py),(sx,sy) in zip(pts,source))
 C=max(abs(x+px-sx)+(sy-py) for (px,py),(sx,sy) in zip(pts,source))
 opt=(C-A)/2
 vals=[]
 for yi in (math.floor(opt/2.16),math.ceil(opt/2.16)):
  y=round(yi*2.16,3);ds=[abs(x+px-sx)+abs(y+py-sy) for (px,py),(sx,sy) in zip(pts,source)]
  collision=[i['n'] for i in D['insts'] if x<i['x']+i['w']-1e-6 and i['x']<x+fw-1e-6 and y<i['y']+i['h']-1e-6 and i['y']<y+fh-1e-6]
  vals.append(dict(x=x,y=y,w=fw,h=fh,max_um=max(ds),worstbit=ds.index(max(ds)),collisions=collision,legal340=max(ds)<=340,legal405=max(ds)<=405))
 out.append(dict(orientation=orient,candidates=vals,best=min(vals,key=lambda v:v['max_um'])))
rec=dict(scope='actual CLOSED group+standard LEF perbit firstcapture model; exact1122staticframes only; partialrelayoccupancy/clock/outputchain/native qualification owed',source=src,group_lef_size=sz,station_layout=[fw,fh,reps],model=out,lef_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in LEFS.glob('*.lef')})
Path(os.environ.get('MODEL_OUTPUT','krs_receipt.json')).write_text(json.dumps(rec,indent=2));print(json.dumps(rec,indent=2))
