#!/usr/bin/env python3
"""Place read data by actual physical source slice and preserve coherent CDC atoms.
A complete-known-hard-rectangle development candidate, with all incident pin legs audited separately.
"""
import argparse,json,pathlib,re

def shelf(ids,leaves,width):
 pos={};rows=[];height=0
 for i in sorted(ids,key=lambda i:(-leaves[i]['outline_um'][1],-leaves[i]['outline_um'][0])):
  w,h=leaves[i]['outline_um'];eligible=[(rr[1]-w,j)for j,rr in enumerate(rows)if rr[1]>=w and rr[2]>=h]
  if eligible:
   _,j=min(eligible);y,free,rh,x=rows[j];rows[j]=[y,free-w-21.6,rh,x+w+21.6]
  else:y=height;x=0;rows.append([y,width-w-21.6,h,w+21.6]);height=y+h+21.6
  pos[str(i)]=[x,y]
 return pos,height-21.6

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=pathlib.Path,required=True);a=ap.parse_args();r=a.root;iv=json.load(open(r/'inventory.json'));base=json.load(open(r/'packing.json'));co=json.load(open(r/'coherent_groups.json'));leaves=iv['leaves'];start=base['options'][4];fixed={x['leaf']for x in base['source_binding']};pos={str(i):start['positions'][str(i)]for i in fixed};read_islands=[];used=set(fixed)
 for s in range(4):
  ids=[x['leaf']for x in co['read_data_ownership']if x['physical_slice']==s]
  ids += [i for i,x in enumerate(leaves)if re.search(r'u_mem.slice\['+str(s)+r'\].',x['path'])and (x['master'].startswith('dsfd_vm_static_return_bank8_l')or x['master'].startswith('dsfd_vm_static_fsr_b'))]
  assert len(ids)==24 and not set(ids)&used
  pp,h=shelf(ids,leaves,777.6);assert h<2440.8,h
  origin=[1987.2,2462.4*s+(2440.8-h)/2]
  for key,xy in pp.items():pos[key]=[xy[k]+origin[k]for k in [0,1]]
  read_islands.append(dict(physical_slice=s,leaf_count=24,origin_um=origin,outline_um=[777.6,h],leaf_ids=ids));used.update(ids)
 # All cap/CDC atoms occupy a separate real strip; exact R0 local pins remain unchanged.
 groups=co['groups'];x=2786.4;y=0;rowh=0;free=756.0;xx=0;atom_homes=[]
 for g in sorted(groups,key=lambda g:(-g['outline_um'][1],-g['outline_um'][0])):
  w,h=g['outline_um']
  if free<w:y+=rowh+21.6;rowh=0;xx=0;free=756
  for key,xy in g['positions'].items():assert int(key)not in used;pos[key]=[x+xx+xy[0],y+xy[1]];used.add(int(key))
  atom_homes.append(dict(group=g['name'],origin_um=[x+xx,y]));xx+=w+21.6;free-=w+21.6;rowh=max(rowh,h)
 y+=rowh+21.6
 rest=set(range(len(leaves)))-used;pp,h=shelf(rest,leaves,756)
 # Place shared control at the central physical epoch of the four stacked slices.
 origin=[2786.4,max(y,4320.0)]
 for key,xy in pp.items():pos[key]=[xy[k]+origin[k]for k in [0,1]]
 assert len(pos)==640
 collision=[];outside=[];items=list(pos.items());W,H=3542.4,9828.0
 for n,(key,xy)in enumerate(items):
  w,h=leaves[int(key)]['outline_um']
  if xy[0]<0 or xy[1]<0 or xy[0]+w>W+1e-6 or xy[1]+h>H+1e-6:outside.append(key)
  for other,XY in items[n+1:]:
   ww,hh=leaves[int(other)]['outline_um']
   if xy[0]<XY[0]+ww-1e-6 and xy[0]+w>XY[0]+1e-6 and xy[1]<XY[1]+hh-1e-6 and xy[1]+h>XY[1]+1e-6:collision.append([key,other])
 assert not collision and not outside,(collision[:3],outside)
 option=dict(name='body1x4v_source_slice_reads_coherent_CDC',outline_um=[W,H],positions=pos,placed_hard_leaves=640,collisions=collision,outside=outside,read_islands=read_islands,coherent_atom_homes=atom_homes)
 rec=dict(scope='NATIVE_CANDIDATE_READ_PIPE4_CAP_PIPE2_NOT_GENERATOR_ADOPTED',source_commit=iv['source_commit'],options=[option],not_claimed=['Full parent WFC/XIO control hardware absent','No new RTL/register/edge/clock root/physical producer external home invented','Actual whole-die placement and cut/static-calendar/native closure absent'])
 (r/'packing_producer_local.json').write_text(json.dumps(rec,indent=1)+'\n');print(json.dumps(dict(outline_um=[W,H],placed=len(pos),read_islands=read_islands),indent=1))
if __name__=='__main__':main()
