#!/usr/bin/env python3
"""Literal candidate pin requests beside actual historical LEF occupancy.
No placement/routing/consumer-clock or physical qualification is inferred.
"""
import argparse,collections,hashlib,json,math,re,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[2]
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();rows=[]
 for typ,count in [('kvt',4),('kve',56),('kvp',8)]:
  path=f'physical/ref_tile/s81su_{typ}_ref/views/dsfd_su_t_{typ}/dsfd_su_t_{typ}.lef';raw=subprocess.check_output(['git','-C',str(R),'show','HEAD:'+path]);text=raw.decode();w,h=map(float,re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)',text).groups());old=[]
  for m in re.finditer(r'\n  PIN (\S+)\n(.*?)(?=\n  END )',text,re.S):
   name,body=m.groups();direction=re.search(r'DIRECTION (\S+)',body)[1];layer=None
   for line in body.splitlines():
    lm=re.search(r'LAYER (\S+)',line)
    if lm:layer=lm[1]
    rm=re.search(r'RECT\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)',line)
    if rm:
     rect=list(map(float,rm.groups()));x,y=(rect[0]+rect[2])/2,(rect[1]+rect[3])/2;dist={'W':x,'E':w-x,'S':y,'N':h-y};old.append(dict(pin=name,direction=direction,layer=layer,rect_um=rect,nearest_face=min(dist,key=dist.get)))
  names=([f'e_mode[{i}]' for i in range(2)]+[f'e_nb[{i}]' for i in range(14)]) if typ=='kvt' else ['norm_v']+[f'norm_y[{i}]' for i in range(128)]
  face,layer=('N','M5') if typ=='kvt' else ('E','M4');length=w if face=='N' else h;pitch=.48;start=math.floor(((length-pitch*(len(names)-1))/2-.06)/.096)*.096+.06;new=[]
  for i,n in enumerate(names):
   t=round(start+i*pitch,6);rect=[round(t-.02,6),round(h-.12,6),round(t+.02,6),h] if face=='N' else [round(w-.12,6),round(t-.02,6),w,round(t+.02,6)]
   conflicts=[o['pin'] for o in old if o['layer']==layer and max(rect[0],o['rect_um'][0])<min(rect[2],o['rect_um'][2]) and max(rect[1],o['rect_um'][1])<min(rect[3],o['rect_um'][3])]
   assert not conflicts,(typ,n,conflicts)
   new.append(dict(pin=n,direction='OUTPUT',face=face,layer=layer,rect_um=rect,old_same_layer_pin_rect_overlaps=conflicts))
  uniq={x['pin']:x for x in old};data_in=sum(o['direction']=='INPUT' and n not in ('ck','rst') for n,o in uniq.items());data_out=sum(o['direction']=='OUTPUT' for o in uniq.values());rows.append(dict(top='dsfd_su_t_'+typ+'_current',instances=count,outline_um=[w,h],old_lef=dict(path=path,sha256=hashlib.sha256(raw).hexdigest(),pin_count=len(uniq),face_direction_counts=dict(collections.Counter(x['nearest_face']+':'+x['direction'] for x in uniq.values())),all_pin_rectangles=old),new_pins=new,recipe3_pin_register_bits_per_leaf=data_in+data_out+len(new),recipe3_edges=dict(input=1,output=1),consumer_intent='KVT mode/base outputs north to local CN/IK write-control strip; actual placement unassigned.' if typ=='kvt' else 'Pre-RoPE BF16 norm branch east to g_kvq[*].u_cn_norm_write (groups of four native engines); writer/control physical homes unassigned.',open=['Proposed new rects have no same-layer old PIN overlap only; OBS/vias/spacing/reach/cut/nativeCTS/TTFF/DRC remain unchecked.','Need actual consumer homes/registered seam assignment; these coordinates are a die pin request, not an adopted grant.','Historical old clocks/insertion/views do not qualify these current source masters.']))
 a.out.write_text(json.dumps(dict(scope='Independent current wrapper candidate pin request under S-DIE diagnostic outline grant, not physical closure or floorplan adoption',new_output_pin_instances=sum(len(x['new_pins'])*x['instances'] for x in rows),masters=rows),indent=1)+'\n');print(json.dumps([{k:v for k,v in x.items() if k in ['top','instances','outline_um','recipe3_pin_register_bits_per_leaf','consumer_intent']} for x in rows]))
if __name__=='__main__':main()
