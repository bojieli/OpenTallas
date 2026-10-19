import json,pathlib
P=pathlib.Path(__file__).parent;old=json.load(open(P/'integrated_inputs/positions.json'));packing=json.load(open(P/'full_placement_model.json'));model=json.load(open(P/'full_scope_model.json'));pos={n:c['bbox'] for n,c in old['insts'].items()};pos.update({r['name']:r['bbox'] for r in packing['placed']});out=[]
def geom(a,b):
 x,y,X,Y=a;l,v,L,V=b
 return dict(box_separation_lower_um=(max(0,x-L,l-X)+max(0,y-V,v-Y))/1000,any_point_Manhattan_upper_um=(max(X,L)-min(x,l)+max(Y,V)-min(y,v))/1000)
for r in model['plans']:
 source=r['driver']['cell'];target=r['endpoint'].rsplit('/',1)[0];nodes=[source]+[z['name'] for z in r['added_cells']]+[target];out.append(dict(endpoint=r['endpoint'],original_source_net=r['original_net'],nodes=nodes,wire_geometry=[dict(source=a,target=b,**geom(pos[a],pos[b])) for a,b in zip(nodes,nodes[1:])]))
json.dump(dict(schema='int8.new_hold_geometry.source_model.v1',scope='All604 proposed branches with exact immutable/offline-packed boxes; distances are box bounds, NOT a routed pin or extracted wire-cap claim. Actual .000752fF lower-load requirement remains HOLD until native extraction, never inferred from these distances.',branches=out),open(P/'wire_geometry_model.json','w'),indent=2);print('branches',len(out),'maxnewwire bboxbound',max(z['any_point_Manhattan_upper_um'] for r in out for z in r['wire_geometry']))
