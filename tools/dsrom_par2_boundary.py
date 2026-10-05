#!/usr/bin/env python3
"""Price the PAR2 intra-rank die-to-die boundary of DS4096-TP4-S58-PAR2-NP2048 with the opt-in extension
tools/uarch_model_par2_boundary.py.  Model only: no RTL, no P&R, no pinned file is modified.

Basis: the S58 selection's own cons_v41_rom settings (tools/dsrom_4096_partition_token_options.py: head 8,
table 36, 1.2 GHz SS, 0.9 GHz serial domain, elem_stages 8, SS wires, VMC_FUSED, PRODUCT_HUB, DIE_SHRUNK_INTERIM).
Writes the corrected hub-edge model; the historical PAR2 record is preserved.
"""
import argparse
import copy
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import uarch_model as u  # noqa: E402
import uarch_model_par2_boundary as X  # noqa: E402

OUT = ROOT / "results/uarch/dsrom_hub_edge_wires_20261003"
CAP = ROOT / "results/uarch/dsrom_4096_comparable_capacity_20261002/partition_token_options.json"
CTXS = (1048576, 200000)
PINNED = {1048576: (2563.7, 3809.4), 200000: (2680.6, 4176.7)}   # dsrom_utilisation_redesign option 0 (S58)

VARIANTS = [
    # id, S, par2 config (None = baseline), note
    ("base_S58", 58, None, "unified model as pinned: no PAR2 term"),
    ("pkgA_collectives_only_mesh", 58, dict(mode="owner", board="mesh", field_term=False),
     "PAR2 pair in package -> TP-4 over 4 packages on the model's board mesh; field crossings not added"),
    ("pkgA_collectives_only_fc4", 58, dict(mode="owner", board="fc4", field_term=False),
     "same, four-package quad fully connected on the board (fc4)"),
    ("owner_mesh", 58, dict(mode="owner", board="mesh"), "as designed, board mesh"),
    ("owner_fc4", 58, dict(mode="owner", board="fc4"), "as designed, fc4 quad"),
    ("owner_edge_fc4", 58, dict(mode="owner_edge", board="fc4"), "remote tree rooted at the shared-edge PHY"),
    ("owner_board", 58, dict(mode="owner_board"), "PAR2 pair split across packages (light-FEC board link)"),
    ("mirror_hub_fc4", 58, dict(mode="mirror_hub", board="fc4"), "replicated hubs run the chain; attention on shard 0"),
    ("mirror_full_fc4", 58, dict(mode="mirror_full", board="fc4"), "mirror_hub + attention/indexer mirrored (KV x2)"),
    ("layer_split_S116_fc4", 116, dict(mode="layer_split", board="fc4"),
     "no row split: die pair = consecutive packed groups, odd hops in-package UCIe"),
    ("layer_split_S116_mesh", 116, dict(mode="layer_split", board="mesh"), "same on the board mesh"),
    ("unpaired_S116", 116, None, "reference: S116 with every hop on the board, TP pair in package (no PAR2)"),
    ("expert_split_fc4", 58, dict(mode="owner", board="fc4", split="experts"),
     "split by whole routed experts (dense on shard 0): one crossing in, one out per layer"),
    ("expert_split_fc4_overlap", 58, dict(mode="owner", board="fc4", split="experts", credit_overlap=True),
     "same, four-package collective's extra bytes credited to the existing overlap (level 5)"),
    ("expert_split_mesh", 58, dict(mode="owner", board="mesh", split="experts"), "same on the board mesh"),
    ("expert_split_board", 58, dict(mode="owner_board", split="experts"),
     "expert split, shards in different packages (TP pair kept in package)"),
    ("owner_fc4_overlap", 58, dict(mode="owner", board="fc4", credit_overlap=True), "owner, overlap credited"),
    ("expert_split_fc4_link20ns", 58, dict(mode="owner", board="fc4", split="experts", link_core_s=20e-9),
     "UCIe core 20 ns"),
    # link sensitivity
    ("owner_fc4_link3ns", 58, dict(mode="owner", board="fc4", link_core_s=3e-9), "UCIe core 3 ns"),
    ("owner_fc4_link20ns", 58, dict(mode="owner", board="fc4", link_core_s=20e-9), "UCIe core 20 ns"),
    ("mirror_full_fc4_link20ns", 58, dict(mode="mirror_full", board="fc4", link_core_s=20e-9), "UCIe core 20 ns"),
    ("layer_split_S116_fc4_link20ns", 116, dict(mode="layer_split", board="fc4", link_core_s=20e-9), "UCIe core 20 ns"),
]


def price(S, ctx, par2):
    cap = json.loads(CAP.read_text())
    rows = {r["stages"]: r for r in cap["all_stage_capacity_rows"]}
    saved = copy.deepcopy(u.PRESETS["proposal"])
    u.PRESETS["proposal"]["bf16_stripe_macros"] = 2 * rows[S]["BF16_pairs_per_die"]
    try:
        with u._cons_ctx(ctx):
            p = X.cons_v41_rom_par2(S, 8, 36, bf16="columns", clock_hz=u.PRODUCT_CLOCK_HZ,
                                    field_concurrency=u.FIELD_CONCURRENCY,
                                    added_latency=dict(u.SOFTPLUS_FIX, **u.W11_STREAM_SS, **u.PLUS_LAT),
                                    dyn_scale=u.PRODUCT_DYN_SCALE, slow_domain=(.9e9, "w18"), elem_stages=8,
                                    ss_wire=True, serial=u.PRODUCT_SERIAL, die=u.DIE_SHRUNK_INTERIM, vmh=u.VMC_FUSED,
                                    hub_block=u.PRODUCT_HUB, par2=par2)
    finally:
        u.PRESETS["proposal"].clear()
        u.PRESETS["proposal"].update(saved)
    out = dict(stages=S, ctx=ctx, ar_tok_s=p["ar_tokens_s_b1"], mtp_tok_s=p["mtp_tokens_s_b1"],
               ar_token_us=round(1e6 / p["ar_tokens_s_b1"], 2), ar_saturated_tok_s=p["ar_saturated_tokens_s"],
               stage_hops=p["stage_hops"], layer_dies=p["layer_dies"], hbm_stacks=p["hbm_stacks"],
               BF16_pairs_per_die=rows[S]["BF16_pairs_per_die"])
    if "par2" in p:
        out["par2_passes"] = [{k: (round(v * 1e9, 2) if k == "one_way_s" else v) for k, v in x.items()
                               if k != "on_path"} | dict(on_path={k: (round(v * 1e6, 3) if k == "added_s_on_path"
                                                                     else v) for k, v in x["on_path"].items()})
                              for x in p["par2"]["passes"]]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT / "model.json"))
    ap.add_argument("--variants", nargs="+", choices=[r[0] for r in VARIANTS],
                    default=["base_S58", "owner_fc4", "layer_split_S116_fc4"],
                    help="Mappings to compose; select all names explicitly for the historical sensitivity sweep")
    a = ap.parse_args()
    clock = u.PRODUCT_CLOCK_HZ
    census = X.call_census()
    results = []
    for vid, S, cfg, note in VARIANTS:
        if vid not in a.variants:
            continue
        full = X.default_cfg(**cfg) if cfg else None
        for ctx in CTXS:
            r = price(S, ctx, full)
            r.update(id=vid, note=note, cfg={k: v for k, v in (full or {}).items()},
                     one_way_ns=round(X.one_way_s(full, clock) * 1e9, 2) if full else None)
            results.append(r)
            print(json.dumps({k: r[k] for k in ("id", "ctx", "ar_tok_s", "mtp_tok_s", "ar_token_us")}), flush=True)
    if "base_S58" not in a.variants:
        raise SystemExit("base_S58 is required for consistent comparisons")
    for ctx, (ar, mtp) in PINNED.items():
        b = next(r for r in results if r["id"] == "base_S58" and r["ctx"] == ctx)
        b["historical_without_endpoint_wires"] = dict(ar_tok_s=ar, mtp_tok_s=mtp)
        b["ar_wire_correction_us"] = round(b["ar_token_us"] - 1e6 / ar, 3)
    base = {r["ctx"]: r for r in results if r["id"] == "base_S58"}
    for r in results:
        b = base[r["ctx"]]
        r["ar_delta_pct_vs_base"] = round(100 * (r["ar_tok_s"] / b["ar_tok_s"] - 1), 2)
        r["mtp_delta_pct_vs_base"] = round(100 * (r["mtp_tok_s"] / b["mtp_tok_s"] - 1), 2)
    src = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in (
        "tools/uarch_model.py", "tools/uarch_model_par2_boundary.py", "tools/dsrom_par2_boundary.py",
        "tools/decode_critical_path.py", "tools/arch_budget_v41.py", "configs/hardware/technology.json",
        str(X.CHOICES.relative_to(ROOT)), str(CAP.relative_to(ROOT)))}
    rec = dict(schema="opentallas.dsrom.hub-edge-wires.v2", candidate="DS4096-TP4-S58-PAR2-NP2048",
               model_extension=X.MODEL_EXTENSION, default_off=True,
               wire_source=u.HUB_EDGE_WIRE_SOURCE, endpoint_wires_in_all_mappings=True,
               source_sha256=src, clock_hz=clock,
               link=dict(X.tech_links(), vm_to_ucie_stages=X.VM_TO_UCIE_STAGES,
                         vm_to_serdes_stages=X.VM_TO_SERDES_STAGES, ss_reach_um=u.SS_REACH_UM[1.2e9],
                         stage_period_ps=round(261 + 1.135 * u.SS_REACH_UM[1.2e9], 1),
                         ucie_ondie_routing_replaced_s=X.UCIE_ONDIE_ROUTING_S,
                         link_core_s=X.default_cfg("owner")["link_core_s"],
                         one_way_ns={m: round(X.one_way_s(X.default_cfg(m), clock) * 1e9, 2) for m in X.MODES},
                         bandwidth=X.bandwidth_check(X.default_cfg("owner"), clock)),
               census=census, results=results,
               scope="Analytical; dataflow levels 1-5 only; golden rounding/reduction order unchanged in every mode "
                     "(row split cuts no reduction; mirrored hubs compute bit-identical chains; layer split moves "
                     "whole matrices).  No RTL/P&R; not adopted.")
    b = (json.dumps(rec, indent=1, sort_keys=True, default=sorted) + "\n").encode()
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists() and out.read_bytes() != b:
        raise SystemExit(f"{out} exists with different bytes")
    out.write_bytes(b)
    print("wrote", out)


if __name__ == "__main__":
    main()
