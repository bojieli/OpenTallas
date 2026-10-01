#!/usr/bin/env python3
"""Source-pinned modeled accounting; no RTL, evaluation, adoption or headline edits.

Reuse the committed consolidation after verifying every declared input hash,
then rebuild the selected critical paths. Materialize sparse model
dependencies before running; missing optional receipts can change the model.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

ROOT = Path(subprocess.check_output(["git","rev-parse","--show-toplevel"],
                                  cwd=Path(__file__).resolve().parent,text=True).strip())


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def capacity(stacks, weight_bytes, state_bytes, expected, *, busiest=None):
    import uarch_model as U
    physical = stacks * U.HBM_STACK_B
    usable = physical * U.HBM_CAP_EFF
    allocatable = usable - weight_bytes
    users = int(allocatable // state_bytes) if busiest is None else busiest["users"]
    assert users == expected
    return dict(stacks=stacks, physical_bytes=physical, usable_bytes=usable,
                capacity_efficiency=U.HBM_CAP_EFF, reserve_bytes=physical-usable,
                shared_weights_in_hbm_bytes=weight_bytes,
                per_user_logical_kv_and_index_bytes=state_bytes,
                usable_after_shared_weights_bytes=allocatable,
                modeled_users=users, busiest_die=busiest,
                rule="floor((usable HBM - one shared weight copy) / per-user state)"
                if busiest is None else "busiest-die shard limit; aggregate division is not the capacity rule")


def build(c):
    import uarch_model as U
    import arch_budget_qwen3 as Q
    h = next(p for p in c["v41_rom"]["points"] if p.get("product_final"))
    dh = next(p for p in c["hbm"]["v41_sweep"]
              if p["tp"] == 96 and p["stacks_per_die"] == 4 and p["replicas"] == 1)
    qh = next(p for p in c["hbm"]["qwen"] if p["dies"] == 2 and p["stacks"] == 8)
    qr = c["qwen_product_ss"]
    qc = c["qwen_rom"]["product_row"]
    wl, qkv = U._qwen_wl()
    dq = U.hbm_gpu_design("qwen")
    ops = U.qwen_hbm_ops(dq["element"], dq["barrier"]["boundary_cycles"], dq["drain_cycles"])
    qw = 2 * sum(b for b, _ in ops) - qkv
    dc = U.A._env()["c"]
    dk = di = dw = 0
    for layer in range(dc["num_layers"]):
        r = dc["compress_ratios"][layer]
        if layer in dc["kv_source_layer_ids"] and r:
            dk += 1048576 // r * U.A.CKV_ROW_B
            di += 1048576 // r * U.A.IDX_KEY_B
        dw += dc["window_tokens"] * U.A.WIN_ROW_B
    dstate = dk + di + dw
    assert dstate == U._v41_state_user()
    dwgt = U._V41_CFG["checkpoint_bytes"]
    rings = max(2, math.ceil(h["layers_per_stage"]))
    per_die = 1048576 * (U.A.CKV_ROW_B + U.A.IDX_KEY_B) / 4 + dc["window_tokens"] * U.A.WIN_ROW_B * rings
    die_usable = U.A.ROM_DIE_HBM_STACKS * U.HBM_STACK_B * U.HBM_CAP_EFF
    dbusy = dict(stacks=U.A.ROM_DIE_HBM_STACKS, usable_bytes=die_usable,
                 per_user_bytes=per_die, compressed_and_index_bytes=1048576*(U.A.CKV_ROW_B+U.A.IDX_KEY_B)/4,
                 window_ring_bytes=dc["window_tokens"]*U.A.WIN_ROW_B*rings, window_rings=rings,
                 users=int(die_usable//per_die), placement="TP-4 stage; uncompressed source layer is the busiest state shard")
    qfrac = U.QWEN_TP_SHAPE[4][1] / Q.Q["KV"]
    qbusy = dict(stacks=4, usable_bytes=4*U.HBM_STACK_B*U.HBM_CAP_EFF,
                 per_user_bytes=qkv*qfrac, users=int(4*U.HBM_STACK_B*U.HBM_CAP_EFF//(qkv*qfrac)),
                 kv_heads_per_die=U.QWEN_TP_SHAPE[4][1], placement="TP-4 whole GQA heads; two of eight KV heads per die")

    # Rebuild only the selected ROM point to expose the complete solved DAG,
    # rather than treating its top-eight-family summary as a full breakdown.
    graphs = []
    original_top = U._cons_top
    def capture(g, n=8):
        graphs.append(g)
        return original_top(g, n)
    U._cons_top = capture
    try:
        rebuilt = U.cons_v41_rom(h["stages"], h["head_dies"], h["table_dies"], 1.0, None,
                                "columns", U.PRODUCT_CLOCK_HZ, h["field_concurrency"], h["added_latency"],
                                U.PRODUCT_DYN_SCALE, h["slow_domain"], h["chain_stages"], h["elem_stages"],
                                h["ss_wire"], h["serial"], h["die"], h["vmh"], U.PRODUCT_HUB)
    finally:
        U._cons_top = original_top
    assert rebuilt["ar_tokens_s_b1"] == h["ar_tokens_s_b1"]
    g = graphs[0]
    sink = next(x for x in g.nodes if x.endswith("token.return"))
    families = original_top(g, len(g.nodes))
    categories = {}
    for x in g.path(sink):
        k = g.nodes[x]["kind"]
        categories[k] = categories.get(k, 0) + sum(g.contrib[x].values())*1e6
    dtotal = sum(categories.values())
    assert round(1e6/dtotal,1) == h["ar_tokens_s_b1"]
    qclock = qr["clock_hz"]
    qparts = dict(layer_body=36*qr["layer_chain_cycles"]/qclock*1e6,
                  collectives=qr["exchange"]["token_cycles"]/qclock*1e6,
                  kv_prep=qr["kv_prep_cycles"]/qclock*1e6)
    qbase = qr["cycles"]/qclock*1e6
    qparts["head_embedding_and_other"] = qbase-sum(qparts.values())
    qparts["droop_schedule"] = qbase*(1/qr["droop"]["droop_rate"]-1)
    qtotal = sum(qparts.values())
    assert round(1e6/qtotal,1) == qr["tokens_s_b1"]
    qstream, peak = U.stream_overlap(ops, dq["hbm_Bpc"], dq["sm_count"]*128,
                                     dq["staging_kb_per_sm"]*1024*dq["sm_count"])
    qh_us = qstream/dq["clock_hz"]*1e6
    assert round(1e6/qh_us,1) == qh["ar_tokens_s_b1"]
    qh_service = dict(weight_hbm=qw/2/dq["hbm_Bpc"]/dq["clock_hz"]*1e6,
                      kv_hbm=qkv/2/dq["hbm_Bpc"]/dq["clock_hz"]*1e6)
    qh_service["exposed_tail_and_dependency_stalls"] = qh_us-sum(qh_service.values())
    assert qh_service["exposed_tail_and_dependency_stalls"] >= 0
    ds_parts = U._hbm_chain_n(96, 32, 1)
    wire = U.hbm_ss_wire_delta(4)
    dv = U.hbm_gpu_design("v41")
    for k in ("sm_matvec", "x_broadcast_fill", "dedicated_and_su", "verify_extra_issue", "barrier"):
        ds_parts[k] *= dv["clock_hz"]/U.PRODUCT_CLOCK_HZ
    ds_parts["barrier"] *= (dv["barrier"]["boundary_cycles"]+wire["boundary_extra_cycles"])/dv["barrier"]["boundary_cycles"]
    ds_parts["collective_latency"] += wire["collectives"]*wire["collective_extra_cycles"]/U.PRODUCT_CLOCK_HZ*1e6
    assert abs(sum(ds_parts.values())-dh["chain_us_ar"]) <= 0.051
    w19 = U.HBM_W19
    assert abs(sum(w19["parts_us_fused"].values())-w19["ar_us"]) < 1e-9
    rows = [
        dict(design="Qwen3-8B ROM option C", context_tokens=8192, dies=4,
             capacity=capacity(16,0,qkv,qr["capacity_users"],busiest=qbusy),
             weight_storage=dict(location="ROM, shared by users", hbm_payload_equivalent_bytes=qw,
                                 rom_bit_reference=U._qwen_rom_bits(), payload_equivalent_is_not_physical_rom_bits=True,
                                 rom_bit_reference_scope="Original TP-2 placement bit ledger; target_bits_total is repartitioned over the four-die option C. stored_bits_per_die is not a current TP-4 per-die measurement."),
             cost=qc["capex_usd"], cost_components={k:qc[k] for k in ("die_usd","package_usd","hbm_usd","hardware_usd")}, critical_path=dict(total_us=qtotal, additive_parts_us=qparts,
                 clock_hz=qclock, rtl_attributed_as_built=qr["rtl_attributed_as_built"],
                 rtl_attributed_body_only=qr["rtl_attributed_body_only"],
                 calibration="Analytical SS target row. RTL-attributed alternatives are separate, not folded into this row.")),
        dict(design="Qwen3-8B HBM TP-2", context_tokens=8192, dies=2,
             capacity=capacity(8,qw,qkv,qh["capacity_users"]), cost=qh["cost"]["capex_usd"], cost_components=qh["cost"],
             critical_path=dict(total_us=qh_us, additive_parts_us=qh_service,
                 clock_hz=dq["clock_hz"], peak_staging_bytes=peak,
                 overlap="Prefetched fluid stream. HBM weight/KV service plus exposed residual equals total; dependent-op latency is overlapped and must not be added again.",
                 dependency_latency_sum_us=sum(lat for _,lat in ops)/dq["clock_hz"]*1e6)),
        dict(design="DeepSeek-V4.1 ROM product model", context_tokens=1048576, dies=h["dies"],
             capacity=capacity(h["hbm_stacks"],0,dstate,h["capacity_users_1m"],busiest=dbusy),
             weight_storage=dict(location="ROM, shared by users; no checkpoint charged to HBM", checkpoint_payload_equivalent_bytes=dwgt),
             cost=h["cost"]["capex_usd"], cost_components=h["cost"], critical_path=dict(total_us=dtotal, additive_parts_us=categories,
                 complete_family_breakdown_us=families, rounded_family_sum_us=sum(families.values()),
                 streaming_clock_hz=h["clock_hz"], serial_domain=h["slow_domain"],
                 in_order_su_exposure_caveat=U.cons_in_order_caveat(h["ar_tokens_s_b1"],h["mtp_tokens_s_b1"]),
                 scope="Solved product DAG with modeled fusion/interleaving. Complete families include rounding; core NAM variant is not part of this exact-fusion estimate.")),
        dict(design="DeepSeek-V4.1 HBM TP-96", context_tokens=1048576, dies=96,
             capacity=capacity(384,dwgt,dstate,dh["capacity_users_1m"]), cost=dh["cost"]["capex_usd"], cost_components=dh["cost"],
             critical_path=dict(analytical_chain_us=sum(ds_parts.values()), analytical_parts_us=ds_parts,
                 parallel_weight_sweep_us=dh["weight_sweep_us"],
                 analytical_total_us=max(sum(ds_parts.values()),dh["weight_sweep_us"]),
                 rule="max(chain, parallel weight sweep); no double counting",
                 w19_composed_total_us=w19["ar_us"], w19_composed_parts_us=w19["parts_us_fused"],
                 w19_scope="Source-composed modeled token, not connected full-token RTL or contextual SS/FF acceptance; separate from the analytical chain.",
                 mtp_verify_us=w19["mtp_pass_us"], mtp_verify_parts_us=w19["mtp_parts_us_fused"], drafter_us=w19["drafter_us"]))]
    return dict(rows=rows, deepseek_logical_state=dict(compressed_kv_bytes=dk,index_bytes=di,window_bytes=dw),
                qwen_kv_format=Q.KV_FMT_SPEC, hbm_alternatives=c["hbm"]["qwen"][1:],
                manufacturing_cost_assumptions=c["fab"], inherited_model_caveats=c["model_caveats"])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--basis-record", type=Path, default=ROOT/"results/uarch/consolidation.json")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    sys.path.insert(0,str(ROOT/"tools"))
    reads=set()
    def audit(event,args):
        if event=="open" and isinstance(args[0],str):
            try: p=Path(args[0]).absolute().relative_to(ROOT)
            except ValueError: return
            if (ROOT/p).is_file() and p.suffix in (".py",".json") and not str(p).startswith("results/quality/w16_"):
                reads.add(str(p))
    sys.addaudithook(audit)
    import uarch_model as U
    c=json.loads(a.basis_record.read_text()); pins=dict(c["source_sha256"])
    assert all(digest(ROOT/p)==v for p,v in pins.items()), "committed consolidation input drift"
    basis=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
    result=build(c)
    pins.update({p:digest(ROOT/p) for p in list(reads)})
    for module in list(sys.modules.values()):
        path=getattr(module,"__file__",None)
        if not path: continue
        try: rel=Path(path).resolve().relative_to(ROOT)
        except ValueError: continue
        if rel.suffix==".py":pins[str(rel)]=digest(ROOT/rel)
    pins[str(Path(__file__).resolve().relative_to(ROOT))]=digest(__file__)
    result.update(schema="opentallas.w16.four-design-modeled-accounting.v1",
                  observed_utc=datetime.now(timezone.utc).isoformat(),basis=basis,source_sha256=pins,
                  extraction="Reused committed consolidation with all declared source pins matching current files; independently reconstructed selected ROM/HBM paths and capacity. A redundant whole-sweep CPU extraction was stopped after establishing exact pin equivalence; no verdict was discarded.",
                  objective="Minimum single-user decode latency primary; independent-request batching secondary.",
                  qualification="Modeled accounting only. No full-product timing, hardware adoption or SS/FF claim. No headline edits. Costs are manufacturing capex with model mask assumptions, not GPU purchase prices; capacity counts storage fit, not concurrent speed or throughput.",
                  shared_weights_rule="One weight copy per TP group shared by users. Replicated independent groups duplicate weights; this artifact uses one group per design.",
                  nam_adoption=False, full_qcnam_verdict=None,
                  nam_scope="Definitive completed-core failure excludes the tested DeepSeek QC-NAM variant as eligible gain; full verdict remains pending all-lane guard. Exact fusion remains separately gated.",
                  calibration="Historical reduced W11 cycle ratios are not multiplied into these product rows. Qwen body/collective attribution and DeepSeek in-order exposure remain separate caveats.")
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open("x") as f:json.dump(result,f,indent=2,default=str);f.write("\n")
    print(json.dumps([{k:r[k] for k in ("design","cost")} | {"capacity_users":r["capacity"]["modeled_users"]} for r in result["rows"]]))


if __name__=="__main__": main()
