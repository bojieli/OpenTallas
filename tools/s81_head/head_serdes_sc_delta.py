#!/usr/bin/env python3
"""DIE-HEAD-76-SERDESRF plan event (candidate): hd_serdes SC form = four more hard children in the existing slot.

Copies a HEAD plan whose hd_serdes already holds u_chn (ot_s81_kp4_dchn) and the two SRAM macros, and adds
  u_phy.u_link.u_tx                    ot_s81hd_sc_tx   388.8 x 120.96 at (1797.12, 25.92)  (above the coll_i0 window)
  u_phy.u_link.u_dec.u_syn.u_bm0..2    ot_s81hd_sc_bmq   95.04 x 103.68 at x 596.16 / 717.12 / 838.08, y 25.92
                                                          (west of u_chn, whose W face takes the key-equation result)
from the supplied child views (--views: {tx: {lef, lib, pins_file}, bmq: {...}}), the opt-in define
OT_S81HD_SERDES_SC and the RXQ / SC sources.  The type pins, buses, pads, clock and reset contracts are unchanged.
PIN CYCLES (declared): pma_tx +2 ck edges (KP4 encoder LA 2 + FF 1); RX = the RXQ form (+2 pma_rck edges, +1 ck edge).
Every child is placed inside the 150-um digital strip (VDDPHY region y >= 150) without overlap; checked here.
"""
import argparse
import copy
import json
import os
from pathlib import Path

STRIP_Y = 150.0
CHILDREN = [
    ("tx", "u_phy.u_link.u_tx", "ot_s81hd_sc_tx", [1797.12, 25.92], [388.8, 120.96]),
    ("bmq", "u_phy.u_link.u_dec.u_syn.u_bm0", "ot_s81hd_sc_bmq", [596.16, 25.92], [95.04, 103.68]),
    ("bmq", "u_phy.u_link.u_dec.u_syn.u_bm1", "ot_s81hd_sc_bmq", [717.12, 25.92], [95.04, 103.68]),
    ("bmq", "u_phy.u_link.u_dec.u_syn.u_bm2", "ot_s81hd_sc_bmq", [838.08, 25.92], [95.04, 103.68]),
]
SOURCES = ["rtl/dsrom_sys/s81_head/ot_s81hd_serdes_rxq.sv", "rtl/dsrom_sys/s81_head/ot_s81hd_serdes_sc.sv",
           "rtl/dsrom_sys/s81_head/ot_s81hd_serdes_sc_cores.sv", "rtl/hbm_accel/cores_split/reform_1104b/ot_s81_kp4_enc_la.sv"]
DEFINE = "OT_S81HD_SERDES_SC"


def overlap(a, b):
    (ax, ay), (aw, ah) = a
    (bx, by), (bw, bh) = b
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah


def apply(plan, views):
    out = copy.deepcopy(plan)
    t = out["partition_types"]["hd_serdes"]
    have = {c["inst"]: c for c in t.get("hard_cores", [])}
    if "u_phy.u_link.u_dec.u_chn" not in have:
        raise ValueError("base plan must already hold the u_chn child (l48 form)")
    if any(i in have for _, i, *_ in CHILDREN):
        raise ValueError("SC children already present")
    tw, th = t["outline_um"]
    placed = [(c["origin_um"], c["outline_um"], c["inst"]) for c in t["hard_cores"]]
    for kind, inst, mod, xy, wh in CHILDREN:
        x, y = xy
        w, h = wh
        if x < 4.32 or y < 4.32 or x + w > tw - 4.32 or y + h > min(th, STRIP_Y) - 2.0:
            raise ValueError(f"{inst} leaves the digital strip")
        for o in placed:
            if overlap((xy, wh), (o[0], o[1])):
                raise ValueError(f"{inst} overlaps {o[2]}")
        v = views[kind]
        if v.get("module", mod) != mod:
            raise ValueError(f"{kind} view is {v.get('module')}, want {mod}")
        t["hard_cores"].append(dict(inst=inst, module=mod, lef=v["lef"], lib=v["lib"], origin_um=list(xy),
                                    outline_um=list(wh), orient="R0", pins_file=v["pins_file"],
                                    obs_max=v.get("obs_max", "M5"),
                                    note="DIE-HEAD-76-SERDESRF SC child" + (" (pma_tx +2 ck edges)" if kind == "tx" else
                                                                            " (RXQ ldq/S_b relay inside, 0 cycles)")))
        placed.append((xy, wh, inst))
    for s in SOURCES:
        if s not in t["sources"]:
            t["sources"].append(s)
    d = t.setdefault("verilog_defines", [])
    if DEFINE not in d:
        d.append(DEFINE)
    t["note"] = t.get("note", "") + ("; DIE-HEAD-76-SERDESRF SC form: hard children u_tx (KP4 TX, PIN CYCLES pma_tx +2) "
                                     "+ u_bm0..2 (RiBM) + u_chn; RX = RXQ form; parent synth count pending")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--plan", required=True)
    ap.add_argument("--views", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    src, dst = Path(a.plan).resolve(), Path(a.out).resolve()
    if src == dst:
        raise SystemExit("write a candidate copy")
    vf = Path(a.views).resolve()
    views = json.loads(vf.read_text())
    p = apply(json.loads(src.read_text()), views)
    for c in p["partition_types"]["hd_serdes"]["hard_cores"]:
        pf = c.get("pins_file")
        if pf and not Path(pf).is_absolute():
            base = vf.parent if c["module"].startswith("ot_s81hd_sc_") else src.parent
            c["pins_file"] = os.path.relpath((base / pf).resolve(), dst.parent)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(p, indent=2) + "\n")
    print(json.dumps(dict(status="CANDIDATE", added_children=[c[1] for c in CHILDREN], pin_cycles="pma_tx +2 ck",
                          define=DEFINE)))


if __name__ == "__main__":
    main()
