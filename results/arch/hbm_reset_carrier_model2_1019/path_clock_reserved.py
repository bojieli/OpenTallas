exec(open('/srv/opentallas-scratch/claude/hbm-reset-carrier-model2-1019/probe.py').read().split('cl=[]')[0])
clock_obstacles=[]
for line in open(C/'run.tcl'):
 a=re.search(r'place_inst -name (dk[hrs]_\S+) -location \{([\d.]+) ([\d.]+)\}',line)
 if a:
  name,x,y=a.groups();x=float(x);y=float(y);g.block_rect(x,y,x+1.62,y+.27);clock_obstacles.append([name,x,y])
r['clock_obstacles_count']=len(clock_obstacles);r['clock_obstacle_envelope_um']=[1.62,.27];r['clock_native_envelope_qualification']='source allocator envelope, actual per-master LEF remains required'
target=g.reserve('hop',p,targets=[('rst_n_in',p)])
source=(11234.7,20124.72)
try:
 hops=g.chain(source,target)
 r['status']='HARD_AND_CLOCK_RESERVED_GEOMETRY_ONLY';r['source_clock_cell']='dkh_P2/Y';r['source_cell_origin']=source;r['hops']=[dict(t,clk=g.tile_pin(t,'clk'),input=g.tile_pin(t,'rst_n_in'),output=g.tile_pin(t,'rst_n')) for t in hops+[target]]
 pts=[source]+[g.tile_pin(t,'rst_n') for t in hops];ins=[g.tile_pin(t,'rst_n_in') for t in hops+[target]];r['spans_um']=[md(a,b) for a,b in zip(pts,ins)];r['area_um2']=len(hops+[target])*32.4**2
except Exception as e:r['status']='PATH_REFUSED';r['error']=repr(e)
print(json.dumps(r,indent=2))
