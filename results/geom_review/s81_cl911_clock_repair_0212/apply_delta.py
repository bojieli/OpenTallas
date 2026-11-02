#!/usr/bin/env python3
import sys,json
p=json.load(open(sys.argv[1]));t=p['partition_types']['col_h10_r0_p1__t1__cl911743eb'];ck=t['clock'];assert ck.get('tap_radius_um',200)==200
n=next(n for n in ck['added_taps'] if n['name']=='clk_t28');assert n['xy']==[1126.44,980.6];n['xy']=[1126.432,958.496]
with open(sys.argv[2],'w') as f:json.dump(p,f,separators=(',',':'));f.write('\n')
