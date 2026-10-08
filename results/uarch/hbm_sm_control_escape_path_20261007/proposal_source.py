import json,sys
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools')
from hbm_sm_control_path_probe import portal,price_path
p=json.load(open('/tmp/hbm-sm3x3-vm8-native-control-escape-bays.json'));by={i['name']:i for i in p['insts']};own={i['sm']:i['box_um'] for i in p['native_owner_bays']};dst={i['sm']:i['box_um'] for i in p['native_descriptor_bays']};c=12.16
rows=[]
for sm in ('sm4','sm7','sm18','sm20','sm21','sm23'):
 it=by[sm];s=portal(own[sm],it['orient'],c);t=portal(dst[sm],it['orient'],c);x=it['x']+it['w']+c if it['orient'] in ('MY','R180') else it['x']-c
 path=[s,(x,s[1]),(x,t[1]),t]
 corridors=[[min(a[0],b[0])-c,min(a[1],b[1])-c,max(a[0],b[0])+c,max(a[1],b[1])+c] for a,b in zip(path,path[1:])]
 blockers=[i['name'] for i in p['insts'] if any(max(b[0],i['x'])<min(b[2],i['x']+i['w'])-1e-6 and max(b[1],i['y'])<min(b[3],i['y']+i['h'])-1e-6 for b in corridors)]
 rows.append(dict(sm=sm,path_um=path,corridor_rectangles_um=corridors,macro_relocations=blockers,**price_path(path)))
out=dict(status='proposed route reservations; not solid obstructions; station placement and dual rail width unqualified',station_assumption_um=[20,20],side_clearance_um=2.16,rows=rows,area_upper_bound_um2=sum((b[2]-b[0])*(b[3]-b[1]) for r in rows for b in r['corridor_rectangles_um']))
json.dump(out,open('/tmp/hbm-six-control-u-corridors.json','w'),indent=2)
print([(r['sm'],r['macro_relocations']) for r in rows]);print(out['area_upper_bound_um2'])
