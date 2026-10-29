import json,sys
A=json.load(open(sys.argv[1]))["partition_types"];B=json.load(open(sys.argv[2]))["partition_types"]
def walk(a,b,p,out):
    if type(a)!=type(b): out.append(p);return
    if isinstance(a,dict):
        for k in set(a)|set(b):
            if k not in a or k not in b: out.append(p+"/"+k+"(missing)")
            else: walk(a[k],b[k],p+"/"+k,out)
    elif isinstance(a,list):
        if len(a)!=len(b): out.append(p+"(len)");return
        for i,(x,y) in enumerate(zip(a,b)): walk(x,y,p+"/%d"%i if not isinstance(x,dict) or "name" not in x else p+"/"+str(x.get("name")),out)
    elif a!=b: out.append(p)
for tn in sys.argv[3:]:
    out=[];walk(A[tn],B[tn],"",out)
    import collections
    c=collections.Counter("/".join(x.split("/")[:3]) for x in out)
    print(tn,len(out),dict(c.most_common(8)))
