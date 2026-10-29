import json,sys,collections
SW,SH,OX,OY,P=0.054,0.27,4.32,4.32,0.81
rows=[];mac=[];blk=[];fix=[]
for l in open('blk.tsv'):
    f=l.rstrip('\n').split('\t');r=tuple(map(float,f[1:5]))
    if f[0]=='W':rows.append(r)
    elif f[0]=='B':blk.append(r)
    elif f[0]=='F':(mac if f[5].startswith('ot_') else fix).append(r)
# grid buckets for fixed cells
G=collections.defaultdict(list)
for r in fix:
    for gx in range(int(r[0]//5),int(r[2]//5)+1):G[(gx,int(r[1]//SH+0.5))].append(r)
def snap(x,y):return OX+round((x-OX)/SW)*SW,OY+round((y-OY)/SH)*SH
def ov(a,b,e=1e-6):return a[0]<b[2]-e and b[0]<a[2]-e and a[1]<b[3]-e and b[1]<a[3]-e
def inrow(r):return any(w[0]-1e-6<=r[0] and r[2]<=w[2]+1e-6 and abs(w[1]-r[1])<1e-3 for w in rows)
def check(r):
    bad=[]
    if any(ov(r,(m[0]-2.16,m[1]-2.16,m[2]+2.16,m[3]+2.16)) for m in mac):bad.append('halo')
    if not inrow(r):bad.append('norow')
    if any(ov(r,m) for m in mac):bad.append('macro')
    if any(ov(r,b) for b in blk):bad.append('blk')
    if any(ov(r,q) for q in G[(int(r[0]//5),int(r[1]//SH+0.5))]+G[(int(r[2]//5),int(r[1]//SH+0.5))]):bad.append('fixed')
    return bad
def rects(t,mode='L',dx=0,dy=0):
    x,y,n=t['x']+dx,t['y']+dy,t['pad'];out=[]
    for s in range(n):
        px,py = (x-(n-s)*P-0.3,y) if not t.get('pad_xy') else t['pad_xy'][s]
        sx,sy=snap(px,py);out.append(('pad%d'%s,(sx,sy,sx+0.378,sy+SH)))
    sx,sy=snap(x,y);out.append(('drv',(sx,sy,sx+1.62,sy+SH)));return out
if __name__=='__main__':
    plan=json.load(open(sys.argv[1]));tot=collections.Counter();n=0
    for t in plan['taps']:
        for nm,r in rects(t):
            b=check(r)
            if b:n+=1;tot[t['id']]+=1;print(t['id'],nm,['%.3f'%v for v in r],b)
    print('ILLEGAL',n,dict(tot))
