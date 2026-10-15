"""Real compact embedding endpoint binding; no unqualified view substitution."""
def land_emb_ifw_binding():
    return dict(module='qkd_land_emb_ifw', file='rtl/qwen_sys/split_20261014/qkd_land_emb_ifw.sv',
                ports=dict(ck=['ck'], rst_n=['rst_n'], emf=['emf','emf_cr'], emr=['emr','emr_cr'],
                           dno=['dno'], upi=['upi'], cri=['cri'], fi=['fi'], gfi=['gfi'], mf=['mf']),
                classed={'st':'by_design: stack strap, match gateway WS/WN/ES/EN index'})
