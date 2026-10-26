import odb,json
D=odb.dbDatabase.create();D=odb.read_db(D,'/work/projected_grt.odb')
g=D.getChip().getBlock().getGCellGrid();nx=len(g.getGridX());ny=len(g.getGridY())
out={'grid':[nx,ny],'layers':{},'overflow':0.0,'overflow_cells':0}
for name in ['M2','M3','M4','M5']:
 l=D.getTech().findLayer(name);s=0.0;n=0;m=0.0;totalcap=0.0;usage=0.0
 for x in range(nx):
  for y in range(ny):
   cap=g.getCapacity(l,x,y);u=g.getUsage(l,x,y);d=max(0.0,u-cap)
   totalcap+=cap;usage+=u
   if d>0:n+=1;s+=d;m=max(m,d)
 out['layers'][name]={'overflow':s,'overflow_cells':n,'max':m,'capacity':totalcap,'usage':usage}
 out['overflow']+=s;out['overflow_cells']+=n
print('ACTUAL_GCELL_CONGESTION',json.dumps(out,sort_keys=True))
open('/work/gcell_overflow.json','w').write(json.dumps(out,indent=2)+'\n')
assert out['overflow']==0.0,'actual routed ODB grid overflow'
