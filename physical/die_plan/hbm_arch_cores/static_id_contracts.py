"""Exact existing HBM physical identity contracts; no name-pattern exemptions."""
RING_MASTER = "ot_hfd_coll_q2_hard_v8g__ring_ag"
KEYBUF_MASTER = "ot_hnx_idxn_keybuf_slice"
SU_MASTER = "ot_hbm_su_static_pgslice_lg__lane_exp0_id"
# OWNER 2026-10-30 00:10 (3)(B): the SU free-ID master exposes the physical strap_* ALIAS of its native 11-bit
# lane_lane_id (wired straight through in the master's own wrapper; same row as tools/die_plan/parent_id_straps.py
# PHYSICAL_ID_ALIASES).  The native unprefixed name is never a physical static pin.
SU_ALIAS, SU_NATIVE, SU_WIDTH = "strap_lane_lane_id", "lane_lane_id", 11
SU_PACKED_MASTER = "ot_hnx_su_plain4__7dd6a1bbbf47_rst3__id44"
SU_ID_WIDTHS = {SU_MASTER: 11, SU_PACKED_MASTER: 44,
    "ot_hbm_su_static_pgslice_lg__lanes__canon_cf1e77__nocoll": 9,
    "ot_hbm_su_static_pgslice_lg__lanes_plain__canon_663526__nocoll": 9,
    "ot_hnx_su_plain4__7dd6a1bbbf47_rst3__id44__nocoll": 44,
    "ot_hbm_su_static_pgslice_lg__lane_exp__canon_7cd691": 11,
    "ot_hbm_su_static_pgslice_lg__lanes__canon_cf1e77": 9,
    "ot_hbm_su_static_pgslice_lg__lanes_plain__canon_663526": 9}

# exact (master, strap port) -> (contract kind, width)
CONTRACTS = {(RING_MASTER, "strap_qid"): ("HBM_RING_QID", 2),
             **{(m, SU_ALIAS): ("HBM_SU_LANE_ID_ALIAS", w) for m,w in SU_ID_WIDTHS.items()},
             (KEYBUF_MASTER, "strap_lane_id"): ("KEYBUF_LANE_ID", 3)}


def static_inputs(module, widths, dirs):
    # COORD 10-29 05:35, ce2560d35809: the collective ring qid; OWNER 10-30 (3)(B): the SU lane-ID alias.
    # The similarly named xload bdring has NO such authorization.
    if module in SU_ID_WIDTHS and SU_NATIVE in widths:
        raise ValueError(f"{module}: native {SU_NATIVE} must not be a physical pin; expose {SU_ALIAS} (OWNER 10-30 B)")
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
