import json,sys,collections,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[3];sys.path.insert(0,str(root/'tools/die_plan'))
import schema as S,gen_phys,g2
path=root/'physical/die_plan/qwen_kvsys/plan_of_record/plan_c.json';P=S.Plan(json.loads(subprocess.check_output(['git','-C',str(root),'show','63d1c1f03:physical/die_plan/qwen_kvsys/plan_of_record/plan_c.json'])),path);t=P.types['kv3_hub_Wi'];s=P.slot('hub_Wi','ft6');old=s['bit_sites_um'][-1];pins={b:(x,y) for bus,b,l,x,y,f in gen_phys.type_pins(P,'kv3_hub_Wi') if bus=='ft6_o'}
new=[[round(x-40.014,6),round(y-(34.02 if i<164 else 0),6)] for i,(x,y) in enumerate(old)]
w,h=s['bit_site_cell_um'];occup=collections.defaultdict(list)
for sl in t['ft_slots']:
 for stage,pp in enumerate(sl.get('bit_sites_um',[])):
  if sl['name']=='ft6' and stage==len(s['bit_sites_um'])-1:continue
  for b,(x,y) in enumerate(pp):occup[round(y,5)].append((x,x+w,sl['name'],stage,b))
clash=[];selfclash=[]
for i,(x,y) in enumerate(new):
 for a,b,ss,j,bb in occup[round(y,5)]:
  if x<b-1e-6 and x+w>a+1e-6:(selfclash if ss=='CANDIDATE' else clash).append((i,ss,j,bb))
 occup[round(y,5)].append((x,x+w,'CANDIDATE',3,i))
macro=[]
for i,(x,y) in enumerate(new):
 for c in t['hard_cores']:
  a,b=c['origin_um'];ww,hh=c['outline_um']
  if x+w>a-4.32 and x<a+ww+4.32 and y+h>b-4.32 and y<b+hh+4.32:macro.append((i,c['inst']))
prior=s['bit_sites_um'][-2]
def out(pp):return [abs(x+w/2-pins[i][0])+abs(y+h/2-pins[i][1])+g2.FLOP_INSET_UM for i,(x,y) in enumerate(pp)]
def prev(pp):return [abs(x-prior[i][0])+abs(y-prior[i][1]) for i,(x,y) in enumerate(pp)]
j={'scope':'PREP only; exact per-bit planned sites, no physical DB/timing qualification','bits':len(new),'translation':{'all_x_um':-40.014,'bits0_163_y_um':-34.02},'old_max_out_um':max(out(old)),'new_max_out_um':max(out(new)),'new_out_gt405':sum(x>405 for x in out(new)),'new_max_prior_um':max(prev(new)),'new_prior_gt405':sum(x>405 for x in prev(new)),'other_ft_overlap_count':len(clash),'other_ft_overlap_examples':clash[:12],'self_overlap_count':len(selfclash),'self_overlap_examples':selfclash[:12],'macro_halo_overlap_count':len(macro),'macro_overlap_examples':macro[:12]}
print(json.dumps(j,indent=1));Path(__file__).with_name('prep.json').write_text(json.dumps(j,indent=1))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
fig,axes=plt.subplots(1,2,figsize=(14,7))
for ax in axes:
 for c in t['hard_cores']:
  a,b=c['origin_um'];ww,hh=c['outline_um'];ax.add_patch(Rectangle((a,b),ww,hh,fc='#dddddd',ec='#777777'))
 for sl in t['ft_slots']:
  pp=[p for st in sl.get('bit_sites_um',[]) for p in st]
  if pp:ax.scatter([p[0] for p in pp],[p[1] for p in pp],s=.3,c='#aabbbb')
 ax.scatter([p[0] for p in old],[p[1] for p in old],s=2,c='#d95f02',label='old last FT bank')
 ax.scatter([p[0] for p in new],[p[1] for p in new],s=2,c='#0072b2',label='candidate same FF bank')
 ax.scatter([p[0] for p in pins.values()],[p[1] for p in pins.values()],s=3,c='#333333',label='unchanged mandatory pins')
 ax.set_aspect('equal');ax.set_xlabel('type-local x (um)');ax.set_ylabel('type-local y (um)')
axes[0].set_xlim(0,1278.72);axes[0].set_ylim(0,1676.16);axes[0].set_title('hub_Wi: outline, hard macros and FT banks')
axes[1].set_xlim(-10,650);axes[1].set_ylim(570,855);axes[1].set_title('L1450 last two banks and fixed output windows');axes[1].legend(loc='lower right',fontsize=8)
fig.suptitle('PREP: zero-cycle L1450 per-bit bank correction; no placement/STA credit')
fig.tight_layout();fig.savefig(str(Path(__file__).with_name('review.png')),dpi=160)
