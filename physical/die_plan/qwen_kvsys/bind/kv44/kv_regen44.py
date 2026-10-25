"""KV-BIND 10-24 asbuilt.param_regen hook for the kv44 re-bind (plan v3.8x) = ../kv_regen36e.py (BINDER4 rule values:
ECTL RESPONSE_LAT / QK_ISSUE_AGE, AHUB AP_OFS / FR_OFS, SEQ KVN_A0, PV ctl TRUNK_D / FLAG_D, d2d TXDP_K; its guard
re-measures the ECTL K round trip on THIS bind and fails if the v3.6 rule table is stale) + the TOK-QK opt-ins:
  KV-R2  host (qkd_host_root_admission_obsx_bo1)  D2D_BOOT_ORDER = 1  (BO1: D2D boot epoch waits for the accepted programme)
  KV-R3  d2d_kv (qkd_d2d_static_sfm)              OBS1_COMPAT = 1     (STATUS v1 receiver compatibility, main 60c21cd01d)
and one bound raise forced by plan v3.8x:
  vport_* (qkd_pv16_vport_b)  RT bound 31 -> 32: v3.8x lengthens the slg <-> vport lanes so the RT rule
  (9 + max_g(D(vq_g) + D(rs_g)), kv_param_rules_v36) gives RT 32 on 12 of 16 ports (kv41: 30/31; kv_wreq_dq44.py).
  RT is the HARDWARE BOUND of the boot-selected slot tap (cfg_age word RT <= bound, else age_bad); one type -> all 16.
  Slot line DQ + RT + 1 = 48 deep (was 47); behaviour for any word RT <= 31 is unchanged.
and one stale rule value replaced:
  ahub (qkd_ahub_static_dw) AP_OFS: the v3.6 rule table value 64'hffd2ffd1ffd1ffd1 is stale on v3.8x (ap lanes +1/+3/+1/+3,
  f_aqm_w +1); AP_OFS_KV44 = regen_constants.py kv_ahub (AP_OFS_s = asb_s + Delta D(ap_s) + Delta D(f_aqm)) on the kv44
  bind, pinned here like D2D_TXDP_K: bind_post.py re-derives it from every bind and FAILS (MISMATCH) on any change."""
import importlib.util
import re
from pathlib import Path

_b = Path(__file__).resolve().parent.parent / "kv_regen36e.py"
_s = importlib.util.spec_from_file_location("kv_regen36e", _b)
K36 = importlib.util.module_from_spec(_s)
_s.loader.exec_module(K36)
OPT_IN = {r"qkd_host_root_admission_obsx_bo1": dict(D2D_BOOT_ORDER=1), r"qkd_d2d_static_sfm": dict(OBS1_COMPAT=1)}
RT_BOUND = 32
AP_OFS_KV44 = "64'hffd5ffd2ffd5ffd3"   # WS +2, WN +4, ES +1, EN +3 vs v36 (EN ES WN WS = [63:48]..[15:0])


def regen(ctx):
    r = K36.regen(ctx)
    n = {}
    for c in ctx.F.cells:
        for rx, ps in OPT_IN.items():
            if re.fullmatch(rx, c.module):
                r["params"].setdefault(c.path, {}).update(ps)
                n[rx] = n.get(rx, 0) + 1
    na = 0
    for c in ctx.F.cells:
        if re.search(r"qkd_ahub_static_dw", c.module):
            r["params"][c.path]["AP_OFS"] = AP_OFS_KV44
            na += 1
    if na != 1:
        raise ValueError(f"kv_regen44: {na} ahub cells")
    r["record"]["applied"]["AP_OFS_kv44"] = AP_OFS_KV44
    nv = 0
    for c in ctx.F.cells:
        if c.module == "qkd_pv16_vport_b":
            r["params"].setdefault(c.path, {})["RT"] = RT_BOUND
            nv += 1
    if nv != 16:
        raise ValueError(f"kv_regen44: {nv} qkd_pv16_vport_b cells (expect 16)")
    if n != {k: 1 for k in OPT_IN}:
        raise ValueError(f"kv_regen44: opt-in cells found {n} (expect one host bo1 and one d2d sfm)")
    r["record"]["kv44_opt_in"] = dict(KV_R2="host.D2D_BOOT_ORDER=1", KV_R3="d2d_kv.OBS1_COMPAT=1", cells=n, vport_RT_bound=dict(value=RT_BOUND, cells=nv, why="v3.8x RT rule gives 32 on 12 ports"))
    return r
