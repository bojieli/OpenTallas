import json,sys,collections
sys.path.insert(0,sys.argv[1]); import plan_cut as PC, hbm_r10_delta as R10
t=json.load(open(sys.argv[2])); W,H=t['outline_um']; axis=sys.argv[3]; x0=float(sys.argv[4]) if len(sys.argv)>4 else 0; x1=float(sys.argv[5]) if len(sys.argv)>5 else W
pr=R10.profile(W,H,t,x0,x1); print(axis,pr[axis])
at=pr[axis]['at_um']+ (x0 if axis=='x' else 0)
c=collections.Counter()
for s in t['internal_stations']:
    a,b=s['from_um'],s['to_um']; i=0 if axis=='x' else 1
    if min(a[i],b[i])<at<max(a[i],b[i]) and (axis=='x' or (x0<=max(a[0],b[0]) and min(a[0],b[0])<=x1)):
        k=(s.get('launch','').split('.')[0][:28], str(s.get('capture','')).split('.')[0][:28]); c[k]+=s['bits']
for k,v in c.most_common(25): print(v,k)
