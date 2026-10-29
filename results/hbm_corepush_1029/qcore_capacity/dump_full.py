import odb,json,collections
x=odb.dbDatabase.create();odb.read_db(x,'/kit/run/results/asap7/hbc_ot_hbm_su_static_qcore_r13/base/5_1_grt-failed.odb');b=x.getChip().getBlock();g=b.getGCellGrid();u=b.getDbUnitsPerMicron();xs=g.getGridX();ys=g.getGridY();out={'units':u,'grid_x_um':[v/u for v in xs],'grid_y_um':[v/u for v in ys],'layers':{},'block_obstructions':[],'macros':[],'PG':[]};cells=[]
for l in x.getTech().getLayers():
 if not 2<=l.getRoutingLevel()<=7:continue
 n=l.getName();row={'direction':str(l.getDirection()),'positive_cap_cells':0,'capacity_sum':0,'usage_sum':0,'excess_sum':0,'zero_cap_used_cells':0,'max_capacity':0,'max_usage':0,'top_bins':collections.Counter()}
 for i in range(len(xs)-1):
  for j in range(len(ys)-1):
   cap=g.getCapacity(l,i,j);use=g.getUsage(l,i,j);row['capacity_sum']+=cap;row['usage_sum']+=use;row['max_capacity']=max(row['max_capacity'],cap);row['max_usage']=max(row['max_usage'],use);row['positive_cap_cells']+=cap>0
   ex=max(0,use-cap);row['excess_sum']+=ex;row['zero_cap_used_cells']+=cap==0 and use>0
   if ex:
    cx=xs[i]/u;cy=ys[j]/u;row['top_bins'][f'x{int(cx//25)*25}/y{int(cy//25)*25}']+=ex;cells.append(dict(layer=n,direction=row['direction'],ix=i,iy=j,x_um=cx,y_um=cy,cap=cap,usage=use,excess=ex))
 row['top_bins']=row['top_bins'].most_common(5);out['layers'][n]=row
for o in b.getObstructions():
 r=o.getBBox();l=r.getTechLayer();out['block_obstructions'].append(dict(layer=l.getName()if l else None,rect_um=[r.xMin()/u,r.yMin()/u,r.xMax()/u,r.yMax()/u]))
for i in b.getInsts():
 if str(i.getMaster().getType())!='BLOCK':continue
 r=i.getBBox();ox,oy=i.getOrigin();m={'name':i.getName(),'orient':str(i.getOrient()),'origin_um':[ox/u,oy/u],'box_um':[r.xMin()/u,r.yMin()/u,r.xMax()/u,r.yMax()/u],'obs':[]}
 for o in i.getMaster().getObstructions():
  l=o.getTechLayer();m['obs'].append(dict(layer=l.getName()if l else None,master_rect_um=[o.xMin()/u,o.yMin()/u,o.xMax()/u,o.yMax()/u]))
 out['macros'].append(m)
for n in b.getNets():
 if str(n.getSigType())not in ('POWER','GROUND'):continue
 for sw in n.getSWires():
  for z in sw.getWires():
   if z.isVia():continue
   l=z.getTechLayer();out['PG'].append(dict(net=n.getName(),layer=l.getName()if l else None,rect_um=[z.xMin()/u,z.yMin()/u,z.xMax()/u,z.yMax()/u]))
json.dump(out,open('/diag/native_capacity.json','w'),indent=1);json.dump(cells,open('/diag/native_excess_cells.json','w'),indent=1);print(json.dumps(out['layers']))
