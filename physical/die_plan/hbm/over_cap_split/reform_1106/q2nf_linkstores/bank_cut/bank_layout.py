"""Render two bank-store helpers and soft controller; no physical launch."""
import json,re,collections
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
base=Path(__file__).resolve().parent
old=json.loads((base.parent/'q2nf_parent_candidate.json').read_text())
cl=json.loads((base/'boundary_clocks_bank.json').read_text())
W,H=old['parent_outline_um'];fig,ax=plt.subplots(figsize=(13,10))
ax.add_patch(Rectangle((0,0),W,H,fc='#e4efd7',ec='black'))
children={k:v for k,v in old['children'].items() if k!='rest_control'}
fields=[];pins=[]
for idx,(key,ch) in enumerate(children.items()):
 x,y=ch['origin_um'];w,h=ch['outline_um'];g='g_linkstore'+str(idx);face=x+w if idx==0 else x
 ax.add_patch(Rectangle((x,y),w,h,fc='#cce0f4',ec='black',lw=1.5))
 ax.text(x+w/2,y+h-12,key+' bank-store',ha='center',fontsize=11)
 group=collections.defaultdict(list)
 for row in cl['boundaries'][g]:
  if 'clock' in row['child_sink_roles']:continue
  domains=row['consumer_domains'] if row['direction']=='input' else row['producer_domains']
  bank=[int(re.fullmatch(r'clk_link\[(\d+)\]',c)[1])-(1 if idx==0 else 6) for c in domains if re.fullmatch(r'clk_link\[(\d+)\]',c)]
  slot=bank[0] if len(bank)==1 else -1
  group[slot].append(row)
 for slot,rows in sorted(group.items()):
  cy=(249.384,327.24,415.896,493.752)[slot] if slot>=0 else y+20
  start=round((cy-(len(rows)-1)*.192/2-.024)/.048)*.048+.024
  assert y+4.32<start and start+len(rows)*.192<y+h-4.32
  for j,row in enumerate(rows):pins.append(dict(child=key,raw_bit=row['raw_bit'],net=row['net'],direction=row['direction'],xy_um=[face,round(start+j*.192,6)],layer='M4',original_parent_domains=row['consumer_domains'] if row['direction']=='input' else row['producer_domains']))
  fields.append(dict(child=key,bank=slot,bits=len(rows),face='E'if idx==0 else'W',x_um=face,y_um=[start,start+(len(rows)-1)*.192],pitch_um=.192))
  ax.plot([face,face],[start,start+(len(rows)-1)*.192],lw=6,color='#c3493a')
  ax.text(face+(8 if idx==0 else -8),cy,f'{len(rows)}b',ha='left'if idx==0 else'right',fontsize=8,color='#a42823')
for row in old['macros']:
 x,y,X,Y=row['rect_um'];ax.add_patch(Rectangle((x,y),X-x,Y-y,fc='#8995a5',ec='white',lw=.5))
 if row['owner'] in ('link0','link1'):ax.text((x+X)/2,(y+Y)/2,'MY -> live E'if row['owner']=='link0'else'live W <- R0',ha='center',va='center',fontsize=8)
ax.text(393,117,'SOFT controller + retained external R2 shell\n115,864 mapped stdcells; placement not yet qualified',ha='center',fontsize=11)
ax.text(392,52,'Zero new edges; original indexed bank clocks\nPG/OBS and actual first-capture sites remain open',ha='center',fontsize=10,color='#a42823')
ax.set(xlim=(0,W),ylim=(0,H),aspect='equal',xlabel='x (um)',ylabel='y (um)',title='Q2NF bank-focused candidate: two hard bank stores, soft full-footprint parent\nAll 19 measured SRAM sites retained; indexed data fields are preparation only')
fig.tight_layout();fig.savefig(base/'bank_parent_review.png',dpi=140)
area=W*H-sum(v['outline_um'][0]*v['outline_um'][1]for v in children.values())-sum((m['rect_um'][2]-m['rect_um'][0])*(m['rect_um'][3]-m['rect_um'][1])for m in old['macros']if m['owner']=='rest_control')
report=dict(schema='q2nf.bank_geometry_prep.v1',parent_outline_um=[W,H],hard_children=children,soft_controller_macros=[m for m in old['macros']if m['owner']=='rest_control'],all_19_sram_sites_preserved=True,hard_child_channel_um=21.6,controller_free_area_before_halos_um2=area,controller_nominal_capacity_at_45_um2=area*.45,controller_mapped_cell_area_um2=18460.78776,fields=fields,raw_bit_pin_candidates=pins,macro_orientation_contract={'link0':'MY','link1':'R0'},extra_cycles=0,status='PREP_ONLY; no physical release',remaining=['exact mapped sequential first-capture/launch and clock alias census','real generated pin geometry and access','real supply metal and parent landing/OBS','actual standard-cell/clock/reset placement in retained R2 parent'])
(base/'bank_parent_candidate.json').write_text(json.dumps(report,indent=2)+'\n')
print({k:report[k]for k in ['controller_free_area_before_halos_um2','controller_nominal_capacity_at_45_um2','controller_mapped_cell_area_um2']});print('pins',len(pins))
