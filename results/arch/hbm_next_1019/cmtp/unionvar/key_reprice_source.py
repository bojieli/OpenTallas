#!/usr/bin/env python3
"""Conditional architecture prices from source joint cardinality statistics (no new RTL).

max: each U,Cmax bank reserves Cmax rows for every expert.
profile: exact cardinality-class kernels and layer-boundary prefix preparation assumed.
Noncaptured draft/seed cases use the structural cardinality bound min(N, topk*N-U+1). Prep/loader/store-area are
reported separately, never hidden as a measured rate. S2 at pooled workload means is
an expectation proxy, not a static-safety proof for a native dispatcher.
"""
import argparse,dataclasses,json,math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from hbm_next import plane_compiler as PC
from hgi_sim import hbm_plane_model as M,ds_mtp_verify as V

def main(a):
    data=json.loads(a.stats.read_text())
    key='max_bucket_expert_weighted_hist' if a.key=='max' else 'true_expert_hist'
    hh={6:{int(c):f for c,f in data['verify6'][key].items()},
        4:{int(c):f for c,f in data['users4'][key].items()}}
    oldsm,oldmeas=PC.post_sm,PC.apply_meas
    active_hist={}
    def hist(N,union=None,topk=6):
        mode=PC.CUR.get('mode')
        if (N==6 and mode=='verify') or (N==4 and mode=='users'):
            return hh[N]
        if union is None:return active_hist.get(N,{N:1.0})
        U=max(topk,int(round(union)))
        assert U<=topk*N, (N,topk,U)
        # Sum of c_u is topk*N; every other union expert consumes >=1 row.
        return {min(N,topk*N-U+1):1.0}
    def post_sm(out,N,lanes,union,topk,kn,h):
        h=hist(N,union,topk);active_hist[N]=h
        if N>1:
            U=max(topk,int(round(union))) if union else topk*N;pe=topk*N/U
            for r in out:
                if getattr(r,'mtp_kind','')=='egather':
                    nb=4*r.desc['A'].n
                    want=sum(fr*V.coll_cycles(r.op,c*nb,96)[0] for c,fr in h.items())
                    r.base_cost*=want/V.coll_cycles(r.op,int(round(pe*nb)),96)[0]
        return oldsm(out,N,lanes,union,topk,kn,h)
    def apply_meas(out,N,kn,h,lanes,pe=1):return oldmeas(out,N,kn,active_hist.get(N,{N:1.0}),lanes,pe)
    PC.post_sm=post_sm;PC.apply_meas=apply_meas
    PC.CUR['hist']=PC.lane_hists()
    st=M.load_stats(PC.STATS)
    st['verify_union'][6]['mean']=data['verify6']['mean_U']
    st['users_union'][4]=data['users4']['mean_U']
    kn=PC.Knobs(**dict(PC.HEAD,P=3,rpl=False),
       meas=PC.MEAS_ALL2+('idx_frame','fused_frame','fused_tree','sm3'))
    r=PC.run_case(kn,st,a.jobs,3,4)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.with_suffix('.raw.json').write_text(json.dumps(r,indent=1,default=str)+'\n')
    # No store/loader credit: these terms remain explicit architecture obligations.
    result=dict(key=a.key,status='conditional model candidate; no RTL/native adoption',
        candidate_histograms=hh,price=r,
        preparation={'max':'max reduction while route tables emit; registered selection, new cycles unmeasured',
            'profile':'fixed prefix metadata prep before loop; all expert kernel choices latched before start'}[a.key],
        prep_cycles_per_layer=a.prep_cycles,store_area_mm2=None,all_layers_resident=False,
        native_dispatch=False,SS_FF=False,
        notes=['Unknown verify routing is the documented decorrelated estimator.',
            'Noncaptured draft/seed use min(N,topk*N-U+1); no-sharing draft U15 implies c1 exactly.',
            'All prices use actual compiled local SM shape ceilings; global row cardinality bounds every SM subset.',
            'Pooled mean U/S2 schedule is an expectation proxy; exact bank-by-bank model proof still needed.'])
    # Extra prep is exposed on every main-model layer (40) per verify and user token.
    # It is conservatively NOT overlapped; draft/seed prep remains unpriced => not an adoption number.
    d=40*a.prep_cycles
    result['with_main_layer_prep_only']=dict(
        mtp_tok_s=r['mtp']['tok_s']*r['mtp']['step_cycles']/(r['mtp']['step_cycles']+d),
        mu_agg_tok_s=r['mu']['agg_tok_s']*r['mu']['step_cycles']/(r['mu']['step_cycles']+d))
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=1,default=str)+'\n')
    print(a.key,'AR',r['ar_tok_s'],'MTP',r['mtp']['tok_s'],'MU4',r['mu']['agg_tok_s'],r['mu']['per_user_tok_s'])
if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--stats',type=Path,required=True);ap.add_argument('--key',choices=('max','profile'),required=True)
    ap.add_argument('--out',type=Path,required=True);ap.add_argument('--jobs',type=int,default=4);ap.add_argument('--prep-cycles',type=int,default=0);main(ap.parse_args())
