"""ISS2E lock-step compare (EQ_CYCLE_SHIFTED).  Per programme block (P lines): the DUT uop/done event list (U, D) must
equal the reference list; a block that hit the cycle cap (T) only needs equality up to the shorter list (the DUT
issues at half rate).  Fault (F, sticky, rise only): both logs must raise it the same number of times, at an event
position (number of U/D events before it) that differs by at most one event; the fault does not stop the issue, so a
one-edge later detection in the half-rate DUT moves it past at most one issued row.  Exit 1 on any mismatch."""
import sys
def blocks(f):
    b={}; cur=None
    for l in open(f):
        l=l.strip()
        if l.startswith("P "): cur=int(l[2:]); b[cur]=[]
        elif cur is not None: b[cur].append(l)
    return b
def split(lst):
    ev=[]; fpos=[]
    for x in lst:
        if x=="T": continue
        if x=="F": fpos.append(len(ev))
        else: ev.append(x)
    return ev,fpos
R=blocks(sys.argv[1]); D=blocks(sys.argv[2]); bad=0; tcap=0; ev=0; nf=0; fshift=0
for p in R:
    r,rf=split(R[p]); d,df=split(D.get(p,[]))
    capped=("T" in R[p]) or ("T" in D.get(p,[]))
    if capped:
        tcap+=1; n=min(len(r),len(d))
        ok=r[:n]==d[:n]
        rf=[x for x in rf if x<n]; df=[x for x in df if x<n]
    else:
        n=len(r); ok=(r==d)
    if not ok:
        i=next((i for i,(a,b) in enumerate(zip(r,d)) if a!=b), min(len(r),len(d)))
        print("MISMATCH prog",p,"at event",i,"ref",r[i:i+3],"dut",d[i:i+3]); bad+=1
    elif len(rf)!=len(df) or any(abs(a-b)>1 for a,b in zip(rf,df)):
        if not (capped and abs(len(rf)-len(df))==1 and all(abs(a-b)<=1 for a,b in zip(rf,df))):
            print("FAULT_MISMATCH prog",p,"ref",rf,"dut",df); bad+=1
    nf+=len(rf); fshift+=sum(1 for a,b in zip(rf,df) if a!=b); ev+=n
print(f"COMPARE progs {len(R)} capped {tcap} events {ev} faults {nf} fault_shift1 {fshift} mismatches {bad}")
sys.exit(1 if bad else 0)
