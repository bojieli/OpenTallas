#!/usr/bin/env python3
"""DIE-S81-27 WS3 fix-only lot replan: compose delta_ws3_lot_1029 (DIE-S81-26) onto a COPY of the FROZEN plan_s13r2.

COORD 10-29 11:28 "WS3: build both variants to G0/G0C in parallel; first pass wins" (rule 12.17(3), fix-only after freeze).
OWNER 10-29: S81 PMA 129.6 x 2246.4 rotates 90 deg along the shore; no re-aspect, no fake shim.  plan_s13r2.json is read only.

Geometry (both variants, from delta_ws3_lot_1029.json):
  lk_WS3 (serdes__t12, only instance) 1442.88x2453.76 -> 2885.76x1226.88 shore lot, same origin (8760.96,103.68), MX;
    io_lk_WS3_u_phy = PMA R90 tx/rx pair stacked in depth [8824.6..11071.0]x[103.68..362.88]; pg_domain_phy_lk_WS3 per json;
  iqf (iqf__t1) (10203.84,103.68) -> (8760.96,1330.56) (old WS3 upper half).
Re-pins (types touched, all single-instance):
  serdes__t12      6 coll ft slots: W windows unchanged in die y (lk_WS0 seam), N(die) windows at the json seam_x;
  iqf__t1          old ft0/ft1 (hbmrd/DFI) removed; 8 coll ft slots ft2..ft9 S<->N; idx_i0/idx_o0/flt_o0 N -> E face
                   (svc_0 W); qc_o0/ql_i0 stay N, moved into the free s_0S_x00 S-face gap [455.8, 663.7];
  svc_lo_..._rs_w  (svc_0) dfi_o0/hbmrd_i0 S -> E; ft0 (idx) N->S becomes N->W; ft1/ft2 (qc/ql) removed;
  svc_lo_..._rs    (svc_2) + ft0 (DFI W->S) + ft1 (hbmrd S->W), stations sited by tools/die_plan/ft_corridor.py;
  phy__t1          dfi_i7/hbmrd_o7 W -> N face under svc_2;
  slice_station__t49 (s_0S_x00) ft0 in E->S (qc), ft3 out E->S (ql).
Stations of every changed slot = ceil(route / ft_station_max_um) on check.py's own lane_geometry route (R3), +1 only
when ft_corridor cannot site the bank (reported).  Lane latency = gen.py latency --inplace after the landing compose.
Variants (landing region table = s13 sidecar minus collector, boxes of lk_WS3/iqf moved to the new rects):
  V1  landing-region tags travel (iqf stays hard_phy_hbm);
  V2  iqf retagged std_bg_25_0 (the tag of the footprint it moves into, = lk_WS0/lk_WS3);
  BASE  no geometry change (control: un-compose + re-compose of plan_s13r2 only).
usage: compose_ws3_1029.py --variant V1|V2|BASE --out DIR [--plan P] [--sidecar S] [--delta D]
       compose_ws3_1029.py --render PLAN.json --out PNG [--title T]"""
import argparse
import copy
import hashlib
import importlib.util
import json
import math
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/die_plan"))
sys.path.insert(0, str(ROOT))
import schema as S  # noqa: E402

X0, YS, YM, YT = 8760.96, 103.68, 1330.56, 2557.44
WS3_OUT = [2885.76, 1226.88]
IQF_NEW = [8760.96, 1330.56]
SVC0_O, SVC2_O = (10203.84, 1330.56), (11646.72, 1330.56)
EW, NS = ["M6", "M4"], ["M7", "M5"]
# lane -> (iqf slot, direction) for the 8 collective lanes that now cross iqf
COLL = {"coll__lk_WS0__s_0S_LP": ("ft2", "in"), "coll__lk_WS1__s_0S_LP": ("ft3", "in"),
        "coll__lk_WS2__s_0S_LP": ("ft4", "in"), "coll__lk_WS3__s_0S_LP": ("ft5", "in"),
        "coll__s_0S_LP__lk_WS0": ("ft6", "out"), "coll__s_0S_LP__lk_WS1": ("ft7", "out"),
        "coll__s_0S_LP__lk_WS2": ("ft8", "out"), "coll__s_0S_LP__lk_WS3": ("ft9", "out")}
OTHER = ["dfi__svc_0__phy_hbm", "hbmrd__phy_hbm__svc_0", "qc__iqf__s_0N_LP", "ql__s_0N_LP__iqf",
         "idx__s_3S_C__iqf", "idx__iqf__svc_0", "flt__iqf__svc_0"]
TOUCHED = list(COLL) + OTHER
# type-local windows chosen here (all inside free face spans; see the type dumps in the receipt)
W_HBMRD_EW = [280.0, 523.42]          # svc_0 E = svc_2 W (y local; same origin y)
W_DFI_EW = [524.62, 822.0]
W_HBMRD_NS = [550.08, 793.5]          # svc_2 S = phy_hbm N (x local; same origin x)
W_DFI_NS = [795.6, 1092.98]
W_QL_N = [460.8, 569.636]             # iqf N = s_0S_x00 S (x local; same origin x); s00 S free gap [455.772, 663.744]
W_QC_N = [576.0, 632.028]
W_IDXI_E = [598.272, 708.644]         # iqf E = svc_0 W (y local; same origin y)
W_IDXO_E = [710.976, 820.58]
W_FLT_E = [549.312, 557.924]


def r6(v):
    return round(float(v), 6)


def load_mod(name, path):
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def slot_of(t, name):
    return next(s for s in t.get("ft_slots", []) if s["name"] == name)


def bus_of(t, name):
    return next(b for b in t["buses"] if b["name"] == name)


def mkport(src, sbus, dst, dbus, width, kind, face, layers, win, order):
    return dict(id=None, src=dict(part=src, bus=sbus), dst=dict(part=dst, bus=dbus), width=width, kind=kind, face=face,
                layers=list(layers), window_um=[r6(win[0]), r6(win[1])], order=order)


def apply_geometry(raw, delta, log):
    T = raw["partition_types"]
    parts = {p["name"]: p for p in raw["partitions"]}
    ports = {p["id"]: p for p in raw["ports"]}
    lanes = {l["id"]: l for l in raw["lanes"]}
    g = {x["name"]: x for x in delta["geometry"]["partitions"]}
    assert parts["lk_WS3"]["origin_um"] == g["lk_WS3"]["new"]["origin"] and parts["lk_WS3"]["orient"] == "MX"
    assert parts["iqf"]["origin_um"] == g["iqf"]["old"]["origin"] and parts["iqf"]["orient"] == "R0"
    for n, tn in (("lk_WS3", "serdes__t12"), ("iqf", "iqf__t1"), ("svc_0", "svc_lo_dsdv_svc_rs_w__t1"),
                  ("svc_2", "svc_lo_dsdv_svc_rs__t1"), ("phy_hbm", "phy__t1"), ("s_0S_x00", "slice_station__t49")):
        assert parts[n]["type"] == tn and sum(p["type"] == tn for p in raw["partitions"]) == 1, (n, tn)
    # ---------------------------------------------------------------- partitions / outlines
    parts["iqf"]["origin_um"] = list(IQF_NEW)
    t12 = T["serdes__t12"]
    H = WS3_OUT[1]
    old_h = t12["outline_um"][1]
    t12["outline_um"] = list(WS3_OUT)
    log.append(f"lk_WS3 serdes__t12 outline [1442.88, {old_h}] -> {WS3_OUT} (origin {parts['lk_WS3']['origin_um']}, MX)")
    log.append(f"iqf origin {g['iqf']['old']['origin']} -> {IQF_NEW}")
    # ---------------------------------------------------------------- collective lanes
    cs = {r["lane"]: r for r in delta["coll_slots"]}
    t_iqf = T["iqf__t1"]
    t_iqf["ft_slots"] = [s for s in t_iqf["ft_slots"] if s["name"] not in ("ft0", "ft1")]
    log.append("iqf__t1 ft0 (hbmrd E->N) / ft1 (DFI N->E) removed (DFI/hbmrd now via svc_2)")
    used_n = []                                    # WS3 local-S (= die N) windows, overlap guard
    for lid, (qs, d) in COLL.items():
        ln = lanes[lid]
        ids = list(ln["ports"])
        row = cs[lid]
        if d == "in":
            i = next(k for k, p in enumerate(ids) if ports[p]["src"]["part"] == "lk_WS3")
            a = ports[ids[i]]
            assert a["face"] == "N" and a["dst"]["part"] == "s_0S_x00", a
            s00w = list(a["window_um"])
            wd = s00w[1] - s00w[0]
            if row["kind"] == "ws3_own":
                seam = list(s00w)
            else:
                seam = [r6(row["seam_x"] - wd / 2), r6(row["seam_x"] + wd / 2)]
                k0 = ports[ids[i - 1]]
                assert k0["dst"]["part"] == "lk_WS3" and k0["face"] == "E"
                sl = slot_of(t12, row["ws3_slot"])
                assert sl["name"] + "_o" == a["src"]["bus"] and sl["in_face"] == "W" and sl["out_face"] == "S"
                lo, hi = k0["window_um"]
                sl["in_window_um"] = [r6(H - (hi - YS)), r6(H - (lo - YS))]
                sl["out_window_um"] = [r6(seam[0] - X0), r6(seam[1] - X0)]
                log.append(f"serdes__t12 {sl['name']} W {sl['in_window_um']} -> S(die N) {sl['out_window_um']}")
            used_n.append((seam[0], seam[1], lid))
            dst = dict(a["dst"])
            a["dst"] = dict(part="iqf", bus=qs + "_i")
            a["window_um"] = list(seam)
            b = mkport("iqf", qs + "_o", dst["part"], dst["bus"], a["width"], a.get("kind", "data"), "N", NS, s00w,
                       a.get("order", "lsb_low"))
            ids.insert(i + 1, b)
            t_iqf["ft_slots"].append(dict(name=qs, in_face="S", out_face="N", width=a["width"], stations=1,
                                          in_window_um=[r6(seam[0] - X0), r6(seam[1] - X0)],
                                          out_window_um=[r6(s00w[0] - X0), r6(s00w[1] - X0)], order=a.get("order", "lsb_low"),
                                          layers=list(NS)))
        else:
            i = next(k for k, p in enumerate(ids) if ports[p]["dst"]["part"] == "lk_WS3")
            a = ports[ids[i]]
            assert a["face"] == "S" and a["src"]["part"] == "s_0S_x00", a
            s00w = list(a["window_um"])
            wd = s00w[1] - s00w[0]
            if row["kind"] == "ws3_own":
                seam = list(s00w)
            else:
                seam = [r6(row["seam_x"] - wd / 2), r6(row["seam_x"] + wd / 2)]
                k1 = ports[ids[i + 1]]
                assert k1["src"]["part"] == "lk_WS3" and k1["face"] == "W"
                sl = slot_of(t12, row["ws3_slot"])
                assert sl["name"] + "_i" == a["dst"]["bus"] and sl["in_face"] == "S" and sl["out_face"] == "W"
                lo, hi = k1["window_um"]
                sl["out_window_um"] = [r6(H - (hi - YS)), r6(H - (lo - YS))]
                sl["in_window_um"] = [r6(seam[0] - X0), r6(seam[1] - X0)]
                log.append(f"serdes__t12 {sl['name']} S(die N) {sl['in_window_um']} -> W {sl['out_window_um']}")
            used_n.append((seam[0], seam[1], lid))
            dst = dict(a["dst"])
            a["dst"] = dict(part="iqf", bus=qs + "_i")
            b = mkport("iqf", qs + "_o", dst["part"], dst["bus"], a["width"], a.get("kind", "data"), "S", NS, seam,
                       a.get("order", "lsb_low"))
            ids.insert(i + 1, b)
            t_iqf["ft_slots"].append(dict(name=qs, in_face="N", out_face="S", width=a["width"], stations=1,
                                          in_window_um=[r6(s00w[0] - X0), r6(s00w[1] - X0)],
                                          out_window_um=[r6(seam[0] - X0), r6(seam[1] - X0)], order=a.get("order", "lsb_low"),
                                          layers=list(NS)))
        ln["ports"] = ids
        log.append(f"{lid}: +iqf {qs} ({'S->N' if d == 'in' else 'N->S'}) seam die-x {seam} s00 {s00w}")
    used_n.sort()
    for (a0, a1, la), (b0, b1, lb) in zip(used_n, used_n[1:]):
        assert b0 - a1 >= 1.0, ("WS3/iqf seam windows overlap", la, lb, a1, b0)
    assert used_n[0][0] >= X0 + 6 and used_n[-1][1] <= X0 + 1442.88 - 6
    # ---------------------------------------------------------------- svc_0 / svc_2 / phy_hbm: DFI + hbmrd via svc_2
    t0 = T["svc_lo_dsdv_svc_rs_w__t1"]
    t2 = T["svc_lo_dsdv_svc_rs__t1"]
    tp = T["phy__t1"]
    b = bus_of(t0, "hbmrd_i0"); b.update(face="E", window_um=list(W_HBMRD_EW), layers=list(EW))
    b = bus_of(t0, "dfi_o0"); b.update(face="E", window_um=list(W_DFI_EW), layers=list(EW))
    t0["ft_slots"] = [s for s in t0["ft_slots"] if s["name"] not in ("ft1", "ft2")]
    f0 = slot_of(t0, "ft0")
    assert f0["in_face"] == "N" and f0["out_face"] == "S"
    f0["out_face"] = "W"
    f0["out_window_um"] = list(W_IDXI_E)
    f0.pop("layers", None)
    f0["in_layers"], f0["out_layers"] = list(NS), list(EW)
    for k in ("regs_um", "bit_sites_um", "bit_site_cell_um"):
        f0.pop(k, None)
    for nm, win in (("idx_i0", W_IDXO_E), ("flt_i0", W_FLT_E)):
        b = bus_of(t0, nm)
        assert b["face"] == "S", (nm, b["face"])
        b.update(face="W", window_um=list(win), layers=list(EW))
    log.append("svc_0 type: dfi_o0/hbmrd_i0 S -> E face; idx_i0/flt_i0 S -> W (iqf E); ft0 (idx) N->S -> N->W; "
               "ft1/ft2 (qc/ql) removed")
    t2.setdefault("ft_slots", [])
    assert not any(s["name"] in ("ft0", "ft1") for s in t2["ft_slots"])
    t2["ft_slots"] += [
        dict(name="ft0", in_face="W", out_face="S", width=1368, stations=1, in_window_um=list(W_DFI_EW),
             out_window_um=list(W_DFI_NS), in_layers=list(EW), out_layers=list(NS), in_order="lsb_low", out_order="lsb_high",
             order="lsb_low"),
        dict(name="ft1", in_face="S", out_face="W", width=1120, stations=1, in_window_um=list(W_HBMRD_NS),
             out_window_um=list(W_HBMRD_EW), in_layers=list(NS), out_layers=list(EW), in_order="lsb_high", out_order="lsb_low",
             order="lsb_low")]
    log.append("svc_2 type: +ft0 DFI W->S, +ft1 hbmrd S->W (anti-ordered L turns: equal per-bit length)")
    b = bus_of(tp, "dfi_i7"); b.update(face="N", window_um=list(W_DFI_NS), layers=list(NS), order="lsb_high")
    b = bus_of(tp, "hbmrd_o7"); b.update(face="N", window_um=list(W_HBMRD_NS), layers=list(NS), order="lsb_high")
    log.append("phy__t1: dfi_i7/hbmrd_o7 W -> N face under svc_2")
    ln = lanes["dfi__svc_0__phy_hbm"]
    p0, p1 = (ports[i] for i in ln["ports"])
    assert p0["src"] == dict(part="svc_0", bus="dfi_o0") and p1["dst"] == dict(part="phy_hbm", bus="dfi_i7")
    ln["ports"] = [mkport("svc_0", "dfi_o0", "svc_2", "ft0_i", p0["width"], "data", "E", EW,
                          [SVC0_O[1] + W_DFI_EW[0], SVC0_O[1] + W_DFI_EW[1]], "lsb_low"),
                   mkport("svc_2", "ft0_o", "phy_hbm", "dfi_i7", p0["width"], "data", "S", NS,
                          [SVC2_O[0] + W_DFI_NS[0], SVC2_O[0] + W_DFI_NS[1]], "lsb_high")]
    ln = lanes["hbmrd__phy_hbm__svc_0"]
    p0, p1 = (ports[i] for i in ln["ports"])
    assert p0["src"] == dict(part="phy_hbm", bus="hbmrd_o7") and p1["dst"] == dict(part="svc_0", bus="hbmrd_i0")
    ln["ports"] = [mkport("phy_hbm", "hbmrd_o7", "svc_2", "ft1_i", p0["width"], "data", "N", NS,
                          [SVC2_O[0] + W_HBMRD_NS[0], SVC2_O[0] + W_HBMRD_NS[1]], "lsb_high"),
                   mkport("svc_2", "ft1_o", "svc_0", "hbmrd_i0", p0["width"], "data", "W", EW,
                          [SVC2_O[1] + W_HBMRD_EW[0], SVC2_O[1] + W_HBMRD_EW[1]], "lsb_low")]
    # ---------------------------------------------------------------- iqf own lanes
    for nm, face, win in (("idx_i0", "E", W_IDXI_E), ("idx_o0", "E", W_IDXO_E), ("flt_o0", "E", W_FLT_E),
                          ("ql_i0", "N", W_QL_N), ("qc_o0", "N", W_QC_N)):
        b = bus_of(t_iqf, nm)
        b.update(face=face, window_um=list(win), layers=list(EW if face == "E" else NS))
    log.append("iqf__t1: idx_i0/idx_o0/flt_o0 N -> E (svc_0 W face); ql_i0/qc_o0 N windows -> s_0S_x00 S gap")
    t49 = T["slice_station__t49"]
    s = slot_of(t49, "ft0"); assert s["in_face"] == "E"; s["in_face"] = "S"; s["in_window_um"] = list(W_QC_N)
    s = slot_of(t49, "ft3"); assert s["out_face"] == "E"; s["out_face"] = "S"; s["out_window_um"] = list(W_QL_N)
    log.append("slice_station__t49: ft0 in E->S (qc), ft3 out E->S (ql)")
    ln = lanes["qc__iqf__s_0N_LP"]
    ids = list(ln["ports"])
    assert ports[ids[0]]["dst"] == dict(part="svc_0", bus="ft1_i") and ports[ids[1]]["dst"] == dict(part="s_0S_x00", bus="ft0_i")
    q0 = ports[ids[0]]
    ln["ports"] = [mkport("iqf", "qc_o0", "s_0S_x00", "ft0_i", q0["width"], q0.get("kind", "data"), "N", NS,
                          [X0 + W_QC_N[0], X0 + W_QC_N[1]], "lsb_low")] + ids[2:]
    ln = lanes["ql__s_0N_LP__iqf"]
    ids = list(ln["ports"])
    assert ports[ids[-2]]["src"] == dict(part="s_0S_x00", bus="ft3_o") and ports[ids[-1]]["dst"] == dict(part="iqf", bus="ql_i0")
    q0 = ports[ids[-1]]
    ln["ports"] = ids[:-2] + [mkport("s_0S_x00", "ft3_o", "iqf", "ql_i0", q0["width"], q0.get("kind", "data"), "S", NS,
                                     [X0 + W_QL_N[0], X0 + W_QL_N[1]], "lsb_low")]
    ln = lanes["idx__s_3S_C__iqf"]
    ids = list(ln["ports"])
    q0 = ports[ids[-1]]
    assert q0["src"] == dict(part="svc_0", bus="ft0_o") and q0["dst"] == dict(part="iqf", bus="idx_i0")
    ln["ports"] = ids[:-1] + [mkport("svc_0", "ft0_o", "iqf", "idx_i0", q0["width"], "data", "W", EW,
                                     [IQF_NEW[1] + W_IDXI_E[0], IQF_NEW[1] + W_IDXI_E[1]], "lsb_low")]
    for lid, bus, win in (("idx__iqf__svc_0", "idx_o0", W_IDXO_E), ("flt__iqf__svc_0", "flt_o0", W_FLT_E)):
        ln = lanes[lid]
        (q0,) = (ports[i] for i in ln["ports"])
        assert q0["src"] == dict(part="iqf", bus=bus)
        ln["ports"] = [mkport("iqf", bus, "svc_0", q0["dst"]["bus"], q0["width"], q0.get("kind", "data"), "E", EW,
                              [IQF_NEW[1] + win[0], IQF_NEW[1] + win[1]], "lsb_low")]
    log.append("qc/ql: iqf N <-> s_0S_x00 S direct (svc_0 ft1/ft2 dropped); idx: svc_0 ft0 W -> iqf E; idx/flt iqf E -> svc_0 W")
    # ---------------------------------------------------------------- renumber the touched lanes' ports
    rename = {}
    old_ids = set()
    new_ports = []
    for lid in TOUCHED:
        ln = lanes[lid]
        out = []
        for k, p in enumerate(ln["ports"]):
            pr = ports[p] if isinstance(p, str) else p
            if isinstance(p, str):
                old_ids.add(p)
            nid = f"{lid}__{k}"
            if isinstance(p, str):
                rename[p] = nid
            pr = dict(pr, id=nid)
            new_ports.append(pr)
            out.append(nid)
        ln["ports"] = out
    old_all = {pid for lid in TOUCHED for pid in [x for x in ports if x.startswith(lid + "__")]}
    keep = [p for p in raw["ports"] if p["id"] not in old_all]
    for ch in raw["die"].get("channels", []):
        assert not set(ch.get("ports", [])) & old_all, ch.get("name")
    raw["ports"] = keep + new_ports
    ids = [p["id"] for p in raw["ports"]]
    assert len(ids) == len(set(ids)), "duplicate port ids"
    # every removed/changed slot bus is used exactly by the touched lanes
    gone = {("svc_0", "ft1_i"), ("svc_0", "ft1_o"), ("svc_0", "ft2_i"), ("svc_0", "ft2_o"),
            ("iqf", "ft0_i"), ("iqf", "ft0_o"), ("iqf", "ft1_i"), ("iqf", "ft1_o")}
    for p in raw["ports"]:
        for side in ("src", "dst"):
            assert (p[side]["part"], p[side]["bus"]) not in gone, (p["id"], side)
    # ---------------------------------------------------------------- PHY io / PG domain / u_phy slot / clock keepout
    io = next(x for x in raw["die"]["io"] if x["name"] == "io_lk_WS3_u_phy")
    newio = [r6(v) for v in delta["geometry"]["io"]["io_lk_WS3_u_phy"]["new"]]
    # the delta's window is the bare PMA pair (2246.4 x 259.2): one 150-um bump row = 14 sites < 26 SerDes signals.
    # PHY macro = PMA pair + its 63.64-um inner guard (2246.4 x 322.84, the delta's band depth) -> 2 rows x 14 = 28
    # sites (= the old WS3 window's 28); the domain keeps the 63.64-um guard on W/E/N around it (lk_WS0 convention)
    newio[3] = r6(newio[1] + 322.84)
    log.append("io_lk_WS3_u_phy depth 259.2 -> 322.84 (PMA pair + inner guard; 1 bump row = 14 < 26 signals otherwise)")
    import die_io as IO
    io["rect_um"] = newio
    io["sites"] = IO.count_sites(newio, io["pitch_um"], io.get("bump_exclude_um", ()))
    io["note"] = (io.get("note", "") + "; DIE-S81-27 WS3 lot replan (fix-only, OWNER 10-29 PMA R90): PMA 129.6 x 2246.4 "
                  "tx/rx pair rotated along the shore, stacked in depth = 2246.4 x 259.2 at the die edge")
    dom = next(x for x in raw["die"]["pg"]["domains"] if x["name"] == "phy_lk_WS3")
    drect = [r6(v) for v in delta["geometry"]["pg_domain_phy_lk_WS3"]["new"]]
    dom["rect_um"] = drect
    dom["bumps"]["rect_um"] = list(newio)
    dom["phy_macro_um"] = list(newio)
    lot = [X0, YS, X0 + WS3_OUT[0], YM]
    dom["core_strip_um"] = [[drect[0], drect[3], lot[2], lot[3]], [drect[2], lot[1], lot[2], drect[3]]]
    dom["core_edge_bumps"] = "relocate"
    dom["note"] = (dom.get("note", "") + "; DIE-S81-27 WS3 lot replan: domain = PMA R90 band + guard inside the 2885.76 x "
                   "1226.88 shore lot (delta_ws3_lot_1029.json); core strip = rest of the lot")
    log.append(f"io_lk_WS3_u_phy -> {newio} sites {io['sites']} (signals {io.get('signals')}); phy_lk_WS3 domain -> {drect}")
    mac_local = [r6(newio[0] - X0), r6(H - (newio[3] - YS)), r6(newio[2] - newio[0]), r6(newio[3] - newio[1])]
    u = next(c for c in t12["contents"] if c["inst"] == "u_phy")
    u["origin_um"] = mac_local[:2]
    u["outline_um"] = mac_local[2:]
    u["note"] = ("SerDes PMA tx/rx pair R90 along the shore (OWNER 10-29), stacked in depth 2246.4 x 259.2 in a 2885.76 x "
                 "1226.88 shore lot (DIE-S81-27 WS3 fix-only lot replan); the rest of the lot holds boundary flops and ft stations")
    t12["clock"]["tap_um"] = list(delta["geometry"]["clock_taps"]["lk_WS3"]["new_type"])
    t12["clock"]["keepouts_um"] = [[0.0, r6(H - (drect[3] - YS)), r6(drect[2] - X0), H]]
    t12["note"] = t12.get("note", "") + "; DIE-S81-27 WS3 shore lot 2885.76 x 1226.88 (PMA R90), coll ft windows re-laid"
    t_iqf["note"] = t_iqf.get("note", "") + "; DIE-S81-27 WS3 lot replan: iqf moved to (8760.96,1330.56), 8 coll ft slots"
    ins = raw.setdefault("reset", {}).setdefault("in_sites", {})
    for tn in ("serdes__t12", "iqf__t1"):
        if tn in ins:
            log.append(f"reset.in_sites[{tn}] {ins.pop(tn)} dropped (outline/position changed: wavefront re-picks it)")
    return rename, old_all


CHANGED_SLOTS = [("lk_WS3", s) for s in ("ft0", "ft1", "ft2", "ft3", "ft4", "ft5")] + \
                [("iqf", f"ft{k}") for k in range(2, 10)] + \
                [("svc_0", "ft0"), ("svc_2", "ft0"), ("svc_2", "ft1"), ("s_0S_x00", "ft0"), ("s_0S_x00", "ft3")]


def slot_lengths(raw):
    from check import zroute, plen
    P = S.Plan(raw)
    out = {}
    for lid in P.lanes:
        for part, slot, a, b in P.lane_crossings(lid):
            if (part, slot) not in CHANGED_SLOTS:
                continue
            s = P.slot(part, slot)
            seg = zroute(P.port_point(a), P.port_point(b), P.die_face(part, s["in_face"]), P.die_face(part, s["out_face"]))
            out[(part, slot)] = (plen(seg), lid)
    missing = set(CHANGED_SLOTS) - set(out)
    assert not missing, missing
    return out, P


def set_stations(raw, log):
    lens, P = slot_lengths(raw)
    smax = min(float(P.budgets.get("ft_station_max_um", S.SIGNAL_REACH_UM)), S.SIGNAL_REACH_UM)
    T = raw["partition_types"]
    parts = {p["name"]: p for p in raw["partitions"]}
    rec = {}
    for (part, slot), (L, lid) in sorted(lens.items()):
        s = slot_of(T[parts[part]["type"]], slot)
        old = s.get("stations")
        k = max(1, math.ceil(L / smax - 1e-9))
        s["stations"] = k
        rec[f"{part}/{slot}"] = dict(lane=lid, route_um=round(L, 2), stations=k, hop_um=round(L / k, 1), before=old)
    log.append(f"stations (R3 ceil(route/{smax:g})): " + ", ".join(f"{k}={v['stations']}({v['route_um']})" for k, v in rec.items()))
    return rec


def site_svc(raw, rec, log):
    """explicit exact-bit station banks for the svc slots (dense hard-core field) with tools/die_plan/ft_corridor.py;
    +1 station only for a slot the corridor cannot site at its R3 count (reported, never silent)."""
    import ft_corridor as FC
    T = raw["partition_types"]
    led = []
    for tn, part, names in (("svc_lo_dsdv_svc_rs_w__t1", "svc_0", ["ft0"]), ("svc_lo_dsdv_svc_rs__t1", "svc_2", ["ft0", "ft1"])):
        for attempt in range(4):
            failed = []
            keep = copy.deepcopy(T[tn]["ft_slots"])
            got = FC.place(raw, [tn], failed=failed)
            if not failed:
                led += got
                break
            T[tn]["ft_slots"][:] = keep
            msg = failed[0]["error"]
            bad = [n for n in names if f"{n}" in msg] or names
            for n in bad:
                s = slot_of(T[tn], n)
                s["stations"] += 1
                rec[f"{part}/{n}"]["stations"] = s["stations"]
                rec[f"{part}/{n}"]["added_for_siting"] = rec[f"{part}/{n}"].get("added_for_siting", 0) + 1
            log.append(f"ft_corridor {tn} attempt {attempt}: {msg[:300]} -> +1 station on {bad}")
        else:
            raise SystemExit(f"ft_corridor could not site {tn}")
    for x in led:
        log.append(f"ft_corridor {x['type']}/{x['slot']}: {x.get('stations')} hops {x.get('hops_um')} len {x.get('len_um')}")
    return led


def update_table(raw, table, variant, rename, old_all, log):
    tab = copy.deepcopy(table)
    tab.pop("collector", None)
    reg = {r["k"]: r for r in tab["regions"]}
    r_ws3 = next(r for r in tab["regions"] if r["parts"] == ["lk_WS3"])
    r_iqf = next(r for r in tab["regions"] if r["parts"] == ["iqf"])
    r_ws3["box_um"] = [X0, YS, r6(X0 + WS3_OUT[0]), YM]
    r_iqf["box_um"] = [X0, YM, r6(X0 + 1442.88), YT]
    if variant == "V2":
        log.append(f"V2: landing region k={r_iqf['k']} (iqf) tag {r_iqf['tag']} -> {r_ws3['tag']}")
        r_iqf["tag"] = r_ws3["tag"]
    else:
        log.append(f"V1: iqf keeps tag {r_iqf['tag']} (tags travel)")
    tag = {}
    for r in tab["regions"]:
        for q in r["parts"]:
            assert q not in tag, q
            tag[q] = r["tag"]
    P = S.Plan(raw)
    lane_of = {pid: lid for lid, ln in P.lanes.items() for pid in ln["ports"]}
    rows = []
    for pid, pr in P.ports.items():
        a, b = pr["src"]["part"], pr["dst"]["part"]
        if a in tag and b in tag and tag[a] != tag[b]:
            rows.append(dict(port=pid, lane=lane_of.get(pid), src=a, dst=b, src_region=tag[a], dst_region=tag[b],
                             width=pr["width"], kind=pr.get("kind", "data"), added_cycles=tab["added_cycles_per_crossing"]))
    old = {r["port"]: r for r in table["ports"]}
    new = {r["port"]: r for r in rows}
    touched_new = {r["port"] for r in rows if r["lane"] in TOUCHED}
    untouched_old = {p for p in old if p not in old_all}
    untouched_new = set(new) - touched_new
    assert untouched_old == untouched_new, ("crossings changed outside the touched lanes",
                                             sorted(untouched_old ^ untouched_new)[:10])
    for p in untouched_new:
        assert old[p] == new[p], p
    order = [r["port"] for r in table["ports"] if r["port"] in untouched_new] + sorted(touched_new)
    assert len(order) == len(set(order)) == len(rows)
    tab["ports"] = [new[p] for p in order]
    tab["crossings"] = len(rows)
    tab["bits"] = sum(r["width"] for r in rows)
    tab["lanes"] = len({r["lane"] for r in rows})
    by = {}
    for r in rows:
        k = "std->std"
        by.setdefault(k, dict(ports=0, bits=0))
        by[k]["ports"] += 1
        by[k]["bits"] += r["width"]
    tab["by_class_pair"] = by
    per_lane = {}
    for lid in TOUCHED:
        per_lane[lid] = dict(before=sum(1 for r in table["ports"] if r["lane"] == lid),
                             after=sum(1 for r in rows if r["lane"] == lid))
    log.append(f"landing table: crossings {table['crossings']} -> {tab['crossings']}; touched-lane crossings {per_lane}")
    return tab, per_lane


def lane_cycles(raw):
    return {lid: v["cycles"] for lid, v in raw["latency"]["lanes"].items()}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--variant", choices=("V1", "V2", "BASE"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--plan", default=str(ROOT / "physical/die_plan/s81/plan_s13r2.json"))
    ap.add_argument("--sidecar", default=str(ROOT / "physical/die_plan/s81/s13/landed_sidecar_s13.json"))
    ap.add_argument("--delta", default=str(ROOT / "physical/die_plan/s81/delta_ws3_lot_1029.json"))
    ap.add_argument("--render")
    ap.add_argument("--title", default="")
    a = ap.parse_args()
    if a.render:
        return render(a.render, a.out, a.title)
    t_start = time.time()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    m = load_mod("recompose_s12", ROOT / "results/die_s81_19_1028/scripts/recompose_s12.py")
    frozen = json.load(open(a.plan))
    side = json.load(open(a.sidecar))
    delta = json.load(open(a.delta))
    raw, clones = m.uncompose(frozen)
    log = [f"uncompose: {len(frozen['partition_types'])} types -> {len(raw['partition_types'])} base ({len(clones)} clones)"]
    tab0 = {k: v for k, v in side.items() if k != "collector"}
    rec, led, per_lane = {}, [], {}
    v = a.variant
    if v == "BASE":
        tab = tab0
    else:
        rename, old_all = apply_geometry(raw, delta, log)
        rec = set_stations(raw, log)
        led = site_svc(raw, rec, log)
        tab, per_lane = update_table(raw, tab0, v, rename, old_all, log)
    raw["note"] = raw.get("note", "") + (
        f"; DIE-S81-27 WS3 fix-only lot replan {v} on a COPY of frozen plan_s13r2 (delta_ws3_lot_1029, compose_ws3_1029.py)"
        if v != "BASE" else "; DIE-S81-27 BASE control: plan_s13r2 un-composed + re-composed unchanged")
    src = out / "plan_source.json"
    src.write_text(json.dumps(raw, indent=1))
    (out / "landed_table.json").write_text(json.dumps(tab, indent=1))
    import clock_landing_plan as CL
    t0 = time.time()
    new, sc = CL.compose(raw, tab, plan_path=str(src), observer_part=m.OBS_PART, observer=dict(m.OBS))
    log.append(f"landing compose {time.time() - t0:.0f} s")
    tag = {"V1": "ws3v1", "V2": "ws3v2", "BASE": "base"}[v]
    plan_p = out / f"plan_s13r2_{tag}.json"
    side_p = out / f"landed_sidecar_s13_{tag}.json"
    plan_p.write_text(json.dumps(new, indent=1))
    side_p.write_text(json.dumps(sc, indent=1))
    r = subprocess.run([sys.executable, str(ROOT / "tools/die_plan/gen.py"), "latency", str(plan_p), "--inplace",
                        "--out", str(out / "lat")], cwd=str(ROOT), capture_output=True, text=True)
    log.append(f"gen.py latency --inplace rc {r.returncode}: {(r.stdout + r.stderr)[-400:]}")
    if r.returncode:
        raise SystemExit("\n".join(log))
    new = json.load(open(plan_p))
    c0, c1 = lane_cycles(frozen), lane_cycles(new)
    changed = {lid: dict(before=c0.get(lid), after=c1.get(lid), d=c1.get(lid, 0) - c0.get(lid, 0))
               for lid in sorted(set(c0) | set(c1)) if c0.get(lid) != c1.get(lid)}
    ins = [k for k in c1 if k.startswith("coll__lk_WS")]
    outs = [k for k in c1 if k.startswith("coll__s_0S_LP__lk_WS")]
    col = sc["collector"]
    res = dict(variant=v, log=log, stations=rec, ft_corridor=led, landing_crossings_per_touched_lane=per_lane,
               touched_lanes={lid: dict(before=c0[lid], after=c1[lid], d=c1[lid] - c0[lid],
                                        landing=new["latency"]["lanes"][lid].get("clock_landing"),
                                        stations=new["latency"]["lanes"][lid].get("stations")) for lid in TOUCHED},
               lane_cycle_changes=changed, lane_sum=dict(before=sum(c0.values()), after=sum(c1.values())),
               coll_max=dict(in_before=max(c0[k] for k in ins), in_after=max(c1[k] for k in ins),
                             out_before=max(c0[k] for k in outs), out_after=max(c1[k] for k in outs)),
               landing=dict(placement_failures=len(col["placement_failures"]), max_monitor_hop_um=col["max_die_hop_um"],
                            boot_ready_cycles=col["boot_budget"]["ready_at_glue_max_cycles"]),
               inputs=dict(plan=dict(path=a.plan, sha256=sha(a.plan)), sidecar=dict(path=a.sidecar, sha256=sha(a.sidecar)),
                           delta=dict(path=a.delta, sha256=sha(a.delta))),
               outputs=dict(plan=str(plan_p), plan_sha256=sha(plan_p), sidecar=str(side_p)),
               secs=round(time.time() - t_start))
    (out / f"compose_{tag}_receipt.json").write_text(json.dumps(res, indent=1))
    print(json.dumps({k: res[k] for k in ("variant", "touched_lanes", "coll_max", "lane_sum", "landing", "secs")}, indent=1))
    print(f"{len(changed)} lanes changed cycles")


def render(plan_path, png, title):
    """zoomed view of the composed region: partitions, PMA/PG domain, macros, touched-lane routes + station regs."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    import check as C
    raw = json.load(open(plan_path))
    P = S.Plan(raw)
    box = (5700, 0, 13300, 3900)
    fig, ax = plt.subplots(figsize=(19, 10))
    col = {"lk_WS3": "#f4d03f", "iqf": "#85c1e9", "svc_0": "#d7bde2", "svc_2": "#d5f5e3", "phy_hbm": "#f5b7b1",
           "s_0S_x00": "#fad7a0", "lk_WS0": "#fcf3cf"}
    for n in P.parts:
        x0, y0, x1, y1 = P.rect(n)
        if x1 < box[0] or x0 > box[2] or y1 < box[1] or y0 > box[3]:
            continue
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc=col.get(n, "#eeeeee"), ec="k", lw=1.2, zorder=1))
        ax.text(max(x0, box[0]) + 20, min(y1, box[3]) - 70, f"{n}\n{P.parts[n]['type']} {P.orient(n)}", fontsize=7, zorder=5)
        for mb in S.placed_macro_boxes(P.ptype(n)).values():
            a_ = P.to_die(n, (mb[0], mb[1]))
            b_ = P.to_die(n, (mb[2], mb[3]))
            ax.add_patch(Rectangle((min(a_[0], b_[0]), min(a_[1], b_[1])), abs(b_[0] - a_[0]), abs(b_[1] - a_[1]),
                                   fc="#999999", ec="none", alpha=.35, zorder=2))
    for io in raw["die"]["io"]:
        if io.get("part") in ("lk_WS3", "lk_WS0", "phy_hbm"):
            r = io["rect_um"]
            ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fc="#2e86c1", ec="#1b4f72", alpha=.5, zorder=3))
            ax.text(r[0] + 10, r[1] + 10, f"{io['name']} sites {io['sites']}/{io.get('signals')}", fontsize=7, color="w", zorder=6)
    for d in raw["die"]["pg"]["domains"]:
        if d["name"] in ("phy_lk_WS3", "phy_lk_WS0"):
            r = d["rect_um"]
            ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fc="none", ec="#c0392b", lw=1.5, ls="--", zorder=4))
    cmap = plt.get_cmap("tab20")
    for i, lid in enumerate(TOUCHED):
        if lid not in P.lanes:
            continue
        pts, regs, xs = C.lane_geometry(P, lid)
        xy = [(x, y) for x, y in pts]
        c = cmap(i % 20)
        ax.plot([p[0] for p in xy], [p[1] for p in xy], "-", color=c, lw=1.6, zorder=7, label=lid)
        ax.plot([p[0] for p in regs], [p[1] for p in regs], "o", color=c, ms=3, zorder=8)
        for pid in P.lanes[lid]["ports"]:
            pr = P.ports[pid]
            if pr["face"] in "NS":
                yv = P.rect(P.face_part(pid))[3 if pr["face"] == "N" else 1]
                ax.plot(pr["window_um"], [yv, yv], "-", color=c, lw=5, alpha=.6, zorder=6)
            else:
                xv = P.rect(P.face_part(pid))[2 if pr["face"] == "E" else 0]
                ax.plot([xv, xv], pr["window_um"], "-", color=c, lw=5, alpha=.6, zorder=6)
    ax.set_xlim(box[0], box[2])
    ax.set_ylim(box[1], box[3])
    ax.set_aspect("equal")
    ax.legend(fontsize=6, loc="upper right", ncol=2)
    ax.set_title(title or plan_path, fontsize=9)
    fig.tight_layout()
    fig.savefig(png, dpi=110)
    print(png)


if __name__ == "__main__":
    main()
