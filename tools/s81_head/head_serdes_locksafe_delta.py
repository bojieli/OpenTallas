#!/usr/bin/env python3
"""HEAD SerDes warm-reset sequencer plan delta (DIE-HEAD-54, OWNER 2026-11-02 17:55 decision 1).

OWNER (final): "SerDes soft warm reset = a local reset sequencer holding reset >= 64 edges after
the PMA clock restarts. Implement it as the HEAD reset contract."

Copies a HEAD plan and, in partition type hd_serdes only:
  * u_phy module ot_s81hd_serdes_link -> ot_s81hd_serdes_link_ls (LOCKSAFE=1, HOLD_EDGES=64), the
    released adapter plus the shared, gated ot_pdie_pma_reset_hold; the core keeps instance u_link, so
    the counted hard child u_phy.u_link.u_dec.u_chn (ot_s81_kp4_dchn) keeps its path and views;
  * one new PHY pad pma_lock (in, 1 bit) = the PMA lock authority, bound to u_phy.pma_lock;
  * sources += the wrapper and the shared sequencer file.
No other type, port, bus, pin, clock or cycle changes. Cost: 9 FF per SerDes link (2 sync + 6 count +
1 ready), +66 recovered-clock boot edges, zero mission cycles.
"""
import argparse
import copy
import json
from pathlib import Path

TYPE = "hd_serdes"
OLD, NEW = "ot_s81hd_serdes_link", "ot_s81hd_serdes_link_ls"
SRC_NEW = ["rtl/dsrom_sys/s81_head/ot_s81hd_serdes_link_ls.sv", "rtl/dsrom_sys/s81_link/ot_pdie_serdes_locksafe.sv"]
PAD = {"name": "pma_lock", "dir": "in", "width": 1,
       "note": "PMA lock authority for the warm-reset sequencer (OWNER 11-02 17:55): low = hold the link in reset; "
               "release 2 + 64 recovered-clock edges after lock with the PMA clock running"}


def apply(plan, hold_edges=64):
    out = copy.deepcopy(plan)
    t = out["partition_types"][TYPE]
    cs = [c for c in t["contents"] if c["inst"] == "u_phy"]
    if len(cs) != 1 or cs[0]["module"] != OLD:
        raise ValueError(f"{TYPE}.u_phy must be the released {OLD}")
    if any(p["name"] == PAD["name"] for p in t.get("pads", [])):
        raise ValueError("pma_lock pad already present")
    c = cs[0]
    c["module"] = NEW
    c["params"] = dict(c.get("params", {}), LOCKSAFE=1, HOLD_EDGES=hold_edges)
    c["bind"] = dict(c["bind"], pma_lock="pad:pma_lock")
    c["note"] = c.get("note", "") + "; OWNER 11-02 17:55 warm-reset sequencer (ot_pdie_pma_reset_hold, 2+64 rck edges)"
    t["pads"] = list(t.get("pads", [])) + [dict(PAD)]
    src = list(t.get("sources", []))
    for s in SRC_NEW:
        if s not in src:
            src.append(s)
    t["sources"] = src
    t["note"] = t.get("note", "") + "; warm-reset sequencer 9 FF/link, 0 mission cycles (DIE-HEAD-54)"
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--plan", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--hold-edges", type=int, default=64)
    a = ap.parse_args()
    src, dst = Path(a.plan).resolve(), Path(a.out).resolve()
    if src == dst:
        raise SystemExit("write a candidate copy; do not overwrite the input plan")
    dst.write_text(json.dumps(apply(json.loads(src.read_text()), a.hold_edges), indent=1) + "\n")
    print(f"wrote {dst}")


if __name__ == "__main__":
    main()
