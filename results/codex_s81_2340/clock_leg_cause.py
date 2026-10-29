import json,sys
sys.path.insert(0,'tools/die_plan')
import schema as S,die_trial as D
p=S.Plan(json.load(open(sys.argv[1])));site=D.SiteMap(p)
legs=json.load(open(sys.argv[2]))['long_450um'];out=[]
for e in legs:
 a,b=e['src_xy'],e['dst_xy'];mid=[(a[i]+b[i])/2 for i in (0,1)]
 hits=site.hits(mid)
 out.append(dict(e,mid_xy=mid,mid_blockages=hits,nearest=site.nearest(mid)))
 print(json.dumps(out[-1]),flush=True)
json.dump(out,open(sys.argv[3],'w'),indent=2)
