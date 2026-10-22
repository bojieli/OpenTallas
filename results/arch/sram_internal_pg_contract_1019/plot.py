#!/usr/bin/env python3
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
P=Path(__file__).resolve().parent;m=json.loads((P/'model.json').read_text());base=json.loads((P/'input/c634_model.json').read_text())
fig,axs=plt.subplots(2,3,figsize=(17,10),layout='constrained')
colors={'VDD':'#bd362f','VSS':'#245da8'}
def box(ax,r,**kw):ax.add_patch(Rectangle((r[0]/1000,r[1]/1000),(r[2]-r[0])/1000,(r[3]-r[1])/1000,**kw))
for row,(f,v) in enumerate(m['families'].items()):
 ax=axs[row,0];w,h=v['outline_nm'];cb=v['original_bitcore_bbox_nm'];box(ax,[0,0,w,h],fill=False,edgecolor='black');box(ax,cb,facecolor='#dedede',edgecolor='#777777',alpha=.6)
 if v['north_attachment_apron_height_nm']:
  a=v['new_attachment_core_bbox_nm'];box(ax,[a[0],cb[3],a[2],a[3]],facecolor='#ffbf47',edgecolor='#ad7100')
 for s in base['families'][f]['signal_ledger']:
  for z in s['new_shapes']:box(ax,z['rect_nm'],facecolor='#a4a4a4',edgecolor='none',alpha=.65)
 for z in v['new_actual_supply_metal']:
  if z['layer'] in ['M4','M5']:box(ax,z['rect_nm'],facecolor=colors[z['net']],edgecolor='none')
 for z in v['lower_core_exclusions']:box(ax,z['rect_nm'],facecolor='#28a085',edgecolor='none')
 ax.set_xlim(-w*.025/1000,w*1.025/1000);ax.set_ylim(-h*.04/1000,h*1.04/1000);ax.set_aspect('equal');ax.set_title(f.upper()+' complete actual modeled supply + known access\nGrey: bitcore reservation; green: lower exclusions')
 for col,rr in [(1,v['contact_ledger'][0]),(2,max(v['contact_ledger'],key=lambda z:z['c634_rail_unchanged_nm'][3]))]:
  ax=axs[row,col];x,y0=rr['new_M1_core_port_center_nm'];rail=rr['c634_rail_unchanged_nm'];y=(rail[1]+rail[3])//2;trunk=next(t for t in json.loads((P/'input/899b_model.json').read_text())['families'][f]['trunks'] if t['net']==rr['net']);tx=trunk['center_x_nm']
  box(ax,rr['lower_core_exclusion']['rect_nm'],facecolor='#dcf0e8',edgecolor='#15916e',linestyle='--')
  for z in v['new_actual_supply_metal']:
   if z['id'].startswith(rr['id']+':') or z['role']=='full_height_internal_supply_trunk':
    box(ax,z['rect_nm'],facecolor=colors[z['net']],edgecolor='none',alpha=.25 if z['layer']=='M4' else .6)
  for z in rr['pads']:box(ax,z['rect_nm'],fill=False,edgecolor={'M1':'#9b45b3','M2':'#f28b22','M3':'#168d50'}[z['layer']],linewidth=1.5)
  for vv in rr['via_stacks']:
   for z in vv['objects']:
    if z['layer'].startswith('V'):box(ax,z['rect_nm'],facecolor='black',edgecolor='black',alpha=.75)
  ax.axhline(cb[3]/1000,color='#777777',linestyle=':',linewidth=1)
  ax.set_xlim((min(x,tx)-90)/1000,(max(x,tx)+90)/1000);ax.set_ylim((y-108)/1000,(y+108)/1000);ax.set_aspect('equal')
  ax.set_title(rr['id']+' '+rr['net']+'\nM1 purple / M2 orange / M3 green / cuts black')
  ax.annotate('M1 core port\nV1/V2/V3 stack',(x/1000,y0/1000),xytext=((x-50)/1000,(y+75)/1000),fontsize=8,arrowprops={'arrowstyle':'->'})
  ax.annotate('V4 → M5 trunk',(tx/1000,y/1000),xytext=((tx-60)/1000,(y-90)/1000),fontsize=8,arrowprops={'arrowstyle':'->'})
 for ax in axs[row]:ax.set_xlabel('X µm');ax.set_ylabel('Y µm');ax.grid(alpha=.15)
fig.suptitle('NEW ANALYTICAL MASTER: explicit internal supply occupancy and lower-core interfaces\nFinite geometry contract only — no native AP / PDN / transistor / timing qualification',fontsize=15)
fig.savefig(P/'internal_pg_contract.png',dpi=180)
