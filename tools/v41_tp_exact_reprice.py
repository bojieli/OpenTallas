"""Current-source V4.1 sensitivity for the bit-exact MoE w2 output-row split.

The current headline still models the numerically inexact K split. This tool
reprices the mandatory activation and output gathers without promoting the
old collective timing measurements to a new calibrated headline.
"""
import json, math, sys
from pathlib import Path
T = Path(__file__).resolve().parent
sys.path.insert(0, str(T))
import decode_critical_path as DC  # noqa: E402
import arch_lanes_v41 as AL  # noqa: E402


def v41_moe_rowsplit(ops, c, L, x, xq, fp4):
    m = ops.m
    D, NE, KE, FF = c["hidden_size"], c["num_routed_experts"], c["experts_per_token"], c["moe_intermediate_size"]
    G = m.group
    P = f"L{L}.ffn"
    SU, SU_BASE, FADD, V41 = DC.SU, DC.SU_BASE, DC.FADD, DC.V41
    rt = ops.matvec(f"{P}.router", [x], L, n_out=NE, k=D, bytes_=NE * D * 4, fmt="fp32",
                    desc="gate [384, 5120] FP32, experts split")
    sp = ops.ew(f"{P}.softplus_sqrt", [rt], math.ceil(NE / G), SU_BASE + V41["softplus"], L, desc="sqrt(softplus)")
    sp = ops.collective(f"{P}.router_allgather", [sp], L, op="all_gather", payload=NE * 4,
                        desc="384 FP32 router scores") or sp
    bias = ops.ew(f"{P}.bias", [sp], NE, SU_BASE + FADD, L, desc="+ bias")
    tk = ops.select_local(f"{P}.top6", [bias], L, n=NE, k=KE, desc=f"top-{KE} of {NE}")
    tk = ops.select_final(f"{P}.top6_order", [tk], L, k=KE, ways=1, ascending=True, desc="experts in id order")
    wn = ops.ew(f"{P}.weights", [tk, sp], KE, (KE - 1) * FADD + FADD + SU_BASE + ops.p.fdiv_cycles + FADD, L,
                stream=False, desc="weights")
    sh = ops.matvec(f"{P}.shared_gu", [xq, rt], L, n_out=2 * FF, k=D, bytes_=2 * FF * D, desc="shared w1|w3")
    shs = ops.ew(f"{P}.shared_swiglu", [sh], math.ceil(FF / G), SU["SIGM"] + 2 * FADD, L, desc="swiglu")
    shq = ops.actquant(f"{P}.shared_quant", [shs], math.ceil(FF / G), L)
    inter = math.ceil(KE * FF / G)
    gu = ops.matvec(f"{P}.experts_gu", [tk, sh], L, n_out=2 * FF * KE, k=D, bytes_=KE * 2 * FF * D * fp4,
                    fmt="fp4", desc="routed w1|w3 striped")
    sw = ops.ew(f"{P}.swiglu", [gu], inter, SU["SIGM"] + 2 * FADD, L, desc="swiglu")
    sw = ops.ew(f"{P}.route_w", [sw, wn], inter, SU_BASE + FADD, L, stream=False, desc="x routing weight")
    sq = ops.actquant(f"{P}.quant2", [sw], inter, L)
    # ROW SPLIT: every die needs the whole FP8 activation of the 7 experts (codes + UE8M0 scale per 32)
    assert (G, KE, FF, D) == (4, 6, 2304, 5120)
    local_ff = FF // G
    padded_act_entries = math.ceil((local_ff + local_ff // 32) / 16) * 16
    ag = ops.collective(f"{P}.act_allgather", [sq, shq], L, op="all_gather",
                        payload=G * (KE + 1) * padded_act_entries * 4,
                        desc="COLL-v1 padded 32-bit VM entries for 6 routed + shared activations")
    deps = [ag] if ag else [sq, shq]
    dn = ops.matvec(f"{P}.down", deps, L, n_out=D, k=FF * (KE + 1), bytes_=KE * D * FF * fp4 + D * FF,
                    fmt="fp4", desc="routed + shared w2, output rows split, full K, experts summed in id order")
    return ops.collective(f"{P}.y_allgather", [dn], L, op="all_gather", payload=D * 4,
                          desc="COLL-v1 BF16 outputs in 32-bit VM entries") or dn




def build():
    """Reprice current V4.1 source with the mandatory bit-exact w2 output-row split.

    The existing collective-lever tails measured an all-reduce and do not calibrate
    the new two-gather schedule. The result is a model sensitivity, not a headline.
    """
    import hashlib
    root = T.parent
    baseline = json.loads((root / "results/arch/v41_lanes.json").read_text())
    region = json.loads((root / "results/arch/v41_hbm_region_preflight.json").read_text())
    for path, digest in region["source_sha256"].items():
        assert hashlib.sha256((root / path).read_bytes()).hexdigest() == digest, path
    old = DC.v41_moe
    try:
        current = AL.build()
        for ctx in ("1048576", "200000"):
            for rate in ("ar", "mtp"):
                actual = current["design_point"][ctx][rate]
                pinned = baseline["design_point"][ctx][rate]
                assert abs(actual - pinned) / pinned < 1e-9, (ctx, rate, actual, pinned)
        DC.v41_moe = v41_moe_rowsplit
        row = AL.build()
    finally:
        DC.v41_moe = old
    keys = ("design_point_overlap_assumed", "design_point_no_levers", "design_point")
    points = {}
    for k in keys:
        points[k] = {}
        for ctx in ("1048576", "200000"):
            b, r = current[k][ctx], row[k][ctx]
            points[k][ctx] = {mode: dict(baseline=b[mode], rowsplit=r[mode],
                                         delta_fraction=r[mode] / b[mode] - 1)
                              for mode in ("ar", "mtp")}
    srcs = ("tools/v41_tp_exact_reprice.py", "tools/decode_critical_path.py",
            "tools/arch_lanes_v41.py", "tools/arch_latency_ladder_v41.py",
            "tools/arch_budget_v41.py", "tools/collective_exposure.py",
            "tools/v41_collective_exposure.py", "results/arch/v41_lanes.json",
            "results/rtl/v41_collective_levers_campaign.json",
            "results/rtl/v41_stage_collective_campaign.json",
            "results/arch/v41_hbm_region_preflight.json",
            "configs/hardware/technology.json")
    pins = {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in srcs}
    return dict(schema="v41_tp_exact_reprice_v1", source_sha256=pins,
                scope="batch-one per-user AR/MTP model sensitivity only; no aggregate, energy, or chip-throughput claim",
                contract=dict(tp=4, experts=7, ff=2304, outputs=5120,
                              activation_per_expert_per_die_entries=608,
                              activation_allgather_payload_B=4 * 7 * 608 * 4,
                              y_allgather_payload_B=5120 * 4,
                              old_combine_allreduce_payload_B=5120 * 4,
                              activation_dependency="after all expert quant, before w2",
                              output_dependency="after per-expert BF16 round and local expert sum"),
                points=points,
                calibration=dict(overlap_assumed="conditional ideal overlap; no new collective bench",
                                 no_levers="old C7 exposure class transferred; sensitivity only",
                                 design_point="old all-gather-small lever tails transferred to two new all-gathers; uncalibrated",
                                 required_collective_bench=dict(
                                     current_die_collective_flit_bytes=64,
                                     activation_local_flits=266, output_local_flits=80,
                                     previous_small_gather_words=1,
                                     previous_small_gather_word_bytes=512,
                                     source="results/rtl/v41_stage_collective_campaign.json patterns.gather_router",
                                     note="old gather bench used a 512-byte word, while the die uses 64-byte flits; measure both gathers at the die width with the new quant and w2 producer schedule, including blocking COLL and queue backpressure"),
                                 adopted_rate_claim="pending exact two-gather collective RTL timing and full-shape bit-exact gate"),
                capacity=dict(source="results/arch/v41_hbm_region_preflight.json",
                              model_striped_key_users=region["capacity"]["users_model_striped_keys"],
                              replicated_key_static_users=region["capacity"]["users_current_replicated_keys"],
                              replicated_key_addressable_users=region["capacity"]["max_replicated_users_with_28_bit_key_window"],
                              multiuser_key_address_isolation=region["isolation"]["multiuser_key_address_isolation"],
                              adopted_saturation_claim_valid=False,
                              gate="paired sharded writer and scanner with user offset, exact two-user scan, parallel scan scheduler and route at modeled bandwidth; serial correctness reader cannot support the modeled scan rate"))


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=T.parent / "results/arch/v41_tp_exact_reprice.json")
    a = ap.parse_args()
    rec = build()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: {c: {m: round(v[m]["rowsplit"]) for m in ("ar", "mtp")}
                          for c, v in x.items()} for k, x in rec["points"].items()}))


if __name__ == "__main__":
    main()
