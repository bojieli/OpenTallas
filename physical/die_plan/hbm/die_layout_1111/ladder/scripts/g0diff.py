import json,sys,collections,re
def load(p):
    r=json.load(open(p)); return [f for f in r['findings'] if f.get('level')=='ERROR']
A=load(sys.argv[1]); B=load(sys.argv[2])
def norm(m):
    m=re.sub(r'-?[0-9]+\.?[0-9]*','#',m); return m
sa=collections.Counter((f['check'],f['msg']) for f in A); sb=collections.Counter((f['check'],f['msg']) for f in B)
new=[k for k in sb if k not in sa]; lost=[k for k in sa if k not in sb]
print('base',len(A),'new plan',len(B),'new msgs',len(new),'lost msgs',len(lost))
c=collections.Counter(); ex={}
for ch,m in new:
    k=(ch,re.sub(r'(L\w+?)_\d+','L*',re.sub(r'(NE|NW)_\w+','P*',re.sub(r'q_\w+','T*',norm(m))))[:110]); c[k]+=1; ex.setdefault(k,m[:240])
for k,v in c.most_common(int(sys.argv[3]) if len(sys.argv)>3 else 40): print(v,k[0],'|',ex[k])
print('--- lost by check',collections.Counter(ch for ch,m in lost))
print('--- new by check',collections.Counter(ch for ch,m in new))
