exec(open('/srv/opentallas-scratch/claude/hbm-reset-carrier-model2-1019/probe.py').read().split('cl=[]')[0])
target=g.reserve('hop',p,targets=[('rst_n_in',p)])
source=(11234.7,20124.72)
try:
 hops=g.chain(source,target)
 r['status']='BASELINE_GEOMETRY_PATH_ONLY';r['source_clock_cell']='dkh_P2/Y';r['source_cell_origin']=source;r['hops']=[dict(t,clk=g.tile_pin(t,'clk'),input=g.tile_pin(t,'rst_n_in'),output=g.tile_pin(t,'rst_n')) for t in hops+[target]]
 pts=[source]+[g.tile_pin(t,'rst_n') for t in hops];ins=[g.tile_pin(t,'rst_n_in') for t in hops+[target]];r['spans_um']=[md(a,b) for a,b in zip(pts,ins)];r['area_um2']=len(hops+[target])*32.4**2
except Exception as e:r['status']='PATH_REFUSED';r['error']=repr(e)
print(json.dumps(r,indent=2))
