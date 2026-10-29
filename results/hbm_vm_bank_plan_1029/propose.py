"""Grown VM bank geometry proposal, 4 real SRAMs in the existing270x403.92lot.
No source/caller adoption or P&R. Literal port coordinates are rebuilt for the
qualified 3925-port ONECLK ABI. New bit positions are NOT claimed to preserve
old semantic field identities across the 17->18sector insertion.
"""
import copy,hashlib,json,math,sys
from pathlib import Path
D,O=map(Path,sys.argv[1:3]);O.mkdir(parents=True,exist_ok=True);W,H=270.,403.92
names=['vecd4ae','vec6293'];base={v:json.load(open(D/f'cores/hnx_vms_bank_q0_faces__{v}__270x403.92__canon.json'))for v in names}
required={p['name']:p for p in base['vec6293']};assert len(required)==3933
clocks={n for n in required if n.startswith('clk')};assert len(clocks)==9
keep=set(required)-clocks|{'clk'};assert len(keep)==3925
macros=[{'name':'u_ot_pr_core.bank.'+n,'master':'ot_sram_1r1w_1024x256_m2_r2c2','origin_um':[47.52,y],'rect_um':[47.52,y,222.264,round(y+70.488,6)]}for n,y in zip(['u_a','u_b','u_c','u_h'],[8.64,103.68,198.72,293.76])]
root=[133.944,185.76];island=[129.6,181.44,138.24,190.08]
for m in macros:
 a,b,c,d=m['rect_um'];assert 4.32<=a<c<=W-4.32 and 4.32<=b<d<=H-4.32
 assert island[2]<=a-4.32 or island[0]>=c+4.32 or island[3]<=b-4.32 or island[1]>=d+4.32
rep={'schema':'hbm.vm-bank-grown-plan.v1','status':'UNSIGNED PROPOSAL; NO PNR','outline_um':[W,H],'source_master':'hfd_vms_bank_native_q0_faces_r2048_oneclk','source_capacity_commit':'4b2165eb2','macro_count':4,'macro_total_area_um2':round(4*174.744*70.488,6),'core_area_um2':W*H,'macro_fraction':4*174.744*70.488/(W*H),'new_data_stages':0,'oneclk_added_cycles':0,'root_pin_um':root,'root_island_um':island,'profiles':{},'holds':['Actual 3925-source port census + ONECLK proof required, current old profile vec6293 was interface-only and old macro inventory UNKNOWN.','std-cell area/FF incidence, source-bound actual pin-to-reg/write/read/macroclk reach and clock/PG model before place.','bid/sid constant/quasi-static contract checked separately; no undeclared tie/por alias.','Every parent peer bit target/clock/reset/START/CA and caller ABI must regenerate in one event.']}
for variant,pins0 in [('canonical',base['vecd4ae'])]:
 pins={p['name']:copy.deepcopy(p)for p in pins0 if p['name']in keep};old=set(pins)
 for n in keep-old:
  assert n in required
  stem=n.split('[')[0];siblings=[p for key,p in pins.items()if key.split('[')[0]==stem]
  assert siblings,(n,'no current semantic bus face')
  pins[n]=copy.deepcopy(siblings[-1]);pins[n]['name']=n
 pins['clk'].update(layer='M5',x=root[0],y=root[1],w=.048,h=.48)
 faces={f:[]for f in'WENS'}
 for n,p in pins.items():
  if n=='clk':continue
  x,y=p['x'],p['y'];f='W'if x<1 else'E'if x>W-1 else'S'if y<1 else'N'if y>H-1 else None
  if f is None:
   assert n=='rst_n',(variant,n,p)
   continue
  faces[f].append(p)
 peaks={};moves=[]
 for f,pp in faces.items():
  along='x'if f in'NS'else'y';length=W if f in'NS'else H
  pp.sort(key=lambda p:(p[along],p['name']))
  # Native M4/M5 .048um tracks. Alternate 3/4-track spacing for the crowded
  # 1383-ish South pins; 4 tracks elsewhere. 60 pins/10um is the hard limit.
  steps=[(3 if i%2==0 else 4) if f=='S' else 4 for i in range(len(pp)-1)]
  extent=.048*sum(steps);assert extent<=length-8.64,(f,len(pp),extent,length)
  start=.024+round(((length-extent)/2-.024)/.048)*.048;cur=start
  for i,p in enumerate(pp):
   before=[p['x'],p['y']];p[along]=round(cur,6);moves.append({'pin':p['name'],'old_um':before,'new_um':[p['x'],p['y']]})
   if i<len(steps):cur+=steps[i]*.048
  vals=sorted(p[along]for p in pp);peak=0;j=0
  for i,x in enumerate(vals):
   while j<len(vals)and vals[j]<=x+10+1e-8:j+=1
   peak=max(peak,j-i)
  peaks[f]=peak/10;assert peaks[f]<=6,(variant,f,peaks[f])
  assert all(abs((p[along]-.024)/.048-round((p[along]-.024)/.048))<1e-6 for p in pp)
 out=[pins[n]for n in sorted(pins)];assert len(out)==3925 and set(pins)==keep
 occupied=set()
 for p in out:
  k=(p['layer'],p['x'],p['y']);assert k not in occupied,(variant,p);occupied.add(k)
 payload=json.dumps(out,indent=1)+'\n';(O/f'pins_{variant}_oneclk.json').write_text(payload)
 rep['profiles'][variant]={'pins':3925,'source_literal_port_set':'grown3933 minus8redundantclockports','peak_pins_per_um_10um':peaks,'pins_sha256':hashlib.sha256(payload.encode()).hexdigest(),'removed_clock_ports':sorted(clocks-{'clk'}),'full_endpoint_delta':f'pin_delta_{variant}.json','current_macro_inventory':'UNKNOWN in parent; actual source now substantiates4macro count','existing_raw_grown_B_face_failure':'vec6293 puts2802pins on270umSouthface: average10.38pins/um; replaced with balanced canonical face assignment' }
 (O/f'pin_delta_{variant}.json').write_text(json.dumps(moves,indent=1)+'\n')
(O/'macros.json').write_text(json.dumps(macros,indent=1)+'\n');(O/'estimate.json').write_text(json.dumps(rep,indent=1)+'\n');print(json.dumps(rep,indent=1))
if True:
 import matplotlib;matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 from matplotlib.patches import Rectangle
 fig,axs=plt.subplots(1,2,figsize=(10,8))
 for ax,v in zip(axs,['canonical','canonical']):
  ax.add_patch(Rectangle((0,0),W,H,fill=False))
  for m in macros:
   a,b,c,d=m['rect_um'];ax.add_patch(Rectangle((a,b),c-a,d-b,color='.8'));ax.text((a+c)/2,(b+d)/2,m['name'].split('.')[-1],ha='center');ax.add_patch(Rectangle((a-4.32,b-4.32),c-a+8.64,d-b+8.64,fill=False,linestyle='--',edgecolor='.5'))
  pp=json.load(open(O/f'pins_{v}_oneclk.json'));ax.scatter([p['x']for p in pp],[p['y']for p in pp],s=1);a,b,c,d=island;ax.add_patch(Rectangle((a,b),c-a,d-b,color='orange'));ax.plot(*root,'r*');ax.set(xlim=(-5,W+5),ylim=(-5,H+5),aspect='equal',title=v+'3925ports4SRAM\nPIN6 proposal / no physical source claim')
 fig.tight_layout();fig.savefig(O/'proposal.png',dpi=150)
