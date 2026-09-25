#!/usr/bin/env python3
"""Per-operator critical path of one decode token: a reporting wrapper.

The machinery that used to live here -- the operator dependency graph, its
pricing with this repository's measured RTL depths, the collective algorithms
and the fabric -- is now ``src/opentallas/critical_path.py``, and
``roofline.evaluate`` prices EVERY point of every roofline study with it
(``roofline.serial_step``).  This tool only reports the attribution behind the
headline points:

* the Taalas HC1 gate (Llama-3.1-8B on the reconstructed HC1 die) and
  Qwen3-8B on the same die, straight from ``roofline.taalas_hc1_anchor``;
* the DeepSeek-V4.1-Flash N5 array and wafer designs at batch 1, 64 and 4,096,
  rebuilt from the committed study rows (``results/roofline/candidates/
  deepseek-v41-flash/n5_vs_b200/points.json``) -- the chosen tensor group, the
  microbatch, the stream-unit width and the sweep are the row's own;
* for those two designs at batch 1, the step with each reduction algorithm
  forced, and with each tensor group the study searched.

For every target it writes the per-category breakdown of the critical path,
the per-layer path, the longest serial steps and the census of every
collective (operation, span, payload, algorithm, latency).  Output:
results/roofline/critical_path/decode_critical_path.json.  Rerun it after the
studies (``python3 tools/run_roofline_studies.py --force``).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "src"))

import decode_targets  # noqa: E402
import hdc_isa as I  # noqa: E402
import hdc_timing  # noqa: E402

from opentallas import critical_path as C  # noqa: E402
from opentallas.roofline import (  # noqa: E402
    AreaSplit,
    DeviceBudget,
    StaticPower,
    Technology,
    Topology,
    evaluate,
    taalas_hc1_anchor,
)
from opentallas.schema import ModelProfile  # noqa: E402

SCHEMA = "opentallas.decode-critical-path.v2"
OUT = ROOT / "results/roofline/critical_path/decode_critical_path.json"
TECH = ROOT / "configs/hardware/technology.json"
LLAMA = ROOT / "configs/models/anchors/llama-3.1-8b.json"
QWEN = ROOT / "configs/models/qwen3-8b.json"
V41 = ROOT / "configs/models/candidates/deepseek-v4.1-flash.json"
V41_POINTS = ROOT / "results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/points.json"
RESULTS = ROOT / "results/roofline"
LEGACY = ROOT / "results/roofline/critical_path/legacy_serial_model_targets.json"
ARRAY_DESIGN = "DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-array-hw-hybrid-x188"
WAFER_DESIGN = "DeepSeek-V4.1-Flash/ROM-N5-native-HBMKV-wafer-hybrid-x12"
PHYS = ROOT / "results/physical_abi3/asap7/hdc"
CLOCK_BLOCKS = ["ot_hdc_matvec", "ot_hdc_stream", "v41/ot_hdc_softplus", "v41/ot_hdc_select_k512",
                "v41/ot_hdc_blockdot", "v41/ot_hdc_actquant", "v41/ot_hdc_fp4qdq"]
BATCHES = (1, 64, 4096)


def select_latency(k: int, ascending_index: bool, extra: int = 2) -> int:
    """ot_hdc_select: cycles from the segment's last accepted element to the first output."""
    return k + extra + (k if ascending_index else 0)


def physical(block: str) -> dict:
    return json.loads((PHYS / block / "physical.json").read_text())["design"]


def routed_clock() -> tuple[float, list[dict]]:
    rows = [dict(block=b, fmax_hz=physical(b)["fmax_hz"], closed=physical(b)["closed"]) for b in CLOCK_BLOCKS]
    return min(r["fmax_hz"] for r in rows), rows


def rtl_constant_check(tech: Technology) -> dict[str, list]:
    """The technology table's datapath depths against the RTL timing model they were copied from."""
    rom = C.RomDatapath.from_technology(tech)
    K = hdc_timing.K
    su = {name: K["su_depth"][getattr(I, "SFU_" + name)] for name in ("NONE", "EXP", "RECIP", "RSQRT", "SIGM")}
    pairs = {
        "seq_gap": (rom.seq_gap, K["seq_gap"]), "idle_reg": (rom.idle_reg, K["idle_reg"]),
        "me_lat": (rom.me_lat, K["me_lat"]), "me_tree": (rom.me_tree, K["me_tree"]),
        "red_tail": (rom.red_tail, K["red_tail"]), "interleave": (rom.interleave, I.INTERLEAVE),
        "su_none": (rom.su_none, su["NONE"]), "su_exp": (rom.su_exp, su["EXP"]),
        "su_recip": (rom.su_recip, su["RECIP"]), "su_rsqrt": (rom.su_rsqrt, su["RSQRT"]),
        "su_sigm": (rom.su_sigm, su["SIGM"]),
        "stream_lane_area_um2": (rom.su_lane_um2, physical("ot_hdc_stream")["area_um2"]),
        "clock_hz": (rom.clock_hz, routed_clock()[0]),
    }
    return {k: [a, b] for k, (a, b) in pairs.items() if not math.isclose(float(a), float(b), rel_tol=1e-6)}


def machine_from_row(row: dict) -> tuple[C.MachineSpec, tuple | None]:
    """The priced machine a committed study row was evaluated on."""
    single = row["topology_kind"] == "single_chip" or row["parallelism"] == "none"
    expert = row["parallelism"] == "expert"
    parts = int(row["device_count"])
    m = C.MachineSpec(family=row["family"], group=1 if single else int(row["tensor_group"]),
                      microbatch=float(row["microbatch_per_slot"]), clock_hz=float(row["serial_clock_hz"]),
                      su_width=int(row["stream_unit_width"] or 16), kv_in_hbm=row["kv_store"] == "hbm",
                      multi_stage=int(row["pipeline_stages"]) > 1, expert_parallel=expert,
                      ep_span=parts if expert else 1,
                      ep_tokens_per_node=float(row["microbatch_per_slot"]) / parts if expert else 0.0)
    links = None if single else (row["intra_link"], row["link"], int(row["intra_domain_size"]),
                                 parts if expert else 0)
    return m, links


def attribute(tech: Technology, model: ModelProfile, row: dict, *, layers: set | None = None,
              algorithm: str = "best") -> dict:
    m, links = machine_from_row(row)
    sg = C.serial_graph(tech, model, context_tokens=int(row["context_tokens"]), machine=m, fabric_links=links,
                        algorithm=algorithm)
    S, share = float(row["serial_sweep_s"]), float(row["serial_kv_share_of_sweep"])
    det = sg.detail(S * (1 - share), S * share, layers=layers)
    hops = C.price_stage_hops(tech, sg.shape, stages=int(row["pipeline_stages"]), fabric_links=links,
                              group=m.group, microbatch=m.microbatch)
    hop_s = hops["latency_s"] + hops["bytes_s"]
    det["breakdown_s"]["pipeline_hops"] += hop_s
    critical = det["critical_path_s"] + hop_s
    step = max(critical, S)
    det.update(critical_path_s=critical, token_period_s=step, tokens_s_per_user=1.0 / step,
               sweep_s=S, pipeline_hop_events=hops["events"], graph_nodes=len(sg.graph.nodes))
    return det


def study_row(points: list, design: str, batch: int) -> dict:
    for q in points:
        if q["design"] == design and q["batch_size"] == batch:
            return q
    raise KeyError((design, batch))


def pick_design(points: list, preferred: str, marker: str) -> str:
    names = {q["design"] for q in points}
    if preferred in names:
        return preferred
    rows = [q for q in points if marker in q["design"] and q["batch_size"] == 1 and q["feasible"]]
    return max(rows, key=lambda q: q["per_user_tokens_s"])["design"]


def summary_row(row: dict, det: dict) -> dict:
    return {
        "design": row["design"], "batch": row["batch_size"], "tensor_group": row["tensor_group"],
        "tensor_group_declared": row["tensor_group_declared"], "pipeline_stages": row["pipeline_stages"],
        "users_per_stage": row["microbatch_per_slot"], "stream_unit_width": row["stream_unit_width"],
        "study_tokens_s_per_user": row["per_user_tokens_s"], "study_aggregate_tokens_s": row["aggregate_tokens_s"],
        "tokens_s_per_user": det["tokens_s_per_user"], "token_period_s": det["token_period_s"],
        "critical_path_s": det["critical_path_s"], "sweep_s": det["sweep_s"],
        "breakdown_s": det["breakdown_s"], "collectives_per_layer": row["collectives_per_layer"],
        "collective_algorithms": row["collective_algorithms"],
        "legacy_layer_fixed_latency_s": row["legacy_layer_fixed_latency_s"],
        "legacy_link_latency_s": row["legacy_link_latency_s"],
        "per_layer_critical_path_us": det["per_layer_critical_path_us"],
        "top_serial_steps": det["top_serial_steps"], "collectives": det["collectives"],
        "tensor_group_search": row.get("tensor_group_search"),
    }


def budget_from(d: dict) -> DeviceBudget:
    """A DeviceBudget rebuilt from an artifact's design entry (its area split, rates and power are
    outputs of the floorplan, independent of the serial-latency model)."""
    t, sp, st = d["topology"], d["area_split_per_device"], d["static_power"]
    topo = Topology(kind=t["kind"], device_count=t["device_count"], parallelism=t["parallelism"], link=t["link"],
                    on_wafer_regions=t["on_wafer_regions"], intra_link=t["intra_link"],
                    intra_domain_size=t["intra_domain_size"], tensor_group_size=t["tensor_group_size"],
                    moe_fanout=t["moe_fanout"])
    split = AreaSplit(total_mm2=sp["total_mm2"], rom_mm2=sp["rom_mm2"], compute_mm2=sp["compute_mm2"],
                      sram_mm2=sp["sram_mm2"], interconnect_mm2=sp["interconnect_mm2"], hbm_phy_mm2=sp["hbm_phy_mm2"],
                      overhead_mm2=sp["overhead_mm2"], policy=sp["policy"], reasons=tuple(sp["reasons"]))
    static = StaticPower(leakage_w=st["leakage_w"], clock_w=st["clock_w"], memory_interface_w=st["memory_interface_w"],
                         enumerated_w=st["enumerated_w"], floor_w=st["floor_w"], total_w=st["total_w"],
                         clock_frequency_hz=st["clock_frequency_hz"], detail=st["detail"])
    return DeviceBudget(name=d["name"], node=d["node"], topology=topo, split=split, weight_store=d["weight_store"],
                        kv_store=d["kv_store"], weight_amortization=d["weight_amortization"],
                        silicon_area_mm2_per_device=d["silicon_area_mm2_per_device"],
                        silicon_area_mm2_total=d["silicon_area_mm2_total"],
                        weight_capacity_bytes=d["weight_capacity_bytes"], kv_capacity_bytes=d["kv_capacity_bytes"],
                        weight_read_bytes_s=d["weight_read_bytes_s"], kv_read_bytes_s=d["kv_read_bytes_s"],
                        compute_ops_s=d["compute_ops_s"], shared_memory_path=d["shared_memory_path"],
                        cooling_limit_w=d["cooling_limit_w"], static_power=static, hbm_stacks=d["hbm_stacks"],
                        hbm_generation=d["hbm_generation"], native_formats=tuple(d["native_formats"]),
                        emulated_formats=d["emulated_formats"], provenance={}, reasons=tuple(d["reasons"]),
                        published_reference=d["published_reference"], rom_bank_pooling=d["rom_bank_pooling"])


def named_design_after(tech: Technology, entry: dict) -> dict:
    """One of the legacy snapshot's named designs, re-evaluated on the same budget with the serial path."""
    d = entry["budget"]
    model = ModelProfile.load(V41)
    budget = budget_from(d)
    rows = {}
    for batch in (1, 64, 1024, 4096):
        step = evaluate(budget, model, context_tokens=200_000, batch_size=batch, technology=tech,
                        execution_format=d["execution_format"])
        sl = step.metrics["serial_latency"]
        rows[batch] = dict(per_user=step.per_user_tokens_s if step.feasible else None,
                           aggregate=step.aggregate_tokens_s if step.feasible else None,
                           tensor_group=step.metrics["tensor_group"], pipeline_stages=step.metrics["pipeline_stages"],
                           intra_link=step.metrics["intra_link"],
                           chain_s=step.component_times_s["layer_fixed_latency"],
                           communication_s=step.component_times_s["link_latency"], sweep_s=sl["sweep_s"],
                           collectives_per_layer=sl["collectives_per_layer"],
                           collective_algorithms=sl["collective_algorithms"],
                           tensor_group_search=[dict(tensor_group=r["tensor_group"], intra_link=r["intra_link"],
                                                     tokens_s_per_user=1 / r["step_s"])
                                                for r in sl["tensor_group_search"]])
    aggs = [r["aggregate"] for r in rows.values() if r["aggregate"]]
    return {"design": entry["design"], "per_user_b1": rows[1]["per_user"], "per_user_b64": rows[64]["per_user"],
            "aggregate_b64": rows[64]["aggregate"], "aggregate_max_of_1_64_1024_4096": max(aggs) if aggs else None,
            "by_batch": rows}


def before_after(tech: Technology, rec: dict) -> dict:
    legacy = json.loads(LEGACY.read_text())
    after = decode_targets.targets(RESULTS)
    out: dict = {"legacy_source_commit": legacy["source_commit"], "targets": {}}
    for key in legacy["targets"]:
        out["targets"][key] = {"before": legacy["targets"][key], "after": after[key]}
    for key, entry in legacy["named_designs"].items():
        out["targets"][key] = {"before": {k: v for k, v in entry.items() if k != "budget"},
                               "after": named_design_after(tech, entry)}
    out["targets"]["hc1_llama31_8b"] = {
        "before": legacy["hc1_llama31_8b"],
        "after": {"per_user_b1": rec["hc1_llama31_8b"]["tokens_s_per_user"],
                  "ratio_to_published": rec["hc1_llama31_8b"]["modelled_over_published_rate"]}}
    out["targets"]["qwen3_8b_single_reticle"] = {
        "before": legacy["qwen3_8b_single_reticle"],
        "after": {"per_user_b1": rec["qwen3_8b_single_reticle"]["tokens_s_per_user"]}}
    return out


def build() -> dict:
    tech = Technology.load(TECH)
    rec: dict = dict(schema=SCHEMA, tool="tools/decode_critical_path.py",
                     machinery="src/opentallas/critical_path.py (priced by roofline.serial_step on every study point)")
    clock, rows = routed_clock()
    rec["clock"] = dict(hz=C.RomDatapath.from_technology(tech).clock_hz, routed_min_hz=clock, blocks=rows)
    rec["rtl_constant_mismatches"] = rtl_constant_check(tech)
    rec["serial_latency_inputs"] = tech.raw["serial_latency"]
    rec["determinism"] = C.DETERMINISM

    for key, path in (("hc1_llama31_8b", LLAMA), ("qwen3_8b_single_reticle", QWEN)):
        model = ModelProfile.load(path)
        chk = taalas_hc1_anchor(tech, model)
        step = chk.detail["step"]
        sl = step["metrics"]["serial_latency"]
        m = C.MachineSpec(family="rom", group=1, microbatch=1.0, clock_hz=sl["clock_hz"],
                          su_width=int(sl["stream_unit_width"]), kv_in_hbm=False)
        sg = C.serial_graph(tech, model, context_tokens=step["context_tokens"], machine=m, fabric_links=None)
        S, share = sl["sweep_s"], sl["kv_share_of_sweep"]
        det = sg.detail(S * (1 - share), S * share, layers={0, model.num_layers})
        out = dict(model=model.name, tokens_s_per_user=step["per_user_tokens_s"],
                   token_period_s=step["step_time_s"], critical_path_s=det["critical_path_s"], sweep_s=S,
                   breakdown_s=det["breakdown_s"], per_layer_critical_path_us=det["per_layer_critical_path_us"],
                   top_serial_steps=det["top_serial_steps"], stream_unit_width=sl["stream_unit_width"],
                   legacy_layer_fixed_latency_s=step["metrics"]["legacy_layer_fixed_latency_s"],
                   band=chk.detail["layer_fixed_latency_band"])
        if key == "hc1_llama31_8b":
            out.update(published_tokens_s_per_user=chk.published_value,
                       modelled_over_published_rate=chk.ratio, gate_passed=chk.passed, tolerance=chk.tolerance,
                       residual_us=step["step_time_s"] * 1e6 - 1e6 / chk.published_value)
        rec[key] = out

    points = json.loads(V41_POINTS.read_text())
    model = ModelProfile.load(V41)
    rows: dict = {}
    for kind, preferred, marker in (("array", ARRAY_DESIGN, "array-hw-hybrid"),
                                    ("wafer", WAFER_DESIGN, "wafer-hybrid")):
        design = pick_design(points, preferred, marker)
        for bt in BATCHES:
            row = study_row(points, design, bt)
            det = attribute(tech, model, row, layers=None if bt == 1 else {2, 3, 20})
            s = summary_row(row, det)
            if bt == 1:
                algos = {}
                for alg in C.ALGORITHMS:
                    try:
                        algos[alg] = attribute(tech, model, row, layers=set(), algorithm=alg)["tokens_s_per_user"]
                    except ValueError:
                        algos[alg] = None
                s["algorithm_tokens_s_per_user"] = {k: (v if v and math.isfinite(v) and v > 0 else None)
                                                   for k, v in algos.items()}
            rows[f"{kind}_batch{bt}"] = s
    rec["deepseek_v41_flash"] = rows
    rec["before_after"] = before_after(tech, rec)
    return rec


def print_summary(rec: dict) -> None:
    def line(tag: str, s: dict) -> None:
        b = s["breakdown_s"]
        print(f"{tag:26s} {s['tokens_s_per_user']:9.0f} tok/s/user  " +
              " ".join(f"{k}={v * 1e6:.2f}us" for k, v in b.items() if v))
    h = rec["hc1_llama31_8b"]
    line("HC1 Llama-3.1-8B", h)
    print(f"  published {h['published_tokens_s_per_user']:.0f}; modelled/published {h['modelled_over_published_rate']:.3f}")
    line("Qwen3-8B on the HC1 die", rec["qwen3_8b_single_reticle"])
    for k, s in rec["deepseek_v41_flash"].items():
        line(f"V4.1 {k} g{s['tensor_group']}", s)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    rec = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(rec, indent=1, default=float) + "\n")
    print_summary(rec)


if __name__ == "__main__":
    main()
