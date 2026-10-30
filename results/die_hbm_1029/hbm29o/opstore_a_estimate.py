#!/usr/bin/env python3
"""DIE-HBM-29-O: opstore_a fit estimate in q_b113 (ESTIMATE ONLY, no plan build).

V1 = q_b113 repack (partition outline fixed): K's 760.32x483.84 opstore_a (4x8 grid) + ctl shifted west.
V2 = opstore_a split along its two operand groups into 2 hard cores of 16 macros (2 col x 8 row each).
Reads the d28c plan of record, DIE-HBM-28-K's delta and the opstore_a canonical pin file; writes
opstore_a_estimate.json + opstore_a_estimate.png.  usage: opstore_a_estimate.py PLAN_DIR K_DELTA PINS OUT_DIR
"""
import collections, json, os, re, sys

PLAN, KDELTA, PINS, OUT = sys.argv[1:5]
d = json.load(open(os.path.join(PLAN, "die_plan.json")))
T = d["partition_types"]["q_b113"]
W, H = T["outline_um"]
MW, MH = 172.824, 41.064           # ot_sram_1r1w_256x256_m2_r2c2 (K static script, LEF-asserted)
GAP = 17.28                         # core-to-core gap used in d28c (lane14->lane15, lane15->opstore_a)
LAT = 8.64

cores = {h["inst"].replace("u_sfucore_Q_", ""): [h["origin_um"][0], h["origin_um"][1],
         h["origin_um"][0] + h["outline_um"][0], h["origin_um"][1] + h["outline_um"][1]] for h in T["hard_cores"]}
bands = []
for b in T["die_ft_bands"]:
    lo, hi = b["span_um"]
    bands.append(dict(dir=b["dir"], layers=b["layers"],
                      rect=[0, lo, W, hi] if b["dir"] == "EW" else [lo, 0, hi, H]))


def area(r): return max(0.0, r[2] - r[0]) * max(0.0, r[3] - r[1])


def inter(a, b): return [max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])]


def gap(a, b):
    dx = max(b[0] - a[2], a[0] - b[2], 0); dy = max(b[1] - a[3], a[1] - b[3], 0)
    return max(dx, dy) if (dx == 0 or dy == 0) else (dx * dx + dy * dy) ** .5


def check(name, cs):
    res = dict(cores={k: [round(v, 3) for v in r] for k, r in cs.items()}, errors=[])
    for k, r in cs.items():
        if r[0] < 0 or r[1] < 0 or r[2] > W or r[3] > H:
            res["errors"].append(f"{k} outside partition")
        for b in bands:
            ov = area(inter(r, b["rect"]))
            if ov > 0:
                i = inter(r, b["rect"])
                res.setdefault("band_overlap", []).append(dict(core=k, band=b["dir"], layers=b["layers"],
                    rect=[round(v, 3) for v in i], area_um2=round(ov, 1),
                    band_width_covered_um=round((i[2] - i[0]) if b["dir"] == "NS" else (i[3] - i[1]), 3)))
    ks = sorted(cs)
    for i, a in enumerate(ks):
        for b in ks[i + 1:]:
            g = gap(cs[a], cs[b])
            if area(inter(cs[a], cs[b])) > 0 or g < GAP - 1e-6:
                res["errors"].append(f"{a}/{b} gap {g:.3f} < {GAP}")
    # internal stations (+ ft regs) that would land inside a core body (12.2a1: no parent cells in cores)
    inside = collections.Counter()
    for s in T["internal_stations"]:
        for x, y in s["regs_um"]:
            for k, r in cs.items():
                if r[0] < x < r[2] and r[1] < y < r[3]:
                    inside[k] += s["bits"]
    res["station_bits_inside_new_bodies"] = dict(inside)
    res["core_area_um2"] = round(sum(area(r) for r in cs.values()), 1)
    res["verdict"] = "FITS" if not res["errors"] else "NO FIT"
    return res


out = dict(lane="DIE-HBM-29-O", plan=os.path.abspath(PLAN), partition="q_b113 (+ q_b113__physical_v1, same frame)",
           partition_outline=[W, H], bands=bands)
# ---- area arithmetic -------------------------------------------------------------------------------------------
pa = W * H
ns = [b for b in bands if b["dir"] == "NS"][0]["rect"]; ew = [b for b in bands if b["dir"] == "EW"][0]["rect"]
east = [ns[2], ew[3] - 0, W, H]          # east of the NS band, north of the EW band (cores sit at y >= 216)
east[1] = 216.0
west = [0, 216.0, ns[0], H]
k = json.load(open(KDELTA))
need = {n: area(r) for n, r in cores.items() if n != "opstore_a"}
need["opstore_a_V1"] = 760.32 * 483.84
out["area"] = dict(partition_um2=round(pa, 1), east_of_NS_band_um2=round(area(east), 1), east_rect=east,
                   west_strip_um2=round(area(west), 1), west_strip_rect=west, ns_band_um2=round(area(ns), 1),
                   hard_cores_um2={n: round(v, 1) for n, v in need.items()}, hard_core_sum_um2=round(sum(need.values()), 1),
                   east_packing_pct=round(100 * sum(need.values()) / area(east), 1),
                   macro_area_um2=round(32 * MW * MH, 1), k_fit=k["fit"])
# lane-core cell density as the logic-area yardstick (cells per um2 of lane core outline)
lane_cells = 306861; lane_a = 388.8 * 345.6; opa_cells = 240918
out["area"]["logic_yardstick"] = dict(lane_cells_per_um2=round(lane_cells / lane_a, 3),
    opstore_a_logic_um2_at_lane_density=round(opa_cells * lane_a / lane_cells, 1))
# row-2 width check without touching the NS band: ctl + gap + opstore_a must fit in [ns_hi, W - GAP]
row2_w = (W - GAP) - ns[2]
out["row2_without_band"] = dict(width_um=round(row2_w, 3), ctl_w=669.6, max_opstore_a_w=round(row2_w - 669.6 - GAP, 3),
    two_col_w_min=round(2 * MW + 10.8 + 2 * 10.8, 3), three_col_w_min=round(3 * MW + 2 * 10.8 + 2 * 10.8, 3),
    two_col_16row_h_min=round(16 * (MH + .024) + 3 * 10.8, 3), row2_h=round(H - (924.48 + GAP), 3))

# ---- placements ------------------------------------------------------------------------------------------------
cur = dict(cores)
out["current"] = check("current", cur)
v1 = dict(cores)
v1.pop("opstore_a")
v1["opstore_a"] = [1080.0, 941.76, 1080.0 + 760.32, 941.76 + 483.84]
v1["ctl"] = [388.8, 924.48, 388.8 + 669.6, 924.48 + 626.4]
out["V1"] = check("V1", v1)
v2 = dict(cores)
v2.pop("opstore_a")
v2["opstore_a0"] = [1434.24, 941.76, 1434.24 + 390.528, 941.76 + 436.32]
v2["opstore_a1"] = [1416.96 - 390.528, 941.76, 1416.96, 941.76 + 436.32]
x_ctl = (v2["opstore_a1"][0] - GAP - 669.6) // LAT * LAT
v2["ctl"] = [x_ctl, 924.48, x_ctl + 669.6, 924.48 + 626.4]
out["V2"] = check("V2", v2)
# half-core geometry (K grid, 2 col x 8 row): width/height with K's margins
half_w = 2 * 16.416 + 2 * MW + 12.096
half_h = 2 * 53.148 + 8 * MH + 7 * 0.024
out["V2"]["half_core"] = dict(K_grid_w=round(half_w, 3), K_grid_h=round(half_h, 3), outline=[390.528, 436.32],
    note="2 col x 8 row with K's col channel 12.096 needs 390.576 wide; 390.528 needs col channel 12.048 or edge 16.392",
    macro_pct=round(100 * 16 * MW * MH / (390.528 * 436.32), 1),
    logic_um2_per_half=round(390.528 * 436.32 - 16 * MW * MH, 1))

# ---- V2 boundary pins from the canonical opstore_a pin file ----------------------------------------------------
pins = json.load(open(PINS))
c = collections.Counter(re.sub(r"\[\d+\]$", "", p["name"]) for p in pins)
bcast = ["g_operand_0_u_group_sw_d", "g_operand_0_u_group_sw_mask", "x_u_core_u_vm_stage_group", "x_u_core_u_vm_stage_v",
         "x_u_core_u_engine_u_memory_g_operand_2_u_group_sw_addr", "clk", "x_u_core_u_engine_u_arithmetic_rst_control_n",
         "glue", "glue_1"]
dup = {n: c[n] for n in bcast}
out["V2"]["pins"] = dict(opstore_a_total=len(pins), by_bus=dict(sorted(c.items())), duplicated_broadcast=dup,
    duplicated_total=sum(dup.values()), cross_half_bits=1, split_total=len(pins) + sum(dup.values()) + 2,
    note="split by operand group: group g lane ports rd_addr/rd_re/rd_src/rd_q[4l+g], scalar[g], relay group g+2 "
         "(rd 512, rq 16, flt 1, sw_v 8) go to half g; stage sector data/mask/addr/group/v are broadcast to both "
         "groups (RTL ot_hgi_sfu_static_operand_store.sv g_operand loop) -> duplicated; the one sticky fault "
         "becomes 2 (half a0 fault -> a1 OR, 1 crossing bit, or both to ctl)")
json.dump(out, open(os.path.join(OUT, "opstore_a_estimate.json"), "w"), indent=1)

# ---- render ----------------------------------------------------------------------------------------------------
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
fig, axs = plt.subplots(1, 3, figsize=(21, 6.8))
col = dict(lane14="#9ecae1", lane15="#9ecae1", opstore_b="#a1d99b", ctl="#fdd0a2", opstore_a="#fb6a4a",
           opstore_a0="#fb6a4a", opstore_a1="#fc9272")
for ax, (ttl, cs) in zip(axs, [("d28c current (opstore_a 390.5x436.3: 32 macros do NOT fit)", cur),
                               ("V1 repack: opstore_a 760.32x483.84, ctl west by 267.84", v1),
                               ("V2 split: 2 x (390.528x436.32, 16 macros), ctl west by 319.68", v2)]):
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1.5))
    for b in bands:
        r = b["rect"]
        ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], color="#bcbddc", alpha=.45, lw=0))
        ax.text((r[0] + r[2]) / 2, (r[1] + r[3]) / 2 if b["dir"] == "NS" else 110, f"{b['dir']} band {'/'.join(b['layers'])}",
                ha="center", va="center", fontsize=7, rotation=90 if b["dir"] == "NS" else 0)
    for n, r in cs.items():
        ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fc=col.get(n, "#ddd"), ec="k", lw=1, alpha=.85))
        ax.text((r[0] + r[2]) / 2, (r[1] + r[3]) / 2, f"{n}\n{r[2]-r[0]:.1f}x{r[3]-r[1]:.1f}", ha="center", va="center", fontsize=7)
    if "opstore_a" in cs and cs is cur:
        r = cs["opstore_a"]
        ax.add_patch(Rectangle((r[2] - 760.32, r[1]), 760.32, 483.84, fill=False, ec="r", ls="--", lw=1.2))
        ax.text(r[2] - 740, r[3] + 60, "needed 760.32x483.84", color="r", fontsize=7)
    for s in T["internal_stations"]:
        for x, y in s["regs_um"]:
            ax.plot(x, y, ".", ms=3, color="k")
    ax.set_xlim(-30, W + 30); ax.set_ylim(-30, H + 30); ax.set_aspect("equal"); ax.set_title(ttl, fontsize=9)
fig.suptitle("q_b113 (type frame, um; dots = d28c internal station sites) -- DIE-HBM-29-O estimate", fontsize=10)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "opstore_a_estimate.png"), dpi=110)
print(json.dumps({k: out[k] for k in ("area", "row2_without_band")}, indent=1))
for v in ("current", "V1", "V2"):
    print(v, out[v]["verdict"], out[v]["errors"], out[v].get("band_overlap"), out[v]["station_bits_inside_new_bodies"])
print(json.dumps(out["V2"]["half_core"]), json.dumps({k: v for k, v in out["V2"]["pins"].items() if k != "by_bus"}))
