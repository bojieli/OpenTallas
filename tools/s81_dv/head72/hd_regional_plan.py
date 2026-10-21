#!/usr/bin/env python3
"""Required HEAD successor assembly reserve; actual child packing remains explicit owed work."""
import json,sys
from pathlib import Path
from hd_floorplan import construct
from hd_plan import build
from hd_peer_plan import build as peer_build

def main(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    placement=construct(lep=(2592.0,2592.0))
    (out/'floorplan_h3.json').write_text(json.dumps(placement,indent=1)+'\n')
    source=out/'plan_before_peers.json'
    source.write_text(json.dumps(build(placement),indent=1)+'\n')
    target=out/'plan_unrouted_h3.json'
    peer_build(source,target)
    p=json.loads(target.read_text())
    lep=next(b for b in p['blocks'] if b['name']=='lep')
    lep['master']='ot_s81hd_lep_regional'
    p['facts']['lep_regional']=dict(source='4447aecf8',module='ot_s81hd_lep_regional',
        endpoint='ot_s81sl_lep_mu_ab_regional_r3r',reserve=lep,
        clocks={'ck':'C','ck_A':'A','ck_B':'B'},parent_reset_stages=2,
        reset_roots='Independent same-age C/A/B parent forest leaves; no C root aliases A/B',
        cycle_delta={'C_to_pair':4,'pair_to_C':5,'lane_payload_valid':2,'reverse_credit':2,'credit_RTT':4},
        closed_view=None,packing_status='OWED actual lane/core/ML packing and <=405um segment proof; no closed LEP view claimed')
    p['facts']['physical72']['design']='S81 HEAD H3 regional endpoint reset-root successor, diagnostic source view'
    target.write_text(json.dumps(p,indent=1)+'\n')
    source.unlink()
    print('HEAD_H3',len(p['blocks']),'blocks',len(p['links']),'links','die',p['facts']['die_um'],'LEP reserve',lep['w'],lep['h'])
if __name__=='__main__':main(sys.argv[1])
