import json,sys,collections
def pairs(p):
    b=json.load(open(p))["buses"]; c=collections.Counter()
    for x in b:
        if not x.get("lane") and not x.get("spine"): c[(x["src"],x["dst"])]+=x["width"]
    return c
A=pairs(sys.argv[1]); B=pairs(sys.argv[2])
print("base pairs",len(A),sum(A.values()),"new plan pairs",len(B),sum(B.values()))
print("GONE",sorted((k,v) for k,v in A.items() if k not in B))
print("NEW",sorted((k,v) for k,v in B.items() if k not in A))
print("CHANGED",sorted((k,A[k],v) for k,v in B.items() if k in A and A[k]!=v))
