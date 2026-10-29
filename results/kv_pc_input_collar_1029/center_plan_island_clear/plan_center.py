from pathlib import Path
import json,re,importlib.util,collections,math,inspect
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon,Rectangle
base=Path(__file__).parent
sp=importlib.util.spec_from_file_location('g','/home/ubuntu/OpenTallas/tools/autopilot/geom_rules.py');g=importlib.util.module_from_spec(sp);sp.loader.exec_module(g);D=g.Design('/srv/opentallas-scratch/claude/codex-geom-1029/kv/kvspc.tsv')
face=collections.defaultdict(set)
for p in D.pins:
 if p['sig'] in ('POWER','GROUND','CLOCK') or g.CLOCK_PIN_RE.search(p['name']) or p['name'].startswith('strap_'):continue
 ni=D.pin_net.get(p['k']);queue=[(ni,0)];seen=set()
 while queue:
  n,dep=queue.pop()
  if n is None or n in seen or dep>4:continue
  seen.add(n)
  for s in ([D.nets[n][1]] if p['io']=='OUTPUT' else D.nets[n][2]):
   if not s or s[0]!='i' or s[2]:continue
   c=s[1]
   if D.kind(c)=='S':face[p['io']].add(c)
   elif D.kind(c)=='B':queue.extend((nn,dep+1) for nn in ([a for a,ck in D.cell_in[c] if not ck] if p['io']=='OUTPUT' else D.drives[c]))
move=set(face['INPUT']-face['OUTPUT']);viol=json.load(open('/srv/opentallas-scratch/claude/codex-geom-1029/kv/kvspc_long_legs_classified.json'));byname={c[6]:cid for cid,c in D.cells.items()}
for a in viol:
 if not a['source_pins'] and byname[a['source']] not in face['OUTPUT']:move.add(byname[a['source']])
for cid,c in D.cells.items():
 if any(k in c[6] for k in ('.u_chain.spc', '.u_chain.sst', '.u_chain.emb_return_slot', '.u_ecc.u_ecc.fault')) and c[0]=='S' and cid not in face['OUTPUT']:move.add(cid)
blocks=[tuple(float(v)/1000 for v in m) for m in re.findall(r'^kvr2_blk \$kvr2_b (\d+) (\d+) (\d+) (\d+)',(base/'kvr2_reserve.tcl').read_text(),re.M)]
ov=lambda a,b:a[0]<b[2]-1e-6 and b[0]<a[2]-1e-6 and a[1]<b[3]-1e-6 and b[1]<a[3]-1e-6
X,Y=198.72,181.44;R=31.0;SW,SH=.054,.27;slots=[]
for rr in range(-114,115,2):
 y=Y+rr*SH
 # include full cell body in L1 diamond
 half=R-max(abs(y-Y),abs(y+SH-Y))
 if half<1.5:continue
 left=4.32+math.ceil((X-half-4.32)/SW)*SW;right=X+half
 slots.append([left,y,right])
slots.sort(key=lambda r:(abs(r[1]-Y),r[1]));anchors=[];row=0
for cid in sorted(move,key=lambda c:(-D.cells[c][4]+D.cells[c][2],D.cells[c][6])):
 c=D.cells[cid];w=c[4]-c[2];h=c[5]-c[3]
 while row<len(slots):
  x,y,right=slots[row];r=(x,y,x+w,y+h)
  hit=[b for b in blocks if ov(r,b)]
  if hit:slots[row][0]=max(b[2] for b in hit)+.54;continue
  if x+w>right+1e-7:row+=1;continue
  break
 if row==len(slots):raise SystemExit('packing area exhausted')
 x,y,right=slots[row];slots[row][0]=x+w+.54
 r=(x,y,x+w,y+h);D.cells[cid]=(c[0],c[1],*r,c[6]);anchors.append(dict(name=c[6],box_um=r,master=c[1],origin_id=cid))
rs=inspect.getsource(g.r2r_metrics).replace('    best, arg, n_gt = 0.0, None, 0','    best, arg, n_gt = 0.0, None, 0\n    D.reach_rows=[]').replace('            n_gt += 1','            n_gt += 1\n            D.reach_rows.append((src,cap,mx))')
exec(rs,g.__dict__)
m=g.r2r_metrics(D)
print('BAD_SOURCES',collections.Counter(D.cells[src][6] for src,cap,dist in D.reach_rows).most_common(30))
print('BAD_CAPTURES',collections.Counter(re.sub(r'\\\[\d+\\\]','[*]',D.cells[cap][6]) for src,cap,dist in D.reach_rows).most_common(10))
out=base/'center_plan';out.mkdir(exist_ok=True)
(out/'anchors.json').write_text(json.dumps(dict(scope='Prebuild PC collar central old-capture constraint; unchanged old graph + new boundary capture, not current placed source',center_um=[X,Y],radius_um=R,preserve_output_faces=len(face['OUTPUT']),reserved_blocks=blocks,anchors=anchors,graph=m),indent=2)+'\n')
fig,ax=plt.subplots(figsize=(8,8));ax.set_aspect('equal');ax.set_xlim(0,397.44);ax.set_ylim(0,362.88)
pp=[p for p in D.pins if p['sig'] not in ('CLOCK','POWER','GROUND')]
ax.scatter([p['x'] for p in pp if p['io']=='INPUT'],[p['y'] for p in pp if p['io']=='INPUT'],s=3,c='green',label='Canonical input faces: new +1 capture collar')
ff=[g.ctr(D.cells[c]) for c in face['OUTPUT']];ax.scatter([v[0] for v in ff],[v[1] for v in ff],s=2,c='purple',alpha=.4,label='2297 existing output face FF retained')
ax.add_patch(Polygon([(X-R,Y),(X,Y+R),(X+R,Y),(X,Y-R)],fill=False,color='red',lw=1));ax.scatter([(a['box_um'][0]+a['box_um'][2])/2 for a in anchors],[(a['box_um'][1]+a['box_um'][3])/2 for a in anchors],s=2,c='blue',label=f'{len(anchors)} old input/control captures: proposed centre homes')

for bb in blocks:ax.add_patch(Rectangle((bb[0],bb[1]),bb[2]-bb[0],bb[3]-bb[1],fill=False,edgecolor='orange',hatch='///',lw=.5))
ax.scatter([X],[Y],marker='*',c='orange',s=80,label='Unchanged core clock/reset entry')
ax.set_title('PC input-collar source plan: +1 coherent input/boot edge\nNo macros; 1831 new FF; proposed core-capture homes, no P&R');ax.legend(loc='upper right',fontsize=6);ax.set_xlabel('um');ax.set_ylabel('um');fig.tight_layout();fig.savefig(out/'overview.png',dpi=140)
print(json.dumps(dict(anchors=len(anchors),area_um2=sum((a['box_um'][2]-a['box_um'][0])*(a['box_um'][3]-a['box_um'][1]) for a in anchors),graph=m),indent=2))
