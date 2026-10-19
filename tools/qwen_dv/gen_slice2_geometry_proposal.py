#!/usr/bin/env python3
"""Non-gating source-bound body allocation proposal; no soft-area or clock claim."""
from pathlib import Path
import json,re,hashlib,math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
root=Path(__file__).resolve().parents[2];out=root/'results/arch/safe_qw_slice_w_1019'
spec=json.loads((root/'physical/ref_tile/qfd_dv_slice2_wh/spec.json').read_text())
def size(view):
 files=list((root/view).glob('*.lef'));assert len(files)==1,view
 s=files[0].read_text();m=re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)',s);assert m,view
 return [float(m[1]),float(m[2])]
objects=[]
for i,m in enumerate(spec['macros']):
 v=m['view'];w,h=size(v)
 if i<10:x,y=129.6+216*i,475.2
 else:
  positions=[129.6,259.2,388.8,518.4,648,864,1080,1209.6,1339.2,1468.8,1598.4,1814.4]
  x,y=positions[i-10],604.8
 objects.append(dict(kind='legacy_VM_native_body_escape_pending',view=v,at=[x,y],size_um=[w,h],name=f'VM{i}'))
for c in spec['children']:
 c=dict(c);x,y=c['at'];w,h=size(c['view']);kind='closed_SFU_body'
 if 'qfd_dv_lane_h' in c['view']:
  kind='new_native_head_reserved_unqualified';w,h=216,172.8
 elif 'ot_qfd_xs_leaf' in c['view']:kind='xs_leaf_reserved_unqualified'
 # Reserve216x172.8 head slot; move adjacent SFUs on exact lattice.
 if 'g_lane' in c['inst']:
  if int(re.search(r'g_lane\?(\d+)\?',c['inst'])[1])>=4:y+=43.2
  if 'u_rcp' in c['inst']:x+=43.2
  if 'u_exp' in c['inst'] or 'u_rsq' in c['inst']:y+=43.2
 objects.append(dict(kind=kind,view=c['view'],at=[round(x/43.2)*43.2,round(y/43.2)*43.2],size_um=[w,h],name=c['inst']))
clients=[('u_sks',514,9,(43.2,1080)),('u_skn',514,9,(345.6,1080)),('u_hb',512,8,(43.2,1252.8)),('u_h9',512,8,(345.6,1252.8)),('u_scale_wait',512,8,(43.2,1425.6))]
view='physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1';w,h=size(view);groups=[]
for client,width,n,(gx,gy) in clients:
 group=dict(client=client,useful_bits=width,banks=n,masked_tail_bits=64*n-width,allocation_um=[gx,gy,302.4,172.8],clock_root='ck_core',clock_sinks=n,clock_entry_candidate_um=[gx+151.2,gy+86.4],status='ALLOCATED_NATIVE_BODIES_ONLY_NO_CTS_OR_ESCAPE_PROOF');groups.append(group)
 for b in range(n):
  objects.append(dict(kind='new_native32x64_body',view=view,at=[gx+43.2+86.4*(b%3),gy+43.2+43.2*(b//3)],size_um=[w,h],name=f'u_c.u_stn.{client}.u_m.g_bank[{b}].u_m',clock_pin='clk'))
issues=[]
for a in objects:
 x,y=a['at'];w,h=a['size_um']
 if any(abs(v/43.2-round(v/43.2))>1e-6 for v in [x,y]):issues.append('nonlattice '+a['name'])
 if x<20 or y<20 or x+w>2462.376-20 or y+h>2591.976-20:issues.append('boundary '+a['name'])
for i,a in enumerate(objects):
 for b in objects[i+1:]:
  ax,ay=a['at'];aw,ah=a['size_um'];bx,by=b['at'];bw,bh=b['size_um']
  dx=max(ax-bx-bw,bx-ax-aw,0);dy=max(ay-by-bh,by-ay-ah,0)
  # Chebyshev separation is conservative for diagonal pin-face escape.
  if max(dx,dy)<20-1e-5:issues.append('gap<20 '+a['name']+' / '+b['name'])
plan=dict(status='GEOMETRY_PROPOSAL_NOT_KIT_OR_GATE',outline_um=[2462.376,2591.976],native_macro_origins_grid_um=43.2,min_body_channel_um=20,objects=objects,storage_groups=groups,body_clearance_issues=issues,clock_contract='42 storage +22 VM native clock pins on core root; group entry candidates are physical distribution anchors, not new roots or closed CTS. All native TT/FF phase/arrival and final unbuffered reach<=405 remain owed.',reset_contract='No reset placement claim. Core320/lpc leaves and soft child forests need measured assignment/reach; add and price release stages if two <=405um tree levels cannot reach.',std_band_contract='Unallocated remaining space is not a utilization claim. Mapped real soft area and routed channels are required before kit generation.',pending=['all memory PG/via pin-access and native clocks','native ML5/RD2 and xs_leaf views','legacy VM raw-pin escape/GRT/DRC','source combined stream/station reset and exact native SRAM-model production','mapped soft area and placement bands','regional clock entry, source-forwarded hop and reset physical proof'])
(out/'geometry_proposal.json').write_text(json.dumps(plan,indent=2)+'\n')
colors={'legacy_VM_native_body_escape_pending':'#a6cee3','new_native32x64_body':'#33a02c','closed_SFU_body':'#b2df8a','new_native_head_reserved_unqualified':'#fdbf6f','xs_leaf_reserved_unqualified':'#cab2d6'}
fig,ax=plt.subplots(figsize=(10,10.5));ax.add_patch(Rectangle((0,0),2462.376,2591.976,fill=False,color='black'))
for a in objects:
 x,y=a['at'];w,h=a['size_um'];ax.add_patch(Rectangle((x,y),w,h,facecolor=colors[a['kind']],edgecolor='#333',linewidth=.4))
for g in groups:
 x,y,w,h=g['allocation_um'];ax.add_patch(Rectangle((x,y),w,h,fill=False,edgecolor='green',linestyle='--',linewidth=.8));ax.text(x+7,y+10,g['client'],fontsize=6)
ax.set(xlim=(-50,2510),ylim=(-50,2640),xlabel='um',ylabel='um',aspect='equal',title='SAFE-QW-SLICE regional geometry proposal\n42 native storage banks; native head / xs leaf / escape / CTS pending')
handles=[Rectangle((0,0),1,1,facecolor=c,label=k.replace('_',' ')) for k,c in colors.items()];ax.legend(handles=handles,fontsize=7,loc='upper left');ax.grid(alpha=.15)
fig.tight_layout();fig.savefig(out/'geometry_proposal.png',dpi=160);plt.close(fig)
print('objects',len(objects),'storage',sum(g['banks'] for g in groups),'clearance issues',issues)
