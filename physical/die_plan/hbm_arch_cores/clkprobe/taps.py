import csv,collections,numpy as np,sys
for d in sys.argv[1:]:
    E=list(csv.DictReader(open(d+"/clknets.csv")))
    S={r['inst']:r for r in csv.DictReader(open(d+"/sinks.csv"))}
    par={r['sink']:r['drv'] for r in E}
    def tap(i):
        seen=0
        while i in par and seen<60:
            i=par[i]; seen+=1
            if i.startswith('ot_dtap_'): return i
        return None
    g=collections.defaultdict(list)
    for r in S.values():
        if r['arr_max']: g[(tap(r['inst']),r['kind'])].append(float(r['arr_max'])/1e12)
    print(d); means=[]
    for k in sorted(g,key=lambda k:(str(k[0]),k[1])):
        a=np.array(g[k]); print("   %-12s %-5s n %5d min %4.0f mean %4.0f max %4.0f"%(k[0],k[1],len(a),a.min(),a.mean(),a.max()))
