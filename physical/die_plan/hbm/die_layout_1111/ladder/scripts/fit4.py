import json,sys
sys.path.insert(0,'.')
import lgeom as G, pack as PK
raw=json.load(open(sys.argv[1]));T=raw['partition_types'];pm={p['name']:p for p in raw['partitions']}
spec=json.load(open(sys.argv[2]))
for side in ('NE','NW'):
    R=G.rects(side,spec[side])
    for n,(x0,y0,x1,y1) in sorted(R.items()):
        if n.endswith('b000'): continue
        w,h=round(x1-x0,2),round(y1-y0,2); t=T[pm[n]['type']]
        cores=[dict(inst=c['inst'],w=c['outline_um'][0],h=c['outline_um'][1],ocx=c['origin_um'][0]) for c in t['hard_cores']]
        r=PK.pack(w,h,cores)
        print(n,w,h,len(cores),'FIT lane %s shelves %s'%(r[1]['lane_um'],r[1]['shelves']) if r else 'NOFIT','minW',PK.min_width(h,cores),flush=True)
