#!/usr/bin/env python3
"""Apply only the reviewed source-clock coordinate correction to a private plan."""
import json,sys
p=json.load(open(sys.argv[1]));types=p['types'];t=types['slice_station__t18'];ck=t['clock'];assert ck['tap_radius_um']==150.0
node=next(x for x in ck['taps'] if x['name']=='clk_t16');assert node['xy']==[196.6712,294.8172],node
node['xy']=[197.088,294.112]
with open(sys.argv[2],'w') as f:json.dump(p,f,separators=(',',':'));f.write('\n')
