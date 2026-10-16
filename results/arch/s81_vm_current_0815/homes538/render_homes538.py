#!/usr/bin/env python3
"""Lightweight rendering/incident audit of an existing held actual-pin home JSON."""
import argparse,collections,gzip,json,math
from pathlib import Path
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.patches import Rectangle,Patch

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--registry',type=Path,required=True);ap.add_argument('--graph',type=Path,required=True);ap.add_argument('--homes',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 bindings=json.loads((a.registry/'leaves.json').read_text())['leaves'];home=json.loads(a.homes.read_text());P=home['placement'];W,H=home['outline_um']
 with gzip.open(a.registry/'models.json.gz','rt')as f:models=json.load(f)
 def xy(i,p,b):
  l=bindings[i];q=P[l['path']];n=p+f'[{b}]'if l['ports'][p]['bits']>1 else p;m=models[l['pin_source']]['pins'];n=n if n in m else p+'[0]';x,y=m[n]['anchor_um'];return (q['x_um']+(q['w_um']-x if q['flip_x']else x),q['y_um']+(q['h_um']-y if q['flip_y']else y))
 bundles={};families=collections.defaultdict(list);longest=[]
 with gzip.open(a.graph/'pin_join.jsonl.gz','rt')as f:
  for line in f:
   z=json.loads(line)
   if z['status']=='CONSTANT':continue
   for i,p,b,d in z['consumers']:
    if i<0:continue
    for j,q,c,dd in z['drivers']:
     if j<0 or i==j:continue
     x,y=xy(j,q,c);u,v=xy(i,p,b);dist=abs(x-u)+abs(y-v);key=(j,q,i,p)
     if key not in bundles:bundles[key]=[0,0.,0.,0.,0.,0.,0.]
     row=bundles[key];row[0]+=1;row[1]+=x;row[2]+=y;row[3]+=u;row[4]+=v;row[5]+=dist;row[6]=max(row[6],dist)
     families[(bindings[j]['master'],q,bindings[i]['master'],p)].append(dist)
     if dist>4000:longest.append(dict(source=bindings[j]['path'],source_port=q,source_bit=c,target=bindings[i]['path'],target_port=p,target_bit=b,manhattan_um=dist))
 fs=[]
 for k,vs in families.items():fs.append(dict(source_master=k[0],source_port=k[1],target_master=k[2],target_port=k[3],bit_pairs=len(vs),star_bit_um=sum(vs),max_um=max(vs),over400um=sum(v>400 for v in vs)))
 fs.sort(key=lambda x:-x['star_bit_um']);longest.sort(key=lambda x:-x['manhattan_um'])
 audit=dict(scope='Actual direct hard-to-hard pin pair geometry only; partial parent grants, soft operators, clock trees and routing capacity remain open. Star pair lengths are not routing demand or cut.',case=home['case'],families=fs,longest100=longest[:100],bundles=len(bundles),bit_pairs=sum(r[0]for r in bundles.values()))
 (a.out/(home['case']+'_incident.json')).write_text(json.dumps(audit,indent=1)+'\n')
 def color(m):
  if m=='dsfd_vm_static_bank128':return '#bdd0e2'
  if 'payload33'in m:return '#9f79ba'
  if 'field4'in m:return '#a3c4a8'
  if 'read_q'in m or 'return_bank'in m:return '#77b0ca'
  if 'wfc'in m or 'xio'in m:return '#ef927a'
  if 'fault'in m or 'diag'in m:return '#ebce71'
  return '#cecece'
 fig,ax=plt.subplots(figsize=(16,14));lines=[];widths=[];colors=[]
 for (j,q,i,p),r in bundles.items():
  n,x,y,u,v,_,_=r;lines.append([(x/n,y/n),(u/n,v/n)]);widths.append(min(1.2,.1+n/2000));colors.append('#9a352b'if bindings[i]['master']in ('dsfd_vm_xio_return','dsfd_vm_wfc_return')else'#555555')
 ax.add_collection(LineCollection(lines,linewidths=widths,colors=colors,alpha=.10,zorder=1))
 clocks=[]
 for i,l in enumerate(bindings):
  q=P[l['path']];x,y,w,h=[q[k]for k in ['x_um','y_um','w_um','h_um']];ax.add_patch(Rectangle((x,y),w,h,facecolor=color(l['master']),edgecolor=('#bd1212' if l['path']=='dut.u_wfc.u_ret' else '#555555'),hatch=('///' if l['path']=='dut.u_wfc.u_ret' else None),linewidth=(1.2 if l['path']=='dut.u_wfc.u_ret' else .3),zorder=2))
  for p in l['ports']:
   if p=='ck'or p.endswith('_ck')or p.startswith('ck_'):clocks.append(xy(i,p,0))
  if 'wfc'in l['master']or'xio'in l['master']or'native_valid_diag'in l['master']:ax.text(x+w/2,y+h/2,l['path'].removeprefix('dut.').replace('u_',''),fontsize=4.5,ha='center',va='center',zorder=4)
 ax.scatter(*zip(*clocks),s=1.6,c='#b5101d',zorder=3)
 for i,l in enumerate(bindings):
  q=P[l['path']];ax.text(q['x_um']+q['w_um']/2,q['y_um']+q['h_um']/2,str(i),fontsize=2.5,ha='center',va='center',zorder=4)
 ax.text(15,H-60,'N: actual capture sources; external capture grant unresolved',fontsize=8,color='#992222')
 ax.text(W/2,20,'S: SU adjacency under owner review; no boundary pin grant assumed',fontsize=8,color='#992222',ha='center')

 ax.set(xlim=(0,W),ylim=(0,H),aspect='equal',xlabel='VM-local x (um)',ylabel='VM-local y (um)',title=f"{home['case']}:538 actual hard leaves /128 SRAM, PREVIEW ONLY\nActual leaf rectangles / signal pins / clock entries; frame is search bounds only. ALL external boundary grants and hf OR home unresolved")
 ax.legend(handles=[Patch(facecolor=color(m),label=t)for m,t in [('dsfd_vm_static_bank128','128 bank/SRAM'),('s81_a2f_field4','Field4'),('s81_a2_w0_payload33','Payload33 x16'),('dsfd_vm_static_read_q6_p','Read/return'),('dsfd_vm_xio_return','WFC/XIO'),('dsfd_vm_native_valid_diag','Diagnostics')]],loc='upper left',fontsize=7)
 fig.tight_layout();fig.savefig(a.out/(home['case']+'_connected.png'),dpi=155);ax.set(xlim=(0,W),ylim=(1450,2350));fig.set_size_inches(18,5);fig.tight_layout();fig.savefig(a.out/(home['case']+'_middle.png'),dpi=165);plt.close(fig)
 print(home['case'],'largest families',fs[:5]);print('LONGEST',longest[0]if longest else None)
if __name__=='__main__':main()
