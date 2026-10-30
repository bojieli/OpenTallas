"""Exact existing HBM physical identity contracts; no name-pattern exemptions."""
RING_MASTER = "ot_hfd_coll_q2_hard_v8g__ring_ag"
SU_MASTER = "ot_hbm_su_static_pgslice_lg__lane_exp0_id"
# OWNER 2026-10-30 00:10 (3)(B): the SU free-ID master exposes the physical strap_* ALIAS of its native 11-bit
# lane_lane_id (wired straight through in the master's own wrapper; same row as tools/die_plan/parent_id_straps.py
# PHYSICAL_ID_ALIASES).  The native unprefixed name is never a physical static pin.
SU_ALIAS, SU_NATIVE, SU_WIDTH = "strap_lane_lane_id", "lane_lane_id", 11

# exact (master, strap port) -> (contract kind, width)
CONTRACTS = {(RING_MASTER, "strap_qid"): ("HBM_RING_QID", 2),
             (SU_MASTER, SU_ALIAS): ("HBM_SU_LANE_ID_ALIAS", SU_WIDTH)}


def static_inputs(module, widths, dirs):
    # COORD 10-29 05:35, ce2560d35809: the collective ring qid; OWNER 10-30 (3)(B): the SU lane-ID alias.
    # The similarly named xload bdring has NO such authorization.
    if module == SU_MASTER and SU_NATIVE in widths:
        raise ValueError(f"{SU_MASTER}: native {SU_NATIVE} must not be a physical pin; expose {SU_ALIAS} (OWNER 10-30 B)")
    out = []
    for (m, port), (kind, width) in sorted(CONTRACTS.items()):
        if module != m or port not in widths:
            continue
        if type(widths[port]) is not int or widths[port] != width or dirs.get(port) != "input":
            raise ValueError(f"{kind} requires the exact {width}-bit input {port}")
        out.append(port)
    return out


def contract(module, straps):
    """straps.json contract record of a kit's declared static ID straps (exactly one approved row)."""
    rows = [(CONTRACTS.get((module, s)), s) for s in straps]
    if len(rows) != 1 or rows[0][0] is None:
        raise ValueError(f"{module}: straps {list(straps)} are not exactly one approved HBM static ID contract")
    (kind, width), port = rows[0]
    return {"kind": kind, "module": module, "port": port, "width": width}


def su_native_prep(module, widths, dirs):
    """Validate PREP only; never grants a native-name false-path exemption."""
    if module != SU_MASTER or widths.get("lane_lane_id") != 11 or dirs.get("lane_lane_id") != "input":
        raise ValueError("SU native identity PREP requires exact master and 11-bit lane_lane_id input")
    return {"module":module,"port":"lane_lane_id","width":11,
            "status":"PREP_OWNER_NAMING_DECISION_REQUIRED","physical_exemption":False}
