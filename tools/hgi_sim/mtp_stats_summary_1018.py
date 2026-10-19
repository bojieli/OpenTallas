#!/usr/bin/env python3
"""HBM-MTP / MTP-STATS (10-18): compose stats/summary.json from moe_union.json (mtp_union_stats_1018.py) plus the
structural sparse-attention facts of DeepSeek-V4.1-Flash and the Qwen3-8B DFlash records.

    python3 tools/hgi_sim/mtp_stats_summary_1018.py --moe moe_union.json --router router_full.pt --out summary.json
"""
import argparse, hashlib, json, subprocess
import numpy as np

PS = ("1", "2", "4", "6", "8")


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def git_show(path):
    return subprocess.run(["git", "-C", "/home/ubuntu/OpenTallas", "show", f"origin/main:{path}"], capture_output=True,
                          text=True, check=True).stdout


def git_sha(path):
    return hashlib.sha256(git_show(path).encode()).hexdigest()


def pick(o, keys=("mean", "p50", "p90", "max")):
    return {k: o["pooled"][k] for k in keys}


def main():
    import torch
    ap = argparse.ArgumentParser()
    ap.add_argument("--moe", required=True)
    ap.add_argument("--router", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    m = json.load(open(a.moe))
    ic = json.loads(git_show("compiler/models/deepseek-v4.1-flash/inference_config.json"))

    # ---------------- (a) MoE union table
    moe = dict(top_k=ic["n_activated_experts"], n_routed_experts=ic["n_routed_experts"],
               n_shared_experts=ic["n_shared_experts"], layers=ic["n_layers"],
               note="union = distinct routed experts per layer over the P lanes; shared expert always shared (1 per layer)",
               consecutive_continuation={}, consecutive_verify={}, independent_users_mixed={},
               independent_users_same_workload={}, uniform_random=m["uniform_random_union"])
    for P in PS:
        c = m["cont"][P]
        moe["consecutive_continuation"][P] = dict(**pick(c), layer_mean_range=c["layer_mean_range"],
                                                  lane_hist_frac=c["lane_hist_frac"],
                                                  mean_lanes_per_union_expert=c["mean_lanes_per_union_expert"])
        if P in m["verify"]:
            v = m["verify"][P]
            moe["consecutive_verify"][P] = dict(
                gamma=int(P) - 1, cycles=v["cycles"], tau_greedy=v["tau"], mean_unknown_lanes=v["mean_unknown_lanes"],
                exact_lanes_only_lower_bound=pick(v["v_known_lanes"]),
                proxy_continuation=pick(v["v_cont"]),
                estimate_decorrelated=dict(**pick(v["v_decor"]), lane_hist_frac=v["v_decor"]["lane_hist_frac"],
                                           mean_lanes_per_union_expert=v["v_decor"]["mean_lanes_per_union_expert"]),
                strict_upper_bound=pick(v["v_upper"]),
                per_layer_mean_decorrelated=v["v_decor"]["per_layer"]["mean"],
                per_layer_p90_decorrelated=v["v_decor"]["per_layer"]["p90"])
        for src, dst in (("indep_mixed", "independent_users_mixed"),
                         ("indep_same_workload", "independent_users_same_workload")):
            if P in m[src]:
                i = m[src][P]
                moe[dst][P] = dict(**pick(i), layer_mean_range=i["layer_mean_range"], lane_hist_frac=i["lane_hist_frac"],
                                   mean_lanes_per_union_expert=i["mean_lanes_per_union_expert"],
                                   per_layer_mean=i["per_layer"]["mean"], per_layer_p90=i["per_layer"]["p90"])
    moe["consecutive_verify"]["8"] = "no gamma-7 drafts captured (DSpark block is 5); use consecutive_continuation['8']"
    moe["sizing_recommendation"] = (
        "Verify (one user, P=6): size expert slots for the decorrelated estimate mean ~24.7 / p90 30 per layer "
        "(strict bound 36); 23.9 (continuation proxy) is ~1 expert optimistic. Independent users: P=6 mean 31.1 / "
        "p90 34 (mixed), 28.8 / 33 same workload, ~uniform-random 34.6. ~70% (verify) / ~87% (users) of union "
        "experts serve exactly ONE lane: grouped GEMM over the union is mostly 1-row GEMVs, so per-expert weight "
        "reads scale with the union, not with P")

    # ---------------- (b) sparse attention, structural from config + trace contexts
    R = torch.load(a.router, weights_only=False, map_location="cpu")
    ctx = np.concatenate([np.arange(int(x["L"]), x["router_idx"].shape[1]) for x in R])
    ratios = ic["compress_ratios"][:ic["n_layers"]]
    topk, win = ic["index_topk"], ic["window_size"]
    groups = []
    src = ic["index_source_layers"]
    for j, s in enumerate(src):
        r = ratios[s]
        lines = ctx // r
        groups.append(dict(index_source_layer=s, layers=[s, (src[j + 1] - 1) if j + 1 < len(src) else ic["n_layers"] - 1],
                           compress_ratio=r, uses_candidate_pool=s > ic["candidate_source_layer"],
                           frac_decode_positions_all_lines_selected=round(float((lines <= topk).mean()), 4),
                           lines_at_1M=(1 << 20) // r))
    att = dict(
        model_facts=dict(index_topk=topk, window_tokens=win, index_source_layers=src,
                         kv_source_layers=ic["kv_source_layers"], compress_ratios_backbone=ratios,
                         candidate_source_layer=ic["candidate_source_layer"],
                         candidate_pool_lines=ic["candidate_topk_blocks"] * ic["candidate_block_size"],
                         distinct_selection_sets_per_token=len(src)),
        trace_context_tokens=dict(min=int(ctx.min()), p50=float(np.median(ctx)), p90=float(np.percentile(ctx, 90)),
                                  max=int(ctx.max()), decode_positions=int(ctx.size)),
        groups=groups,
        independent_users=dict(union_over_P_single=1.0, exact=True,
                               why="different users have disjoint KV caches: union = P x single by construction "
                                   "(window and selected lines alike)"),
        consecutive_positions=dict(
            measured=False,
            why="no capture of indexer top-k indices exists (router_full.pt holds MoE gates only); the real "
                "selection needs the full 40-layer forward of the released checkpoint, which only the GPU tool "
                "tools/v41_dspark_onpolicy/v41router.py runs (CUDA-only); the CPU golden (tools/hdc_golden_v41.py) "
                "is the reduced 40 MB model and its indexer selection carries no real-attention statistics",
            exact_parts={
                "window": f"union of P windows = {win} + P - 1 lines (vs P x {win})",
                "short_context": "while compressed lines <= index_topk (ctx <= 512 x ratio) every lane selects ALL lines: "
                                 "union = single + new block lines (<= ceil((P-1)/ratio)); see groups[].frac_decode_"
                                 "positions_all_lines_selected for how often the traces are in that regime",
                "new_block_lines": "lane j additionally sees the j earlier verify positions' own lines (causal), "
                                   "<= P-1 lines total"},
            bounds_1M=dict(single_selected=topk, union_lower=topk, union_upper_P=f"{topk} x P",
                           note="at 1M context a lane selects 512 of 524,288 (ratio 2) or of the 16,384-line candidate "
                                "pool (layers > 20); overlap between adjacent positions is unmeasured: price the "
                                "KV-line-stationary engine at the upper bound P x 512 selected lines + 128 + P - 1 "
                                "window until the GPU indexer capture (pending) measures it"),
            follow_up="extend v41router.py with an Indexer hook (top-512 indices per index-source layer) and re-run "
                      "phase R1 on the same 120 traces (contexts 0.3-8.6K, ~1.6 h GPU) plus synthetic 64K-1M "
                      "contexts; needs coordinator OK (localhost GPU; fleet has none)"))

    # ---------------- (c) Qwen3-8B DFlash
    qc = json.loads(git_show("compiler/models/qwen3-8b/config.json"))
    ba = json.loads(git_show("results/speculative/dflash_block_acceptance.json"))
    tau_by_block = {b: dict(cycle_weighted_primary=v["pooled"]["primary"]["tau_direct_cycle_weighted"],
                            workload_mean_primary=v["pooled"]["primary"]["tau_direct_mean_of_workloads"],
                            cycle_weighted_all=v["pooled"]["all"]["tau_direct_cycle_weighted"])
                    for b, v in ba["blocks"].items()}
    qwen = dict(
        model=dict(layers=qc["num_hidden_layers"], hidden=qc["hidden_size"], kv_heads=qc["num_key_value_heads"],
                   q_heads=qc["num_attention_heads"], ffn=qc["intermediate_size"], moe=False),
        drafter=ba["drafter"], block=16,
        sharing=dict(weights="fully shared: dense model, every weight word serves all P = B verify lanes "
                             "(and P independent users alike)",
                     kv_consecutive="fully shared: every lane reads the same prefix lines [0, pos); lane j adds "
                                    "the j earlier block lines (causal) -> union = pos + B - 1 lines vs pos single",
                     kv_independent_users="disjoint: union = P x single",
                     drafter="non-causal block attention over context + whole block; drafter weights shared"),
        tau_by_block_measured=tau_by_block,
        tau_rows_used=dict(
            dflash_timing_b16=dict(published=8.01, measured_cycle_weighted=3.656, measured_workload_mean=4.662,
                                   src="tools/hgi_sim/dflash_timing.py TAU"),
            dflash_timing_b8=dict(published_scaled=round(8.01 * 5.8265 / 8.3572, 3), measured_cycle_weighted=3.2956,
                                  measured_workload_mean=3.7478),
            composition_default_third_party=3.1445,
            note="tau_by_block_measured are direct runs at each block (OOD below 16): P = B lanes for DFlash"),
        sources={p: git_sha(p) for p in ("results/speculative/dflash_block_acceptance.json",
                                         "results/arch/hgi_sim_20261009/dflash/README.md",
                                         "tools/hgi_sim/dflash_timing.py", "compiler/models/qwen3-8b/config.json")})

    ds_tau = dict(walk_greedy_120_agentic_traces=m["tau_greedy_walk_by_gamma"],
                  composition_default_gamma5=4.159,
                  note="walk tau is these 120 agentic traces only (greedy); 4.159 = owner 6-class blend")
    out = dict(
        schema="opentallas.hbm_mtp_next_1018.stats_summary.v1",
        lane="HBM-MTP / MTP-STATS", date="2026-10-18",
        deepseek_moe_union=moe, deepseek_sparse_attention=att, deepseek_tau_by_P=ds_tau, qwen_dflash=qwen,
        sources=dict(moe_union_json=dict(path="results/arch/hbm_mtp_next_1018/stats/moe_union.json", sha256=sha(a.moe)),
                     captures=m["sources"],
                     capture_tools="tools/v41_dspark_onpolicy/{v41gen,v41draft,v41router}.py (2026-10-03 run, "
                                   "released DeepSeek-V4.1-Flash dba1be0a, BF16/FP8 GPU path)",
                     inference_config_sha256=git_sha("compiler/models/deepseek-v4.1-flash/inference_config.json"),
                     tools=["tools/hgi_sim/mtp_union_stats_1018.py", "tools/hgi_sim/mtp_stats_summary_1018.py"]))
    json.dump(out, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
