#!/usr/bin/env python3
"""TOKEN-XDIE-HBM (2026-10-18): compose the HBM d4g cross-die collective term of the token from the measured two-die
transport co-sim (rtl/hbm_accel/generic/collective/xdie/run_xdie_hbm_link.sh) and the d4g pricer's collective census.

    python3 tools/xdie_hbm_compose.py --run DIR --out results/rtl/xdie_hbm_1018/record.json

T_token += sum_l n_l * sum_x max(0, E_meas(x) - O_meas(l, x))
  E_meas(x) = k_x * E_link(P_link(x)) + C_on(x)
    E_link(P) : measured in RTL, COLL wr reservation on die A -> last frame published by die B's COLL endpoint, both
                directions at once, at the production per-link frame count P (linear interpolation between measured sweep
                points; beyond the sweep: extrapolated with the last measured segment's slope, grade flagged)
    P_link(x) = ceil((G - 1) * f / NL), f = ceil(bytes / G / 64)  (the pricer's own frame accounting, perf.coll_cycles /
                ds_die_split: (G-1) f flits a die over NL = 4 delivery lanes)
    k_x       = crossings in series (1 gather / merge, 2 all-reduce or reduce-mcast)
    C_on(x)   = on-die COLL work the transport vehicle does not contain: VM read -> COLL issue 23 edges and RX publish ->
                VM write 5 edges (collq_schedule.json / STATIC_V4_CONTRACT), COLL_VM relays 3 x 14.91 + COLL_RING k x 9.38
                (ds_relay_latency plan-b stages), the d4g on-die quadrant adder of the record (d4g_quadrant_1017), and for
                reductions an 8-way golden-order FP32 tree (3 levels x LAT 3) -- grade 'priced-on-die'
  O_meas      = cycles the compiler's static schedule hides: d4g pricer cm_census hidden_cycles = 0.0 for every AR tag
                (results/arch/hbm_d4g_price_1017/price5/cm_census.json); Qwen timing.schedule breaks out none -> 0.
Scaling N -> production: a crossing is one switch chip at any die count (one-tier multi-plane fabric), so E_link does not
depend on N; the die count enters only through P_link (G = 192 DS, 8 Qwen).  The 2-die vehicle is one port pair; the NL
rails of a die run the same transport in parallel on separate COLL rails / endpoints / SerDes (no shared on-die stage in
the vehicle's scope).
"""
import argparse, json, math, re, subprocess
from pathlib import Path

COLL_VM, COLL_RING, VM_RD, VM_WR, RED8 = 14.91, 9.38, 23, 5, 9
NL = 4
# census: tools/hgi_sim (d4g pricer) per-token collective records; priced = per instance (train) cycles, 1.2 GHz
DS = [  # tag, kind, bytes (per train), count per token, crossings, on-die adder, priced per instance
    ("x_proj qa+kvraw 2-record train", "ALL_GATHER", 3584, 32, 1, 22.8, 2 * 381.1),
    ("x_proj 4-record train L2/8/14", "ALL_GATHER", 7744, 3, 1, 22.8, 4 * 195.5),
    ("x_proj 4-record train L20", "ALL_GATHER", 4672, 1, 1, 22.8, 4 * 189.7),
    ("x_proj 3-record train L24-36", "ALL_GATHER", 3648, 4, 1, 22.8, 3 * 253.5),
    ("o-group reduce-mcast (8 contributors)", "GROUP_REDUCE_MCAST", 32768, 40, 2, 22.8, 1326.4),
    ("attn_out y / ffn_out yf", "ALL_GATHER", 10240, 80, 1, 0.0, 763.1),
    ("router gsc", "ALL_GATHER", 1536, 40, 1, 22.8, 763.8),
    ("MoE expert_intermediate s0..s6 7-record train (dispatch/combine)", "ALL_GATHER", 32256, 40, 1, 22.8, 7 * 124.6),
    ("indexer q iq", "ALL_GATHER", 8192, 8, 1, 82.4, 763.1),
    ("96x512 index TOPK_MERGE", "TOPK_MERGE", 393216, 8, 1, 10.4, 4191.0),
    ("argmax / LM head", "ARGMAX_MERGE", 768, 1, 1, 10.4, 763.8),
]
DS_PRICED_ONLY = [("kv ROW_GATHER to 64 head dies (bypass form)", 8, 21500.0 / 8)]   # census total ~21.5k, kept priced
QW = [
    ("o_proj / down ALL_REDUCE_SUM (n 4096)", "ALL_REDUCE_SUM", 8192, 72, 2, 84.0, 1310.5),
    ("argmax / LM head", "ARGMAX_MERGE", 768, 1, 1, 10.4, 561.3),
]


def parse(log):
    pts = {}
    for m in re.finditer(r"XDIE_INST \d+ P=(\d+) A->B E=([\d.]+) first=([\d.]+) \| B->A E=([\d.]+) first=([\d.]+)", log.read_text()):
        P = int(m[1]); pts[P] = dict(E=max(float(m[2]), float(m[4])), first=max(float(m[3]), float(m[5])),
                                     E_ab=float(m[2]), E_ba=float(m[4]))
    ok = re.search(r"^XDIE_HBM .* PASS$", log.read_text(), re.M) is not None
    return pts, ok


def interp(pts, P):
    xs = sorted(pts)
    if P <= xs[0]:
        return pts[xs[0]]["E"], "measured"
    for a, b in zip(xs, xs[1:]):
        if a <= P <= b:
            ea, eb = pts[a]["E"], pts[b]["E"]
            return ea + (eb - ea) * (P - a) / (b - a), "measured" if P in pts else "measured-interpolated"
    a, b = xs[-2], xs[-1]
    s = (pts[b]["E"] - pts[a]["E"]) / (b - a)
    return pts[b]["E"] + s * (P - b), "measured-extrapolated"


def compose(rows, G, pts, model):
    out, tot_m, tot_p = [], 0.0, 0.0
    for tag, kind, nbytes, cnt, k, adder, priced in rows:
        f = max(1, math.ceil(nbytes / G / 64))
        P = math.ceil((G - 1) * f / NL)
        el, grade = interp(pts, P)
        c_on = VM_RD + VM_WR + 3 * COLL_VM + k * COLL_RING + adder + (RED8 if "REDUCE" in kind else 0)
        e = k * el + c_on
        o = 0.0
        out.append(dict(model=model, collective=tag, kind=kind, per_token_count=cnt, payload_bytes=nbytes, G=G,
                        flits_per_rank=f, P_link_frames=P, crossings=k, E_link_meas_cycles=round(el, 1), C_on_die=round(c_on, 1),
                        E_meas_cycles=round(e, 1), O_meas_cycles=o, exposed_per_instance=round(max(0.0, e - o), 1),
                        exposed_per_token=round(cnt * max(0.0, e - o), 1), priced_per_instance=priced,
                        priced_per_token=round(cnt * priced, 1), grade=f"{grade} transport (current GEN2 RTL) + priced-on-die",
                        overlap_source="d4g pricer cm_census hidden_cycles=0.0 (AR)" if model == "DS" else "timing.schedule: none broken out -> 0"))
        tot_m += cnt * max(0.0, e - o); tot_p += cnt * priced
    return out, tot_m, tot_p


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--run", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--rtl-commit", default=""); a = ap.parse_args()
    run = Path(a.run)
    ds_pts, ds_ok = parse(run / "ds_pass.log"); qw_pts, qw_ok = parse(run / "qw_pass.log")
    ds_rows, ds_m, ds_p = compose(DS, 192, ds_pts, "DS")
    qw_rows, qw_m_direct, qw_p = compose(QW, 8, qw_pts, "Qwen")
    for r in qw_rows: r["form"] = "direct 2-phase over 4 lanes (needs 7 direct peers: NOT realisable with 5 die links)"
    # realisable Qwen TP8 form: hypercube recursive halving / doubling over 3 of the 5 die links, 6 dependent steps
    hc = []
    for tag, kind, nbytes, cnt, k, adder, priced in QW:
        if kind != "ALL_REDUCE_SUM":
            continue
        fl = math.ceil(nbytes / 64)
        steps = [fl // 2, fl // 4, fl // 8, fl // 8, fl // 4, fl // 2]
        el = [interp(qw_pts, P)[0] for P in steps]
        c_on = 3 * COLL_VM + adder + sum(VM_RD + VM_WR + (3 if i < 3 else 0) for i in range(6))
        e = sum(el) + c_on
        hc.append(dict(model="Qwen", collective=tag + " [hypercube 3D]", kind=kind, per_token_count=cnt, payload_bytes=nbytes, G=8,
                       step_frames=steps, E_link_steps=[round(x, 1) for x in el], C_on_die=round(c_on, 1), E_meas_cycles=round(e, 1),
                       O_meas_cycles=0.0, exposed_per_instance=round(e, 1), exposed_per_token=round(cnt * e, 1),
                       priced_per_instance=priced, priced_per_token=round(cnt * priced, 1),
                       grade="measured-interpolated transport (current GEN2 RTL) + priced-on-die; topology assumed",
                       form="hypercube recursive halving/doubling, 3 links a die, 6 dependent crossings (realisable)"))
    qw_m = sum(r["exposed_per_token"] for r in hc) + sum(r["exposed_per_token"] for r in qw_rows if r["kind"] != "ALL_REDUCE_SUM")
    qw_rows += hc
    ro = sum(c * p for _, c, p in DS_PRICED_ONLY)
    muts = {m: ("REJECTED" if re.search(r"^XDIE_HBM .* FAIL$", (run / f"{m}.log").read_text(), re.M) else "SURVIVED")
            for m in ("m1", "m2", "m3", "m4", "m5") if (run / f"{m}.log").exists()}
    rec = dict(schema="opentallas.xdie_hbm.record.v1", lane="TOKEN-XDIE-HBM", date="2026-10-18",
               vehicle="rtl/hbm_accel/generic/collective/xdie/tb_xdie_hbm_link.sv (2 dies, both directions)",
               rtl_commit=a.rtl_commit, rtl_base="claude/hd4g-gen2-1018 7c124deae (d4g GEN2 die RTL)",
               instantiated_rtl=["ot_hgi_coll_link_e (+capture_ctl_e, static_capture_ctl, pinreg_ctl/store, seq_ctl, CRC, replay SRAM leaf)",
                                 "hfd_ep_static (+ot_hep_rx_pingpong / rx_block, ot_sram_1r1w_64x512)",
                                 "ot_pdie_serdes (ot_s81_kp4_enc/dec RS(544,514), ot_s81_rate_match; behavioural PMA_LAT 4)"],
               modelled=dict(off_chip_DS="switch 250 ns + 2 x 3 m twinax 27.6 ns = 277.6 ns (333 words); PHY/FEC part of the 377.6 ns budget is MEASURED digital + behavioural PMA (tools/dshbm_1m_coll.py TU constants; memory switch-crossing-377-justified-1016)",
                             off_chip_Qwen="in-package trace 4 words = 3.3 ns (assumption; Qwen TP8 never reaches the switch, perf.coll_cycles G<=8)",
                             die_lane_relays="RLY=10 registered stages each way (COLL_EP 9.6 plan-b stage, ds_relay_latency)",
                             clocks="die B 300 ppm slow; one pad bit error in ~every second PMA word (FEC t=15)"),
               constants=(run / "constants.txt").read_text().strip().splitlines() if (run / "constants.txt").exists() else [],
               sweep=dict(DS=ds_pts, Qwen=qw_pts), pass_DS=ds_ok, pass_Qwen=qw_ok, mutants=muts,
               rows=ds_rows + qw_rows,
               composition=dict(
                   formula="T_token += sum_l n_l * sum_x max(0, E_meas(x) - O_meas(l,x)); E_meas = k*E_link(P_link) + C_on; P_link = ceil((G-1)*ceil(bytes/G/64)/4)",
                   DS=dict(G=192, xdie_measured_exposed_cycles=round(ds_m, 1), priced_same_rows=round(ds_p, 1),
                           row_gather_kept_priced=ro, token_cycles_price5=629775.1),
                   Qwen=dict(G=8, xdie_measured_exposed_cycles=round(qw_m, 1), direct_form_not_realisable=round(qw_m_direct, 1),
                             priced_same_rows=round(qw_p, 1),
                             token_cycles_price5=round(1.2e9 / 946.2, 1)),
                   scaling="E_link independent of die count (one switch chip a crossing); N enters via P_link; vehicle = 1 port pair of NL=4 parallel rails"),
               gaps=["COLL issuer / programme (ot_hgi_coll_static_issuer_v6 inside v8g) and the epcal_<q> endpoint calendar are NOT in the vehicle: their fixed slots are driven by the bench at the cycles the compiler would program (next step: v8g parent + epcal + real F20 programme)",
                     "golden-order reduction / VM writes are on-die COLL stages already benched per unit (COLLQ bench, q_hard_v5 lockstep); here priced-on-die constants",
                     "ROW_GATHER kept priced; TOPK_MERGE payload extrapolated beyond the 256-frame sweep",
                     "LA / LXB / GAPB derived from a calibration run's landing bounds + fixed guards; production compiler bound must add ppm-drift margin over long epochs"])
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(dict(DS=rec["composition"]["DS"], Qwen=rec["composition"]["Qwen"], mutants=muts, pass_DS=ds_ok, pass_Qwen=qw_ok), indent=1))


if __name__ == "__main__":
    main()
