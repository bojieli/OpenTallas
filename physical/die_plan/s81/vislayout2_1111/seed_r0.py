#!/usr/bin/env python3
"""seed_r0.py PLAN TYPE OUT_SEED.json [VARIANT] : VISLAYOUT2-S81 COL-H9R0 hand form.
Defect: u_cf (crs4 fifo, 280.8 x 69.12) sits R0 at the E edge with its xl0-3 lanes (1104 b, S face) facing AWAY from
their type port (E edge y 1100.7) and its x2 broadcast (605 b to the 8 e ROM S faces) facing AWAY from the ROMs: the lanes
wrap cf's E end in a 30 um ring (ring V p99 1.70-1.82).  bs1 sits under the c1 row (y 43) and bs3 290 um W of e3.u_e pins.
Form v1: cf MX in place (xl lanes N toward the port, x2 S toward the ROM aprons); bs1/bs3 under the e1/e3 junction
(centre between the two xs_q pin groups), bs1 lifted into the e1 apron (y 181.44, as bs0).
v2 = v1 + cf lifted onto the n5/n6 level with n5/n6 moved below it (shorter lane climb)."""
import json, sys
P = json.load(open(sys.argv[1])); tn = sys.argv[2]; out = sys.argv[3]; var = sys.argv[4] if len(sys.argv) > 4 else "v1"
t = P["partition_types"][tn]; seed = {}
H = {h["inst"].split(".", 1)[1]: h for h in t["hard_cores"]}
L = lambda v: round(round(v / 8.64) * 8.64, 3)
def put(n, x, y, o=None):
    h = H[n]; seed[h["inst"]] = {"origin_um": [round(x, 3), round(y, 3)], "orient": o or h.get("orient", "R0")}
cf = H["u_cf"]["origin_um"]
e1 = H["u_e1.u_w"]["origin_um"][0]; e3 = H["u_e3.u_w"]["origin_um"][0]
if var.startswith("x"):            # single-move probes
    if var == "xmx": put("u_cf", cf[0], cf[1], "MX")
    if var == "x0": put("u_cf", cf[0], cf[1])
    if var == "xup": put("u_cf", cf[0], 665.28)
    if var == "xupmx": put("u_cf", cf[0], 665.28, "MX")
    if var == "xn":
        put("u_n9", 933.12, 838.08); put("u_n10", 984.96, 838.08); put("u_n11", 1036.8, 838.08); put("u_rg1", 1088.64, 838.08)
    json.dump({tn: seed}, open(out, "w"), indent=1); print(tn, var, len(seed)); sys.exit(0)
if var not in ("v5a", "v5b", "v2b", "v2c", "v3", "v3b", "v4", "v4b", "v4c", "v4d", "v4e", "v4f", "v4g"):
    put("u_bs1", L(e1 + 276.48), 181.44)
if var not in ("v5a", "v5b", "v2a", "v2b", "v2c", "v3", "v3b", "v4", "v4b", "v4c", "v4d", "v4e", "v4f", "v4g"):
    put("u_bs3", L(e3 + 276.48), 570.24)
if var == "v2c":
    put("u_bs1", L(e1 + 276.48), 181.44)
if var == "v1":
    put("u_cf", cf[0], cf[1], "MX")
else:
    # v2: cf MX one row up: xl face (top) at y 734.4 meets the E port windows (740-980 / 981-1221); rd -> ret_o0 <= 810 um
    import os
    put("u_cf", cf[0], float(os.environ.get("CFY", "665.28")), os.environ.get("CFO", "R0"))   # R0: MX costs station 7 (cf.rs relay) a register
    # clear the region above cf (lanes + xo_i0 / ft0_i landing ring storage): n-nodes into the lower E strip gaps and the
    # free band between e3's top (826.2) and the bf block (950.4)
    put("u_n5", 1252.8, 397.44); put("u_n6", 1382.4, 432.0); put("u_n7", 1382.4, 527.04); put("u_n8", 1166.4, 388.8)
    put("u_n9", 933.12, 838.08); put("u_n10", 984.96, 838.08); put("u_n11", 1036.8, 838.08); put("u_rg1", 1088.64, 838.08)
if var in ("v5a", "v5b"):
    # v5 = v4f on the 8.64 lattice (rows -34.56) with an ft-aware top-row shift: types carrying the ft0 E->W pass-through
    # (p1-p3) have fixed ft0 station sites in a column at x 1142.64 just E of e4e.u_ha, so only u_e4 moves (+25.92)
    for n in [n for n in H if n.startswith(("u_c2_", "u_c3_"))] + ["u_s2", "u_s3"]:
        o = H[n]["origin_um"]; put(n, o[0], o[1] - 34.56)
    yb = 518.4 if var == "v5a" else 527.04
    for n in ("u_bs2", "u_bs3"):
        put(n, H[n]["origin_um"][0], yb)
    has_ft = any((f.get("width") or 0) >= 1000 for f in t.get("ft_slots") or [])
    grp = ("u_e4",) if has_ft else ("u_e4", "u_e4e.u_view.u_c", "u_e4e.u_view.u_ha", "u_e4e.u_view.u_hb")
    for n in grp:
        o = H[n]["origin_um"]; put(n, o[0] + (25.92 if has_ft else 43.2), o[1])
    json.dump({tn: seed}, open(out, "w"), indent=1)
    print(tn, var, "ft" if has_ft else "noft", len(seed)); sys.exit(0)
if var in ("v4f", "v4g"):
    yb = 518.4 if var == "v4f" else 527.04       # banks lower: the ROM S-face <-> bank bus spreads over a taller apron
    for n in ("u_bs2", "u_bs3"):
        put(n, H[n]["origin_um"][0], yb)
    var = "v4d"
if var == "v4e":
    put("u_bs3", L(e3 + 276.48), 544.32)       # under the e3 junction, at the facing-face clearance (34.56) below e3
    var = "v4d"
if var in ("v4", "v4b", "v4c", "v4d"):
    # v4: open the bank strip under the e2/e3 S faces: c2/c3 rows + s2/s3 down into the 46 um gap above the e0/e1 N faces
    dy = {"v4": 17.28, "v4b": 25.92, "v4c": 34.56, "v4d": 38.88}[var]
    for n in [n for n in H if n.startswith(("u_c2_", "u_c3_"))] + ["u_s2", "u_s3"]:
        o = H[n]["origin_um"]; put(n, o[0], o[1] - dy)
    # the bank strip stays where it is (the legaliser otherwise rides bs2/bs3/t1 down with the rows)
    var = "v3"
if var in ("v3", "v3b"):
    # v3: widen the port-side column of the top bf row (e4w.u_c | u_e4, 25 um) to 68 um: u_e4 + the e4e group +43.2 E
    # (t2/t2p -> frame_int_o0 549+536 b and t2/t2p -> e4 N face 545 b cross the row there; real GRT HOT at 572-624,1151-1180)
    dx = 43.2 if var == "v3" else 86.4
    for n in ("u_e4", "u_e4e.u_view.u_c", "u_e4e.u_view.u_ha", "u_e4e.u_view.u_hb"):
        o = H[n]["origin_um"]; put(n, o[0] + dx, o[1])
json.dump({tn: seed}, open(out, "w"), indent=1)
print(tn, var, {k.split(".")[-1]: v["origin_um"] + [v["orient"]] for k, v in seed.items()})
