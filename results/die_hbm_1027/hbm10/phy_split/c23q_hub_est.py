"""DIE-HBM-10 C23q hub ESTIMATE (plan time, no build): what does the per-PC PHY bus regroup cost INSIDE the hubs?
Finding while building C23q: the hub->PHY buses are NOT PC-contiguous today (B2o re-route bundled by hub geometry:
e.g. NW L8_o feeds u_ctl_Q_p00/p03/p08-p11/p13/p15), so a PHY cut needs every (ctl leaf, pin group) station whose bus
changes face re-routed inside the hub.  This prices it with the SAME router the hub stations were made with
(hub_repack.route_station on hub_repack.Raster of the hub hard cores, reach 360 um, as hbm_r9_delta.realise).
New buses (by PHY PC, as-built PC p = ctl_NW_p{p}, ctl_NE_p{p} = PC 16+p):
  W/E mcb path (hub type N face, spu0 block x 965.18..2059.0): data in L8_o, ctl in L63w_o, rdata L21_i, rvalid L114w_i
  centre column (hub type E face from y 1957.59): data in L9_o, ctl in L63_o, rdata L22_i; rvalid L114_i stays (b112, N face)
usage: c23q_hub_est.py PLAN MAINSNAP_TOOLS OUT_JSON"""
import json, sys, collections, math
plan, tools, outp = sys.argv[1:4]
sys.path.insert(0, tools + "/die_plan"); sys.path.insert(0, tools)
import hub_repack as HR
P = json.load(open(plan)); T = P["partition_types"]
UMB = 439.248 / 2456          # um per bit at the plan's achieved PHY window density
DATA = {"col_data", "col_strb", "row_row"}; RD = {"dram_rdata"}; RV = {"dram_rvalid"}
BUSES = ("L8_o", "L9_o", "L21_i", "L22_i", "L63_o", "L114_i")
def kind(g):
    return "rdata" if g in RD else "rvalid" if g in RV else "data" if g in DATA else "ctl"
NEWBUS = {"W": {"data": "L8_o", "ctl": "L63w_o", "rdata": "L21_i", "rvalid": "L114w_i"},
          "C": {"data": "L9_o", "ctl": "L63_o", "rdata": "L22_i", "rvalid": "L114_i"}}
out = {}
for tn, wpcs in (("q_hub_nw", set(range(0, 10))), ("q_hub_ne", set(range(6, 16)))):
    t = T[tn]; W, H = t["outline_um"]
    R = HR.Raster(W, H, [HR._core_rect(h) for h in t["hard_cores"]])
    st = []
    for i, s in enumerate(t["internal_stations"]):
        b = next((b for b in BUSES if s.get("launch") == "face bus " + b or s.get("capture") == "face bus " + b), None)
        if b is None: continue
        core_end = s["capture"] if s["launch"].startswith("face bus") else s["launch"]
        inst, grp = core_end.split(".", 1); p = int(inst.rsplit("_p", 1)[1])
        side = "W" if p in wpcs else "C"
        nb = NEWBUS[side][kind(grp)]
        st.append(dict(i=i, bus=b, new=nb, inst=inst, p=p, grp=grp, bits=s["bits"], regs=len(s["regs_um"]),
                       face_first=s["launch"].startswith("face bus"),
                       core_pt=s["to_um"] if s["launch"].startswith("face bus") else s["from_um"],
                       face_pt=s["from_um"] if s["launch"].startswith("face bus") else s["to_um"]))
    # new bus widths and per-(bus, p) bit ranges in PC order
    width = collections.Counter(); rng = {}
    for x in sorted(st, key=lambda x: (x["new"], x["p"], x["grp"])):
        rng[(x["new"], x["i"])] = (width[x["new"]], width[x["new"]] + x["bits"]); width[x["new"]] += x["bits"]
    # windows: N face block from 965.18 (L8, L21, L63w, L114w), E face from 1957.59 (L9, L63, L22); L114_i keeps b112 pin
    win = {}; x0 = 965.18
    for b in ("L8_o", "L21_i", "L63w_o", "L114w_i"):
        L = max(8.64, width[b] * UMB); win[b] = ("N", x0, x0 + L); x0 += L + 0.48
    y0 = 1957.59
    for b in ("L9_o", "L63_o", "L22_i"):
        L = max(8.64, width[b] * UMB); win[b] = ("E", y0, y0 + L); y0 += L + 0.48
    res = []; moved = 0; up = collections.Counter(); fail = 0
    for x in st:
        if x["new"] == "L114_i":
            fp = x["face_pt"]
        else:
            f, a, c = win[x["new"]]; lo, hi = rng[(x["new"], x["i"])]; m = a + (lo + hi) / 2 * UMB
            fp = [m, H] if f == "N" else [W, m]
        same = x["bus"] == x["new"] or (abs(fp[0] - x["face_pt"][0]) < 30 and abs(fp[1] - x["face_pt"][1]) < 30)
        a, b = (fp, x["core_pt"]) if x["face_first"] else (x["core_pt"], fp)
        r = HR.route_station(R, tuple(a), tuple(b), x["regs"], 360.0)
        nreg = len(r["regs"]) if r else None
        if r is None: fail += 1
        if x["bus"] != x["new"]: moved += 1
        d = (nreg - x["regs"]) if nreg is not None else None
        if d is not None: up[d] += 1
        res.append(dict({k: x[k] for k in ("bus", "new", "inst", "grp", "bits", "regs")}, new_regs=nreg,
                        new_len_um=r["length_um"] if r else None))
    per_pc = collections.defaultdict(lambda: [0, 0])
    for r_ in res:
        if r_["new_regs"] is None: continue
        k = (r_["inst"], kind(r_["grp"]) in ("rdata", "rvalid"))
        per_pc[k][0] = max(per_pc[k][0], r_["regs"]); per_pc[k][1] = max(per_pc[k][1], r_["new_regs"])
    out[tn] = dict(stations=len(st), bus_changed=moved, route_fail=fail, reg_delta_hist=dict(sorted(up.items())),
                   new_widths=dict(width), windows=win,
                   max_regs_old=max(x["regs"] for x in st), max_regs_new=max((r_["new_regs"] or 0) for r_ in res),
                   per_pc_regs={f"{k[0]}{'.ret' if k[1] else '.req'}": v for k, v in sorted(per_pc.items())},
                   stations_detail=res)
    print(tn, {k: v for k, v in out[tn].items() if k not in ("stations_detail", "per_pc_regs")})
    print("  per PC max regs old->new:", {k: v for k, v in out[tn]["per_pc_regs"].items()})
json.dump(out, open(outp, "w"), indent=1)
