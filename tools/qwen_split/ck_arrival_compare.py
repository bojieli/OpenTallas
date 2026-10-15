import sys,statistics as st
def ld(f):
    d={}
    for l in open(f):
        t=l.split()
        try: d[t[0]]=(float(t[1]),float(t[2]))
        except: pass
    return d
a=ld(sys.argv[1]); b=ld(sys.argv[2])
k=sorted(set(a)&set(b)); print('sinks',len(a),len(b),'common',len(k))
for lab,D in (('A',a),('B',b)):
    v=[D[x][0] for x in k]; print(lab,'max-arr mean %.2f min %.2f max %.2f spread %.2f'%(st.mean(v),min(v),max(v),max(v)-min(v)))
d=[b[x][0]-a[x][0] for x in k]; print('per-sink delta B-A: mean %.3f min %.3f max %.3f |max| %.3f ps'%(st.mean(d),min(d),max(d),max(abs(x) for x in d)))
