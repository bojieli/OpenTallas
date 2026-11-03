import json,sys
a=json.load(open(sys.argv[1])); b=json.load(open(sys.argv[2]))
def rules(j):
    T={x['type']:x for x in j['types']}
    out={}
    for tn,v in (T.items() if isinstance(T,dict) else []):
        rs=v.get('rules') or v.get('checks') or {}
        if isinstance(rs,list): rs={r.get('rule') or r.get('id'):r for r in rs}
        out[tn]={k:(r.get('status') if isinstance(r,dict) else r, r.get('value') if isinstance(r,dict) else None) for k,r in rs.items()}
    return out
A,B=rules(a),rules(b)
print('top keys',list(a.keys())[:8],'types',len(A),len(B))
new=[];gone=[];worse=[];better=[]
for tn in sorted(set(A)|set(B)):
    for k in sorted(set(A.get(tn,{}))|set(B.get(tn,{}))):
        sa=A.get(tn,{}).get(k,(None,None)); sb=B.get(tn,{}).get(k,(None,None))
        if sb[0]=='FAIL' and sa[0]!='FAIL': new.append((tn,k,sa,sb))
        elif sa[0]=='FAIL' and sb[0]!='FAIL': gone.append((tn,k,sa,sb))
        elif sa[0]=='FAIL' and sb[0]=='FAIL' and sa[1]!=sb[1]: (worse if (sb[1] or 0)>(sa[1] or 0) else better).append((tn,k,sa[1],sb[1]))
nf=lambda X:sum(1 for t in X.values() for s in t.values() if s[0]=='FAIL')
print('FAIL count', nf(A),'->',nf(B),'| types FAIL',sum(1 for t in A.values() if any(s[0]=='FAIL' for s in t.values())),'->',sum(1 for t in B.values() if any(s[0]=='FAIL' for s in t.values())))
print('NEW',len(new),new[:20]); print('GONE',len(gone),gone[:20]); print('WORSE',len(worse),worse[:20]); print('BETTER',len(better),better[:10])
