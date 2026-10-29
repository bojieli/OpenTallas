#!/usr/bin/env python3
"""DIE-S81-26 WS3 fix-only lot replan on plan_s13r2 (estimate + candidate delta, NOT a composed plan).
Geometry (both variants): lk_WS3 serdes__t12 1442.88x2453.76 @ (8760.96,103.68) -> 2885.76x1226.88 shore lot @ same origin
(takes iqf's shore slot); iqf 1442.88x1226.88 @ (10203.84,103.68) -> (8760.96,1330.56) (old WS3 upper half).
V1: landing-region tags travel with partitions (iqf stays hard_phy_hbm).  V2: iqf retagged std_bg_25_0 (the tag of the
footprint it moves into, = lk_WS0/lk_WS3), so no new landed crossing.
Station counts use tools/die_plan/check.py zroute/plen + the R3 rule (route / stations <= 405 um)."""
import json, math, sys, itertools
sys.path.insert(0, sys.argv[1] + "/tools/die_plan")
from check import zroute, plen
PLAN = sys.argv[1] + "/physical/die_plan/s81/plan_s13r2.json"
SIDE = sys.argv[1] + "/physical/die_plan/s81/s13/landed_sidecar_s13.json"
OUT = sys.argv[2]
R = 405.0
p = json.load(open(PLAN)); side = json.load(open(SIDE))
T = p["partition_types"]; PORT = {x["id"]: x for x in p["ports"]}; LN = {x["id"]: x for x in p["lanes"]}
LAT = p["latency"]["lanes"]
tag = {}
for r in side["regions"]:
    for q in r["parts"]: tag[q] = r["tag"]
def st(L): return max(1, math.ceil(L / R - 1e-9))
def c(w): return (w[0] + w[1]) / 2
X0, YS, YM, YT = 8760.96, 103.68, 1330.56, 2557.44     # WS3 W face x, shore, WS3/iqf seam, iqf/s_0S_x00 seam
win = lambda pid: PORT[pid]["window_um"]
# ---- coll lanes: (lane, dir, WS0-side port, s00-side port)
coll = [("coll__lk_WS0__s_0S_LP", "in", "coll__lk_WS0__s_0S_LP__0", "coll__lk_WS0__s_0S_LP__1", "ft4"),
        ("coll__lk_WS1__s_0S_LP", "in", "coll__lk_WS1__s_0S_LP__1", "coll__lk_WS1__s_0S_LP__2", "ft3"),
        ("coll__lk_WS2__s_0S_LP", "in", "coll__lk_WS2__s_0S_LP__2", "coll__lk_WS2__s_0S_LP__3", "ft5"),
        ("coll__s_0S_LP__lk_WS0", "out", "coll__s_0S_LP__lk_WS0__7", "coll__s_0S_LP__lk_WS0__6", "ft0"),
        ("coll__s_0S_LP__lk_WS1", "out", "coll__s_0S_LP__lk_WS1__7", "coll__s_0S_LP__lk_WS1__6", "ft1"),
        ("coll__s_0S_LP__lk_WS2", "out", "coll__s_0S_LP__lk_WS2__7", "coll__s_0S_LP__lk_WS2__6", "ft2")]
own = [("coll__lk_WS3__s_0S_LP", "coll__lk_WS3__s_0S_LP__0", "coll_o0"), ("coll__s_0S_LP__lk_WS3", "coll__s_0S_LP__lk_WS3__6", "coll_i0")]
old_slot = {s["name"]: s for s in T["serdes__t12"]["ft_slots"]}
rows, used = [], []
def free(x1, w):
    return all(x1 + w / 2 + 2.0 <= a or x1 - w / 2 - 2.0 >= b for a, b in used) and x1 - w / 2 >= X0 + 6 and x1 + w / 2 <= 10203.84 - 6
# own lanes first: boundary flop straight under the fixed s_0S_x00 window
for lid, pid, bus in own:
    w = win(pid); x1 = c(w); used.append((w[0], w[1]))
    L2 = 1226.88; k2 = st(L2)
    rows.append(dict(lane=lid, kind="ws3_own", ws3_bus=bus, ws3_N_window=[round(w[0], 3), round(w[1], 3)], iqf_slot_len=L2, iqf_st=k2,
                     ws3_st=0, old_st=0, d_st=k2))
for lid, d, p0, p1, slot in coll:
    yin = c(win(p0)); xs = c(win(p1)); wdt = win(p1)[1] - win(p1)[0]
    best = None
    for x1 in [X0 + 6 + wdt / 2 + 8.64 * i for i in range(170)]:
        if not free(x1, wdt): continue
        a = (X0, yin); b = (x1, YM)
        L1 = plen(zroute(a, b, "W", "N")); L2 = plen(zroute((x1, YM), (xs, YT), "S", "N"))
        key = (st(L1) + st(L2), max(L1 / st(L1), L2 / st(L2)))
        if best is None or key < best[0]: best = (key, x1, L1, L2)
    (_, _), x1, L1, L2 = best[0], best[1], best[2], best[3]
    used.append((x1 - wdt / 2, x1 + wdt / 2))
    old = int(old_slot[slot]["stations"])
    rows.append(dict(lane=lid, kind="through", ws3_slot=slot, ws3_in_y=round(yin, 2), seam_x=round(x1, 2), s00_x=round(xs, 2),
                     ws3_len=round(L1, 1), ws3_st=st(L1), iqf_len=round(L2, 1), iqf_st=st(L2), old_st=old,
                     d_st=st(L1) + st(L2) - old, worst_hop=round(max(L1 / st(L1), L2 / st(L2)), 1)))
# ---- DFI / hbmrd svc_0 <-> phy_hbm via svc_2 (W face local y >= 280 free, S face local x >= 549 free); svc_2 origin
SX, SY = 11646.72, 1330.56
def svc2(wy, wx, inface):
    a = (SX, SY + c(wy)); b = (SX + c(wx), SY)
    L = plen(zroute(a, b, "W", "S")); return L, st(L)
cand = []
for o in range(0, 60, 1):
    # hbmrd inner (243 um windows), dfi outer (297 um windows); 1.2-um gaps; pins 4.6/um <= 6
    hy = (280 + o * 0, 280 + 243.4); hx = (549.3, 549.3 + 243.4)
    dy = (hy[1] + 1.2, hy[1] + 1.2 + 297.4); dx = (hx[1] + 1.2, hx[1] + 1.2 + 297.4)
    cand.append((svc2(hy, hx, "W"), svc2(dy, dx, "W"), hy, hx, dy, dx)); break
(hL, hk), (dL, dk), hy, hx, dy, dx = cand[0]
oldd, oldh = LAT["dfi__svc_0__phy_hbm"], LAT["hbmrd__phy_hbm__svc_0"]
dfi = [dict(lane="dfi__svc_0__phy_hbm", svc0_E_window_local=[round(v, 1) for v in dy], svc2_ft="W->S", svc2_W_local=[round(v, 1) for v in dy],
            svc2_S_local=[round(v, 1) for v in dx], phy_hbm_N_local=[round(v, 1) for v in dx], len=round(dL, 1), st=dk, old_st=oldd["stations"],
            d_cyc=dk - oldd["stations"], worst_hop=round(dL / dk, 1)),
       dict(lane="hbmrd__phy_hbm__svc_0", svc0_E_window_local=[round(v, 1) for v in hy], svc2_ft="S->W", svc2_W_local=[round(v, 1) for v in hy],
            svc2_S_local=[round(v, 1) for v in hx], phy_hbm_N_local=[round(v, 1) for v in hx], len=round(hL, 1), st=hk, old_st=oldh["stations"],
            d_cyc=hk - oldh["stations"], worst_hop=round(hL / hk, 1))]
# ---- iqf own lanes at new spot: qc/ql direct to s_0S_x00 (skip svc_0 ft1/ft2), idx from svc_0 ft0 N->W, idx/flt E face
s0 = {s["name"]: s for s in T["svc_lo_dsdv_svc_rs_w__t1"]["ft_slots"]}
ft0n = c(s0["ft0"]["in_window_um"]); Lidx = plen(zroute((10203.84 + ft0n, 3784.32), (10203.84, YM + 655.0), "N", "W"))
iqf = [dict(lane="qc__iqf__s_0N_LP", change="iqf N face -> s_0S_x00 S face direct (drops svc_0 ft1)", d_cyc=-int(s0["ft1"]["stations"])),
       dict(lane="ql__s_0N_LP__iqf", change="s_0S_x00 S face -> iqf N face direct (drops svc_0 ft2)", d_cyc=-int(s0["ft2"]["stations"])),
       dict(lane="idx__s_3S_C__iqf", change="svc_0 ft0 N->S becomes N->W (exit W face local y ~600-710)", len=round(Lidx, 1), st=st(Lidx),
            old_st=int(s0["ft0"]["stations"]), d_cyc=st(Lidx) - int(s0["ft0"]["stations"]), worst_hop=round(Lidx / st(Lidx), 1)),
       dict(lane="idx__iqf__svc_0", change="iqf E face <-> svc_0 W face (was iqf N / svc_0 S)", d_cyc=0),
       dict(lane="flt__iqf__svc_0", change="iqf E face <-> svc_0 W face", d_cyc=0)]
# ---- landing (+3 per landed crossing) under V1 / V2 tags
def land(chain, tg): return 3 * sum(tg[a] != tg[b] for a, b in zip(chain, chain[1:]))
t1 = dict(tag); t2 = dict(tag); t2["iqf"] = tag["lk_WS3"]
chains = {"coll_in_through": (["lk_WS0", "lk_WS3", "s_0S_x00"], ["lk_WS0", "lk_WS3", "iqf", "s_0S_x00"]),
          "coll_ws3_own": (["lk_WS3", "s_0S_x00"], ["lk_WS3", "iqf", "s_0S_x00"]),
          "qc_ql": (["iqf", "svc_0", "s_0S_x00"], ["iqf", "s_0S_x00"]),
          "dfi_hbmrd": (["svc_0", "iqf", "phy_hbm"], ["svc_0", "svc_2", "phy_hbm"]),
          "idx": (["svc_0", "iqf"], ["svc_0", "iqf"])}
landing = {v: {k: land(b, t) - land(a, tag) for k, (a, b) in chains.items()} for v, t in (("V1", t1), ("V2", t2))}
def total(v):
    out = {}
    for r in rows:
        grp = "coll_ws3_own" if r["kind"] == "ws3_own" else "coll_in_through"
        old = LAT[r["lane"]]["cycles"]; out[r["lane"]] = (old, old + r["d_st"] + landing[v][grp])
    for r in dfi: out[r["lane"]] = (LAT[r["lane"]]["cycles"], LAT[r["lane"]]["cycles"] + r["d_cyc"] + landing[v]["dfi_hbmrd"])
    for r in iqf:
        g = "qc_ql" if r["lane"][:2] in ("qc", "ql") else "idx"
        out[r["lane"]] = (LAT[r["lane"]]["cycles"], LAT[r["lane"]]["cycles"] + r["d_cyc"] + landing[v][g])
    ins = [k for k in out if k.startswith("coll__lk_WS")]; outs = [k for k in out if k.startswith("coll__s_0S_LP__lk_WS")]
    crit = dict(coll_in_max=(max(out[k][0] for k in ins), max(out[k][1] for k in ins)),
                coll_out_max=(max(out[k][0] for k in outs), max(out[k][1] for k in outs)))
    return out, crit
res = dict(schema="opentallas.die_plan_delta_candidate.v0", base="physical/die_plan/s81/plan_s13r2.json@origin/main c6e14b798d4",
           status="CANDIDATE ESTIMATE - not composed, not G0-checked; frozen plan untouched",
           geometry=dict(
               partitions=[dict(name="lk_WS3", type="serdes__t12", old=dict(origin=[8760.96, 103.68], outline=[1442.88, 2453.76]),
                                new=dict(origin=[8760.96, 103.68], outline=[2885.76, 1226.88], orient="MX")),
                           dict(name="iqf", type="iqf__t1", old=dict(origin=[10203.84, 103.68], outline=[1442.88, 1226.88]),
                                new=dict(origin=[8760.96, 1330.56], outline=[1442.88, 1226.88], orient="R0"))],
               io=dict(io_lk_WS3_u_phy=dict(old=[9841.012, 103.68, 10203.84, 2343.8],
                                           new=[8760.96 + 63.64, 103.68, 8760.96 + 63.64 + 2246.4, 103.68 + 259.2],
                                           note="PMA tx+rx 2246.4 x 129.6 each, R90 along the shore, stacked in depth; guard 63.64 -> band 2373.68 x 322.84")),
               pg_domain_phy_lk_WS3=dict(old=[9777.372, 103.68, 10203.84, 2407.44], new=[8760.96, 103.68, 8760.96 + 2437.32, 103.68 + 322.84 + 63.64]),
               types_touched=["serdes__t12 (outline, 6 ft slots + 2 buses re-laid)", "iqf__t1 (8 new S->N/N->S coll ft slots; idx/flt/qc/ql windows re-faced)",
                              "svc_lo_dsdv_svc_rs_w__t1 (svc_0: dfi_o0/hbmrd_i0 S->E, ft0 out S->W, ft1/ft2 removed)",
                              "svc_lo_dsdv_svc_rs__t1 (svc_2: +2 ft slots W<->S for svc_0 DFI/hbmrd)",
                              "phy__t1 (dfi_i7/hbmrd_o7 W -> N face under svc_2)", "slice_station__t49 (s_0S_x00: +qc/ql windows on S face)"],
               clock_taps=dict(lk_WS3=dict(old_die=[8760.96 + 725.76, 103.68 + 2453.76 - 1226.88], new_type=[1442.88, 613.44]),
                               iqf=dict(old_die=[10929.6, 716.64], new_die=[9486.72, 1944.0]))),
           coll_slots=rows, dfi_via_svc2=dfi, iqf_lanes=iqf, landing_delta=landing,
           region_tags=dict(V1=dict(iqf=tag["iqf"]), V2=dict(iqf=tag["lk_WS3"]), lk_WS3=tag["lk_WS3"], s_0S_x00=tag["s_0S_x00"],
                            svc_0=tag["svc_0"], svc_2=tag["svc_2"], phy_hbm=tag["phy_hbm"]))
for v in ("V1", "V2"):
    out, crit = total(v); res[v] = dict(lanes={k: dict(old=a, new=b, d=b - a) for k, (a, b) in out.items()}, critical=crit)
json.dump(res, open(OUT, "w"), indent=1)
print(json.dumps(dict(rows=rows, dfi=dfi, iqf=iqf, landing=landing), indent=0)[:6000])
for v in ("V1", "V2"): print(v, json.dumps(res[v]["critical"]), {k: x["d"] for k, x in res[v]["lanes"].items()})
