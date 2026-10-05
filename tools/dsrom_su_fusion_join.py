#!/usr/bin/env python3
"""Join saved SU baseline and fusion measurements; never run inference or RTL.

This is a component comparison, not an adoption record. Clock, routing,
transport and storage qualification remain separate from functional evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
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


def transport_join(result, baseline, source_root, cached_manifest):
    """Consume actual valid/data landings; distribute elapsed time once."""
    require(result["pass"] is True, "transport failed")
    require(result["source"]["clock_hz"] == 1200000000, "transport clock changed")
    require(result["source"]["params"]["REGISTER_OUTPUT"] == 1, "transport not enabled")
    require(result["source"]["cached_files_sha256"] == cached_manifest, "cached payload source drift")
    for path, digest in result["source"]["source_sha256"].items():
        require(sha(source_root / path) == digest, "transport source drift: " + path)
    events = {}
    for line in result["boundary_events"]:
        m = re.fullmatch(r"SU_BOUNDARY (\w+) cycle=(\d+)(?: vector=(\d+))?", line)
        require(m is not None, "malformed boundary event")
        event, cycle, vector = m.groups()
        events.setdefault(event, []).append((int(cycle), int(vector) if vector is not None else None))
    go, = events["go"]
    require(go[0] == result["go"], "go identity mismatch")
    for kind in ("y", "q"):
        raw, landed = events["raw_" + kind], events["consumer_" + kind]
        require(len(raw) == len(landed) == 5, "incomplete output stream")
        for index, (a, b) in enumerate(zip(raw, landed)):
            require(a[1] == b[1] == index and b[0] - a[0] == 23, "transport order/delay mismatch")
    gain = events["gain_load"]
    require([v for _, v in gain] == list(range(5)) and gain[-1][0] < go[0], "gain availability changed")
    require(events["consumer_q"][-1][0] - go[0] == result["q_last"], "endpoint mismatch")
    chain = next(c for c in baseline["chains"] if c["chain"] == "L20.attn.hc_pre_norm")
    names = [nd["node"] for nd in chain["nodes"]] + ["attn.quant"]
    boundaries = [events[k][-1][0] for k in
                  ("mix_output", "sumsq_root", "reduction_scalar", "raw_y", "consumer_q")]
    nodes, prev, bprev = [], go[0], 0
    for index, (name, end) in enumerate(zip(names, boundaries)):
        if index < 4:
            nd = chain["nodes"][index]
            op = chain["per_op"][nd["op"]]
            bend = op["last_result"] if nd["event"] == "result" else op["last_write"]
        else:
            bend = completion(chain) + 210  # checked against the wired quant record by caller
        nodes.append(dict(node="L20." + name, baseline_cycles=bend - bprev,
                          baseline_us=(bend - bprev) / 900,
                          candidate_cycles=end - prev, candidate_us=(end - prev) / 1200,
                          candidate_boundary_cycle=end,
                          endpoint="actual registered quant landing" if index == 4 else "actual internal dependency edge"))
        prev, bprev = end, bend
    require(sum(n["candidate_cycles"] for n in nodes) == result["q_last"], "double counted candidate")
    return dict(chain=chain["chain"], nodes=nodes, actual_transport_cycles=23,
                gain_load_cycles=5, gain_first_to_output_cycles=boundaries[-1] - gain[0][0],
                gain_loaded_to_go_wait_cycles=go[0] - gain[-1][0],
                input_first_available_cycle=events["lane_input"][0][0],
                input_last_available_cycle=events["lane_input"][-1][0],
                wall_us=dict(baseline_component=bprev / 900, candidate_go_to_output=result["q_last"] / 1200,
                             candidate_first_gain_to_output=(boundaries[-1] - gain[0][0]) / 1200),
                cdc="not in component: use graph crossings once; no zero-CDC adoption",
                gate="component functional/transport PASS; credits/VM lease/area/corridor/SSFF HOLD")


def hcpost_join(run, metadata, baseline, pins, source_root):
    """Only accept the actual NG256 terminal, never extrapolate reduced cases."""
    require(run["ng"] == metadata["ng"] == 256, "HC-post full NG256 required")
    require(run["win"] == 33 and run["wout"] == 23, "HC-post wire geometry")
    require(run.get("ml", 5) == 5 and run.get("al", 4) == 4, "HC-post arithmetic stages")
    require(metadata["cases_pkl_sha256"] == baseline["cases_sha256"], "HC-post operands differ")
    for path, digest in pins["source_sha256"].items():
        require(sha(source_root / path) == digest, "HC-post source drift: " + path)
    require(run["rows"] and all(r["pass_"] is True and r["errors"] == r["fault"] == 0
            and r["words"] == 20480 for r in run["rows"]), "HC-post exactness/coverage")
    require({r["name"] for r in run["rows"]} == {r["name"] for r in metadata["cases"]},
            "missing HC-post terminal cases")
    chains = {c["chain"]: c for c in baseline["chains"]}
    rows = []
    for r in run["rows"]:
        if r["kind"] != "golden_1m":
            continue
        require(r["name"] in chains and chains[r["name"]]["exact"] is True, "HC-post baseline mismatch")
        require(r["beats"] == 20 and r["cycles"] == r["last_out"] + 1 and
                r["last_out"] - r["first_out"] == 19, "HC-post stream/endpoints")
        c = chains[r["name"]]
        b = completion(c)
        final_op = c["per_op"][c["nodes"][-1]["op"]]
        result_event = final_op["last_result"]
        rows.append(dict(chain=r["name"], baseline_wired_cycles=b, baseline_component_us=b / 900,
                         baseline_final_result_cycle=result_event,
                         baseline_result_tail_after_write_cycles=(result_event - b) if result_event is not None else 0,
                         result_tail_note="publication endpoint only; model required reducer/busy/lease dependencies separately, never remove them by assumption",
                         candidate_registered_landing_cycles=r["cycles"], candidate_component_us=r["cycles"] / 1200,
                         conditional_component_delta_us=b / 900 - r["cycles"] / 1200,
                         golden_exact_words=r["words"], sumsq_result_included=False,
                         physical_verdict=pins["model"].get("selected_physical_verdict", "UNKNOWN"),
                         retained_dependencies=["final VM publication/credits/consumer lease",
                            "next HC mix sumsq reducer remains its own graph branch"],
                         cdc="outside component; graph edge charging once by Maxwell", adoption=False))
    require(len(rows) == 8, "missing representative HC-post chain")
    return dict(full_shape_exact=True, rows=rows, cases=len(run["rows"]),
                verdict="UNVALIDATED_COMPONENT_COMPARISON",
                cost=pins["model"], gate=pins["model"].get("selected_physical_verdict", "UNKNOWN") +
                "; functional component only; no area/corridor/SSFF/composed-rate adoption")


def swiglu_join(directory, baseline, quant, source_root):
    metadata = read(directory / "cases.json")
    require(metadata["su_cases_sha256"] == baseline["cases_sha256"], "SwiGLU operands differ")
    runs = [read(p) for p in directory.glob("run*.json")]
    full, = [r for r in runs if r["W"] == 1024 and r["fp"] == "dpi_beh"]
    rtl, = [r for r in runs if r["W"] == 64 and r["fp"] == "rtl"]
    for run in (full, rtl):
        require(run["status"] == "pass" and run["NIN"] == 33 and run["NOUT"] == 23,
                "SwiGLU run/wire failure")
        require(run["clock_hz"] == 1200000000, "SwiGLU clock drift")
        for path, digest in run["source_sha256"].items():
            require(sha(source_root / path) == digest, "SwiGLU source drift: " + path)
        require(all(r["exact"] is True and r["a_errors"] == r["q_errors"] == 0 and
                r["blocks_checked"] * 32 == r["elements"] for r in run["rows"]), "SwiGLU exactness")
    small = {r["case"]: r for r in rtl["rows"]}
    chains = {c["chain"]: c for c in baseline["chains"]}
    rows = []
    for r in full["rows"]:
        require(r["case"] in small and small[r["case"]]["elements"] == r["elements"], "SwiGLU coverage")
        if r["case"].startswith("random."):
            continue
        layer, fn = r["case"].split(".", 1)
        name = f"{layer}.ffn.{fn}"
        require(name in chains and chains[name]["exact"] is True, "SwiGLU baseline")
        require(r["elements"] == (3456 if r["routed"] else 576), "SwiGLU TP4 shape")
        q = quant["nodes"][f"{layer}.ffn." + ("quant2" if r["routed"] else "shared_quant")]
        require(q["exact"] is True and q["blocks"] == r["blocks_checked"], "SwiGLU quant baseline")
        require(r["cycles"] == r["last_out"] - r["first_in"] + 1, "SwiGLU interval convention")
        c = chains[name]
        b = completion(c) + q["qdq_wired_cycles"]
        rows.append(dict(chain=name, golden_exact_elements=r["elements"],
                         baseline_component_cycles=b, baseline_component_us=b / 900,
                         candidate_component_cycles=r["cycles"], candidate_component_us=r["cycles"] / 1200,
                         candidate_activation_cycles=r["act_last"] - r["first_in"] + 1,
                         candidate_quant_transport_cycles=r["last_out"] - r["act_last"],
                         conditional_component_delta_us=b / 900 - r["cycles"] / 1200,
                         baseline_route_weight_already_fused_as_E2=r["routed"],
                         extra_route_w_latency_added=False,
                         graph_warning="baseline chain_swiglu already multiplies route weight: Maxwell must check separate graph route_w before composition",
                         remaining_dependencies=["silu FP32 dependency chain", "32-lane quantiser reduction",
                                                  "finite final VM/consumer credits and graph CDC"], adoption=False))
    require(len(rows) == 8, "missing SwiGLU representative chains")
    return dict(rows=rows, full_shape_exact=True, token_gain=None, ss_ff=None,
                verdict="UNVALIDATED_COMPONENT_COMPARISON")


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
    ap.add_argument("--transport", type=Path)
    ap.add_argument("--cached-manifest", type=Path)
    ap.add_argument("--hcpost-run", type=Path)
    ap.add_argument("--hcpost-cases", type=Path)
    ap.add_argument("--hcpost-pins", type=Path)
    ap.add_argument("--swiglu-dir", type=Path)
    a = ap.parse_args()
    base = a.root / "results/rtl/dsrom_1m_allmeasured_20261004"
    rec = a.root / "results/rtl/dsrom_recovery_20261004"
    inputs = [base / "su_runs/su_N1024_M256_b22r15m5a4_dpi_beh.json",
              base / "su_qdq_wired.json", rec / "su_chains/anatomy.json", rec / "composition.json"]
    result = join(*(read(p) for p in inputs), a.norm_dir, a.root)
    result["inputs_sha256"] = {str(p.relative_to(a.root)): sha(p) for p in inputs}
    result["tool_sha256"] = sha(__file__)
    if a.transport:
        require(a.cached_manifest is not None, "need original cached payload manifest")
        require(read(inputs[1])["nodes"]["L20.attn.quant"]["qdq_wired_cycles"] == 210,
                "wired quant reference changed")
        result["actual_registered_transport"] = transport_join(
            read(a.transport), read(inputs[0]), a.root, read(a.cached_manifest))
        result["inputs_sha256"].update({str(p): sha(p) for p in (a.transport, a.cached_manifest)})
    if a.hcpost_run:
        require(a.hcpost_cases is not None and a.hcpost_pins is not None, "HC-post provenance required")
        result["hcpost"] = hcpost_join(read(a.hcpost_run), read(a.hcpost_cases), read(inputs[0]),
                                        read(a.hcpost_pins), a.root)
        result["inputs_sha256"].update({str(p): sha(p) for p in (a.hcpost_run, a.hcpost_cases, a.hcpost_pins)})
    if a.swiglu_dir:
        result["swiglu"] = swiglu_join(a.swiglu_dir, read(inputs[0]), read(inputs[1]), a.root)
        result["inputs_sha256"].update({str(p): sha(p) for p in a.swiglu_dir.glob("*.json")})
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, indent=2) + "\n")
    print(result["verdict"], len(result["rows"]), "source-bound chains; adoption=false")


if __name__ == "__main__":
    main()
