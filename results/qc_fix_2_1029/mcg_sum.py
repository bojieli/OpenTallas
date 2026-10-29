import sys,csv,statistics as st
for f in sys.argv[1:]:
    r=list(csv.DictReader(open(f),delimiter='\t'))
    d=sorted(float(x['dist']) for x in r)
    if not d: print(f,'captures 0'); continue
    q=lambda p:d[min(len(d)-1,int(p*len(d)))]
    print(f"{f}: captures {len(d)} macros {len(set(x['macro'] for x in r))} med {st.median(d):.1f} p90 {q(.9):.1f} max {d[-1]:.1f} >30um {sum(x>30 for x in d)} >100um {sum(x>100 for x in d)}")
