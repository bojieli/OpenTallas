#!/usr/bin/env python3
"""Compose B2o token prices with adopted one-clock arithmetic and exact W128 HC.

B2_NATIVE_MODE=baseline preserves the plan_study_price_1017 B2o point.
B2_NATIVE_MODE=oneclock adopts ALAT4/MLAT4, one 1.2GHz domain and leaf splits.
B2_NATIVE_MODE=hc128 additionally charges +4 cycles per HC_MIX/HC_MIX_POST
net for the W128 half tree (+TLA7) and smaller root tree (-3); exposed bound.
L74 second-beat and shell crossing charges are pending native record maps;
output is a model update, never a native token-pass/physical sign-off claim.
"""
import os
from hgi_sim import plan_study_price_1017 as PS

MODE=os.environ.get('B2_NATIVE_MODE','baseline')
if MODE not in ('baseline','oneclock','hc128'):
    raise ValueError(MODE)
PS.VARIANTS={k:v for k,v in PS.VARIANTS.items() if k=='c_L4'}
PS.QWEN_EXTRA={}
if MODE!='baseline':
    import hbm_su_c12 as C12
    from hgi_sim import leaf_split_price_1023 as LSP
    C12.P['alat']=4
    C12.P['mlat']=4
    LSP.SERIAL=1.0
    os.environ['OT_HBM_LEAF_SPLIT']='1'
    if MODE=='hc128':
        old=LSP.added
        def added(r):
            a,why=old(r)
            op=getattr(r,'orig_op',f'{r.unit}.{r.op}')
            if op in ('HC.HC_MIX','FUSED.HC_PRE_NORM'):
                return a+4, (why+'+' if why else '')+'hc128_half_plus7_root_minus3'
            return a,why
        LSP.added=added

if __name__=='__main__':
    raise SystemExit(PS.main())
