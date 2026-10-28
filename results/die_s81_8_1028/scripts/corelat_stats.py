import sys,statistics as S
for f in sys.argv[1:]:
    A=[];B=[];na=0
    for l in open(f):
        p,a,b,bd=l.rstrip("\n").split("\t")
        try: a=float(a); b=float(b)
        except: na+=1; continue
        if a>833.333 or a<0: na+=1; continue  # DIE-S81-8: untimed/other-edge guard at one period (CORELAT 400-ps cap cut real vn_a arrivals up to 428 ps)
        A.append(a); 
        if bd=="1": B.append(a)
    for n,X in (("all",A),("bnd",B)):
        if X: print(f, n, len(X), "mean %.1f min %.1f max %.1f"%(S.mean(X),min(X),max(X)))
    print(f,"skipped",na)
