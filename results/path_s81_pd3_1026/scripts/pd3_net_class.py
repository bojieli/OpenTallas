import sys,re,collections
def scan(g):
    wl=collections.Counter(); net=None
    for ln in open(g):
        s=ln.split()
        if len(s)==1 and s[0] not in "()": net=s[0]; 
        elif len(s)==5 and s[4] in("M6","M7"):
            x0,y0,x1,y1=(int(v)/1000 for v in s[:4]); l=max(x1-x0,y1-y0)
            k="gunit" if "gunit" in net else "bk_sel" if "bk_sel" in net else "lk_WS3" if "lk_WS3" in net else "s_4N_x06" if "s_4N_x06" in net else re.sub(r"[\[\d].*","",net)[:14]
            wl[(k,s[4])]+=l
    return wl
A=scan(sys.argv[1]);B=scan(sys.argv[2])
keys=sorted(set(A)|set(B),key=lambda k:-(A[k]-B[k]))
print("class layer A_g0fix_m B_B5_m delta_m")
for k in keys[:15]: print(k, round(A[k]/1e3,1), round(B[k]/1e3,1), round((A[k]-B[k])/1e3,1))
print("TOTAL M6",round(sum(v for k,v in A.items() if k[1]=="M6")/1e3), round(sum(v for k,v in B.items() if k[1]=="M6")/1e3),"M7",round(sum(v for k,v in A.items() if k[1]=="M7")/1e3), round(sum(v for k,v in B.items() if k[1]=="M7")/1e3))
