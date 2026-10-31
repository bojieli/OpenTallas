import re,sys
def nets(f):
    t=open(f).read(); i=t.index("\nNETS "); j=t.index("END NETS",i)
    out={}
    for blk in t[i:j].split(" ;\n"):
        m=re.search(r"^\s*-\s+(\S+)",blk,re.M)
        if not m: continue
        r=blk.find("+ ROUTED")
        out[m.group(1)]=re.sub(r"\s+"," ",blk[r:]) if r>=0 else ""
    return out
a=nets(sys.argv[1]); b=nets(sys.argv[2])
same=sum(1 for k in a if k in b and a[k]==b[k]); diff=[k for k in a if k in b and a[k]!=b[k]]
print("DEFCMP nets_a",len(a),"nets_b",len(b),"same",same,"diff",len(diff),"new",len(set(b)-set(a)),"gone",len(set(a)-set(b)), diff[:5])
