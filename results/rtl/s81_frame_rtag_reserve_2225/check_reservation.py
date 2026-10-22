import subprocess,json,re,pathlib
cache={}
def show(r,p):return subprocess.check_output(['git','show',r+':'+p])
def size(r,v):
 k=(r,v)
 if k not in cache:
  p=v+'/'+v.rsplit('/',1)[-1]+'.lef'
  try:t=show(r,p).decode()
  except subprocess.CalledProcessError:
   fs=subprocess.check_output(['git','ls-tree','-r','--name-only',r,v],text=True).splitlines();p=next(x for x in fs if x.endswith('.lef') and '/provenance/' not in x);t=show(r,p).decode()
  m=re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)',t);assert m,(r,v);cache[k]=[float(x) for x in m.groups()]
 return cache[k]
out=[]
full=[]
for r,k,ids in [('bbfd0c0f5','s81frame_col_h9_rf3rlfs1x',[4,8,13]),('9f6b8434e','s81frame_col_h10_rf3rlfs1x',[1,5,10,15]),('9f6b8434e','s81frame_col_h10_rf3rlfs1y',[1,5,10,15])]:
 s=json.loads(show(r,'physical/ref_tile/'+k+'/spec.json'));boxes=[]
 for c in s['children']+s['macros']:
  w,h=size(r,c['view']);x,y=c['at'];orient=c.get('orient','R0')
  if orient in ['R90','R270','MXR90','MYR90']:w,h=h,w
  boxes.append(dict(inst=c['inst'],view=c['view'],x=x,y=y,w=w,h=h,orient=orient))
 fronts=[]
 for b in boxes:
  if b['inst'] not in ['u_e'+str(i) for i in ids]:continue
  old=dict(b);assert abs(b['w']-116.64)<1e-4 and abs(b['h']-198.72)<1e-4;b['h']=246.24
  over=[];near=[]
  for c in boxes:
   if c is b:continue
   ox=min(b['x']+b['w'],c['x']+c['w'])-max(b['x'],c['x']);oy=min(b['y']+b['h'],c['y']+c['h'])-max(b['y'],c['y'])
   if ox>1e-5 and oy>1e-5:over.append(dict(inst=c['inst'],overlap=[ox,oy]))
   if ox>1e-5:
    gap=max(c['y']-(b['y']+b['h']),b['y']-(c['y']+c['h']))
    if 0<=gap<100:near.append(dict(inst=c['inst'],vertical_gap_um=round(gap,4),shared_x_um=round(ox,4)))
  fronts.append(dict(inst=b['inst'],at=[b['x'],b['y']],old_size=[old['w'],old['h']],proposed_size=[b['w'],b['h']],overlaps=over,near_vertical=near,top_margin_um=round(s['outline']['h']-b['y']-b['h'],4)))
 cuts=sorted(f['at'][1]+241.92 for f in fronts if f['overlaps'])
 def shift(y):return round(y+43.2*sum(y>=cut-0.00001 for cut in cuts),4)
 moves=[]
 for b in boxes:
  ny=shift(b['y'])
  if ny!=b['y']:moves.append(dict(inst=b['inst'],old_at=[b['x'],b['y']],new_at=[b['x'],ny]));b['y']=ny
 all_over=[];bounds=[]
 new_outline=dict(s['outline'],h=round(s['outline']['h']+43.2*len(fronts),4))
 for i,b in enumerate(boxes):
  if b['x']<0 or b['y']<0 or b['x']+b['w']>new_outline['w']+1e-5 or b['y']+b['h']>new_outline['h']+1e-5:bounds.append(b['inst'])
  for c in boxes[i+1:]:
   ox=min(b['x']+b['w'],c['x']+c['w'])-max(b['x'],c['x']);oy=min(b['y']+b['h'],c['y']+c['h'])-max(b['y'],c['y'])
   if ox>1e-5 and oy>1e-5:all_over.append([b['inst'],c['inst'],round(ox,4),round(oy,4)])
 out.append(dict(source=r,kit=k,old_outline=s['outline'],reserved_outline=new_outline,fronts=fronts,row_insertion_cuts=cuts,row_insertion_um=43.2,top_margin_insertion_um=43.2,body_moves=moves,resulting_body_overlaps=all_over,out_of_bounds=bounds,body_count=len(boxes),source_rtl_changed=False,registered_edges_changed=False,qualification=False,new_front_source='e8650f999',new_front_request='physical/ref_tile_specs/s81_bf_native_1015/front_five_roots_n32_soq_roomy',new_front_kit='physical/ref_tile/s81bf_front_five_roots_n32_soq_roomy'))
 full.append(dict(kit=k,boxes=boxes))
p=pathlib.Path('/home/ubuntu/scratch/codex-s81-colla-2000/frame_front_reserve_rows.json');p.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps([{k:v for k,v in x.items() if k not in ['fronts','body_moves']} for x in out],indent=1))
