#!/usr/bin/env python3
"""S81 SerDes warm-reset sequencer plan delta (S81.RESET, DIE-S81-49, OWNER 2026-11-02 17:55 decision 1).

OWNER (final): "SerDes soft warm reset = a local reset sequencer holding reset >= 64 edges after the PMA
clock restarts" -- the same contract HEAD adopted (tools/s81_head/head_serdes_locksafe_delta.py).

Mechanism (source, not this tool): the 14 as-built S81 columns u_lk_* (physical/die_plan/s81/bind/inputs/
die_b178.v) set ot_pdie_serdes_col #(.LOCKSAFE(1), .HOLD_EDGES(64)); the column then holds its whole reset in
the SHARED, gated ot_pdie_pma_reset_hold (rtl/dsrom_sys/s81_link/ot_pdie_serdes_locksafe.sv, the module HEAD's
ot_s81hd_serdes_link_ls uses; no fork) on a new die IO lk_<lane>_pma_lock (asbuilt io_roles -> partition
role pma_lock).  The sequencer sits INSIDE the column, so every child path of the counted/kit views
(u_ptx, u_prx, u_enc, u_dec.*, u_rm) is unchanged.

This delta copies an S81 plan and, in the SerDes partition types (serdes__*) only:
  * adds one pad io_pma_lock (in, 1 bit) = the PMA lock authority (as HEAD's hd_serdes pad pma_lock);
  * records the sequencer in the io_pma_rck pad-clock cdc evidence and the type note.
No other type, port, bus, pin, clock, lane or cycle changes. Cost: 9 FF per column (2 sync + 6 count + 1 ready),
+66 recovered-clock boot edges, zero mission cycles.
"""
import argparse
import copy
import json
from pathlib import Path

PREFIX = "serdes__"
PAD = {"name": "io_pma_lock", "dir": "in", "width": 1,
       "note": "S81.RESET PMA lock authority for the warm-reset sequencer (OWNER 11-02 17:55): low = hold the column "
               "in reset; release 2 + 64 recovered-clock edges after lock with the PMA clock running; asynchronous "
               "assert, release synchronised to io_pma_rck inside ot_pdie_pma_reset_hold"}
CDC_NOTE = ("; S81.RESET: the column reset is held by ot_pdie_pma_reset_hold on pma_rck (async assert on rst low or "
            "io_pma_lock low, 2-flop release synchroniser + 64-edge count), then the per-domain rs_t/rs_r synchronisers")
TYPE_NOTE = "; S81.RESET warm-reset sequencer ot_pdie_pma_reset_hold 9 FF/column, 0 mission cycles (DIE-S81-49)"


def serdes_types(plan):
    return sorted(k for k in plan["partition_types"] if k.startswith(PREFIX))


def apply(plan):
    out = copy.deepcopy(plan)
    names = serdes_types(out)
    if not names:
        raise ValueError("no serdes__* partition types in this plan")
    for tn in names:
        t = out["partition_types"][tn]
        phy = [c for c in t["contents"] if c.get("inst") == "u_phy"]
        if len(phy) != 1 or phy[0].get("module") != "ot_pdie_serdes":
            raise ValueError(f"{tn}.u_phy must be the released ot_pdie_serdes column")
        pads = list(t.get("pads", []))
        if any(p["name"] == PAD["name"] for p in pads):
            raise ValueError(f"{tn}: {PAD['name']} pad already present")
        if not any(p["name"] == "io_pma_rck" for p in pads):
            raise ValueError(f"{tn}: no io_pma_rck pad (not a SerDes column type)")
        t["pads"] = pads + [dict(PAD)]
        for pin in t.get("clock", {}).get("pad_clock", {}).get("pins", []):
            if pin.get("name") == "io_pma_rck" and "cdc_evidence" in pin:
                pin["cdc_evidence"] += CDC_NOTE
        t["note"] = t.get("note", "") + TYPE_NOTE
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--plan", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    src, dst = Path(a.plan).resolve(), Path(a.out).resolve()
    if src == dst:
        raise SystemExit("write a candidate copy; do not overwrite the input plan")
    plan = json.loads(src.read_text())
    dst.write_text(json.dumps(apply(plan), indent=1) + "\n")
    print(f"wrote {dst}: {len(serdes_types(plan))} serdes types + pad {PAD['name']}")


if __name__ == "__main__":
    main()
