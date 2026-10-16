import pathlib,json,math,hashlib
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
root=pathlib.Path(__file__).resolve().parents[2];out=root/'results/arch/qwen_vm_residual_1015/relay_parent_0253/local_leaf_shapes_0400';out.mkdir(exist_ok=True)
assert json.load(open('/home/ubuntu/claude-takeover-20261007/COORDINATOR.lock'))['owner']=='codex'
grid=lambda x:round(.012+round((x-.012)/.048)*.048,6)
rows=[];fig,axs=plt.subplots(2,3,figsize=(15,10))
for j,name in enumerate(['return_plane','read_control_ro6']):
 source=root/'results/arch/qwen_vm_residual_1015/local_leaf_contract_0253'/f'{name}.json';d=json.loads(source.read_text());groups={f:[p['name']for p in d['pins']if p['face']==f and p['name']!='ck']for f in ['W','E','S']}
 for k,(label,w,h) in enumerate([('existing',64.8,64.8),('shorter',64.8,58.32),('compact',51.84,58.32)]):
  pg=[round(.300+2.7*z+delta,6)for z in range(math.ceil(w/2.7))for delta in [0,.192]];ck=grid(w/2);pins=[]
  for f in ['W','E']:
   ns=groups[f];start=grid((h-(len(ns)-1)*.192)/2)
   pins += [dict(name=n,face=f,layer='M4',xy=[0 if f=='W'else w,round(start+i*.192,6)],size=[.144,.024])for i,n in enumerate(ns)]
  av=[round(.012+.048*z,6)for z in range(math.ceil(w/.048))if 4.32<=.012+.048*z<=w-4.32 and abs(.012+.048*z-ck)>2.16 and min(abs(.012+.048*z-x)for x in pg)>=.120-1e-9];ns=groups['S'];sel=[min(av,key=lambda x:abs(x-ck))]if len(ns)==1 else[av[round(i*(len(av)-1)/(len(ns)-1))]for i in range(len(ns))];assert len(set(sel))==len(sel)
  pins += [dict(name=n,face='S',layer='M5',xy=[x,0],size=[.024,.144])for n,x in zip(ns,sel)]+[dict(name='ck',face='S',layer='M5',xy=[ck,0],size=[.024,.144])]
  assert {p['name']for p in pins}=={p['name']for p in d['pins']}
  assert min(abs(ck-x)for x in pg)>=.12
  for p in pins:
   x,y=p['xy'];assert 0<=x<=w and 0<=y<=h
   if p['face']in ['W','E']:assert 4.32<=y<=h-4.32
   else:assert min(abs(x-g)for g in pg)>=.12-1e-9
  span=max(len(groups['W'])-1,len(groups['E'])-1)*.192;bound=span+8.64
  r=dict(name=name,shape=label,outline_um=[w,h],source_contract_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),source_contract=d['source_sha256'],pins=pins,area_um2=w*h,replicas=d['replicas'],total_area_mm2=w*h*d['replicas']/1e6,height_bound_um=bound,PG_M5_pitch_um=2.7,PG_contact_clearance_um=.120,clock_keepout_halfspan_um=2.16,south_available_contacts=len(av),south_required_contacts=len(ns),M4_pitch_um=.192,M4_contact_um=[.144,.024],face_cut_25pct_derated=max(len(groups['W']),len(groups['E']))/(math.floor((h-8.64)/.048)*.75),qualification='Named contacts screen only; no inherited grant/CTS/route. All incident parent homes/cuts/clocks/global placement remain ungranted. No floorplan or routed-density claim.')
  original={p['name']:p for p in d['pins']};r['max_contact_L1_displacement_um']=max(sum(abs(a-b)for a,b in zip(p['xy'],original[p['name']]['xy']))for p in pins);r['max_contact_L1_displacement_by_face_um']={f:max(sum(abs(a-b)for a,b in zip(p['xy'],original[p['name']]['xy']))for p in pins if p['face']==f)for f in ['W','E','S']};r['incident_route_bound']='For any fixed external peer, abstract L1 leg increase cannot exceed contact displacement by triangle inequality. Actual peer homes, obstacles, cut capacity, detailed routing and clock delivery are not established by this bound.'
  rows.append(r);(out/f'{name}_{label}.json').write_text(json.dumps(r,indent=2)+'\n')
  ax=axs[j,k];ax.add_patch(Rectangle((0,0),w,h,facecolor='#f4f8fa',edgecolor='black'))
  for g in pg:
   if g<w:ax.plot([g,g],[0,h],color='#c99b80',alpha=.3,lw=.6)
  for p in pins:
   x,y=p['xy'];ax.plot(x,y,'.',color='#c83c40'if p['name']=='ck'else'#246b8e',ms=2)
  ax.plot([ck-2.16,ck+2.16],[0,0],color='#c83c40',lw=4);ax.set_aspect('equal');ax.set(xlim=(-3,68),ylim=(-3,68),title=f'{name} {label}\n{w}×{h}um; {len(pins)} actual named pins',xlabel='um',ylabel='um');ax.text(w/2,h/2,f'W{len(groups["W"])} / E{len(groups["E"])} / S{len(ns)}+ck\nM4 step .192um\nS contacts {len(ns)}/{len(av)}\ncontact screen ONLY',ha='center',fontsize=8)
fig.suptitle('VM leaf contact-capacity alternatives; current physical routes preserved; proposals require new grant and all-incident route proof');fig.tight_layout();fig.savefig(out/'contact_alternatives.png',dpi=140)
report=dict(scope='Current immutable source336b78d77 leaf contacts; all pins enumerated. Pin capacity does not alone require64.8square.',existing_contacts_min_height_um={'return_plane':max(p['xy'][1]for p in json.loads((root/'results/arch/qwen_vm_residual_1015/local_leaf_contract_0253/return_plane.json').read_text())['pins'])+4.32,'read_control_ro6':max(p['xy'][1]for p in json.loads((root/'results/arch/qwen_vm_residual_1015/local_leaf_contract_0253/read_control_ro6.json').read_text())['pins'])+4.32},shape_sums_mm2={s:sum(r['total_area_mm2']for r in rows if r['shape']==s)for s in ['existing','shorter','compact']},summary=[{k:v for k,v in r.items()if k not in ['pins','source_contract']}for r in rows],recommendation='Retain current immutable336 until verdict. Shorter64.8x58.32 preserves south clock/PG and all south contacts if fixed from existing; recenter side pins, new exact assignment/grant required. Compact51.84x58.32 also passes contacts but moves E/clock/south; use only after complete incident parent routing study. No parent leaf homes granted, therefore neither is route-safe yet.')
(out/'screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k in ['existing_contacts_min_height_um','shape_sums_mm2']}));print([(r['name'],r['shape'],r['south_available_contacts'],r['face_cut_25pct_derated'])for r in rows])
