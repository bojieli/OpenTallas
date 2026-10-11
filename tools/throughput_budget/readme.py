#!/usr/bin/env python3
"""Render the tables of results/arch/throughput_budget_*/README.md from budget.json (python3 -m throughput_budget.readme
BUDGET.json > TABLES.md, from tools/)."""
import json
import sys


def f(x, nd=1):
    if x is None:
        return "–"
    if isinstance(x, (int, float)):
        return f"{x:,.{nd}f}" if isinstance(x, float) else f"{x:,}"
    return str(x)


def main():
    d = json.load(open(sys.argv[1]))
    ds = d["ds_hbm"]
    L = []
    L += ["### DeepSeek-V4.1 1M on the generic HBM die (rank-0 head die, S2)", "",
          f"S2 price {ds['S2_cycles']:,.1f} cycles = {ds['S2_tok_s']:,.1f} tok/s; target {ds['target_tok_s']:,.1f} tok/s = "
          f"{ds['target_cycles']:,.1f} cycles, so every budget is the price × {ds['price_scale_to_target']}.", "",
          "| op | records / token | layers | price cyc / record | budget cyc / record at target | cyc / layer | items / record | "
          "required items / cycle | elasticity (+10 % price) | measured / price | grade | status | token cycles at measured | owner |",
          "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---:|---|"]
    for r in ds["ops"]:
        L.append("| %s | %s | %s | %s | %s | %s | %s %s | %s | %.2f %% | %s | %s | **%s** | %s | %s |" % (
            r["op"], f(r["records_per_token"]), f(r["layers_with_op"]), f(r["price_cycles_per_record"]),
            f(r["budget_cycles_per_record_at_target"]), f(r["price_cycles_per_layer"]), f(r["items_per_record"], 0),
            r["item"].split(" (")[0], f(r["required_items_per_cycle"], 2), 100 * r["token_elasticity_at_plus10pct"] / 1.0,
            "–" if r["measured_ratio"] is None else f"{r['measured_ratio']:.3f}", r["measured_grade"] or "none",
            r["status"], "+" + f(r["impact_cycles_per_token"]) if r["impact_cycles_per_token"] > 0 else f(r["impact_cycles_per_token"]),
            r["owner"].split(" (")[0]))
    L += ["", "### DS bottleneck ranking (measured shortfalls, token cycles on S2 with only that op at its measured ratio)", "",
          "| # | op | measured / price | + cycles / token | tok/s lost | budget cyc / record (at target) | owner |", "|---:|---|---:|---:|---:|---:|---|"]
    for x in d["ds_bottleneck_ranking"]:
        L.append("| %d | %s | %.3f | %s | %s | %s (%s) | %s |" % (x["rank"], x["op"], x["ratio"], f(x["impact_cycles_per_token"]),
                                                               f(x["impact_tok_s"]), f(x["budget_cycles_per_record"]),
                                                               f(x["budget_at_target"]), x["owner"]))
    L += ["", "### DS ops with no production-shape bench (UNQUALIFIED_NO_BENCH), by exposure (token cycles if 2× price)", "",
          "| op | price cyc / token | exposure if 2× | owner | interim |", "|---|---:|---:|---|---|"]
    for x in d["ds_unbenched_by_exposure"]:
        it = x.get("interim") or {}
        L.append("| %s | %s | %s | %s | %s |" % (x["op"], f(x["price_cycles_per_token"]), f(x["exposure_cycles_if_2x"]),
                                              x["owner"], (it.get("src") or "") + (f" (ratio {it['ratio']})" if it.get("ratio") else "")))
    L += ["", "### HBM loader / svc endpoint budget (DS AR, per die; stack figures assume the 4-stack stripe)", "",
          "| stream | kind | bytes / token | B / cycle at the record's price (die) | per stack | token average (die) |", "|---|---|---:|---:|---:|---:|"]
    for k, v in d["svc_endpoint_budget_ds"].items():
        if k == "CP.FETCH":
            L.append("| CP.FETCH | read | %s | needs %s (overlap-aware minimum) | – | designed %s |" % (
                f(v["bytes_per_token"]), v["required_B_per_cycle_die"], v["designed_B_per_cycle_die"]))
        else:
            L.append("| %s | %s | %s | %s | %s | %s |" % (k, v["kind"], f(v["bytes_per_token"]), v["at_price_B_per_cycle_die"],
                                                        v["at_price_B_per_cycle_stack_striped"], v["token_average_B_per_cycle_die"]))
    q = d["qwen_hbm"]
    L += ["", "### Qwen3-8B 8K on the generic HBM die (S2)", "",
          f"S2 price {q['S2_cycles']:,.1f} cycles = {q['S2_tok_s']:,.1f} tok/s; target {q['target_tok_s']} tok/s. {q['note']}.", "",
          "| op | records / token | price cyc / record | budget at target | items / record | elasticity | measured / price | status | token cycles at measured |",
          "|---|---:|---:|---:|---:|---:|---:|---|---:|"]
    for r in q["ops"]:
        L.append("| %s | %s | %s | %s | %s | %.2f %% | %s | %s | %s |" % (
            r["op"], f(r["records_per_token"]), f(r["price_cycles_per_record"]), f(r["budget_cycles_per_record_at_target"]),
            f(r["items_per_record"], 0), 100 * r["token_elasticity_at_plus10pct"],
            "–" if r["measured_ratio"] is None else f"{r['measured_ratio']:.3f}", r["status"], f(r["impact_cycles_per_token"])))
    L += ["", "### ROM pipelines (token-path node prices; per-class critical cycles and the stage II limiter)", ""]
    for k, v in d["rom"].items():
        L += [f"**{k}** ({v['headline']} tok/s, {v['cycles']:,.1f} cycles; {v['n_stages']} stage groups; II limiter "
              f"{v['stage_ii_limiter']['label']} = {v['stage_ii_limiter']['cycles']:,.1f} cycles)", "",
              "| class | critical cyc / token | share | measured fraction | status | unbenched nodes |", "|---|---:|---:|---:|---|---|"]
        for c in v["classes"]:
            L.append("| %s | %s | %.1f %% | %.1f %% | %s | %d (%s) |" % (c["cls"], f(c["critical_cycles_per_token"]), 100 * c["share"],
                                                                     100 * (c["measured_fraction"] or 0), c["status"], c["n_unmeasured"],
                                                                     ", ".join(c["unmeasured_nodes"][:4])))
        L.append("")
    bg = d.get("build_gate") or {}
    L += ["### Build gate: priced ops with no native RTL bench (PRICED-NOT-BUILT)", "", bg.get("rule", "") + ".", "",
          "| model | op | variant | status | records / token | priced cycles / token | critical-path cycles (op at 0) | rate if the op were free | evidence |",
          "|---|---|---|---|---:|---:|---:|---:|---|"]
    for g in sorted(bg.get("priced_not_built", []), key=lambda g: -(g.get("critical_cycles_if_zero") or 0)):
        L.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (g["model"], g["op"], g["variant"] or "", g["status"],
                 f(g["records_per_token"]), f(g["price_cycles_per_token"]), f(g.get("critical_cycles_if_zero")),
                 f(g.get("rate_if_op_free_tok_s")), g["evidence"].replace("|", "/")))
    rates = sorted({x for g in bg.get("priced_not_built", []) for x in g.get("inflates", [])})
    L += ["", "Rate figures these ops inflate (each prices the op at its simulator cost although no RTL runs it): " + "; ".join(rates) + ".", ""]
    hand = d.get("hand_entered") or []
    L += ["### Hand-entered ratios (unmeasured; never qualify)", "",
          "| model | op / element | claimed ratio | source | owner |", "|---|---|---:|---|---|"]
    for h in hand:
        L.append("| %s | %s | %s | %s | %s |" % (h["model"], h.get("element") or h["op"], h.get("claimed_ratio") or "–",
                                              str(h.get("src")).replace("|", "/"), h.get("owner")))
    bii = d.get("bench_ii") or {}
    L += ["", f"### Automated bench II ({len(bii)} elements with a cycles line in a passing exact closure-loop bench)", "",
          "| element | II (cycles / item) | item | stalled stimulus | job @ commit | line |", "|---|---:|---|---|---|---|"]
    for e, b in sorted(bii.items()):
        L.append("| %s | %s | %s | %s | %s @ %s | %s |" % (e, b["ii"] if b["ii"] is not None else "–", b["item"] or "–",
                 "yes" if b["stalled"] else "", b["job"], b["commit"], b["line"][:110].replace("|", "/")))
    L.append("")
    bf = d.get("bf_hier")
    if bf:
        L += ["### DS ROM BF of record: hierarchical full-rate (ot_v41_bf_col + ot_s81_bf_front)", "",
              "| item | value |", "|---|---|",
              f"| target | AR {bf['target']['ds_rom_ar_tok_s']:,} / MTP {bf['target']['ds_rom_mtp_tok_s']:,} tok/s ({bf['target']['row']}; {bf['target']['condition']}) |",
              f"| budget (bench workload: {bf['budget']['rows']} rows, {bf['budget']['partials']} partials, {bf['budget']['issues']:,} issues) | {bf['budget']['issue_cycles']:,} issue cycles + {bf['budget']['partial_extra_cycles']} cycles a partial |",
              f"| measured | {bf['measured']['issue_cycles']:,} issue cycles; partial lag +{bf['measured']['partial_lag_extra_ns_mean']} ns mean / +{bf['measured']['partial_lag_extra_ns_max']} ns max = +{bf['measured']['partial_extra_cycles']} cycles |",
              f"| measured / price | {bf['ratio']} ({bf['status']}) |",
              f"| timing | column: {bf['timing']['ot_v41_bf_col']}; front: {bf['timing']['ot_s81_bf_front']}; {bf['timing']['composed']} |",
              f"| evidence | {', '.join(bf['measured']['benches'])} |", ""]
    cov = d.get("rom_block_coverage") or {}
    if cov:
        un = sorted(k for k, v in cov.items() if v is None)
        L += [f"ROM blocks outside the token-path classes: {len(cov)} covered by name rules (`rom_block_rules`); unmapped: {', '.join(un) or 'none'}.", ""]
    import collections
    cnt = collections.Counter(v["status"] for v in d["elements"].values())
    L += ["### Registry gate (elements)", "", f"{len(d['elements'])} elements mapped: " +
          ", ".join(f"{k} {v}" for k, v in sorted(cnt.items())) + ".", ""]
    print("\n".join(L))


if __name__ == "__main__":
    main()
