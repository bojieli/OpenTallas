import json,collections,sys
from shapely.geometry import box
from shapely.strtree import STRtree
A=sys.argv[1]
ov=json.load(open(A+'/overlay.json'));pl=json.load(open(A+'/plan/access_plan.json'));s=json.load(open(A+'/plan/summary.json'))
m7=[(o[0],o[2:]) for o in ov['obstructions'] if o[1]=='M7']
own=collections.Counter(('BLOCK' if o=='BLOCK' else ('macroPG' if '/' in o else 'inst')) for o,_ in m7)
area=collections.Counter()
for o,r in m7:area['BLOCK' if o=='BLOCK' else ('macroPG' if '/' in o else 'inst')]+=(r[2]-r[0])*(r[3]-r[1])/1e6
t=STRtree([box(*r) for _,r in m7])
cat=collections.Counter();bn=collections.Counter();ex=[]
for q in pl['failed']:
  x0,y0,x1,y1=q['rail'];hits=t.query(box(x0,y0-1400,x1,y1+1400))
  if len(hits)==0:cat['no_M7_obstacle_near']+=1;continue
  owners={('BLOCK' if m7[i][0]=='BLOCK' else ('macroPG' if '/' in m7[i][0] else 'inst')) for i in hits}
  # rail fully inside an M7 obstacle x-span?
  cov=any(m7[i][1][0]<=x0 and m7[i][1][2]>=x1 for i in hits)
  cat[('covered_by_' if cov else 'partial_')+'+'.join(sorted(owners))]+=1
  for i in hits:
    if m7[i][0]!='BLOCK':bn[m7[i][0].split('/')[0]]+=1
nets=collections.Counter(q['net'] for q in pl['failed'])
# big M7 BLOCK obstacles widths
w=collections.Counter(round((r[2]-r[0])/1000,2) for o,r in m7 if o=='BLOCK')
print(json.dumps(dict(m7_obstacles=dict(own),m7_area_um2=dict(area),failed_by_net=nets,failed_category=cat,top_inst_owners=bn.most_common(8),block_m7_widths_um=w.most_common(8),rejections=s['rejections'],examples=s['obstacle_examples']),indent=1))
