#!/usr/bin/env python3
"""Scenario C re-check (2026-10-04): reconcile the C S73 die ledger against Codex's S73/S82 screen, price the
levers that restore reticle margin, and re-price per-user rate, dies and power at the chosen stage count.

Model only, except `credit_rd_sweep` which is the measured directed RTL sweep (tools/dsrom_credit_rd_sweep.py).
Reads pinned records; writes only results/uarch/dsrom_c_recheck_20261004/model.json."""
import argparse, hashlib, json, math, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import dsrom_return_storage_hbm as B  # noqa: E402

C_REC = "results/uarch/dsrom_return_storage_hbm_20261003/model.json"
LEDGER = "results/uarch/dsrom_s73_pair1_20261003/baseline_s82_successor_r1/area_ledger.json"
MCAST = "results/uarch/dsrom_s73_pair1_20261003/baseline_s82_successor_r1/indexer_multicast_model.json"
S82P = "results/uarch/dsrom_s82_token_pricing_20261003/model.json"
OUT = "results/uarch/dsrom_c_recheck_20261004/model.json"
SWEEP = "results/uarch/dsrom_c_recheck_20261004/credit_rd_sweep.json"
RETICLE, MARGIN = 858.0, 0.02
PAIR_STAGES, BF_STAGES = 195750, 41984       # r4 census per rank chain (same constants as dsrom_s73_pair1_records.area)
W1_ADDER_PROXY_NP4096 = 3.158212608          # W1 046bf5026 model.json adder_proxy_mm2 at 8064 nodes
TAU, DRAFT = 3.649, 0.1173                   # inherited assumptions (not measured)
HEAD_TABLE_DIES = 44
LAYER_DIE_W, SERDES_W, HEAD_W, TABLE_W, STACK_IDLE_W = 50.196, 30.6, 738.5, 3324.4, 2.8
PG_RESIDUAL = 0.10                           # ASSUMED (scenario C W5)
DYN_J_AR = {"1048576": 0.1186, "200000": 0.1023}
SAT_TOK_S = 80833.5                          # head-bound saturated AR rate (unchanged by S)


def load(p):
    return json.loads((ROOT / p).read_text())


def return_options():
    nodes = lambda n: 2 * n - 128
    adders = lambda n: W1_ADDER_PROXY_NP4096 * nodes(n) / 8064
    return {
        "retained_NP4096_RD64": dict(
            f=lambda n: B.return_bits(4096) * B.MM2_PER_BIT, new_logic="none", status="Codex S82 baseline (W2 Arendt)"),
        "ragged_RD64": dict(
            f=lambda n: B.return_bits(n) * B.MM2_PER_BIT,
            new_logic="none in the node: unchanged ot_v41_retn_w17w10 nodes wired by the W1 ragged topology "
                      "(046bf5026 gen_dsrom_credit_return.topology, NP2682/R128 = 5236 nodes, 0 padding)",
            status="needs a ragged generator variant instantiating the reference node + golden reduction order of the ragged tree"),
        "credit_RD16_ragged": dict(
            f=lambda n: B.return_bits(n, RD=16, ROOTD=128, pair_buf=8) * B.MM2_PER_BIT + adders(n),
            new_logic="W1 ot_v41_ret_credit node at RD16 + 8-row pair buffer; W1 adder proxy charged (conservative: "
                      "the RD64 reservation excludes adders too)",
            status="directed RTL exact and zero added cycles (this record); L0/L20 program gate + ASAP7 synth pending"),
        "credit_RD8_ragged": dict(
            f=lambda n: B.return_bits(n, RD=8, ROOTD=128, pair_buf=8) * B.MM2_PER_BIT + adders(n),
            new_logic="as RD16 at RD8", status="directed RTL: 10.3% loss at saturation; 0 at 8-row/40-cycle rounds"),
    }


def build():
    led, crec, mc, s82 = load(LEDGER), load(C_REC), load(MCAST), load(S82P)
    terms = led["terms"]
    fixed = led["sensitivity"]["source_classified"]["S73"]["base_fixed_mm2"]
    var = led["sensitivity"]["source_classified"]["S73"]["base_variable_mm2"] / 2682

    def area(S, ret):
        n = math.ceil(PAIR_STAGES / S); bf = math.ceil(BF_STAGES / S); q = n - bf
        inc = sum(t["mm2"] * {"die": 1, "BF": bf / 362, "q": q / 1686, "sites": n / 2048, "removed": 0}[t["mode"]]
                  for t in terms)
        r = ret(n)
        tot = fixed + var * n + inc + r
        return dict(stages=S, pairs=n, fixed=round(fixed, 3), variable=round(var * n, 3), increments=round(inc, 3),
                    return_mm2=round(r, 3), die_mm2=round(tot, 3), margin_mm2=round(RETICLE - tot, 3),
                    margin_frac=round((RETICLE - tot) / RETICLE, 5))

    # self-check: reproduce Codex's screen exactly
    R = return_options()
    for S, key in ((69, "S69"), (73, "S73"), (82, "first_area_screen")):
        assert abs(area(S, R["retained_NP4096_RD64"]["f"])["die_mm2"]
                   - led["sensitivity"]["source_classified"][key]["screen_mm2"]) < 1e-3

    # ------------------------------------------------ (1) reconciliation at S73
    c73 = led["sensitivity"]["source_classified"]["S73"]
    codex_inc = sum(t["mm2"] for t in c73["increment_terms"])
    mine_ret = B.return_bits(2682, **B.CREDIT) * B.MM2_PER_BIT
    mine_die = crec["pair1_staging"]["rows"]["trim_credit"]["conservative"]["die_mm2"]
    mine_var_inc = mine_die - fixed - mine_ret
    recon = dict(
        S=73, pairs=2682,
        scenario_C=dict(die_mm2=mine_die, fixed=round(fixed, 2), variable_plus_increments=round(mine_var_inc, 2),
                        return_mm2=round(mine_ret, 2),
                        return_basis="credit RD4/ROOTD128/pair_buf8 at ragged NP2682 (storage only)",
                        increments_basis="all 64.55 mm2 post-r4 increments scaled with pairs (2*64.55/4096 per site)"),
        codex_S73=dict(die_mm2=round(c73["screen_mm2"], 2), fixed=round(c73["base_fixed_mm2"], 2),
                       variable_plus_increments=round(c73["base_variable_mm2"] + codex_inc, 2),
                       variable=round(c73["base_variable_mm2"], 2), increments=round(codex_inc, 2),
                       return_mm2=round(c73["retained_return_FF50_reservation_mm2"], 2),
                       return_basis="retained NP4096/R128/RD64 FF50 reservation; 1708 unused return inputs"),
        line_items=[
            dict(item="fixed debit (418.27 inherited + 47.21 residual)", scenario_C=465.48, codex=465.48, delta=0.0,
                 applied="identical; legacy-complement removal (287.02) NOT applied in either (complement_credit_mm2=0)"),
            dict(item="variable per-pair (frames+cfg+RNE+WAKE+re-frame) x pairs", scenario_C=None,
                 codex=round(c73["base_variable_mm2"], 2), delta=None,
                 applied="padding trim APPLIED in both: variable scales with 2682 active pairs, not 4096 sites"),
            dict(item="post-r4 increments (64.55 at reference)", scenario_C=None, codex=round(codex_inc, 2), delta=None,
                 applied="Codex prices 25 terms by class (die/BF/q/sites) and removes the PAR2 corridor 4.32"),
            dict(item="variable + increments", scenario_C=round(mine_var_inc, 2),
                 codex=round(c73["base_variable_mm2"] + codex_inc, 2),
                 delta=round(c73["base_variable_mm2"] + codex_inc - mine_var_inc, 2),
                 applied="Codex is 6.2 mm2 SMALLER: per-die terms not scaled and PAR2 corridor removed"),
            dict(item="return storage", scenario_C=round(mine_ret, 2),
                 codex=round(c73["retained_return_FF50_reservation_mm2"], 2),
                 delta=round(c73["retained_return_FF50_reservation_mm2"] - mine_ret, 2),
                 applied="credit shrink NOT applied (W1 RD4 REJECTED, measured 9-cycle slot reuse, 54.1% saturated "
                         "loss) AND return padding trim NOT applied (NP4096 storage kept for 2682 pairs)"),
        ],
        total_delta_mm2=round(c73["screen_mm2"] - mine_die, 2),
        reading="The entire 41.7 mm2 gap is the return tree: +47.9 return (RD4 credit -> retained RD64 at NP4096) "
                "-6.2 from Codex's finer increment classification. Of the +47.9, 18.0 is the untrimmed return "
                "padding (NP4096 vs ragged NP2682 at RD64) and 29.9 is credit depth (RD64 vs RD4). Padding trim of "
                "the field and complement non-removal are the same in both ledgers.")

    # ------------------------------------------------ (2) levers
    sweep = load(SWEEP)
    by = {(c["RD"], c["MODE"], c["PER"], c["SKEW"]): c for c in sweep["cases"]}
    rd_summary = {}
    for rd in (4, 8, 16, 32):
        legal = [c for c in sweep["cases"] if c["RD"] == rd and c.get("reference_fault") == 0]
        rd_summary[f"RD{rd}"] = dict(
            saturated_fixture_rate_loss=round(by[(rd, 0, 40, 0)]["rate_loss"], 4),
            program_rounds_8rows_per_40cyc_max_loss=round(max(c["rate_loss"] for c in legal if c["PER"] == 40 and c["MODE"] == 1), 4),
            max_added_row_cycles_reference_legal=max(c["row_delay_max"] for c in legal),
            exact_cases=sum(c["status"] == "PASS_EXACT" for c in sweep["cases"] if c["RD"] == rd),
            credit_faults=0,
            reference_overflow_cases_credit_fault_free=sum(c["status"].startswith("PASS_CREDIT_NO_FAULT")
                                                           for c in sweep["cases"] if c["RD"] == rd))
    target = RETICLE * (1 - MARGIN)
    table = {k: {S: area(S, v["f"]) for S in range(66, 85)} for k, v in R.items()}
    first_fit = {k: next((S for S in range(66, 85) if t[S]["die_mm2"] <= target), None) for k, t in table.items()}
    first_screen = {k: next((S for S in range(66, 85) if t[S]["die_mm2"] <= RETICLE), None) for k, t in table.items()}
    hop = crec["baseline_at_model"]["hop_us"]
    mc_par, mc_sh = mc["additional_token_us_lower"], mc["additional_token_us_shared_link"]
    levers = [
        dict(lever="L1 ragged RD64 return (trim the return's padding: NP=active pairs)",
             area_mm2_at_S73=round(table["ragged_RD64"][73]["die_mm2"] - table["retained_NP4096_RD64"][73]["die_mm2"], 2),
             per_user_us=0.0, first_S_2pct=first_fit["ragged_RD64"], exact="same node RTL; ragged tree golden order (W1 NP5 ragged golden PASS)",
             label="model area; topology from W1 RTL generator"),
        dict(lever="L2 credit RD16 ragged return (replaces L1)",
             area_mm2_at_S73=round(table["credit_RD16_ragged"][73]["die_mm2"] - table["retained_NP4096_RD64"][73]["die_mm2"], 2),
             per_user_us=0.0, first_S_2pct=first_fit["credit_RD16_ragged"],
             exact="directed RTL exact vs RD64 reference, zero added cycles in every reference-legal case (measured)",
             label="area model (FF50 proxy + W1 adder proxy); rate measured directed, L0/L20 pending"),
        dict(lever="L2b credit RD8 ragged return",
             area_mm2_at_S73=round(table["credit_RD8_ragged"][73]["die_mm2"] - table["retained_NP4096_RD64"][73]["die_mm2"], 2),
             per_user_us=None, first_S_2pct=first_fit["credit_RD8_ragged"],
             exact="exact; 10.3% loss at saturation (measured directed), 0 at 8-row/40-cycle rounds",
             label="REJECT as baseline: saturation loss >1% unless L0/L20 proves rounds never saturate"),
        dict(lever="L3 one stage fewer (any return)", area_mm2_at_S73=None,
             per_user_us=round(-hop, 4), dies=-4, label="model: 0.482 us/hop, ~4.6-5.2 mm2/die per stage near S73-S82"),
        dict(lever="L4 replicate TP-unsharded indexer projections on all 4 ranks (undo canonical-owner multicast)",
             area_mm2_at_S73=0.0, per_user_us=round(-mc_par, 3), per_user_us_shared_link=round(-mc_sh, 3),
             exact="identical weights, identical inputs (x and the all-gathered q latent are on every rank), identical "
                   "pair layout and tree => bit-identical; no new collective",
             label="model; the screen never credited the dedup (frame_credit_mm2=0, reserved_frames_credit_mm2=0): the "
                   "replica pairs are already inside n=ceil(195750/S)",
             note="The 20 deduplicated records (indexer.wk/wq_b) cost 29.48 us (parallel ports) to 85.37 us (one "
                  "shared link) a token in the S82 pricing; C never had this term. The W2 gate 'every shipped "
                  "weight placed exactly once' meant coverage, not a ban on TP replication."),
        dict(lever="L5 HBM PHY credit on one-stack dies (W3) / legacy-complement removal (W4)",
             area_mm2_at_S73=-30.0, per_user_us=0.0,
             label="NOT ADOPTABLE: the PHYs are not among W4's 131.25 mm2 named rectangles, so any PHY credit is "
                   "part of the unmapped 287.02 complement; scan dies keep 4 PHYs and bind; upside only"),
    ]
    s73_reach = dict(
        best_adoptable_at_S73=table["credit_RD16_ragged"][73],
        needed_for_2pct_mm2=round(table["credit_RD16_ragged"][73]["die_mm2"] - target, 2),
        reading="No adoptable lever set reaches S73 with 2% margin: credit RD16 + ragged return lands S73 at "
                "857.9 mm2 (0.01% margin); 17.1 mm2 more is needed and only the unproven PHY/complement credit "
                "(L5) supplies it. S <= 73 is an upside gated on W4 rectangles.")

    # ------------------------------------------------ (3) re-price
    m0 = crec["baseline_at_model"]
    def price(S, mcast_us, reps=1):
        out = {}
        for ctx in ("1048576", "200000"):
            ar0 = 1e6 / m0["m0_ar"][ctx]
            v0 = TAU * 1e6 / m0["m0_mtp"][ctx] - DRAFT * ar0
            ar = ar0 + (S - 58) * hop + mcast_us
            step = v0 + (S - 58) * hop + reps * mcast_us + DRAFT * ar
            out[ctx] = dict(AR_us=round(ar, 3), AR_tok_s=round(1e6 / ar, 1), MTP_step_us=round(step, 3),
                            MTP_tok_s=round(TAU * 1e6 / step, 1))
        return out
    # the price formula must reproduce the committed S82 record
    for sc in s82["scenarios"]:
        if sc["link_assumption"] == "parallel_ports" and sc["verify_multicast_repetitions_assumed"] == 1:
            p = price(82, mc_par)[sc["context"]]
            assert abs(p["AR_us"] - sc["conditional_AR_us"]) < 1e-3 and abs(p["MTP_step_us"] - sc["conditional_MTP_step_us"]) < 1e-3

    def system(S, rate_ar):
        layer = 4 * S; stacks = 4 * S + 128
        static = layer * LAYER_DIE_W + HEAD_W + TABLE_W + stacks * STACK_IDLE_W
        f = 2 / S
        pg = layer * LAYER_DIE_W * (f + (1 - f) * PG_RESIDUAL) + HEAD_W + TABLE_W + stacks * STACK_IDLE_W
        res = dict(stages=S, layer_dies=layer, total_dies=layer + HEAD_TABLE_DIES, packages=(layer + HEAD_TABLE_DIES) // 2,
                   stacks_ASSUMED_W3_rule=stacks, static_kW_icg=round(static / 1e3, 2), static_kW_b1_pg=round(pg / 1e3, 2))
        for ctx in ("1048576", "200000"):
            r = rate_ar[ctx]["AR_tok_s"]
            res[ctx] = dict(b1_AR_tok_s_per_kW_pg=round(r / ((pg + r * DYN_J_AR[ctx]) / 1e3), 1),
                            b1_AR_tok_s_per_kW_icg=round(r / ((static + r * DYN_J_AR[ctx]) / 1e3), 1),
                            best_batch_tok_s_per_kW_icg=round(SAT_TOK_S / ((static + SAT_TOK_S * DYN_J_AR[ctx]) / 1e3), 1))
        return res

    cands = {
        "S82_codex_retained_multicast_parallel": (82, "retained_NP4096_RD64", mc_par),
        "S82_codex_retained_multicast_shared": (82, "retained_NP4096_RD64", mc_sh),
        "S81_ragged_RD64_replicated": (81, "ragged_RD64", 0.0),
        "S77_credit_RD16_replicated": (77, "credit_RD16_ragged", 0.0),
        "S73_scenario_C_as_handed_off_INFEASIBLE": (73, "credit_RD16_ragged", 0.0),
    }
    priced = {}
    for k, (S, ret, m) in cands.items():
        p = price(S, m)
        priced[k] = dict(area=table[ret][S], return_option=ret, indexer_multicast_us=round(m, 3), rate=p, system=system(S, p),
                         wavefront_verify="PENDING separate factor (another agent measuring); not applied")
    base = priced["S82_codex_retained_multicast_parallel"]["rate"]["1048576"]["AR_tok_s"]
    for k in priced:
        priced[k]["AR_1M_vs_S82_parallel"] = round(priced[k]["rate"]["1048576"]["AR_tok_s"] / base - 1, 4)
    credit_gain = priced["S77_credit_RD16_replicated"]["rate"]["1048576"]["AR_tok_s"] / \
        priced["S81_ragged_RD64_replicated"]["rate"]["1048576"]["AR_tok_s"] - 1
    decision = dict(
        build="S81: ragged RD64 return (reference nodes on the W1 ragged topology, NP=2417 active pairs) + indexer "
              "projections replicated on all four ranks (no canonical-owner multicast)",
        area=table["ragged_RD64"][81],
        why=["S82 retained is 856.54 mm2 (0.17% margin): not a safe design point",
             "S81 ragged RD64 is 839.24 mm2 (2.19% margin) with no new flow-control logic and no rate cost",
             "replication removes 29.48-85.37 us a token at zero screened area; it is the largest per-user lever "
             "(+7.4% AR at 1M vs S82 parallel ports, +21.2% vs one shared link)",
             "S73 is not reachable at 2% margin by any adoptable lever (needs the W4/PHY credit)"],
        credit_RD16=dict(
            verdict="REJECT as the baseline under the owner rule: per-user gain after composition +%.2f%% (<1%%)" % (100 * credit_gain),
            numbers=dict(S=77, die_mm2=table["credit_RD16_ragged"][77]["die_mm2"], dies_saved_vs_S81=16,
                         static_kW_saved_icg=round(priced["S81_ragged_RD64_replicated"]["system"]["static_kW_icg"]
                                                   - priced["S77_credit_RD16_replicated"]["system"]["static_kW_icg"], 2)),
            reopen_if="the owner values -16 dies / -0.8 kW static over per-user rate; then it needs the L0/L20 "
                      "occupancy gate and ASAP7 synth of the RD16 node before adoption"),
        upside="S73 (or lower) only after W4 replaces the 287.02 mm2 complement with explicit rectangles that free "
               ">= 17.1 mm2 on scan dies",
    )
    return dict(
        schema="opentallas.dsrom.scenario-c.recheck.v1", date="2026-10-04",
        label="MODEL except credit_rd_sweep (MEASURED directed RTL, Icarus)",
        reticle_mm2=RETICLE, margin_target_frac=MARGIN, margin_target_die_mm2=round(target, 2),
        reconciliation_S73=recon, credit_rd_sweep=dict(record=SWEEP, summary=rd_summary,
            reading="RD >= 16 (next power of two above the measured 9-cycle slot-reuse loop) removes the W1 loss: "
                    "0 added cycles, exact, at saturation and at program-shaped rounds. Sibling skew > WAIT (2) "
                    "overflows the RD64 reference itself (fault); the credit tree stalls fault-free there, so such "
                    "traffic is outside the legal envelope of today's design, not a credit regression."),
        return_screen={k: {str(S): v for S, v in t.items()} for k, t in table.items()},
        first_S_at_reticle=first_screen, first_S_at_2pct_margin=first_fit,
        levers=levers, S73_reach=s73_reach, priced=priced, decision=decision,
        pending=["wavefront verify factor (separate agent)", "L0/L20 program occupancy for any credit depth",
                 "ragged RD64 generator + golden order", "indexer replication RTL (local issue on ranks 1-3)",
                 "W3 stack allocation (420-style rule ASSUMED here)", "physical containment/route at S81"],
        input_sha256={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in (C_REC, LEDGER, MCAST, S82P, SWEEP)},
        tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        pinned_originals_changed=False)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    payload = json.dumps(build(), indent=1, sort_keys=True) + "\n"
    if a.verify:
        assert (ROOT / OUT).read_text() == payload, "record drift"
        print("PASS verify")
    else:
        (ROOT / OUT).parent.mkdir(parents=True, exist_ok=True)
        (ROOT / OUT).write_text(payload)
        print("wrote", OUT)
