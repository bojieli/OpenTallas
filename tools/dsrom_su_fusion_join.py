#!/usr/bin/env python3
"""Join saved SU baseline and fusion measurements; never run inference or RTL.

This is a component comparison, not an adoption record. Clock, routing,
transport and storage qualification remain separate from functional evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def completion(chain):
    node = chain["nodes"][-1]
    op = chain["per_op"][node["op"]]
    return op["last_result"] if node["event"] == "result" else op["last_write"]


def quant_node(name, variant):
    if variant == "hc":
        return name.replace("hc_pre_norm", "quant")
    if variant == "q":
        return name.replace("q_norm", "q_quant")
    return name.replace("kv_norm_rope", "kv_rope_qdq")


def footprint(params):
    n, d = params["N"], params["D"]
    nv = (d + n - 1) // n
    return {
        "replicas_per_die": 1,
        "lanes": n,
        "input_bits_per_cycle": (4 if params["HC"] else 1) * n * 32,
        "gain_load_bytes_per_cycle": n * 4,
        "normalised_output_bits_per_cycle": n * 32,
        "quant_output_bits_per_cycle": n // 32 * (256 + 10 + 512),
        "retained_x_bits": n * nv * 32,
        "retained_gain_bits": n * nv * 32,
        "gain_load_cycles_per_row_if_cold": nv,
        "gain_load_overlap_measured": False,
        "coefficient_fanout": n,
        "x_gain_read_selection": {"banks": n, "words_per_bank": nv,
                                  "word_bits": 32, "selectors_per_bank": 2},
        "area_um2": None,
        "routing_tracks": None,
        "floorplan_fit": None,
        "cost_status": "ESTIMATE: source-counted storage/ports; area, muxes, fanout and corridor unpriced",
    }


def join(baseline, quant, anatomy, comp, norm_dir, source_root):
    require(baseline["status"] == "pass", "baseline failed")
    require(baseline["config"] == dict(baseline["config"], N=1024, M=256,
            BCAST=22, RET=15, MLAT=5, ALAT=4), "unexpected baseline geometry")
    require(quant["exact"] is True, "baseline quant failed")
    meta = read(norm_dir / "cases.json")
    require(meta["cases_pkl_sha256"] == baseline["cases_sha256"], "operand source mismatch")
    chains = {c["chain"]: c for c in baseline["chains"]}
    parts = {c["chain"]: c for c in anatomy["chains"]}
    patches = {p["node"]: p for p in comp["patches"]}
    rows = []
    measurements = []
    for variant, n in (("hc", 1024), ("q", 256), ("kv", 512)):
        full_path = norm_dir / f"run_{variant}_dpi_N{n}.json"
        rtl_path = norm_dir / f"run_{variant}_rtl_N64.json"
        full, rtl = read(full_path), read(rtl_path)
        require(full["status"] == rtl["status"] == "pass", f"{variant}: failed run")
        require(full["fp"] == "dpi" and rtl["fp"] == "rtl", "arithmetic implementations")
        require(full["variant"] == rtl["variant"] == variant, "variant mismatch")
        require(full["params"]["N"] == n and rtl["params"]["N"] == 64, "lane shape mismatch")
        for key in ("D", "HC", "RD", "QUANT", "RW", "BW", "HUB_IN", "HUB_OUT"):
            require(full["params"][key] == rtl["params"][key], f"parameter mismatch: {key}")
        for run in (full, rtl):
            require(run["rows"] and all(r["ok"] is True and r["fault"] == 0 and
                    all(r[k] == 0 for k in ("err_y", "err_ro", "err_q"))
                    for r in run["rows"]), "exactness or fault failure")
            for path, digest in run["source_sha256"].items():
                require(sha(source_root / path) == digest, f"source drift: {path}")
        rtl_rows = {r["case"]: r for r in rtl["rows"]}
        require(set(rtl_rows) == {r["case"] for r in full["rows"]}, "missing RTL comparison case")
        measurements.append(dict(variant=variant, full_shape_sha256=sha(full_path),
                                 rtl_N64_sha256=sha(rtl_path), cost=footprint(full["params"])))
        for r in full["rows"]:
            if r["layer"] == "stress":
                continue
            name = r["case"]
            require(name in chains, f"missing baseline chain: {name}")
            c = chains[name]
            require(c["exact"] is True and all(x["bit_exact"] for x in c["checks"]), "baseline chain exactness")
            qname = quant_node(name, variant)
            q = quant["nodes"].get(qname)
            require(q is not None or name == "head.hc_pre_norm", "missing baseline quant endpoint")
            if q is not None:
                require(q["exact"] is True and q["blocks"] * 32 == r["D"], "quant shape mismatch")
            require(r["checked_y"] == r["D"] and r["checked_q"] * 32 == r["D"], "incomplete comparison")
            require(r["checked_ro"] == (r["D"] if variant == "kv" else 0), "RoPE comparison coverage")
            small = rtl_rows[name]
            require((r["checked_y"], r["checked_q"], r["checked_ro"]) ==
                    (small["checked_y"], small["checked_q"], small["checked_ro"]), "RTL coverage mismatch")
            covered = [nd["node"].partition(":")[0] for nd in c["nodes"]]
            covered = [nd if nd.startswith("head.") else f"{c['layer']}.{nd}" for nd in covered]
            if q is not None and qname not in covered:
                covered.append(qname)
            cdc = sum(patches.get(nd, {}).get("cdc_measured_us", 0) or 0 for nd in covered)
            base_cycles = completion(c) + (q["qdq_wired_cycles"] if q else 0)
            base_us = base_cycles / 900
            landing = r["q_last"] if q else r["y_last"]
            fused_us = landing / 1200
            rows.append(dict(
                chain=name, shape=dict(elements=r["D"], quant_blocks=r["checked_q"]),
                compared_endpoint="quantised output" if q else "normalised output (no head quant baseline)",
                covers=covered, exact_saved_operands=True,
                baseline=dict(wired_cycles=base_cycles, component_us=base_us,
                              cdc_us=cdc, with_saved_cdc_us=base_us + cdc,
                              categories_cycles=parts[name]["categories"]),
                candidate=dict(reported_landing_cycles=landing,
                               actual_observer_cycles=landing - full["params"]["HUB_OUT"],
                               output_wire_budget_cycles=full["params"]["HUB_OUT"],
                               component_plus_output_budget_us=fused_us,
                               with_retained_saved_cdc_us=fused_us + cdc,
                               cdc_removal_measured=False, gain_load_inside_interval=False),
                conditional_component_delta_us=base_us - fused_us,
                remaining_dependencies=["chunk8 sequential sums and golden pairwise tree",
                    "scalar divide/epsilon/rsqrt and result broadcast",
                    "retained lane x and gain reads after reduction",
                    "cross-lane adjacent-pair rotation" if variant == "kv" else "32-lane quantiser reduction",
                    "final VM publication/consumer lease and output credits unmeasured"],
                bypass=dict(lane_local_register_bypass_edges=2 if variant == "hc" else 0,
                            lane_local_register_bypass_description="HC mix op0->op1->op2" if variant == "hc" else "none: reduction and broadcast remain",
                            retained_cross_lane_edges=2 + (1 if variant == "kv" else 0),
                            intermediate_VM_roundtrips_removed="mix -> reduction -> scalar -> scale -> quant",
                            replaced_by="lane x registers and scalar result/broadcast; golden rounding unchanged",
                            cross_lane_waits_removed=False),
                adoption="HOLD: output transport budget, cold gain load, finite credits, area/corridor/SSFF unqualified"))
    return dict(schema="opentallas.dsrom-su-fusion.join.v1", verdict="UNVALIDATED_COMPONENT_COMPARISON",
                adoption=False, token_gain=None, measurements=measurements, rows=rows,
                cases_sha256=baseline["cases_sha256"],
                timing_authority="tools/dsrom_1m_allmeasured.py (Maxwell)",
                scope="saved actual RTL comparisons only; no golden regeneration, no token result, no CDC removal claim")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--norm-dir", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    base = a.root / "results/rtl/dsrom_1m_allmeasured_20261004"
    rec = a.root / "results/rtl/dsrom_recovery_20261004"
    inputs = [base / "su_runs/su_N1024_M256_b22r15m5a4_dpi_beh.json",
              base / "su_qdq_wired.json", rec / "su_chains/anatomy.json", rec / "composition.json"]
    result = join(*(read(p) for p in inputs), a.norm_dir, a.root)
    result["inputs_sha256"] = {str(p.relative_to(a.root)): sha(p) for p in inputs}
    result["tool_sha256"] = sha(__file__)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, indent=2) + "\n")
    print(result["verdict"], len(result["rows"]), "source-bound chains; adoption=false")


if __name__ == "__main__":
    main()
