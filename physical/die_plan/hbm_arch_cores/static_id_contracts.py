"""Exact existing HBM physical identity contracts; no name-pattern exemptions."""
RING_MASTER = "ot_hfd_coll_q2_hard_v8g__ring_ag"
SU_MASTER = "ot_hbm_su_static_pgslice_lg__lane_exp0_id"

def static_inputs(module, widths, dirs):
    # COORD 10-29 05:35, ce2560d35809: only the collective ring qid.
    # The similarly named xload bdring has NO such authorization.
    if module != RING_MASTER or "strap_qid" not in widths:
        return []
    if type(widths["strap_qid"]) is not int or widths["strap_qid"] != 2 or dirs.get("strap_qid") != "input":
        raise ValueError("HBM_RING_QID requires the exact 2-bit input strap_qid")
    return ["strap_qid"]

def su_native_prep(module, widths, dirs):
    """Validate PREP only; never grants a native-name false-path exemption."""
    if module != SU_MASTER or widths.get("lane_lane_id") != 11 or dirs.get("lane_lane_id") != "input":
        raise ValueError("SU native identity PREP requires exact master and 11-bit lane_lane_id input")
    return {"module":module,"port":"lane_lane_id","width":11,
            "status":"PREP_OWNER_NAMING_DECISION_REQUIRED","physical_exemption":False}
