"""S81-UNBLOCK-3 10-27 (COORD ruling TOK-DS-11 (b)): per-frame landing strap LK from the measured landing phase.

dsfd_cfifo_crs4 lands each of the frame's 4 x lanes in ot_s81_land #(.D(4)) at read offset K = lk[3k +: 3].
Window (ot_s81_land header): (E - D) * T + t_hold < dL < E * T - t_cq - t_setup, E = K + R0 - G.
In the plan band composition the lane clock is the band's own clock (frame_band_plan.py: xk = clk; as-built xok =
{4{ck_r0}}), so dL = related-pair skew of one clock net, |dL| <= neighbour_skew_ps.  fc31 straps (E4/E5 on 36 of 72
frames) were set for the retired forwarded-clock x relay chains (dL = routed flight, dv_slice_cut frame_lk) and
violate the window at dL ~ 0 (dv_slice_cut: zero-flight K = 5 frames faulted their lane rings at warm-up)."""
import json
import sys

rec, plan, out = sys.argv[1:4]
frames = json.load(open(rec))["frames"]
P = json.load(open(plan))
T = P["die"]["period_ps"]
skew = P.get("clock", {}).get("neighbour_skew_ps", 80)
D, TCQ_SU, TH = 4, 60, 10          # ring depth (dsfd_cfifo_crs4 u_l); t_cq + t_setup and t_hold, ASAP7 DFF TT (UNCHECKED bounds)


def ok(E, dl):
    return (E - D) * T + TH < dl < E * T - TCQ_SU


legal = [E for E in range(1, 8) if all(ok(E, dl) for dl in (-skew, 0, skew))]
centre = legal[len(legal) // 2]
rows = {}
for inst, f in sorted(frames.items()):
    lk = f["lk_asbuilt"]
    v = int(lk.split("'h")[1], 16)
    k_fc31 = sorted({(v >> (3 * g)) & 7 for g in range(4)})
    rows[inst] = dict(master=f["master"], plan_pos=f["plan_pos"], lane_clock="xk = band clk (xok = ck_r0)",
                      dL_ps=[-skew, skew], legal_E=legal, LK_plan=f"{{4{{3'd{centre}}}}}", K=centre,
                      fc31_strap=lk, fc31_K=k_fc31, fc31_K_in_window=all(k in legal for k in k_fc31))
json.dump(dict(schema="opentallas.s81.frame_lk.v1", period_ps=T, neighbour_skew_ps=skew, D=D, legal_E=legal,
               K_plan=centre, frames=len(rows),
               fc31_out_of_window=sum(not r["fc31_K_in_window"] for r in rows.values()),
               note=__doc__, assumption="E = K (R0 - G = 0: band reset release and lane start on the same calendar edge; "
               "checked dynamically by the ring fault in the L0 RTL sim, UNCHECKED statically)", rows=rows),
          open(out, "w"), indent=1)
print(json.dumps(dict(legal_E=legal, K=centre, frames=len(rows),
                      fc31_out_of_window=sum(not r["fc31_K_in_window"] for r in rows.values()))))
