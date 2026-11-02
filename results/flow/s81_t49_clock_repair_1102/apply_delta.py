"""Apply only the reviewed source-clock coordinate correction."""
import json,sys
p=json.load(open(sys.argv[1]));c=p['partition_types']['slice_station__t49']['clock']
assert c['tap_radius_um']==150 and c['tap_max_sinks']==1500
n=next(x for x in c['taps'] if x['name']=='clk_t25');assert n['xy']==[400.1757,307.2182]
n['xy']=[400.656,307.712]
with open(sys.argv[2],'w')as f:json.dump(p,f,separators=(',',':'));f.write('\n')
