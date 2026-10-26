# S-DIE 2026-10-15: re-run road_optc.py (option C, main 44bb36c57) capturing the per-y road demand profile of the delivered candidate, split VM-lane (hb_*vm*) vs other; output profile.json (y, tracks per road, VM-lane tracks per road)
import sys, json, runpy
sys.path.insert(0,'tools/s81/global_fp')
import road_optc as R
orig=R.stats; LAST={}
def st(chains, topn=12):
    ss=R.segments(chains); ev={}
    for n,lo,hi,b,ch in ss:
        hb = ch.startswith('hb') and 'vm' in ch
        ev.setdefault(lo,[]).append((n,b,hb)); ev.setdefault(hi,[]).append((n,-b,hb))
    cur={n:0 for n in R.WIDTH}; curhb={n:0 for n in R.WIDTH}; prof=[]
    for y in sorted(ev):
        for n,b,hb in ev[y]:
            cur[n]+=b
            if hb: curhb[n]+=b
        prof.append((round(y,1),dict(cur),dict(curhb)))
    LAST['prof']=prof
    return orig(chains,topn)
R.stats=st
sys.argv=['road_optc.py','--replay','./replay.json.gz','--homes','./homes.json','--out','./optc.json']
try:
    R.main()
except SystemExit: pass
json.dump(LAST['prof'],open('./profile.json','w'))
print('profile points',len(LAST['prof']))
