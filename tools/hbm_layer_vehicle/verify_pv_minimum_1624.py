"""Pure pre-admission proof for the exact partial-key connected PV candidate."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from hbm_layer_vehicle import att_images as A


def verify(root,kvroot):
    spec=json.loads((root/'sm_node_scoreboard.json').read_text())
    rec,_=A.load_ds(kvroot,0)
    op=next(o for o in A.plan_d4g(rec)[0] if o[0]=='pv_sm_SW0')
    assert op[3]==list(range(8)) and op[4]==1
    cs=A.B.chunk_sums(rec['p'][op[3]],rec['K'][op[3]])
    want=A.B.bits32(cs[0]).reshape(-1)
    got=np.array([int(v,16) for v in spec['expected_words']],dtype=np.uint32)
    assert len(got)==512 and np.array_equal(got,want)
    assert hashlib.sha256(got.tobytes()).hexdigest()==spec['golden_sha256']
    scope=spec['arithmetic_scope']
    assert scope['consumer_key_rows']==op[3] and scope['semantic_N']==128
    assert scope['full_L0_ATT_PV'] is False
    pre=json.loads((root/'preflight.json').read_text())
    flat=json.loads((root/'flatten.json').read_text())
    profiles={k:v['defines'] for k,v in flat.items()}
    assert pre['compile_global_defines']==[] and pre['preprocessed_master_defines']==profiles
    assert len(profiles)==48 and sum(bool(v) for v in profiles.values())==4
    replay=json.loads((root/'replay_candidate.json').read_text())
    assert pre['NEV_required']==1+sum(e['k']!='M' for e in replay['events'])==5968
    assert pre['preloads']['probability']==pre['preloads']['exp']==pre['preloads']['collateral']==0
    assert pre['fault_faces']==85
    assert len({e['sector'] for e in replay['events'] if e['k']=='M' and e.get('mem')!='hbm'})==16
    # The only VM inputs are genuine score words, not producer outputs.
    assert all(e.get('rec') in (20,21) for e in replay['events'] if e['k']=='M' and e.get('mem')!='hbm')
    return dict(status='PURE_SOURCE_PROGRAMME_CHECKS_PASS_NO_RTL_EXECUTION',key_rows=op[3],semantic_N=128,exact_expected_words=512,golden_sha256=spec['golden_sha256'],NEV=5968,master_profiles=48,nonempty_profiles=4,full_ATT_PV=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--packet',type=Path,required=True);p.add_argument('--kvroot',type=Path,required=True)
    a=p.parse_args();print(json.dumps(verify(a.packet,a.kvroot),indent=1))
