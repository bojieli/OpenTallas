"""DIE-KV-32-SRC: attribute the failed groups of plan_off (variant A form): per clock bucket, stage presence + top blocker tags,
and the M9 stripe-segment geometry (are the 3 x-nearest same-net M9 segments the same column? nearest covering segment distance)."""
import json,collections,sys
C="/srv/opentallas-scratch2/claude/codex-kv-pg-0834/grid3_bbox";D=1000
pl=json.load(open(sys.argv[1]+"/access_plan.json"));pg=json.load(open(C+"/pg_rects.json"))
stripes={n:sorted([tuple(round(v*D) for v in r) for nn,ly,*r in pg if nn==n and ly=="M9"]) for n in ["VDD","VSS"]}
out={}
for bk in sorted({q["clock_bucket"] for q in pl["failed"]}):
  F=[q for q in pl["failed"] if q["clock_bucket"]==bk];st=collections.Counter();tags=collections.defaultdict(collections.Counter);geo=collections.Counter();dcov=[]
  for q in F:
    for k,v in q["tally"].items():
      st[k]+=1
      for t,c in v.items():tags[k][t]+=c
    x0,y0,x1,y1=q["rail"];x=(x0+x1)//2;y=(y0+y1)//2;n=q["net"]
    dst=sorted(stripes[n],key=lambda r:max(r[0]+20-x,0,x-r[2]+20))[:3]
    cols=len({r[0] for r in dst});geo[f"3_nearest_M9_segments_in_{cols}_columns"]+=1
    cov=[r for r in stripes[n] if r[1]+20<=y<=r[3]-20]
    if not cov:geo["no_same_net_M9_segment_covers_rail_y"]+=1
    else:
      d=min(max(r[0]+20-x,0,x-r[2]+20) for r in cov);dcov.append(d)
      geo["covering_M9_segment_within_3_nearest" if any(r in dst for r in cov) else "covering_M9_segment_not_in_3_nearest"]+=1
    # does the rail y fall in an M9 segment gap (cut) of its nearest column?
  dcov.sort()
  out[bk]=dict(groups=len(F),stage_present=dict(st),top_tags={k:dict(v.most_common(6)) for k,v in tags.items()},m9_geometry=dict(geo),nearest_covering_m9_dx_um=dict(p50=dcov[len(dcov)//2]/D if dcov else None,max=dcov[-1]/D if dcov else None))
print(json.dumps(out,indent=1))
