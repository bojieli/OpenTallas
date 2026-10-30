# DIE-QC-44 clock readout of grt_leaf.tcl arrivals.txt: spread / duty / MPW / sink slew per sink class.
# high phase = (a_fall - a_rise) mod T (OpenSTA arrivals include the falling edge time T/2).
import sys,json,math,collections
T=833.0; f=sys.argv[1]; out=sys.argv[2]
F=[];Tp=[];na=0
for l in open(f):
    s=l.split()
    if len(s)<4 or s[3]=='NA' or 'INF' in l or 'inf' in l: na+=1; continue
    c,k,n=s[0],s[1],s[2]; ar,af,sl=map(float,s[3:6])
    (F if k=='F' else Tp).append((n,ar,af,sl,s[6:8]))
def summ(L):
    if not L: return None
    ar=[x[1] for x in L]; hi=[(x[2]-x[1])%T for x in L]; du=[h/T for h in hi]; sl=[x[3] for x in L]
    i=max(range(len(L)),key=lambda j:ar[j]); j=min(range(len(L)),key=lambda j:ar[j])
    return dict(n=len(L),arr_min=round(min(ar),2),arr_max=round(max(ar),2),spread=round(max(ar)-min(ar),2),late=L[i][0],early=L[j][0],
        duty_min=round(min(du),4),duty_max=round(max(du),4),duty_out_45_55=sum(1 for d in du if d<.45 or d>.55),
        min_pulse_ps=round(min(min(h,T-h) for h in hi),1),slew_max=round(max(sl),1))
r=dict(file=f,na=na,provider_ff=summ(F),core_taps=summ(Tp))
# per core instance tap spread
g=collections.defaultdict(list)
for x in Tp: g[x[0].split('__')[0][2:]].append(x[1])
ps=sorted(((max(v)-min(v)),k,len(v)) for k,v in g.items())
r['per_inst_tap_spread_worst']=[[k,n,round(s,2)] for s,k,n in ps[-5:]]
r['insts']=len(g)
json.dump(r,open(out,'w'),indent=1);print(json.dumps(r,indent=1))
