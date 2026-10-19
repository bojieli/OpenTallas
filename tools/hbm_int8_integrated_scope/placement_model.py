import json,pathlib,math
P=pathlib.Path(__file__).parent;J=json.load(open(P/'positions.json'));M=json.load(open(P/'model.json'));u=J['units'];old=J['insts'];mods={};extras=[];branches={}
for b in M['boundary']:mods[b['driver']['cell']]=('INVx6_ASAP7_75t_R',.432)
for n,c in M['typed_cones'].items():
 d=next(z for z in c['native_pins'] if z['direction']=='output');name=d['cell']
 if d['master'].startswith('NAND'):mods[name]=('NAND2x2_ASAP7_75t_R',.54);continue
 mods[name]=('INVx6_ASAP7_75t_R',.432);x,y,_,_=old[name]['bbox'];extras.append((f'int8_reset_{n}_b1_inv','INVx6_ASAP7_75t_R',.432,x,y))
 sinks=sorted([z for z in c['native_pins'] if z['direction']=='input'],key=lambda z:(old[z['cell']]['bbox'][1],old[z['cell']]['bbox'][0],z['cell']));assert len(sinks)==24
 branches[n]=[sinks[:12],sinks[12:]]
 for b in range(2):
  for k in range(4):extras.append((f'int8_reset_{n}_b{b}_hb{k}','HB4xp67_ASAP7_75t_R',.378,x,y))
hold='$abc$36464$auto$blifparse.cc:397:parse_blif$37773';x,y,_,_=old[hold]['bbox']
for k in range(3):extras.append((f'int8_hold_37773_hb{k}','HB4xp67_ASAP7_75t_R',.378,x,y))
rows=sorted(J['rows'],key=lambda r:(r[1],r[0]));occ=[[] for _ in rows]
for name,c in old.items():
 if name in mods:continue
 x,y,X,Y=c['bbox']
 for i,r in enumerate(rows):
  if y<r[3] and Y>r[1]:occ[i].append((x,X))
for v in occ:v.sort()
def allocate(name,master,width,x,y):
 w=round(width*u);candidates=[]
 for i,r in enumerate(rows):
  if abs(r[1]-y)>10000:continue
  a=r[0];gaps=[]
  for l,h in occ[i]:
   if l-a>=w:gaps.append((a,l))
   a=max(a,h)
  if r[2]-a>=w:gaps.append((a,r[2]))
  for a,b in gaps:
   # Original site is .054um; use exact row origin phase.
   lo=r[0]+math.ceil((a-r[0])/54)*54;hi=r[0]+math.floor((b-w-r[0])/54)*54
   if hi<lo:continue
   xx=min(hi,max(lo,r[0]+round((x-r[0])/54)*54));cost=abs(xx-x)+abs(r[1]-y);candidates.append((cost,i,xx))
 assert candidates,name
 cost,i,xx=min(candidates);r=rows[i];occ[i].append((xx,xx+w));occ[i].sort();return {'name':name,'master':master,'bbox':[xx,r[1],xx+w,r[1]+270],'displacement_um':cost/u,'row':i,'orientation_by_native_row':'inherit existing legal row orientation; native legalization must verify'}
placed=[]
for n,(master,w) in sorted(mods.items()):
 x,y,_,_=old[n]['bbox'];placed.append(allocate(n,master,w,x,y))
for n,m,w,x,y in extras:placed.append(allocate(n,m,w,x,y))
json.dump({'scope':'offline MODEL packing only, no native placement or ECO invoked','source_positions_units':u,'replacements':len(mods),'added_cells':len(extras),'max_replacement_displacement_um':max(p['displacement_um'] for p in placed[:len(mods)]),'max_added_displacement_um':max(p['displacement_um'] for p in placed[len(mods):]),'all_clock_and_unchanged_cells_fixed':True,'site_um':.054,'row_height_um':.27,'placed':placed,'reset_branch_exact_native_sinks':branches},open(P/'placement_model.json','w'),indent=2)
print('PACKING_MODEL',len(mods),len(extras),'maxmove',max(p['displacement_um'] for p in placed))
