#!/usr/bin/env python3
"""Price added latency cycles in the DeepSeek-V4.1 ROM q-pair element (ot_v41_rom_elem_q_qt_w10 on
ot_v41_rom_elem_qt_w10 / ot_v41_rom_elem_w10, BF16 = 0: the FP8/FP4 field element) on the per-user decode token.

Model only: no RTL, no P&R.  Basis: the S58 selection's own cons_v41_rom settings
(tools/dsrom_4096_partition_token_options.py: S 58, head 8, table 36, BF16 stripe macros 2 x 724, 1.2 GHz SS,
0.9 GHz serial domain W18 CDC, elem_stages 8, SS wires, VMC_FUSED, PRODUCT_HUB, DIE_SHRUNK_INTERIM).

Mechanism: in the unified model every field matvec node carries an element latency in its depth
(price_matvec: elem_fill 78 + wire + tree + adder levels; _cons_adjust adds the latency inventory per node).
Depth is pure latency after issue (decode_critical_path.Graph.solve), so an added element cycle is exposed on
every matvec node the critical path crosses and on nothing else.  The added cycles are injected through the
latency-inventory hook (_lat_cycles) on exactly the matvec nodes of the chosen scope, at the 1.2 GHz field clock:
  scope "q"   -- q-pair element families only (every field matvec except the BF16-column keys wo_a, router,
                 cmp.wk, lm_head; a_proj's BF16 sub-phase is counted with its FP8 part, conservatively);
  scope "all" -- every field matvec (q pairs and BF16 columns, if the shared ot_v41_rom_elem_w10 base is
                 pipelined for both).
A sensitivity row prices the case where a cycle lands inside the chunk-8 adder recurrence (elem_stages 8 -> 9),
which also lengthens the issue floor (8 x LAT) instead of only the fill.
MTP: DSpark m = 1, 6 positions, tau 3.649: step = verify pass + 3/40 x AR token (V41_DRAFT_FRACTION), so the draft
inherits the AR delta.  Writes results/uarch/dsrom_qelem_pipeline_pricing_20261003.json.
"""
import argparse
import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import uarch_model as u  # noqa: E402

OUT = ROOT / "results/uarch/dsrom_qelem_pipeline_pricing_20261003.json"
CAP = ROOT / "results/uarch/dsrom_4096_comparable_capacity_20261002/partition_token_options.json"
CTXS = (1048576, 200000)
S, HEAD, TABLE = 58, 8, 36
ADDED = (0, 1, 2, 3, 4)
BF16_KEYS = ("wo_a", "router", "cmp.wk", "lm_head")   # price_matvec: BF16 matrices on the BF16 columns
CAPTURE = {}


def _in_scope(nd, scope):
    m = nd.get("_uarch")
    return bool(m) and (scope == "all" or m["key"] not in BF16_KEYS)


def price(ctx, extra, scope, elem_stages=8):
    cap = json.loads(CAP.read_text())
    row = next(r for r in cap["all_stage_capacity_rows"] if r["stages"] == S)
    saved = copy.deepcopy(u.PRESETS["proposal"])
    orig_lat, orig_adj = u._lat_cycles, u._cons_adjust

    def lat(name, nd, l):
        return orig_lat(name, nd, l) + (extra if _in_scope(nd, scope) else 0)

    def adj(g, P, *a, **k):
        T = orig_adj(g, P, *a, **k)
        sink = [n for n in g.nodes if n.endswith("token.return")][0]
        CAPTURE[P] = (g, g.path(sink), T)
        return T
    u.PRESETS["proposal"]["bf16_stripe_macros"] = 2 * row["BF16_pairs_per_die"]
    u._lat_cycles, u._cons_adjust = lat, adj
    try:
        with u._cons_ctx(ctx):
            p = u.cons_v41_rom(S, HEAD, TABLE, bf16="columns", clock_hz=u.PRODUCT_CLOCK_HZ,
                               field_concurrency=u.FIELD_CONCURRENCY,
                               added_latency=dict(u.SOFTPLUS_FIX, **u.W11_STREAM_SS, **u.PLUS_LAT),
                               dyn_scale=u.PRODUCT_DYN_SCALE, slow_domain=(.9e9, "w18"), elem_stages=elem_stages,
                               ss_wire=True, serial=u.PRODUCT_SERIAL, die=u.DIE_SHRUNK_INTERIM, vmh=u.VMC_FUSED,
                               hub_block=u.PRODUCT_HUB)
    finally:
        u._lat_cycles, u._cons_adjust = orig_lat, orig_adj
        u.PRESETS["proposal"].clear()
        u.PRESETS["proposal"].update(saved)
    census = {}
    for P, (g, path, T) in CAPTURE.items():
        q = [n for n in path if _in_scope(g.nodes[n], "q")]
        bf = [n for n in path if g.nodes[n].get("_uarch") and n not in q]
        fam = {}
        for n in q + bf:
            t = n.split(".", 1)[1] if n.startswith(("L", "E")) and "." in n else n
            fam[t] = fam.get(t, 0) + 1
        census[P] = dict(pass_us=round(T * 1e6, 4), path_nodes=len(path), q_matvec_on_path=len(q),
                         bf16_matvec_on_path=len(bf), families_on_path=dict(sorted(fam.items())),
                         q_matvec_in_graph=sum(1 for nd in g.nodes.values() if _in_scope(nd, "q")),
                         all_matvec_in_graph=sum(1 for nd in g.nodes.values() if nd.get("_uarch")))
    CAPTURE.clear()
    return dict(ar=p["ar_tokens_s_b1"], mtp=p["mtp_tokens_s_b1"], ar_us=1e6 / p["ar_tokens_s_b1"],
                mtp_step_us=u.V41_TAU * 1e6 / p["mtp_tokens_s_b1"], census=census)


def git_head():
    return subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()
    cyc_ns = 1e9 / u.PRODUCT_CLOCK_HZ
    rows, base = [], {}
    for ctx in CTXS:
        for scope in ("q", "all"):
            for k in ADDED:
                r = price(ctx, k, scope)
                if k == 0:
                    base[(ctx, scope)] = r
                b = base[(ctx, scope)]
                c1, cv = r["census"][1], r["census"][u.V41_POSITIONS]
                row = dict(ctx=ctx, scope=scope, added_cycles_per_op=k,
                           ar_tok_s=r["ar"], mtp_tok_s=r["mtp"],
                           ar_token_us=round(r["ar_us"], 4), mtp_step_us=round(r["mtp_step_us"], 4),
                           ar_delta_tok_s=round(r["ar"] - b["ar"], 1),
                           ar_delta_pct=round(100 * (r["ar"] / b["ar"] - 1), 3),
                           mtp_delta_tok_s=round(r["mtp"] - b["mtp"], 1),
                           mtp_delta_pct=round(100 * (r["mtp"] / b["mtp"] - 1), 3),
                           ar_token_delta_ns=round((r["ar_us"] - b["ar_us"]) * 1e3, 2),
                           mtp_step_delta_ns=round((r["mtp_step_us"] - b["mtp_step_us"]) * 1e3, 2),
                           ar_exposed_ops_equiv=(round((r["ar_us"] - b["ar_us"]) * 1e3 / (k * cyc_ns), 2) if k else None),
                           mtp_exposed_ops_equiv=(round((r["mtp_step_us"] - b["mtp_step_us"]) * 1e3 / (k * cyc_ns), 2)
                                                  if k else None),
                           ar_path=dict(q=c1["q_matvec_on_path"], bf16=c1["bf16_matvec_on_path"]),
                           verify_path=dict(q=cv["q_matvec_on_path"], bf16=cv["bf16_matvec_on_path"]))
                rows.append(row)
                if k == 0:
                    row["census"] = {str(P): c for P, c in r["census"].items()}
                print(json.dumps({x: row[x] for x in ("ctx", "scope", "added_cycles_per_op", "ar_tok_s", "mtp_tok_s",
                                                      "ar_delta_pct", "mtp_delta_pct", "ar_exposed_ops_equiv")}),
                      flush=True)
    sens = []
    for ctx in CTXS:
        b = base[(ctx, "q")]
        r = price(ctx, 0, "q", elem_stages=9)
        sens.append(dict(ctx=ctx, case="one added cycle inside the chunk-8 adder recurrence (elem_stages 8 -> 9; "
                                       "every field element, issue floor 8 x LAT and K-split adder levels)",
                         ar_tok_s=r["ar"], mtp_tok_s=r["mtp"], ar_delta_pct=round(100 * (r["ar"] / b["ar"] - 1), 3),
                         mtp_delta_pct=round(100 * (r["mtp"] / b["mtp"] - 1), 3)))
    srcs = ("tools/uarch_model.py", "tools/decode_critical_path.py", "tools/arch_budget_v41.py",
            "tools/dsrom_qelem_pipeline_pricing.py", "tools/dsrom_4096_partition_token_options.py",
            "configs/hardware/technology.json", str(CAP.relative_to(ROOT)),
            "rtl/v41rom/ot_v41_rom_elem_q_qt_w10.sv", "rtl/v41rom/ot_v41_rom_elem_qt_w10.sv")
    rec = dict(
        schema="opentallas.dsrom_qelem_pipeline_pricing.v1",
        git_head=git_head(),
        source_sha256={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in srcs if (ROOT / p).exists()},
        basis=dict(candidate="DS4096-TP4-S58 (base, no PAR2 term)", stages=S, head_dies=HEAD, table_dies=TABLE,
                   bf16_stripe_macros="2 x BF16_pairs_per_die (S58 row of partition_token_options.json)",
                   clock_hz=u.PRODUCT_CLOCK_HZ, cycle_ns=round(cyc_ns, 4), elem_stages=8,
                   serial_domain_hz=0.9e9, mtp=dict(positions=u.V41_POSITIONS, tau=u.V41_TAU,
                                                     draft_fraction_of_ar=u.V41_DRAFT_FRACTION,
                                                     step="verify pass (6 positions) + draft_fraction x AR token")),
        method=("Added cycles are injected as depth on each field matvec node of the scope (the element's fill "
                "latency; uarch_model._lat_cycles hook at the 1.2 GHz field clock), then cons_v41_rom re-solves the "
                "graph.  Depth is pure latency after issue in decode_critical_path.Graph.solve (f = max(start + "
                "issue, last input) + depth), so no element-op latency is hidden by streaming: each added cycle is "
                "paid once per matvec node on the critical path.  Element issue (II 1, throughput) is unchanged."),
        ops_per_token_derivation=(
            "Counted from the solved critical path: matvec nodes (price_matvec _uarch) on g.path(token.return).  The "
            "per-layer field chain on the AR path is attn.a_proj -> attn.wq_b -> attn.wo_a (BF16) -> attn.wo_b, "
            "ffn.router (BF16) -> ffn.experts_gu -> ffn.down: 5 q-element ops + 2 BF16-column ops a layer x 40 "
            "layers, + head.lm_head (BF16) = 200 q + 81 BF16.  The MTP verify pass (same graph, issue x 6, one depth "
            "per node) puts ffn.shared_gu on the path too: 240 q + 81 BF16; the 3/40 draft adds 0.075 x the AR "
            "delta.  mHC hc.fn is a hub op, not a field element.  See rows[*].census (k = 0) for the solved counts; "
            "ar_exposed_ops_equiv = delta token time / (k x 0.833 ns) cross-checks them."),
        rows=rows, recurrence_sensitivity=sens,
        uncertainty=[
            "The registered-go cycle is counted on every op.  It is hideable only if the sequencer issues go one "
            "cycle early (the x stream already leads go or the controller pre-asserts); the model does not credit "
            "that, so +1 is an upper bound for the go register.",
            "The datapath cycles are priced as fill latency (outside the chunk-8 adder recurrence).  A cycle inside "
            "the recurrence also stretches issue (8 x LAT floor): see recurrence_sensitivity.",
            "elem_fill 78 is inherited from W2 and not remeasured on the W10 element (w10_baseline_model pending); "
            "the per-cycle cost is independent of that absolute value as long as the critical path does not move.",
            "Scope q excludes the BF16-column matrices; if the shared ot_v41_rom_elem_w10 base is pipelined for "
            "BF16 = 1 too, use scope all."],
        not_adopted=True, rtl_or_pnr=False)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n")
    print("wrote", out)


if __name__ == "__main__":
    main()
