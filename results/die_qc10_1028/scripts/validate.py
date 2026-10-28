import json, sys, statistics as st
sys.path.insert(0,'/srv/opentallas-scratch2/claude/die-qc10-1028/est')
from ocvmodel import ocv, spread
T6='/srv/opentallas-scratch2/claude/die-qc9-1028/ca/t6/'
X=json.load(open(T6+'grp_spice_xing_lpo.json'))['corners']
P={c['port']:c for c in json.load(open(T6+'plan.json'))['crossings']}
for cs in (180.7,150.0):
    tt={r['port']:r for r in X['TT_droop-regions_corelat250']['all']}; ff={r['port']:r for r in X['FF_droop-regions_corelat202.5']['all']}
    pred=[];meas=[]
    for p,r in tt.items():
        lo=hi=None
        for C,rr in (('TT',r),('FF',ff[p])):
            s=(spread(rr['src'],C,cs)+spread(rr['dst'],C,cs))/2
            os_,oh=ocv(rr['unshared_a_ps'],rr['unshared_b_ps'],rr['dist_um'],C)
            l=rr['d_ps']-max(rr['p_dn_ps'],s+os_); h=rr['d_ps']+max(rr['p_up_ps'],s+oh)
            lo=l if lo is None else min(lo,l); hi=h if hi is None else max(hi,h)
        pred.append(hi-lo); meas.append(P[p]['p_up_ps']+P[p]['p_dn_ps'])
    e=[a-b for a,b in zip(pred,meas)]
    print(f'c_spread {cs}: hull width predicted med {st.median(pred):.0f} vs measured med {st.median(meas):.0f}; err med {st.median(e):.0f} p10 {sorted(e)[len(e)//10]:.0f} p90 {sorted(e)[9*len(e)//10]:.0f}')
