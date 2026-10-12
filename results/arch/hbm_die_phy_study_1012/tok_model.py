"""Token-time deltas for options A/B/B2/C from the measured S2 composition (throughput_budget_20261010/budget.json):
critical share of each op = elasticity(+10 %) x T / (0.1 x op cycles a token); a cost change dC moves the token by
share x dC (a LOWER bound on slowdown: the critical share only grows with the cost).  Collective increments use the
measured TU budget (tools/hgi_sim/perf.coll_cycles; 377.6 ns a switch crossing, results/rtl/dshbm_1m_allmeasured_20261004)."""
import json,pathlib,sys
R=pathlib.Path(__file__).resolve().parents[3]; sys.path.insert(0,str(R/'tools/hgi_sim')); sys.path.insert(0,str(R/'tools'))
import perf as P
CLK=1.2e9; XS=377.6e-9*CLK          # one extra switch crossing (vendor budget + measured endpoint), cycles
b=json.load(open(R/'results/arch/throughput_budget_20261010/budget.json'))
def ops(k): return {o['op']:o for o in b[k]['ops']}
def share(o,T): return o['token_elasticity_at_plus10pct']*T/(0.1*o['price_cycles_per_token'])
out={}
T=b['ds_hbm']['S2_cycles']; O=ops('ds_hbm')
sh={k:round(share(o,T),3) for k,o in O.items() if o['price_cycles_per_token']>0}
ag=O['COLL.ALL_GATHER']; ag_sw=P.coll_cycles('ALL_GATHER',ag['items_per_record'],16)[0]
d_ag1=(ag_sw-ag['price_cycles_per_record'])*ag['records_per_token']*sh['COLL.ALL_GATHER']          # AG leaves the 8-die package, 1 tier
d_ag2=(ag_sw+2*XS-ag['price_cycles_per_record'])*ag['records_per_token']*sh['COLL.ALL_GATHER']     # + 2 extra switches (2-tier)
cross={'COLL.GROUP_REDUCE_MCAST':2,'COLL.ROW_GATHER':1,'COLL.TOPK_MERGE':1,'COLL.ARGMAX_MERGE':1}
d_tier=sum(n*2*XS*O[k]['records_per_token']*sh[k] for k,n in cross.items())
# B2: +16 cycles a record whose operand crosses quadrants (ring hop vs today's chain), bound; SU local-lane saving 6-10 cycles
rem=sum(O[k]['records_per_token'] for k in ('COLL.ALL_GATHER','COLL.GROUP_REDUCE_MCAST','FUSED.HC_PRE_NORM','COLL.TOPK_MERGE','COLL.ROW_GATHER'))
d_b2_worst=16*rem; d_b2_gain=-8*O['SU.VOP']['records_per_token']*sh['SU.VOP']
def ts(c): return round(CLK/c,1)
out['ds']=dict(T=T,tok_s_A=ts(T),critical_share=sh,ag_switch_cycles=round(ag_sw,1),
  B=ts(T),B2_worst=ts(T+d_b2_worst),B2_net=ts(T+d_b2_worst+d_b2_gain),
  C_pkg16_contract=ts(T),C_1tier=ts(T+d_ag1),C_2tier=ts(T+d_ag2+d_tier),
  d_cycles=dict(b2_worst=d_b2_worst,b2_gain=round(d_b2_gain),c_ag_1tier=round(d_ag1),c_ag_2tier=round(d_ag2),c_tier_other=round(d_tier)),
  switch_crossings_per_token=dict(A=2*40+8+9+1,C_1tier=2*40+8+9+1+584))
Tq=b['qwen_hbm']['S2_cycles']; Oq=ops('qwen_hbm')
out['qwen']=dict(T=Tq,tok_s_A=ts(Tq),C_tp8_8dies=ts(Tq),C_tp4_4dies_halfBW=ts(Tq+Oq['SM.MATVEC']['price_cycles_per_token']*share(Oq['SM.MATVEC'],Tq)),
  ar_model_G4=P.coll_cycles('ALL_REDUCE_SUM',16384,4)[0],ar_model_G8=P.coll_cycles('ALL_REDUCE_SUM',16384,8)[0],
  B2_worst=ts(Tq+16*(72+145)))
json.dump(out,open(pathlib.Path(__file__).with_name('tok_model.json'),'w'),indent=1)
print(json.dumps(out,indent=1))
