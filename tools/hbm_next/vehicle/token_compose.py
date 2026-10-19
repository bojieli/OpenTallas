#!/usr/bin/env python3
"""HBM-NEXT-VEH (10-19): token composition of the next HBM die (P = 4), priced vs measured.

Method (AGENTS.md "simulate the minimum component"; memory token-pass-release-gate-1018): the token is NEVER simulated
whole.  Each layer segment's cycles come from the compiler's static schedule on the D1 timing model
(tools/hgi_sim/hbm_plane_model.py, re-timed with the next-die knobs by compose_grid.py), and every term that an RTL
bench has MEASURED replaces or bounds its priced value in the ledger below.  The vehicle's layer runs (forked d4g SW
slice + P = 4 lanes as SM4 / ATT4 / UNITS RTL lands) fill the per-layer `measured_cycles` column; until then it is null
and the composition is PRICED, with the measured unit terms applied where they exist.

Inter-die traffic is in the schedule: every off-die collective = endpoint 108.6 + one single-tier switch crossing
(377.6 ns = 453.1 cycles at 1.2 GHz) + tail 0.15 us, = 741.7 cycles fixed + payload over L COLL delivery lanes
(64 B/lane/cycle), 192 dies on ONE switch plane, each die its own SerDes port (32 x 100G).

    python3 tools/hbm_next/vehicle/token_compose.py --grid compose_grid.json --out results/arch/hbm_next_1019/veh
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CLK = 1.2e9
D1_RUN = ROOT / "results/arch/hbm_mtp_next_1018/model/run.json"
STUDY = ROOT / "results/arch/hbm_next_1019/runs"
SM_BENCH = ROOT / "results/arch/hbm_mtp_next_1018/sm_area/bench"
TARGETS = dict(ds_ar=1905.4, ds_mtp=3363.5, ds_mu_agg=4365.3, ds_mu_per_user_floor=1000.0)
REPRESENTATIVE = {"0": "L0 (dense attention window + MoE FFN; slice replay ds_l0)", "2": "L2 (compressed KV + sparse "
                  "indexer, global KV owner)", "3": "L3 (window layer, MoE)", "14": "L14 (Engram home + KV owner)",
                  "head": "MTP/LM head + ARGMAX"}

# measured / RTL-derived unit terms (source-pinned); 'applies' says how the composition uses each one
LEDGER = [
    dict(term="SM P-lane MAC column (bdc + BF16 tcc), P = 1..8",
         priced="P lanes share one weight word; per-line cycles = P = 1 line (D1 sm_mode slots)",
         measured="bit-exact AND cycle-for-cycle equal to the production single-lane column at P = 1, 2, 4, 6, 8; "
                  "mutant (lane aliasing) caught at P = 2, 4 (Verilator 5.050)",
         src="results/arch/hbm_mtp_next_1018/sm_area/bench/run_p*_m*.log; rtl/hbm_accel/sm/mtp_lanes/ot_hbm_sm_bdc_p.sv",
         delta="+1 latency cycle a record for the registered per-lane-group broadcast tree at P >= 4 (D1 synth); "
               "throughput unchanged", status="MEASURED (column); tile hnx_rp4lp4 = SM4 lane, not yet"),
    dict(term="ATT KV-line-stationary 4-query union stream (E1 exactness + 4-query slice)",
         priced="U(N)/U(1) KV union price, top-512 disjoint upper bound (headline)",
         measured="E1 PASS (union stream in golden order exact per lane, reduced ckpt 40 L, N = 6); 4-query slice "
                  "bit-exact vs 4 single-query goldens, 6 mutants FAIL; span = fixed ~113-127 + 7.8 cycles a union row "
                  "(4 lanes 401 vs 1,508 serial)",
         src="results/arch/hbm_next_1019/att4/E1.md, att4/bench/throughput.json",
         delta="slice cycles inside the priced union bound; PV merge A1 (shared 4-lane merge) still gating; balanced "
               "32-SM (lane, run) assignment needed (CMTP S1)", status="EXACTNESS + SLICE CYCLES"),
    dict(term="HC.HC_MIX further-row II (hnx N-row engine = the split HC GEN2 binds: root TPRE 6 + 4 qhub + 32 banks)",
         priced="250 (HCP W256 x6 mode, D1)",
         measured="250.0 exactly linear on the hnx RTL: HC_MIX_CYCLES N 1/2/3/4/6/8 = 998/1,248/1,498/1,748/2,248/2,748, "
                  "lockstep bit-exact vs hdc_golden_v41 chunk8 + tail reference; MUT1/MUT4 FAIL witnesses (Verilator 5.050)",
         src="results/arch/hbm_next_1019/units/hc/README.md (claude/hbm-next-1019@4efc7ebb3); d4g lockstep "
             "results/rtl/hbm_hc_split_1017/verdict.json 996/1,246/2,746",
         delta="0: the composition runs at II 250 (grid axis keeps 600 / 950 / 4,385 / per-position as sensitivities)",
         status="MEASURED = priced (UNITS gate #1 PASS; the 4,385 engine is not the bound one)"),
    dict(term="COLL N-row message train (hnx gather master ot_hnx_coll_gq)",
         priced="COLL.* II = payload x N, fixed part once (CMTP R4)",
         measured="one fire + one 40-edge drain a record, further row 3K/2 edges (K = ceil(F / R)); N = 1 reproduces the "
                  "d4g bench bit for bit; trains N 1..6 PASS; m6/m7/m8 FAIL witnesses (Verilator 5.050)",
         src="results/arch/hbm_next_1019/units/coll/README.md (claude/hbm-next-units-coll-1019@582620634)",
         delta="0 (= price); the 5th delivery lane L = 5 is a DIE + COLL-body + SU change (in the grid as L5)",
         status="MEASURED = priced (on-die ring all-gather)"),
    dict(term="SM4 P = 4 leaf / tile hnx_rp4lp4 (lane-select x beats, slot-major publish)",
         priced="P lanes = 1 AR record (c_AR)",
         measured="bit-exact vs production d4g leaves P1-4, MUT1-3 FAIL; 64-chunk span P4 / P1 = 8,262 / 8,238 (K 16, "
                  "1.003x) and 2,118 / 2,094 (K 4, 1.012x) = +24 = +1 front +1 publish +8p lane skew; tile lockstep "
                  "landed vs flat PASS",
         src="results/arch/hbm_next_1019/sm4/bench_summary.json",
         delta="in the PHYS schedule: +2 + 8 (lanes used - 1) cycles on every SM record (AR +2, N >= 4 +26); layer-"
               "shape leaf runs (short records, 9-32 chunks) = veh/sm4_layer/",
         status="MEASURED (leaf + tile lockstep); in schedule"),
    dict(term="DIE f4c_t5 relay stages (stand-in die case GEN_OK, 693 mm2)",
         priced="D1 plan_b stage set (d4g-class)",
         measured="bit-weighted stages per class, f4c_t5 vs DIE's d4g frame: SM_HBM 2.88 -> 5.25, SM_X 11.25 -> 6.46, "
                  "VM_HUB 16.28 -> 12.0, COLL_VM 15.0 -> 12.25, COLL_RING 8.5 -> 10.25, HBM_VM 19.62 -> 21.0, ... "
                  "(plan-level geometry, not routed)",
         src="results/arch/hbm_next_1019/die/plan/plan_p4.json per_class; die/README.md",
         delta="PHYS axis: the D1 plan_b stages moved by the per-class delta (f4c_t5) or SM_HBM only (f4c_t5_smhbm)",
         status="PLAN-MEASURED (relays + GRT pending, DIE step 2)"),
    dict(term="FUSED.HC_PRE_NORM further-row II", priced="197", measured="197 (LL P6 RTL: (1,451 - 466) / 5)",
         src="results/arch/hbm_mtp_1015/p6_rtl_2330/measurement.json", delta="0", status="MEASURED = priced"),
    dict(term="SU reducer ingress (HH-5, d4g as built: 1 reducer operand / edge / quarter)",
         priced="d4g price assumes full-width reducer ingress",
         measured="RTL-as-read bound: DS AR 1,905.4 -> 1,796.6 (-5.71 %), d4g MTP -17.58 %, Qwen -47.76 %; "
                  "widened W16 -0.14 % / -0.59 %, W32 -0.04 % / -0.19 % (AR / MTP)",
         src="claude/hh5-su-reducer-1018 @714a83601 results/arch/hbm_d4g_price_1017/su_red/price_su_red_w.json",
         delta="next die ASSUMES the widened ingress (W32: <= 0.2 %); as built it would cost >= 5.7 % AR and more "
               "at P = 4 (reductions are per row)", status="RE-PRICED FROM RTL, d4g WIDEN decision pending"),
    dict(term="COLL GROUP_REDUCE_MCAST on-die multicast phase", priced="1,349 edges incl. the cross-die reduce",
         measured="370 edges launch -> last write, on-die phase only (4/4 slice precheck PASS)",
         src="claude/veh-coll2-coll-1018 (VEH-FMT-COLL2)", delta="not comparable until the cross-die phase runs",
         status="PRECHECK (partial)"),
    dict(term="SFU collar programme install", priced="not priced per token (resident)",
         measured="~0.79 M ingress edges an install (stripes padded to 2,048 rows)",
         src="claude/veh-coll2-sfu-1018 (VEH-FMT-COLL2)", delta="SFU programmes MUST stay resident across the "
         "token; at P = 4 the row stepping must not re-install", status="CONSTRAINT"),
    dict(term="d4g SW-slice DS L0 SU records (8 SU.VOP, released-checkpoint fixtures)",
         priced="compiler commit 10-60 serial edges after the priced end (fill 13 + FO 36 + drain 11)",
         measured=None, src="pending: ot-epyc4 sw2 (sw5) / ot-epyc5 sw5e SW-slice build (top Verilator pass running)",
         delta="next-die AR layer = this run (identical RTL + byte-identical images, see ar_repro.json)",
         status="PENDING (vehicle)"),
]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def tok(cyc, n=1.0):
    return round(n * CLK / cyc, 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--grid", type=Path, required=True, help="compose_grid.json (compose_grid.py)")
    ap.add_argument("--ar-repro", type=Path, default=None, help="ar_repro.json")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    g = json.loads(a.grid.read_text())
    if not g.get("self_check_pass"):
        print("REFUSED: compose_grid self-check failed (grid does not reproduce D1 / Phase-1)", file=sys.stderr)
        return 2
    d1 = json.loads(D1_RUN.read_text())["runs"]
    grid = g["grid"]
    L5, L4 = grid["5"], grid["4"]
    tau = g["tau"]

    def point(L, ii, vm):
        r = grid[str(L)]["II"][ii]["VM"][vm]
        return dict(ar_tok_s=grid[str(L)]["ar_tok_s"], mtp_tok_s=r["ds_mtp_tok_s"], mu_agg_tok_s=r["mu_agg_tok_s"],
                    mu_per_user_tok_s=r["mu_per_user_tok_s"],
                    meets=dict(ar=grid[str(L)]["ar_tok_s"] >= TARGETS["ds_ar"] - 0.05,
                               mtp=r["ds_mtp_tok_s"] >= TARGETS["ds_mtp"] - 0.05,
                               mu_agg=r["mu_agg_tok_s"] >= TARGETS["ds_mu_agg"] - 0.05,
                               per_user_floor=r["mu_per_user_tok_s"] >= TARGETS["ds_mu_per_user_floor"]))

    table = {f"L{L}|II{ii}|{vm}": point(L, ii, vm) for L in (4, 5) for ii in grid[str(L)]["II"]
             for vm in ("grown", "asbuilt")}
    phys = g.get("phys") or {}

    def ppoint(ph, ii, vm):
        G = phys[ph]["5"]
        r = G["II"][ii]["VM"][vm]
        return dict(ar_tok_s=G["ar_tok_s"], mtp_tok_s=r["ds_mtp_tok_s"], mu_agg_tok_s=r["mu_agg_tok_s"],
                    mu_per_user_tok_s=r["mu_per_user_tok_s"],
                    meets=dict(ar=G["ar_tok_s"] >= TARGETS["ds_ar"] - 0.05,
                               mtp=r["ds_mtp_tok_s"] >= TARGETS["ds_mtp"] - 0.05,
                               mu_agg=r["mu_agg_tok_s"] >= TARGETS["ds_mu_agg"] - 0.05,
                               per_user_floor=r["mu_per_user_tok_s"] >= TARGETS["ds_mu_per_user_floor"]))
    for ph in phys:
        for ii in phys[ph]["5"]["II"]:
            for vm in ("grown", "asbuilt"):
                table[f"{ph}|L5|II{ii}|{vm}"] = ppoint(ph, ii, vm)
    HP = "f4c_t5"
    head = f"{HP}|L5|II250|grown"
    L5p = phys[HP]["5"]
    hp = L5p["II"]["250"]["VM"]["grown"]
    hb = grid["5"]["II"]["250"]["VM"]["grown"]

    # per-layer composition at the headline point (priced; measured column filled by the vehicle)
    def layers(ar_seg, mtp_seg, mu_seg):
        rows = []
        for k in ar_seg:
            rows.append(dict(segment=k, representative=REPRESENTATIVE.get(k), ar_priced=ar_seg[k],
                             mtp_verify_priced=mtp_seg[k], mu4_priced=mu_seg[k], ar_measured=None,
                             mtp_verify_measured=None, mu4_measured=None,
                             d4g_ar_priced=d1["ds|AR"]["per_segment"][k]))
        return rows
    per_layer = layers(L5p["ar_per_segment"], hp["mtp_per_segment"], hp["mu_per_segment"])
    for row in per_layer:                 # the same segment without the PHYS terms (d4g-class stages, no SM4 latency)
        k = row["segment"]
        row.update(ar_priced_d4g_phys=L5["ar_per_segment"].get(k), mtp_verify_priced_d4g_phys=hb["mtp_per_segment"].get(k),
                   mu4_priced_d4g_phys=hb["mu_per_segment"].get(k))

    # inter-die traffic: COLL busy share and the fixed part per collective
    fcoll = 108.6 + 377.6e-9 * CLK + 0.15e-6 * CLK
    inter = dict(
        dies=192, switch_tiers=1, crossing_ns=377.6, coll_fixed_cycles=round(fcoll, 1),
        coll_lanes=5, coll_bytes_per_cycle=5 * 64,
        coll_busy_share=dict(ar=round(L5p["ar_unit_busy"]["COLL"] / L5p["ar_cycles"], 3),
                             mtp_verify=round(hp["mtp_unit_busy"]["COLL"] / hp["mtp_verify_cycles"], 3),
                             mu4=round(hp["mu_unit_busy"]["COLL"] / hp["mu_step_cycles"], 3)),
        serdes_note="STUDY (a): at P = 4 MU, COLL busy x full 256 B/cycle <= 34 % of the 400 GB/s raw SerDes; L = 5 "
                    "(320 B/cycle = 384 GB/s) is the widest the SerDes feeds; the network is not the ceiling")
    hc_cost = {ii: dict(mtp_tok_s=grid["5"]["II"][ii]["VM"]["grown"]["ds_mtp_tok_s"],
                        mu_per_user_tok_s=grid["5"]["II"][ii]["VM"]["grown"]["mu_per_user_tok_s"],
                        mu_agg_tok_s=grid["5"]["II"][ii]["VM"]["grown"]["mu_agg_tok_s"],
                        hc_busy_mu=grid["5"]["II"][ii]["VM"]["grown"]["mu_unit_busy"].get("HC"))
               for ii in grid["5"]["II"]}
    # per-user rate vs II slope (L5, grown, d4g-class stages) between 600 and 950 -> the II that holds 1,000 tok/s a user
    s600, s950 = (grid["5"]["II"][x]["VM"]["grown"]["mu_step_cycles"] for x in ("600", "950"))
    slope = (s950 - s600) / 350.0
    ii_floor = 600 + (CLK / 1000.0 - s600) / slope if slope > 0 else None
    # MTP step vs II (L5, grown) between 250 and 600 -> the II that still meets the MTP target
    m250, m600 = (grid["5"]["II"][x]["VM"]["grown"]["mtp_step_cycles"] for x in ("250", "600"))
    mslope = (m600 - m250) / 350.0
    ii_mtp = 250 + (tau * CLK / TARGETS["ds_mtp"] - m250) / mslope if mslope > 0 else None
    # physical terms IN the S2 schedule (compose_grid PHYS axis), against the same point on d4g-class stages
    def pv(ph):
        G = phys[ph]["5"]
        r = G["II"]["250"]["VM"]["grown"]
        return dict(ar_tok_s=G["ar_tok_s"], mtp_tok_s=r["ds_mtp_tok_s"], mu_agg_tok_s=r["mu_agg_tok_s"],
                    mu_per_user_tok_s=r["mu_per_user_tok_s"], moved_stages=G.get("phys", {}).get("moved_stages"),
                    sm4_latency_cycles_charged=r.get("phys_sm4_latency_cycles_charged"))
    base_pt = dict(ar_tok_s=L5["ar_tok_s"], mtp_tok_s=hb["ds_mtp_tok_s"], mu_agg_tok_s=hb["mu_agg_tok_s"],
                   mu_per_user_tok_s=hb["mu_per_user_tok_s"])
    physd = dict(rule="the measured next-die terms run inside the static S2 schedule (hidden where off the critical "
                      "path): DIE f4c_t5 per-class relay stage delta on the D1 plan_b stage set + SM4 lane latency "
                      "+2 + 8 (lanes - 1) a SM record; 'f4c_t5_smhbm' moves only SM_HBM (no credit for the shorter "
                      "SM_X / VM_HUB)", d4g_class_stages=base_pt, **{ph: pv(ph) for ph in phys})
    physd["delta_vs_d4g_class_pct"] = {ph: {k: round(100.0 * (physd[ph][k] / base_pt[k] - 1.0), 2)
                                            for k in base_pt} for ph in phys}
    # cross-reference: the CMTP compiler-of-record re-time (rpl / union histogram / M1 rules) scaled by the PHYS ratio
    cm = None
    cmp_ = ROOT / "results/arch/hbm_next_1019/cmtp/retime/retime.json"
    if cmp_.exists():
        c = json.loads(cmp_.read_text())["cases"].get("CMTP P4 headline: + rpl (K-/row-split)")
        if c:
            f = {k: physd[HP][k] / base_pt[k] for k in base_pt}
            cm = dict(src=str(cmp_.relative_to(ROOT)), cmtp=dict(ar_tok_s=c["ar_tok_s"], mtp_tok_s=c["mtp"]["tok_s"],
                                                                 mu_agg_tok_s=c["mu"]["agg_tok_s"],
                                                                 mu_per_user_tok_s=c["mu"]["per_user_tok_s"]),
                      cmtp_x_phys=dict(ar_tok_s=round(c["ar_tok_s"] * f["ar_tok_s"], 1),
                                       mtp_tok_s=round(c["mtp"]["tok_s"] * f["mtp_tok_s"], 1),
                                       mu_agg_tok_s=round(c["mu"]["agg_tok_s"] * f["mu_agg_tok_s"], 1),
                                       mu_per_user_tok_s=round(c["mu"]["per_user_tok_s"] * f["mu_per_user_tok_s"], 1)),
                      note="CMTP adds the P = 4 compiler rules (rpl remainder pass, union histogram, M1 x-load / "
                           "publish) on the same D1 chain; the PHYS factor is VEH's (same point, f4c_t5 vs d4g-class)")
    out = dict(
        schema="opentallas.hbm_next_1019.veh.token_composition.v1", lane="HBM-NEXT-VEH", date="2026-10-19",
        physical_in_schedule=physd, cmtp_cross_reference=cm,
        rule=__doc__, clk_hz=CLK, tau_mtp=tau, targets=TARGETS,
        status="PRICED composition (D1 compiler chain, static S2 schedule) with the MEASURED unit terms in the schedule "
               "(HC II 250 hnx, COLL 3K/2, SM4 lane latency, DIE f4c_t5 stages); NO P = 4 layer measured in RTL yet",
        headline=dict(point=head, knobs="COLL L = 5 (adopted), HC row II 250 (MEASURED hnx), VM grown (>= 412k words, "
                                        "PROG 01:35), DIE f4c_t5 relay stages + SM4 lane latency in the schedule",
                      **ppoint(HP, "250", "grown")),
        d4g_reproduction=dict(model_self_check=g["self_check"], ar_repro=(json.loads(a.ar_repro.read_text())
                                                                          if a.ar_repro else None)),
        grid=table, hc_row_cost=dict(by_II_L5_grown=hc_cost, mu_step_cycles_per_II_cycle=round(slope, 1),
                                     ii_for_1000_per_user=round(ii_floor, 0) if ii_floor else None,
                                     mtp_step_cycles_per_II_cycle=round(mslope, 1),
                                     ii_for_mtp_target=round(ii_mtp, 0) if ii_mtp else None),
        fifth_coll_lane=dict(ar=[L4["ar_tok_s"], L5["ar_tok_s"]],
                             mtp_II600=[L4["II"]["600"]["VM"]["grown"]["ds_mtp_tok_s"], hp["ds_mtp_tok_s"]],
                             mu_agg_II600=[L4["II"]["600"]["VM"]["grown"]["mu_agg_tok_s"], hp["mu_agg_tok_s"]],
                             note="[L = 4, L = 5]"),
        inter_die=inter, ledger=LEDGER, per_layer_headline=per_layer,
        sources_sha256={str(p.relative_to(ROOT)): sha(p) for p in (D1_RUN, STUDY / "coll_lanes.json",
                                                                    STUDY / "hc_ii.json", STUDY / "vm_cap.json")})
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "token_composition.json").write_text(json.dumps(out, indent=1, default=str) + "\n")
    print(json.dumps(out["headline"]), json.dumps(out["hc_row_cost"]["ii_for_1000_per_user"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
