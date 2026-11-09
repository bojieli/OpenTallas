#!/usr/bin/env python3
"""HBM-TRANSPORT-1 11-09: SU-face VM lane-group transport terms of a strict HBM bind (bus_groups.json landed stages).

The SU face of a VM bank samples its calendar selector (tap local_read/local_write), its request (bank rq0/wq0) and
its owner (bank rslot_v/wslot_v) on one edge; an unselected active input faults (ot_hbm_vm_lg_pair_tap,
ot_hbm_vm_lg_static_bank).  The as-built calendar compiler (native_su_calendar.compile_calendar) puts the selector on
the command's own row and the owner two edges later, i.e. it assumes zero lanes.  At bound depth the four legs land
with different depths per tap:

  D_CMD  pgp_<q>.command        -> su_<q><g>.u_slice.g_leaf[k].u_leaf.su_rq   (su_wq: same leg unless bound apart)
  D_CAL  calendar_<q>.lg_local_read/_write -> su_<q><g>.g_tap_r8b.u_tap.local_read/_write
  D_REQ  su_<q><g>...u_tap.near_rq/near_wq -> vmb_<q><b>.rq0/wq0
  D_OWN  calendar_<q>.rslot/wslot -> vmb_<q><b> (same core today: 0; read from the bind if it is ever a landing leg)

Law (real-RTL bench tb_vmlg_su_bound.sv, fixed form 1119/1119 and every +-1 mutant FAIL on bind_lat_vJ and bind_F5b):
  selector row = command row - (D_CAL - D_CMD)             selector_advance_by_bank
  owner row    = command row + 2 + D_CMD + D_REQ - D_OWN   request/write_lane_edges_by_bank (+2 is the as-built LG path)
Epoch form (cx_layer_1021.epoch_calendar: one constant row over the epoch) is immune inside the epoch; its edges need
  SU_START_GUARD = 33 + max(0, max_b(D_CAL - D_CMD))       first command must find the selector at its tap
  EPOCH_TAIL     = 64 + max(0, max_b(D_CMD + D_REQ - D_OWN)) last request must find the owner at its bank
(the as-built margins of 33 / 64 are kept on top of the bound terms).

  python3 tools/hbm_layer_vehicle/su_transport.py --bind BIND_DIR --out su_transport.json
Source-functional lane timing only; never a physical-clock qualification.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SCHEMA = "opentallas.hbm_su_transport.v1"
AS_BUILT_START_GUARD = 33
AS_BUILT_EPOCH_TAIL = 64

_LEAF = re.compile(r"^su_(?P<q>[NS][EW])(?P<g>\d)\.u_slice\.g_leaf\[(?P<k>\d)\]\.u_leaf$")
_TAP = re.compile(r"^su_(?P<q>[NS][EW])(?P<g>\d)\.g_tap_r8b\.u_tap$")
_BANK = re.compile(r"^vmb_(?P<q>[NS][EW])(?P<b>\d)$")
_NEAR = re.compile(r"^su_(?P<q>[NS][EW])(?P<g>\d)\.(?:.*\.)?near_(?P<kind>rq|wq)$")


def _one(table, key, value, what):
    old = table.setdefault(key, value)
    if old != value:
        raise ValueError(f"{what} {key}: two landed depths {old} and {value} (bind must land one value per leg)")


def profile(bus_groups):
    """bus_groups: parsed bus_groups.json -> {schema, quarters: {q: per-bank lists}, su_start_guard, epoch_tail}."""
    cmd, cal, req, own = {}, {}, {}, {}
    for grp in bus_groups["landing"]:
        sink = grp["sink"]
        for m in grp["members"]:
            port, src, d = m["sink_port"], m["source"], int(m["landed_stages"])
            if (mo := _LEAF.match(sink)) and port in ("su_rq", "su_wq") and src.endswith(".command"):
                _one(cmd, (mo["q"], int(mo["g"]), int(mo["k"]), port[3:]), d, "D_CMD")
            elif (mo := _TAP.match(sink)) and port in ("local_read", "local_write") and src.startswith("calendar_"):
                _one(cal, (mo["q"], int(mo["g"]), "rq" if port == "local_read" else "wq"), d, "D_CAL")
            elif (mo := _BANK.match(sink)) and port in ("rq0", "wq0") and (ms := _NEAR.match(src)):
                _one(req, (mo["q"], int(mo["b"]), port[:2]), (int(ms["g"]), d), "D_REQ")
            elif (mo := _BANK.match(sink)) and port in ("rslot_v", "wslot_v") and src.startswith("calendar_"):
                _one(own, (mo["q"], int(mo["b"]), "rq" if port == "rslot_v" else "wq"), d, "D_OWN")
    quarters = {}
    for q in sorted({k[0] for k in req}):
        if any((q, b, kind) not in req for b in range(8) for kind in ("rq", "wq")):
            raise ValueError(f"quarter {q}: SU-face request legs of all 8 banks are required")
        out = {f: [] for f in ("tap", "d_cmd", "d_cal", "d_req", "d_own", "d_cmd_w", "d_cal_w", "d_wq", "d_own_w")}
        for b in range(8):
            g, d_rq = req[(q, b, "rq")]
            g_w, d_wq = req[(q, b, "wq")]
            if g_w != g:
                raise ValueError(f"vmb_{q}{b}: rq0 and wq0 come from different taps")
            k = b - 2 * g
            if k not in (0, 1):
                raise ValueError(f"vmb_{q}{b}: tap su_{q}{g} is not its pair tap")
            if (q, g, k, "rq") not in cmd or (q, g, "rq") not in cal or (q, g, "wq") not in cal:
                raise ValueError(f"su_{q}{g}: command or calendar leg missing in the bind")
            c = cmd[(q, g, k, "rq")]
            for f, v in (("tap", g), ("d_cmd", c), ("d_cal", cal[(q, g, "rq")]), ("d_req", d_rq),
                         ("d_own", own.get((q, b, "rq"), 0)), ("d_cmd_w", cmd.get((q, g, k, "wq"), c)),
                         ("d_cal_w", cal[(q, g, "wq")]), ("d_wq", d_wq), ("d_own_w", own.get((q, b, "wq"), 0))):
                out[f].append(v)
        out["selector_advance_by_bank"] = [out["d_cal"][b] - out["d_cmd"][b] for b in range(8)]
        out["write_selector_advance_by_bank"] = [out["d_cal_w"][b] - out["d_cmd_w"][b] for b in range(8)]
        out["request_lane_edges_by_bank"] = [out["d_cmd"][b] + out["d_req"][b] - out["d_own"][b] for b in range(8)]
        out["write_lane_edges_by_bank"] = [out["d_cmd_w"][b] + out["d_wq"][b] - out["d_own_w"][b] for b in range(8)]
        for f in ("request_lane_edges_by_bank", "write_lane_edges_by_bank"):
            if min(out[f]) < 0:
                raise ValueError(f"quarter {q}: owner lands after its request ({f} {out[f]})")
        adv = max(0, *out["selector_advance_by_bank"], *out["write_selector_advance_by_bank"])
        lag = max(0, *out["request_lane_edges_by_bank"], *out["write_lane_edges_by_bank"])
        out["su_start_guard"] = AS_BUILT_START_GUARD + adv
        out["epoch_tail"] = AS_BUILT_EPOCH_TAIL + lag
        quarters[q] = out
    if not quarters:
        raise ValueError("no SU-face VM lane-group legs in this bind")
    return dict(schema=SCHEMA, quarters=quarters,
                su_start_guard=max(v["su_start_guard"] for v in quarters.values()),
                epoch_tail=max(v["epoch_tail"] for v in quarters.values()),
                law="selector row = cmd row - (D_CAL-D_CMD); owner row = cmd row + 2 + D_CMD + D_REQ - D_OWN")


def calendar_kwargs(prof, quarter):
    """Keyword arguments of native_su_calendar.compile_calendar for one quarter of a profile."""
    q = prof["quarters"][quarter]
    return {f: list(q[f]) for f in ("request_lane_edges_by_bank", "write_lane_edges_by_bank",
                                    "selector_advance_by_bank", "write_selector_advance_by_bank")}


def load(path):
    prof = json.loads(Path(path).read_text())
    if prof.get("schema") != SCHEMA:
        raise ValueError(f"{path}: not an {SCHEMA} profile")
    return prof


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--bind", type=Path, required=True, help="strict bind dir (bus_groups.json)")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    prof = profile(json.loads((a.bind / "bus_groups.json").read_text()))
    prof["bind"] = str(a.bind)
    a.out.write_text(json.dumps(prof, indent=1) + "\n")
    print(json.dumps({q: dict(adv=v["selector_advance_by_bank"], lag=v["request_lane_edges_by_bank"])
                      for q, v in prof["quarters"].items()}))
    print(f"su_start_guard {prof['su_start_guard']} epoch_tail {prof['epoch_tail']}")


if __name__ == "__main__":
    main()
