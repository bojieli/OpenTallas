"""S81 vp parameter forms the vp_local gate measures and the intake accepts (S81-LEAF-CYC 11-11, COORD class fix).

default : the pre-R3 vp (no lane stations).
quad    : S81-LEAF-CYC (OWNER/COORD 11-11 07:45) -- one shared hi and one shared ho station per 4-lane quad on every
          non-KV ot_s81sl_leaf (CS_HI_D 1 GS 1, CS_HO_D 1 GS 1, G 4); hc_post write-back + 2 edges inside the vp.
kv_lane : the KV leaves t1/t3/t4/t5 (ot_s81sl_slice_w3 LF_CS_HI_D/HO_D 1, GS 0): per-lane stations, same + 2 edges.
A gate proof is measured for ONE form (its 'parameters'); the intake gives each bound vp the proof of its own form."""
DEFAULT = dict(ML=7, AL=6, HPL=33, CS_HI_D=0, CS_HI_GS=0, CS_HO_D=0, CS_HO_GS=0, CS_H_G=4, HQX=0)
FORMS = {
    'default': DEFAULT,
    'quad': dict(DEFAULT, CS_HI_D=1, CS_HI_GS=1, CS_HO_D=1, CS_HO_GS=1),
    'kv_lane': dict(DEFAULT, CS_HI_D=1, CS_HO_D=1),
}


def effective(overrides):
    """bound vp parameter overrides (inventory 'params', {} = defaults) -> the full effective parameter dict."""
    unknown = set(overrides) - set(DEFAULT)
    if unknown:
        raise ValueError('unmeasured vp parameter override(s): ' + ', '.join(sorted(unknown)))
    return dict(DEFAULT, **{k: int(v) for k, v in overrides.items()})


def form_of(params):
    """full effective parameter dict -> form name, or None when it is no measured form."""
    for name, p in FORMS.items():
        if p == params:
            return name
    return None
