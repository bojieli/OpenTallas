#!/usr/bin/env python3
"""QC-MP-REGION-2 OPTION A / B preparation (plan analysis only, nothing is built).

Reads a region_clock run (region_plan.json: seam pair rows with the last common clock node and the modelled
non-common clock per side) and the master-plan path census (master_plan.json paths + roads.json partition legs) and
writes, per seam (abutting partition pair):
  * the last common clock node + class (die_root / lattice / region_root / region_node);
  * the bits crossing it per direction (every die path src -> [road partitions] -> dst, consecutive partitions);
  * the flat-OCV setup / hold pessimism (region_clock.nc_estimate, die_ci_margins.json) against the plain related-pair
    budget of a zero-logic pin-register pair from die_ci_margins.json lib + the shared sign-off uncertainty (OWNER 12.24c
    nominal: setup 0, hold 25; sdc_lint.policy_uncertainty):
      setup TT = 833 - 0 - clk_q_max - setup - xtalk_setup ; hold FF = clk_q_min - hold - 25 - xtalk_hold
    (data wire delay between the two pin registers ignored: a few ps, favourable to hold);
  * OPTION A: every seam of class die_root / lattice becomes a landed/forwarded hop (registered both sides, fixed
    static latency, no credits: the existing QC landing ring, +LAND_CYCLES per crossing);  per die path the number of
    landed crossings and the added cycles;
  * OPTION B: predicted insertion and residual pessimism per class for stronger drive / fewer levels / per-quadrant
    die inputs (estimates from the same stage model, UNCHECKED).
"""
import argparse
import json
import math
import sys
from collections import defaultdict, Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import region_clock as RC  # noqa: E402

# landed/forwarded crossing latency: QC landing ring component gate (codex/qc-landing-1026, handoff 10-26: W32
# full-word/epoch ring, source -> receiver 4 cycles vs original 1 at zero phase => +3, phases 0..750 ps).  The
# one-edge QC ledger priced +2 / +3 per edge (+72 / +108 cycles per token on v7 baseline 296341).
LAND_CYCLES = 3
LAND_CYCLES_LOW = 2
from die_sta import PERIOD_PS as PERIOD  # exact canonical timing policy


def budgets(margins, policy=None):
    """planner estimate of the zero-logic seam pair budget; uncertainty = the shared sign-off policy (OWNER 12.24c
    nominal setup 0 / hold 25; OT_MARGIN_POLICY=legacy = 60 / 25 for A/B)."""
    import sdc_lint
    unc_s, unc_h = sdc_lint.policy_uncertainty(policy)
    lib = margins["lib"]
    xt = margins["derived"]["xtalk_default"]
    setup = PERIOD - unc_s - lib["TT"]["clk_q_max_ps"] - lib["TT"]["setup_ps"] - xt["setup_ps"]
    hold = lib["FF"]["clk_q_min_ps"] - lib["FF"]["hold_ps"] - unc_h - xt["hold_ps"]
    return dict(setup_tt_ps=round(setup, 2), hold_ff_ps=round(hold, 2), unc_setup_ps=unc_s, unc_hold_ps=unc_h,
                basis=f"zero-logic pin-register seam pair, DFFHQNx1 (die_ci_margins.json lib), {unc_s:g}/{unc_h:g} ps "
                      "uncertainty (sdc_lint sign-off policy, OWNER 12.24c), xtalk_default; data wire delay ignored")


def part_seq(path, roads_by):
    seq = [path["src"].split(".")[0]]
    for r in roads_by.get(path["id"], []):
        seq.append(r["part"])
    seq.append(path["dst"].split(".")[0])
    out = [seq[0]]
    for p in seq[1:]:
        if p != out[-1]:
            out.append(p)
    return out


def option_b(rp, rows):
    """OPTION B estimates (UNCHECKED, stage model only): insertion and residual flat-OCV pessimism per seam class."""
    R = rp["region_distribution"]
    dp = rp["die_path"]
    tr = rp["trunk"]
    lat = rp["lattice_leaf_model"]
    ins_tt = dp["TT"]["input_to_entry_ps"]["max"]
    ins_ff = dp["FF"]["input_to_entry_ps"]["max"]
    root_in = tr["die_input_um"]
    far = max(RC.md(root_in, e["xy_um"]) for e in R["entries"])
    bound_tt = RC.stage_delay(far, RC.n_min(far), "TT")
    # stage count die input -> entry: trunk + lattice (n_min per lattice leg, from the leaf model) + region legs
    par = {lg["tag"]: lg for lg in R["legs"]}
    ent = {lg["part"]: lg for lg in R["legs"] if lg["to"] == "entry"}
    lat_tt = max(v["TT"] for v in lat.values())
    trunk_tt = RC.stage_delay(tr["len_um"], tr["n_seg"], "TT")
    d0, k = RC.STAGE["TT"]
    full = d0 + k * RC.REP_UM
    lat_stages = round((lat_tt - trunk_tt) / full)            # lattice legs run full 450 um stages (approx.)
    reg_st = []
    for part, lg in ent.items():
        n, t = 0, lg["tag"]
        while t in par:
            n += par[t]["n_seg"]
            t = par[t]["parent"]
        reg_st.append(n)
    stages = dict(trunk=tr["n_seg"], lattice_approx=lat_stages, region_min=min(reg_st), region_max=max(reg_st),
                  core_tree="8-14 (die_ci_margins.json ocv.why)",
                  die_total_min=tr["n_seg"] + lat_stages + min(reg_st), die_total_max=tr["n_seg"] + lat_stages + max(reg_st))
    fc = {c: RC.STAGE[c][0] / (RC.STAGE[c][0] + RC.STAGE[c][1] * RC.REP_UM) for c in ("TT", "FF")}
    pf = {c: fc[c] * (RC.DERATE["cell_late"] + RC.DERATE["ir_late"] + RC.DERATE["cell_early"]) +
          (1 - fc[c]) * (RC.DERATE["net_late"] + RC.DERATE["net_early"]) for c in ("TT", "FF")}
    cls = defaultdict(list)
    for r in rows.values():
        cls[r["common_level"]].append(r)

    def resid(scale_die, core=RC.CORE_LAT):
        out = {}
        for c_, v in sorted(cls.items()):
            nc_tt = max(x["TT"]["noncommon_ps"] for x in v)
            nc_ff = max(x["FF"]["noncommon_ps"] for x in v)
            die_tt, die_ff = nc_tt - core["TT"], nc_ff - core["FF"]
            out[c_] = dict(setup_pess_tt_ps=round(pf["TT"] * (die_tt * scale_die + core["TT"]), 1),
                           hold_pess_ff_ps=round(pf["FF"] * (die_ff * scale_die + core["FF"]), 1))
        return out
    # lattice depth of each seam's common node (tag 't' + bits); per-quadrant inputs feed the depth-2 nodes
    meso_q = sum(1 for r in rows.values() if r["common_level"] in ("die_root",) or
                 (r["common_level"] == "lattice" and len(r["common"]) - 1 < 2))
    meso_16 = sum(1 for r in rows.values() if r["common_level"] in ("die_root", "lattice"))
    q_lat = [v for t_, v in lat.items()]
    return dict(
        note="estimates from the region_clock stage model (UNCHECKED); pessimism = flat OCV of die_ci_margins.json on "
             "the non-common delay (cell share %.2f TT); CPPR removes only the common part, so a shorter tree ABOVE the "
             "last common node changes insertion but not a seam's pessimism" % fc["TT"],
        current=dict(insertion_tt_ps=ins_tt, insertion_ff_ps=ins_ff, stages=stages),
        B1_stronger_drive=dict(
            what="2x BUFx24 per stage (BUFx24 is the largest ASAP7 buffer) or wider/2W shielded M9: per-stage delay "
                 "-10..-20 % (assumed, not calibrated)",
            insertion_tt_ps=[round(ins_tt * 0.8, 0), round(ins_tt * 0.9, 0)],
            residual_pessimism_at_minus20pct=resid(0.8), residual_pessimism_at_minus10pct=resid(0.9)),
        B2_fewer_levels=dict(
            what="no zig-zag / no padding: die input -> farthest entry at the Manhattan radius %.0f um with n_min "
                 "stages (lower bound of any single-input tree)" % far,
            insertion_tt_ps=round(bound_tt, 0), scale_vs_current=round(bound_tt / ins_tt, 3),
            residual_pessimism=resid(bound_tt / ins_tt)),
        B3_per_quadrant_inputs=dict(
            what="4 package clock inputs at the depth-2 lattice nodes (quadrant roots); insertion = quadrant root -> "
                 "entry",
            insertion_tt_ps=round(ins_tt - (min(v["TT"] for v in q_lat) - (lat_tt - (lat_tt - trunk_tt) / 2.0)), 0),
            mesochronous_seams=meso_q,
            residual_pessimism_intra_quadrant="unchanged (CPPR already removes the shared part above the common node)",
            mesochronous="YES: the 4 inputs share no on-die node; their package/PLL distribution skew is "
                         "uncontrolled and non-common, so every seam whose common node was the die root or a depth-1 "
                         "lattice node becomes mesochronous and needs a landed hop anyway"),
        B3b_per_region_inputs=dict(
            what="16 inputs at the lattice leaves; insertion = region only",
            insertion_tt_ps=round(ins_tt - lat_tt, 0), mesochronous_seams=meso_16,
            mesochronous="YES: all die_root + lattice seams (= the OPTION A set) become mesochronous -> landing"),
    )


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--region-plan", required=True, help="region_clock region_plan.json")
    ap.add_argument("--master-plan", required=True, help="master_plan.json (paths census)")
    ap.add_argument("--roads", required=True, help="roads.json (partition legs per path)")
    ap.add_argument("--margins", default=str(HERE / "die_ci_margins.json"))
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    rp = json.loads(Path(a.region_plan).read_text())
    mp = json.loads(Path(a.master_plan).read_text())
    roads = json.loads(Path(a.roads).read_text())["roads"]
    margins = json.loads(Path(a.margins).read_text())
    B = budgets(margins)
    roads_by = defaultdict(list)
    for r in roads:
        roads_by[r["path"]].append(r)
    rows = {tuple(sorted((r["a"], r["b"]))): r for r in rp["pair_rows"]}
    classA = {k for k, r in rows.items() if r["common_level"] in ("die_root", "lattice")}
    # bits per seam per direction
    bits = defaultdict(lambda: [0, 0])
    npaths = Counter()
    nonabut = Counter()
    per_path = []
    for p in mp["paths"]:
        seq = part_seq(p, roads_by)
        kA = 0
        for u, v in zip(seq, seq[1:]):
            k = tuple(sorted((u, v)))
            if k not in rows:
                nonabut[k] += p["bits"]
                continue
            bits[k][0 if (u, v) == k else 1] += p["bits"]
            npaths[k] += 1
            if k in classA:
                kA += 1
        per_path.append(dict(id=p["id"], kind=p.get("kind"), bits=p["bits"], parts=len(seq), landed_A=kA,
                             added_cycles=LAND_CYCLES * kA))
    seams = []
    for k, r in sorted(rows.items(), key=lambda kv: (kv[1]["common_level"], kv[0])):
        b = bits.get(k, [0, 0])
        seams.append(dict(a=k[0], b=k[1], edge_um=r["edge_um"], common=r["common"], cls=r["common_level"],
                          bits_ab=b[0], bits_ba=b[1], paths=npaths.get(k, 0),
                          nc_tt_ps=r["TT"]["noncommon_ps"], setup_pess_tt_ps=r["TT"]["ocv_pessimism_ps"],
                          nc_ff_ps=r["FF"]["noncommon_ps"], hold_pess_ff_ps=r["FF"]["ocv_pessimism_ps"],
                          plain_setup_ok=r["TT"]["ocv_pessimism_ps"] <= B["setup_tt_ps"],
                          plain_hold_ok=r["FF"]["ocv_pessimism_ps"] <= B["hold_ff_ps"],
                          option_a=("landed" if k in classA else "plain")))
    by_cls = defaultdict(list)
    for s_ in seams:
        by_cls[s_["cls"]].append(s_)
    cls_sum = {}
    for c, v in sorted(by_cls.items()):
        cls_sum[c] = dict(seams=len(v), with_traffic=sum(1 for x in v if x["bits_ab"] + x["bits_ba"]),
                          bits=sum(x["bits_ab"] + x["bits_ba"] for x in v),
                          setup_pess_tt_max=max(x["setup_pess_tt_ps"] for x in v),
                          hold_pess_ff_min=min(x["hold_pess_ff_ps"] for x in v),
                          hold_pess_ff_max=max(x["hold_pess_ff_ps"] for x in v),
                          plain_setup_fail=sum(1 for x in v if not x["plain_setup_ok"]),
                          plain_hold_fail=sum(1 for x in v if not x["plain_hold_ok"]))
    kdist = Counter(p["landed_A"] for p in per_path)
    kbits = Counter()
    for p in per_path:
        kbits[p["landed_A"]] += p["bits"]
    A_seams = [s_ for s_ in seams if s_["option_a"] == "landed"]
    optA = dict(rule="landed/forwarded hop on every seam whose last common clock node is the die root or a lattice "
                     "node (owner 10-16/10-18 landed-regions standard: registered both sides, fixed static latency, no "
                     "credits); balanced trees inside each lattice region (region_clock --region-only: no die-wide "
                     "padding)",
                land_cycles=LAND_CYCLES, land_cycles_basis="QC landing ring component gate +3 (codex/qc-landing-1026 "
                "handoff, UNCHECKED here); +2 = the one-edge ledger's low case",
                seams=len(A_seams), seams_with_traffic=sum(1 for x in A_seams if x["bits_ab"] + x["bits_ba"]),
                bits=sum(x["bits_ab"] + x["bits_ba"] for x in A_seams),
                ring_ff_bound=dict(depth=4, note="4-slot ring per landed bit: ~4 x bits storage FF + read reg (ring "
                                   "inventory: codex canonical rings 86320 FF for 65 data + 5 monitor rings)"),
                paths_by_landed_crossings={str(k): dict(paths=v, bits=kbits[k], added_cycles=LAND_CYCLES * k)
                                           for k, v in sorted(kdist.items())},
                max_added_cycles_per_path=LAND_CYCLES * max(kdist),
                per_layer_note="per-layer delta = LAND_CYCLES x (landed crossings on the layer's serial critical "
                               "chain); the chain is TOK-QK's (QCLM per-layer DAG); paths_by_landed_crossings gives "
                               "the per-path counts to compose")
    # path families (numbers -> #): max landed crossings, for TOK-QK to map onto the per-layer chain
    import re
    fam = defaultdict(Counter)
    for p in per_path:
        fam[re.sub(r"[0-9]+", "#", p["id"])][p["landed_A"]] += 1
    optA["families_with_landing"] = {k: dict(sorted(v.items())) for k, v in sorted(fam.items()) if max(v) > 0}
    optB = option_b(rp, rows)
    rec = dict(schema="opentallas.qc_seam_landing.v1", option_b=optB,
               inputs=dict(region_plan=a.region_plan, master_plan=a.master_plan, roads=a.roads,
                           region_plan_tool_sha256=rp["inputs"].get("tool_sha256")),
               budgets=B, classes=cls_sum, option_a=optA, non_abutting_crossings=len(nonabut),
               seams=seams, paths=per_path)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "seam_landing.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(dict(budgets=B, classes=cls_sum, option_a={k: v for k, v in optA.items() if k != "rule"},
                          non_abutting_crossings=len(nonabut)), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
