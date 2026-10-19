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
    dict(term="ATT KV-line-stationary 4-query union stream (E1 exactness)",
         priced="U(N)/U(1) KV union price, top-512 disjoint upper bound (headline)",
         measured="E1 PASS: ascending union with per-lane masks is bit-exact per lane (reduced ckpt 40 L, N = 6: "
                  "0 mismatches); cycles NOT measured",
         src="results/arch/hbm_next_1019/att4/E1.md", delta="aligned 20-SM grouping = 1.17x model upper; balanced "
         "32-SM (lane, run) assignment needed (CMTP)", status="EXACTNESS ONLY"),
    dict(term="HC.HC_MIX further-row II", priced="250 (HCP W256 x6 mode, measured (1,578 - 328) / 5)",
         measured="static HC engine (codex/hc-static-engine-1014 a35449ada) 4,385 a further row; 9,554 one row vs "
                  "1,160 priced", src="tools/hgi_sim/ds_mtp_verify.py:151,184; results/arch/hbm_next_1019/runs/hc_ii.json",
         delta="grid axis II in {250, 600, 950, 4385, per-position fallback}; next-die gate = II <= 950 (target 600)",
         status="UNITS gate #1 OPEN (no N-row HC RTL yet)"),
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
    head = "L5|II600|grown"
    hp = grid["5"]["II"]["600"]["VM"]["grown"]

    # per-layer composition at the headline point (priced; measured column filled by the vehicle)
    def layers(ar_seg, mtp_seg, mu_seg):
        rows = []
        for k in ar_seg:
            rows.append(dict(segment=k, representative=REPRESENTATIVE.get(k), ar_priced=ar_seg[k],
                             mtp_verify_priced=mtp_seg[k], mu4_priced=mu_seg[k], ar_measured=None,
                             mtp_verify_measured=None, mu4_measured=None,
                             d4g_ar_priced=d1["ds|AR"]["per_segment"][k]))
        return rows
    per_layer = layers(L5["ar_per_segment"], hp["mtp_per_segment"], hp["mu_per_segment"])

    # inter-die traffic: COLL busy share and the fixed part per collective
    fcoll = 108.6 + 377.6e-9 * CLK + 0.15e-6 * CLK
    inter = dict(
        dies=192, switch_tiers=1, crossing_ns=377.6, coll_fixed_cycles=round(fcoll, 1),
        coll_lanes=5, coll_bytes_per_cycle=5 * 64,
        coll_busy_share=dict(ar=round(L5["ar_unit_busy"]["COLL"] / L5["ar_cycles"], 3),
                             mtp_verify=round(hp["mtp_unit_busy"]["COLL"] / hp["mtp_verify_cycles"], 3),
                             mu4=round(hp["mu_unit_busy"]["COLL"] / hp["mu_step_cycles"], 3)),
        serdes_note="STUDY (a): at P = 4 MU, COLL busy x full 256 B/cycle <= 34 % of the 400 GB/s raw SerDes; L = 5 "
                    "(320 B/cycle = 384 GB/s) is the widest the SerDes feeds; the network is not the ceiling")
    hc_cost = {ii: dict(mtp_tok_s=grid["5"]["II"][ii]["VM"]["grown"]["ds_mtp_tok_s"],
                        mu_per_user_tok_s=grid["5"]["II"][ii]["VM"]["grown"]["mu_per_user_tok_s"],
                        mu_agg_tok_s=grid["5"]["II"][ii]["VM"]["grown"]["mu_agg_tok_s"],
                        hc_busy_mu=grid["5"]["II"][ii]["VM"]["grown"]["mu_unit_busy"].get("HC"))
               for ii in grid["5"]["II"]}
    # per-user rate vs II slope (L5, grown) between 600 and 950 -> the II that holds 1,000 tok/s a user
    s600, s950 = (grid["5"]["II"][x]["VM"]["grown"]["mu_step_cycles"] for x in ("600", "950"))
    slope = (s950 - s600) / 350.0
    ii_floor = 600 + (CLK / 1000.0 - s600) / slope if slope > 0 else None
    # MTP step vs II (L5, grown) between 250 and 600 -> the II that still meets the MTP target
    m250, m600 = (grid["5"]["II"][x]["VM"]["grown"]["mtp_step_cycles"] for x in ("250", "600"))
    mslope = (m600 - m250) / 350.0
    ii_mtp = 250 + (tau * CLK / TARGETS["ds_mtp"] - m250) / mslope if mslope > 0 else None
    # physical latency adders of the P = 4 die not in the D1 model: paid once a record on the record's first access.
    # Bounds: 0 (hidden under the record's own stream / interleaved chains) .. every record serial on the critical path.
    adders = [dict(term="SM_HBM link 2.88 -> 5.25 bit-weighted relay stages (DIE f4c_t5, results/arch/hbm_next_1019/"
                        "die/README.md; PROG 10-19 00:21)", cycles_per_record=round((5.25 - 2.88) / 2, 3),
                   note="half-cycle forwarded hops: +2.37 stages = +1.19 cycles a SM record"),
              dict(term="SM4 registered per-lane-group weight broadcast tree at P >= 4 (sm_area README)",
                   cycles_per_record=1.0, note="+1 cycle a SM record; also paid by AR unless the P = 1 path bypasses it")]
    per_rec = sum(x["cycles_per_record"] for x in adders)
    recs = dict(ar=d1["ds|AR"]["records"], mtp_verify=d1["ds|MTP|P4"]["records"], mu4=d1["ds|MU|P4"]["records"])
    base = dict(ar=L5["ar_cycles"], mtp_step=hp["mtp_step_cycles"], mu4=hp["mu_step_cycles"])
    upper = {k: base[k if k != "mtp_step" else "mtp_step"] + per_rec * recs["mtp_verify" if k == "mtp_step" else k]
             for k in base}
    phys = dict(adders=adders, cycles_per_record=per_rec, records_upper_bound=recs,
                rule="upper bound = every record (not only SM) serial on the critical path; lower bound = 0",
                headline_bounds=dict(
                    ar_tok_s=[tok(upper["ar"]), tok(base["ar"])],
                    mtp_tok_s=[round(tau * CLK / upper["mtp_step"], 1), round(tau * CLK / base["mtp_step"], 1)],
                    mu_agg_tok_s=[tok(upper["mu4"], 4), tok(base["mu4"], 4)],
                    mu_per_user_tok_s=[tok(upper["mu4"]), tok(base["mu4"])]))
    out = dict(
        schema="opentallas.hbm_next_1019.veh.token_composition.v1", lane="HBM-NEXT-VEH", date="2026-10-19",
        physical_adders=phys,
        rule=__doc__, clk_hz=CLK, tau_mtp=tau, targets=TARGETS,
        status="PRICED composition with measured unit terms; NO layer measured in RTL yet (vehicle runs pending)",
        headline=dict(point=head, knobs="COLL L = 5 (adopted), HC row II 600 (target, UNITS gate), VM grown",
                      **point(5, "600", "grown")),
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
