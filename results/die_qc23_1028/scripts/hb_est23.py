"""DIE-QC-23 ESTIMATE (12.14 estimate-before-build): per-partition kit hold-buffer count + area for the QC plan event
clock.tap_window W=180 (one window intra + seam) + clock.seam_hold {sender 25, seam 180}.  Analytic, from the plan
only (no netlist).  Kit-frame hold requirement of a register-to-register path (gen_phys kit SDC):
    cross-tap intra (launch tap early -W, capture late 0, CRPR only same-tap):  d_min >= W + t_hold + U_h
    seam input  (min input delay sender - seam = -155):                           d_min >= (seam - sender) + t_hold + U_h
    seam output (sdc out_min = -sender + W; launch early -W -> contract exact):   data >= sender + U_h/2 after vclk
k = ceil(deficit / HB4 FF early 44.6 ps) per bit (DIE-KV-5 / die_sta_related HB4 model).  Counted bit classes per
partition (plan structure, every one registered at both ends):
    in   = data/ctl input-port bits (P.ports dst)          k_in   (zero-logic face flop, d_min = wire_in)
    out  = output-port bits                                 k_out  (pin register clk->q + wire vs sender guarantee)
    ft   = ft slot width x (stations - 1) station hops     k_hop  (station-to-station, cross-tap; first hop is 'in')
    ist  = internal_stations bits x len(regs) hops          k_hop
    core = hard-core data pins (die_sta_related.intra_bits) k_core (glue tap <-> core tap: cross-tap BOUND, every pin)
    glue-to-glue internal paths: NOT counted (no partition netlist; reported as the uncounted class, see README).
BOUND form: every bit of a class at the class k (no credit for existing logic depth)."""
import json, math, sys
from collections import defaultdict
planf, tooldir, outf = sys.argv[1:4]
sys.path.insert(0, tooldir)
import die_sta_related as DS

W, SND, SEAM = 180.0, 25.0, 180.0
LEG = dict(W=0.0, in_min=-40.0)                    # current plan: no tap_window, legacy in_min = -insertion_tol 40
HB = dict(cell="HB4xp67_ASAP7_75t_R", ff_early_ps=44.6, tt_late_ps=83.0, area_um2=0.1021)
TH, UH = 10.0, 25.0          # DFF hold FF (bound) + kit hold uncertainty (full, no split credit)
CLKQ_FF, WIRE_ADJ, WIRE_HOP = 18.0, 2.0, 25.0     # FF clk->q; face-flop adjacency wire; ~320 um ft hop (FF, M5-M7)
VCLK_FF, OUT_NEED = 202.5, None
def k(d):
    return max(0, math.ceil(d / HB["ff_early_ps"] - 1e-9))

def ks(w, in_min):
    kin = k(-in_min + TH + UH - WIRE_ADJ)
    khop = k(w + TH + UH - CLKQ_FF - WIRE_HOP)
    kcore = k(w + TH + UH - CLKQ_FF - WIRE_ADJ)
    # output: sender must change >= sender + U_h/2 after vclk (FF); pin register at tap latency ~ vclk: clk->q + wire
    kout = k(max(0.0, SND + UH / 2 - CLKQ_FF - WIRE_ADJ)) if w else 0
    return dict(in_=kin, hop=khop, core=kcore, out=kout)

KN, KO = ks(W, SND - SEAM), ks(LEG["W"], LEG["in_min"])
P = json.load(open(planf))
T = P["partition_types"]
ib = DS.intra_bits(planf)
bits = defaultdict(lambda: defaultdict(int))
for p in P["ports"]:
    if p.get("kind") not in ("data", "ctl"):
        continue
    if p["dst"].get("part"):
        bits[p["dst"]["part"]]["in"] += int(p["width"])
    if p["src"].get("part"):
        bits[p["src"]["part"]]["out"] += int(p["width"])
rows = []
for q in P["partitions"]:
    n, t = q["name"], T[q["type"]]
    b = bits[n]
    b["ft"] = sum(int(s["width"]) * max(0, int(s.get("stations", 0)) - 1) for s in t.get("ft_slots", []) or [])
    b["ist"] = sum(int(s["bits"]) * len(s.get("regs_um", [])) for s in t.get("internal_stations", []) or [])
    b["core"] = ib.get(n, 0)
    area = t["outline_um"][0] * t["outline_um"][1]
    def cells(K):
        return (b["in"] * K["in_"] + b["out"] * K["out"] + (b["ft"] + b["ist"]) * K["hop"] + b["core"] * K["core"])
    cn, co = cells(KN), cells(KO)
    rows.append(dict(part=n, type=q["type"], area_mm2=round(area / 1e6, 4), **{f"bits_{x}": b[x] for x in
                ("in", "out", "ft", "ist", "core")}, cells_new=cn, cells_legacy=co, cells_delta=cn - co,
                area_new_um2=round(cn * HB["area_um2"], 1), pct_new=round(100 * cn * HB["area_um2"] / area, 4)))
rows.sort(key=lambda r: -r["pct_new"])
tot = dict(cells_new=sum(r["cells_new"] for r in rows), cells_legacy=sum(r["cells_legacy"] for r in rows))
tot["cells_delta"] = tot["cells_new"] - tot["cells_legacy"]
tot["area_new_mm2"] = round(tot["cells_new"] * HB["area_um2"] / 1e6, 4)
out = dict(note=__doc__, plan=planf, window_ps=W, seam_hold=dict(sender_ps=SND, seam_ps=SEAM), hb=HB,
           assumptions=dict(t_hold_ff=TH, unc_hold=UH, clkq_ff=CLKQ_FF, wire_adj=WIRE_ADJ, wire_hop=WIRE_HOP),
           k_new=KN, k_legacy=KO, partitions=len(rows), max_pct=rows[0]["pct_new"], over_5pct=[r["part"] for r in rows if r["pct_new"] > 5],
           total=tot, top10=rows[:10], rows=rows, status="UNCHECKED (analytic BOUND, plan-only, glue-to-glue uncounted)")
json.dump(out, open(outf, "w"), indent=1)
print("k_new", KN, "k_legacy", KO)
print("partitions", len(rows), "max %", rows[0]["pct_new"], rows[0]["part"], "over5", len(out["over_5pct"]))
print("total", tot)
for r in rows[:8]:
    print(r)
