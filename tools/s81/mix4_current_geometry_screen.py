#!/usr/bin/env python3
"""Actual closed-leaf dimensions against current MIX4 reserve. Geometry only.
Conservative row alternatives enforce21.6um channels and an explicit relay row;
not a proof of minimum area, pin reach, routing capacity or parent closure.
"""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[2]
V={'mul4':'892399f17','chunk8':'23081f14a','add8':'ff40f7451','norm':'0ab4f50f0','sum':'c7bfebfff','signed_sqrt':'27a678c9a','sigmoid':'d147e15bb','mix_control':'2b910ab42','rly':'6416be4d7','mixq_shcol':'117bf9beb','mixq_shctl':'3032e848c'}
K={'mix_control':'control','mixq_shcol':'shcol','mixq_shctl':'shctl'}
ROWS=[('shell',['mixq_shcol']*2+['mixq_shctl']+['mixq_shcol']*2),('add8',['add8']*4),('mul4a',['mul4']*4),('mul4b',['mul4']*4),('relay',['rly']),('chunkA',['chunk8']*3+['sum']+['chunk8']*3),('chunkB',['chunk8']*3+['sum']*2+['chunk8']*3),('scalar',['norm','signed_sqrt','mix_control','sigmoid','norm'])]

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True,type=Path);a=ap.parse_args();O={};sources={}
 for key,ref in V.items():
  cell='ot_s81_engram_'+key;p=f'physical/ref_tile/s81engm_{K.get(key,key)}/views/{cell}/{cell}.lef';raw=subprocess.check_output(['git','show',ref+':'+p]);m=re.search(rb'SIZE\s+(\S+) BY (\S+)',raw);O[key]=[float(m[1]),float(m[2])];sources[key]={'record':ref,'path':p,'sha256':hashlib.sha256(raw).hexdigest(),'outline_um':O[key]}
 gap=21.6;w=max(sum(O[m][0]for m in row)+gap*(len(row)-1)for _,row in ROWS);boxes=[];y=0
 for tag,row in ROWS:
  rw=sum(O[m][0]for m in row)+gap*(len(row)-1);x=(w-rw)/2;h=max(O[m][1]for m in row)
  for i,m in enumerate(row):boxes.append({'name':tag+str(i),'master':m,'x':round(x,3),'y':round(y,3),'w':O[m][0],'h':O[m][1]});x+=O[m][0]+gap
  y+=h+gap
 h=round(y-gap,3);w=round(w,3);assert len(boxes)==38,len(boxes)
 overlap=[];clearance=[]
 for i,b in enumerate(boxes):
  for c in boxes[i+1:]:
   dx=max(c['x']-(b['x']+b['w']),b['x']-(c['x']+c['w']),0);dy=max(c['y']-(b['y']+b['h']),b['y']-(c['y']+c['h']),0)
   if dx==0 and dy==0:overlap.append([b['name'],c['name']])
   if min(dx,dy)==0:clearance.append(max(dx,dy))
 assert not overlap;assert min(clearance)>=21.599
 # 550um station channel and54um top strip are planning reservations, not qualified masters.
 channel,strip,edge=550.,54.,2.16
 alts=[]
 for cols,rows in [(1,4),(2,2),(4,1)]:
  ww=cols*w+(cols-1)*gap+channel+2*edge;hh=rows*h+(rows-1)*gap+strip+gap+2*edge
  alts.append({'clusters':[cols,rows],'outline_um':[round(ww,3),round(hh,3)],'area_mm2':ww*hh/1e6,'status':'CONSERVATIVE_ROW_PLAN_ONLY'})
 reserve=[1321.92,3229.2];chosen=alts[0];d={'status':'HELD_GEOMETRY_SCREEN','actual_leaf_views':sources,'cluster':{'outline_um':[w,h],'children':len(boxes),'channel_um':gap,'overlaps':0,'min_axis_clearance_um':min(clearance),'boxes':boxes},'current_reserve_um':reserve,'one_by_four_shortfall_um':[round(max(0,chosen['outline_um'][i]-reserve[i]),3)for i in range(2)],'alternatives':alts,'clock_entries_implemented_candidate':193,'station_channel_um':channel,'top_strip_um':strip,'assumptions':['Conservative row packing only, not globally minimal','Stationchannel550/topstrip54 are reservations; no actual relaystation hardview/topingress physicalproof','All leaf pin matching/reach/clocks/PG, parentfill/trialGRT and full current RTL binding remain open','Existing149 ABI hides68220relayFF onck0; 193clock candidate proof pending; prior189clock candidate preserves exact810cycles, topingress localization remains open']};a.out.mkdir(parents=True,exist_ok=True);(a.out/'screen.json').write_text(json.dumps(d,indent=1)+'\n')
 import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
 fig,ax=plt.subplots(figsize=(10,10))
 for i,b in enumerate(boxes):
  ax.add_patch(plt.Rectangle((b['x'],h-b['y']-b['h']),b['w'],b['h'],facecolor=plt.cm.tab20(i%20),alpha=.35,edgecolor='black'));ax.text(b['x']+b['w']/2,h-b['y']-b['h']/2,b['master'],ha='center',va='center',fontsize=7)
 ax.set_xlim(0,w);ax.set_ylim(0,h);ax.set_aspect('equal');ax.set_xlabel('um');ax.set_ylabel('um');ax.set_title(f'Actual MIX4 leaves: conservative {w} x {h} cluster\n21.6um channels, explicit relay row; pin/route/parent binding OPEN');fig.savefig(a.out/'cluster.png',dpi=160)
 print(json.dumps({k:d[k]for k in ['current_reserve_um','one_by_four_shortfall_um','alternatives']},indent=1))
if __name__=='__main__':main()
