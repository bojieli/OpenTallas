import importlib.util,json,pathlib
p=pathlib.Path('/home/ubuntu/coord/tmp/codex-xrt-zeroedge-0423')
s=importlib.util.spec_from_file_location('g','/home/ubuntu/OpenTallas/tools/autopilot/geom_rules.py');g=importlib.util.module_from_spec(s);s.loader.exec_module(g)
def run(mode):
 d=g.Design('/home/ubuntu/coord/tmp/codex-s81-xrt-l4-2235/xrt/current_geom.tsv',memory_reach=True);moves=[]
 for cid,c in list(d.cells.items()):
  name=c[-1].replace('\\','');xy=g.ctr(c);target=None
  if mode and (name.startswith('u.g_d[') and name.endswith('$_DFF_P_')):target=(xy[0],xy[1]-300)
  if mode==2 and name in ['u.ev$_DFF_PN0_','u.eb[2]$_DFF_P_']:target=(155.52,197.64+(0.54 if name.startswith('u.eb') else 0))
  if target:
   dx,dy=target[0]-xy[0],target[1]-xy[1];v=list(c);v[2]+=dx;v[3]+=dy;v[4]+=dx;v[5]+=dy;d.cells[cid]=tuple(v);moves.append({'name':c[-1],'from':xy,'to':target})
 pairs=[];r=g.r2r_metrics(d,pairs);return {'mode':mode,'virtual_only':True,'legalized':False,'parent_pin_contract_approved':False,'moved':moves,'result':r,'top_remaining':sorted(pairs,key=lambda z:-z['distance_um'])[:12]}
a=[run(i) for i in [0,1,2]]; (p/'forecast.json').write_text(json.dumps(a,indent=2))
for z in a: print(z['mode'],len(z['moved']),z['result'])
