"""Independent replay of a CB16 control placement: every control edge, legality vs hard children / bays / outline."""
import json,sys,collections,hashlib
d=json.load(open(sys.argv[1]));sol=json.load(open(sys.argv[2]));P=sol['pos'];S=d['scalar'];err=[]
W,H=d['outline']
assert set(P)==set(S),(len(P),len(S))
def pts(e):
  if 'point' in e: return [tuple(e['point'])]
  if 'node' in e: return [tuple(P[e['node']])]
  x,y,w,h=e['box'];return [(x,y),(x+w,y),(x,y+h),(x+w,y+h)]
mx=collections.defaultdict(float);cnt=collections.Counter()
for e in d['edges']:
  D=max(abs(a[0]-b[0])+abs(a[1]-b[1]) for a in pts(e['src']) for b in pts(e['dst']))
  mx[e['kind']]=max(mx[e['kind']],D);cnt[e['kind']]+=1
  if D>405: err.append(('reach',e['kind'],round(D,1)))
for n,(x,y) in P.items():
  if not(5<=x<=W-5 and 5<=y<=H-5): err.append(('outline',n))
  for h,(hx,hy,hw,hh) in d['hard'].items():
    if hx-5.4<=x<=hx+hw+5.4 and hy-5.4<=y<=hy+hh+5.4: err.append(('in_hard_halo',n,h))
  for b,(bx,by,bw,bh) in d['bays'].items():
    if bx<=x<=bx+bw and by<=y<=by+bh: err.append(('in_bay',n,b))
stack=collections.Counter(tuple(p) for p in P.values())
r=dict(status='FAIL' if err else 'PASS',edges=dict(cnt),max_um={k:round(v,3) for k,v in mx.items()},overall_max_um=round(max(mx.values()),3),
 nodes=len(P),static_straps=len(d['static_straps']),unknown=len(d['unknown']),max_ffs_same_site=max(stack.values()),errors=err[:40],
 solution_sha256=hashlib.sha256(open(sys.argv[2],'rb').read()).hexdigest(),scope='scalar/reset/control FF sites (site = FF centre target; FIRM compact block then released for DPL)')
json.dump(r,open(sys.argv[3],'w'),indent=1);print('CTL_REPLAY',r['status'],r['overall_max_um'],r['max_um'],'stack',r['max_ffs_same_site'],len(err))
