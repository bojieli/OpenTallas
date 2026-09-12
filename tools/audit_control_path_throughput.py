#!/usr/bin/env python3
"""Can the control path feed the datapath, for every model and accelerator?

The datapath is not the whole chip. A transformer decode step is hundreds of
kernel launches per token, and every one of them has to be fetched, decoded,
have its operand views resolved and be issued by the control plane before an
array can run it. If that costs more time than the array spends on the kernel,
the array idles and the datapath's clock frequency is irrelevant.

This tool asks that question against measured numbers on both sides, for each
(model, accelerator) pair, and it refuses to answer it with one figure -- because
the answer depends on DESCRIPTOR FAN-OUT, which is an architectural choice rather
than a measurement.

THE TWO SIDES, BOTH MEASURED
----------------------------
control    ``results/rtl/abi3_g1e_control_end_to_end.json`` runs the shipped
           program through the real control plane in RTL and is checked against
           an independent Python golden model. 241,290 simulated cycles retired
           2,073 engine commands over 3 forward passes: 116.4 control cycles per
           command, 691 commands per forward pass.
           Its clock comes from place-and-route of ot_a3_microsequencer.
datapath   ``ot_compute_unit`` place-and-routed at 1,290 MHz, and
           ``rtl/test/tb_kernel_dispatch_throughput.sv`` measures what one
           descriptor costs it: 270 cycles for a K=256 kernel, which is K plus
           14 cycles of pipeline fill and drain.

THE FAN-OUT QUESTION, WHICH IS THE WHOLE ARCHITECTURE
-----------------------------------------------------
If one descriptor from the sequencer launches work on ONE compute unit, the
sequencer must issue ``units`` descriptors per kernel period, and a single global
sequencer falls short by orders of magnitude the moment the array is wide. If one
descriptor is expanded IN HARDWARE and launched on every unit -- a cluster
dispatcher, a descriptor multicast, the GigaThread-to-SM hierarchy in a GPU, the
descriptor ring in a DPU -- then the sequencer issues one per kernel and its rate
is amortised over the whole array.

Both are reported. The per-unit column is what a naive design gets; the fan-out
column is what the design must do; the ratio between them is the fan-out factor
the hardware has to supply, and it is the specification for the cluster
dispatcher.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTROL_RECORD = ROOT / "results/rtl/abi3_g1e_control_end_to_end.json"
SEQ_FULL = ROOT / "results/physical_abi3/asap7/a3_microsequencer/pnr.json"
SEQ_FRONTEND = ROOT / "results/physical_abi3/asap7/a3_microsequencer/pnr_frontend_only.json"
CAPABILITY_DIR = ROOT / "configs/hardware/abi3_capability"
MODEL_DIR = ROOT / "configs/models"

#: Lanes in one ot_compute_unit, so a capability's tensor lane count converts to
#: a compute-unit count. The unit is the thing a descriptor launches.
LANES_PER_COMPUTE_UNIT = 16

#: Measured by rtl/test/tb_kernel_dispatch_throughput.sv on the real dispatcher
#: and the real compute unit: busy cycles for one descriptor at each kernel depth.
#: The fixed 14 cycles is pipeline fill plus the sequencer's drain margin, and it
#: is why a small kernel cannot reach full utilisation however fast control is.
KERNEL_BUSY_CYCLES = {256: 270, 64: 78, 16: 30}

#: Place-and-routed fmax of ot_compute_unit, cu_0p8: 1,290 MHz, status pass,
#: signal integrity clean.
DATAPATH_FMAX_HZ = 1.290e9


def git_state() -> dict[str, Any]:
    def run(*a: str) -> str:
        return subprocess.run(["git", *a], cwd=ROOT, capture_output=True,
                              text=True, check=False).stdout.strip()
    return {"commit": run("rev-parse", "HEAD") or None,
            "worktree_dirty": bool(run("status", "--porcelain"))}


def control_cost() -> dict[str, Any]:
    """Control cycles per engine command, and commands per forward pass."""
    body = json.loads(CONTROL_RECORD.read_text())
    rec = body["records"][0]
    cycles = int(rec["cost"]["simulated_cycles"])
    passes = int(rec["cost"]["passes"])
    commands = int(rec["issue_census"]["instances"])
    return {
        "source": str(CONTROL_RECORD.relative_to(ROOT)),
        "rung": body.get("rung"),
        "rung_status": body.get("status"),
        "simulated_cycles": cycles,
        "forward_passes": passes,
        "engine_commands_total": commands,
        "cycles_per_command": cycles / commands,
        "commands_per_forward_pass": commands / passes,
        "workload_id": rec.get("workload_id") or body.get("workload_id"),
    }


def sequencer_clocks() -> dict[str, Any]:
    out = {}
    for name, path in (("full", SEQ_FULL), ("frontend_only", SEQ_FRONTEND)):
        if not path.exists():
            continue
        body = json.loads(path.read_text())
        metrics = (body.get("place_and_route") or {}).get("metrics") or {}
        out[name] = {
            "fmax_hz": metrics.get("fmax_hz"),
            "status": body.get("status"),
            "standard_cell_count": metrics.get("standard_cell_count"),
            "core_area_um2": metrics.get("core_area_um2"),
            "source": str(path.relative_to(ROOT)),
            "modules": [s["path"].split("/")[-1]
                        for s in (body.get("design") or {}).get("sources", [])],
        }
    return out


def models() -> list[dict[str, Any]]:
    """Active parameters per token, from each model's own config."""
    rows = []
    for path in sorted(MODEL_DIR.glob("*.json")):
        body = json.loads(path.read_text())
        active = body.get("active_parameters")
        per_param = body.get("operations_per_active_parameter")
        if not active or not per_param:
            continue
        rows.append({
            "model": path.stem,
            "active_parameters": float(active),
            "operations_per_active_parameter": float(per_param),
            "operations_per_token": float(active) * float(per_param),
            "num_layers": body.get("num_layers"),
            "source": str(path.relative_to(ROOT)),
        })
    return rows


def accelerators() -> list[dict[str, Any]]:
    rows = []
    for path in sorted(CAPABILITY_DIR.glob("*.json")):
        body = json.loads(path.read_text())
        engines = (body.get("engines") or {})
        tensor = engines.get("tensor") or {}
        lanes = tensor.get("lanes")
        if not lanes:
            continue
        rows.append({
            "capability": path.name,
            "tensor_lanes": int(lanes),
            "compute_units": int(lanes) // LANES_PER_COMPUTE_UNIT,
            "vector_lanes": (engines.get("vector") or {}).get("lanes"),
        })
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kernel-depth", type=int, default=256,
                    choices=sorted(KERNEL_BUSY_CYCLES),
                    help="K of one weight-SRAM pass (default 256)")
    ap.add_argument("--passes-per-descriptor", type=int, default=1,
                    help=("how many K-passes ONE descriptor launches. This is "
                          "descriptor coarseness, and it is the strongest lever "
                          "there is: it multiplies the work a descriptor covers "
                          "without costing the control plane anything"))
    ap.add_argument("--control-clock", choices=("full", "frontend_only"),
                    default="full",
                    help="which place-and-routed sequencer clock to charge")
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()

    ctrl = control_cost()
    clocks = sequencer_clocks()
    if args.control_clock not in clocks:
        raise SystemExit(f"no place-and-route record for sequencer {args.control_clock!r}")
    f_ctrl = float(clocks[args.control_clock]["fmax_hz"])
    #: Work one descriptor covers on ONE unit. A coarse descriptor launches
    #: several weight-SRAM passes back to back; only the first pays the pipeline
    #: fill, so the marginal cost of a further pass is K cycles, not K+14.
    base = KERNEL_BUSY_CYCLES[args.kernel_depth]
    extra = args.passes_per_descriptor - 1
    busy = base + extra * args.kernel_depth

    # One descriptor costs the control plane this long, in seconds and in
    # datapath cycles -- the second is the number the utilisation sweep uses.
    ctrl_seconds = ctrl["cycles_per_command"] / f_ctrl
    ctrl_interval_datapath_cycles = ctrl_seconds * DATAPATH_FMAX_HZ
    descriptors_per_second = 1.0 / ctrl_seconds

    # One compute unit retires a descriptor every `busy` datapath cycles.
    unit_seconds = busy / DATAPATH_FMAX_HZ
    per_unit_rate = 1.0 / unit_seconds

    rows = []
    for acc in accelerators():
        units = acc["compute_units"]
        need_per_unit = per_unit_rate * units        # a descriptor each, per unit
        need_fanout = per_unit_rate                 # one descriptor for the array
        rows.append({
            **acc,
            "descriptors_needed_per_s_no_fanout": need_per_unit,
            "descriptors_needed_per_s_with_fanout": need_fanout,
            "control_descriptors_per_s": descriptors_per_second,
            "sufficient_without_fanout": descriptors_per_second >= need_per_unit,
            "sufficient_with_fanout": descriptors_per_second >= need_fanout,
            "shortfall_factor_without_fanout": need_per_unit / descriptors_per_second,
            "ratio_with_fanout": descriptors_per_second / need_fanout,
            "required_fanout": max(1, int(-(-need_per_unit // descriptors_per_second))),
            #: Utilisation a unit actually reaches: it retires a descriptor every
            #: `busy` cycles but can only be handed one every `interval`, so the
            #: duty cycle is the ratio, capped at 1.
            "utilisation_with_fanout": min(1.0, busy / ctrl_interval_datapath_cycles),
        })

    #: ---- end to end: a whole decode step, not one kernel -------------------
    #: The per-accelerator table above asks whether control can feed a unit at a
    #: chosen descriptor granularity. This asks the question the chip actually has
    #: to answer: for a whole transformer decode step, how much array time does
    #: one command buy, and is that more than the command costs?
    #:
    #: Commands per forward pass is MEASURED (691, from G1e on the shipped Qwen3
    #: program). Applying it to the DeepSeek models assumes their lowering issues
    #: a comparable number of commands per layer, scaled by layer count -- an
    #: assumption, recorded as a refusal, not a measurement.
    qwen_layers = 36
    cmds_per_layer = ctrl["commands_per_forward_pass"] / qwen_layers
    e2e = []
    for m in models():
        for acc in accelerators():
            units = acc["compute_units"]
            lanes_total = units * LANES_PER_COMPUTE_UNIT
            flops_per_cycle = lanes_total * 2          # one MAC is two operations
            datapath_cycles = m["operations_per_token"] / flops_per_cycle
            commands = cmds_per_layer * (m["num_layers"] or qwen_layers)
            cycles_per_command = datapath_cycles / commands
            ctrl_seconds_token = commands * ctrl["cycles_per_command"] / f_ctrl
            data_seconds_token = datapath_cycles / DATAPATH_FMAX_HZ
            e2e.append({
                "model": m["model"],
                "capability": acc["capability"],
                "compute_units": units,
                "operations_per_token": m["operations_per_token"],
                "commands_per_token": commands,
                "datapath_cycles_per_token": datapath_cycles,
                "datapath_cycles_per_command": cycles_per_command,
                "control_seconds_per_token": ctrl_seconds_token,
                "datapath_seconds_per_token": data_seconds_token,
                #: The two run in SEPARATE clock domains, decoupled by the
                #: dispatcher's descriptor queue, so the step takes the LONGER of
                #: them and not the sum. That decoupling is the thing
                #: ot_cluster_dispatcher exists to provide; without it these add.
                "tokens_per_second_decoupled":
                    1.0 / max(ctrl_seconds_token, data_seconds_token),
                "tokens_per_second_if_serialised":
                    1.0 / (ctrl_seconds_token + data_seconds_token),
                "control_headroom_factor": data_seconds_token / ctrl_seconds_token,
                "control_is_bottleneck": ctrl_seconds_token > data_seconds_token,
                "required_fanout": units,
            })

    body = {
        "schema": "opentallas.audit.control_path_throughput.v1",
        "question": ("Can the control plane issue kernel descriptors fast enough "
                     "to keep each accelerator's compute units busy, and what "
                     "descriptor fan-out does that require?"),
        "git": git_state(),
        "control": {**ctrl, "clock": clocks[args.control_clock],
                    "clock_selected": args.control_clock,
                    "seconds_per_descriptor": ctrl_seconds,
                    "descriptors_per_second": descriptors_per_second,
                    "interval_in_datapath_cycles": ctrl_interval_datapath_cycles},
        "datapath": {
            "block": "ot_compute_unit",
            "fmax_hz": DATAPATH_FMAX_HZ,
            "kernel_depth_k": args.kernel_depth,
            "busy_cycles_per_descriptor": busy,
            "busy_cycles_basis": ("measured by rtl/test/tb_kernel_dispatch_"
                                  "throughput.sv on the real dispatcher and the "
                                  "real compute unit"),
            "descriptors_per_second_per_unit": per_unit_rate,
        },
        "accelerators": rows,
        "end_to_end_decode": e2e,
        "refusals": [
            "no-single-verdict: whether control is the bottleneck depends on "
            "descriptor fan-out, which is an architectural choice and not a "
            "measurement. Both columns are reported and neither is collapsed.",
            "one-workload: the 116.4 cycles per command and 691 commands per "
            "forward pass are the SHIPPED Qwen3 program measured by G1e. A "
            "different lowering of the same model, or a different model, issues "
            "a different number of commands, and this tool does not model that.",
            "kernel-depth-is-a-parameter: a descriptor that launches a shallower "
            "kernel keeps its unit busy for fewer cycles and needs a "
            "proportionally faster control plane. The default K=256 is the "
            "deepest the compute unit's weight SRAM holds.",
            "tensor-engine-only: the fan-out arithmetic here charges the tensor "
            "engine's compute units. Vector, attention and reduction engines "
            "also consume descriptors and are not counted, so the required "
            "control rate is a LOWER bound.",
            "not-a-silicon-claim: ASAP7 is a predictive, non-manufacturable PDK "
            "and both clocks come from it.",
            "commands-per-token-measured-on-one-model: 691 commands per forward "
            "pass is G1e's measurement of the SHIPPED Qwen3 program. The "
            "end-to-end rows scale it by layer count for the DeepSeek models, "
            "which assumes a comparable lowering and is an assumption.",
            "compute-bound-only: the end-to-end rows price arithmetic at the "
            "array's peak and charge no weight traffic, no attention over the KV "
            "cache and no interconnect. A real decode step is usually "
            "memory-bound at batch 1, so the datapath time is a LOWER bound and "
            "the control headroom a lower bound with it.",
            "decoupling-is-required-not-assumed: tokens_per_second_decoupled is "
            "valid only because ot_cluster_dispatcher puts a descriptor queue "
            "between the two clock domains. The serialised column is what a "
            "design without it gets.",
        ],
    }

    print(f"control plane: {ctrl['rung']} ({ctrl['rung_status']}), "
          f"{ctrl['cycles_per_command']:.1f} cycles/command, "
          f"{ctrl['commands_per_forward_pass']:.0f} commands/forward pass")
    print(f"  sequencer {args.control_clock}: {f_ctrl/1e6:.0f} MHz "
          f"({clocks[args.control_clock]['standard_cell_count']} cells) "
          f"-> {descriptors_per_second/1e6:.2f} M descriptors/s")
    print(f"  that is {ctrl_interval_datapath_cycles:.0f} datapath cycles per "
          f"descriptor at {DATAPATH_FMAX_HZ/1e6:.0f} MHz")
    print(f"datapath: one K={args.kernel_depth} descriptor keeps a unit busy "
          f"{busy} cycles -> {per_unit_rate/1e6:.2f} M descriptors/s per unit\n")

    print(f"  {'capability':<40} {'units':>6} {'per-unit short':>15} "
          f"{'fan-out req':>12} {'util w/fanout':>14}")
    for r in rows:
        util = r["utilisation_with_fanout"]
        verdict = "OK" if r["sufficient_with_fanout"] else "SHORT"
        print(f"  {r['capability']:<40} {r['compute_units']:>6} "
              f"{r['shortfall_factor_without_fanout']:>13.0f}x "
              f"{r['required_fanout']:>12} "
              f"{util*100:>11.1f}% {verdict}")

    any_short = any(not r["sufficient_with_fanout"] for r in rows)
    print()
    if any_short:
        print("CONTROL IS THE BOTTLENECK, and fan-out alone does not fix it.")
        print(f"  One descriptor covers {busy} datapath cycles of work on a unit,")
        print(f"  but the control plane can only supply one every "
              f"{ctrl_interval_datapath_cycles:.0f} cycles.")
        need_passes = -(-int(ctrl_interval_datapath_cycles) // args.kernel_depth)
        print(f"  A descriptor must cover at least "
              f"{ctrl_interval_datapath_cycles:.0f} cycles, i.e. "
              f"{need_passes} K={args.kernel_depth} passes, AND fan out to the array.")
    else:
        print("Control keeps up, GIVEN the fan-out in the table: one descriptor "
              "must be expanded\nin hardware across every compute unit, not "
              "issued once per unit by the sequencer.")
    print("\n  end-to-end decode, one token, compute-bound, control decoupled:")
    print(f"  {'model':<24} {'capability':<34} {'cyc/cmd':>9} {'headroom':>9} {'tok/s':>9}")
    for r in e2e:
        flag = "  CONTROL-BOUND" if r["control_is_bottleneck"] else ""
        print(f"  {r['model']:<24} {r['capability'].replace('.json',''):<34} "
              f"{r['datapath_cycles_per_command']:>9.0f} "
              f"{r['control_headroom_factor']:>8.1f}x "
              f"{r['tokens_per_second_decoupled']:>9.1f}{flag}")
    bound = [r for r in e2e if r["control_is_bottleneck"]]
    print()
    if bound:
        print(f"CONTROL-BOUND in {len(bound)} of {len(e2e)} combinations.")
    else:
        print(f"Control is NOT the bottleneck in any of the {len(e2e)} "
              f"(model, accelerator) combinations,")
        print(f"  minimum headroom {min(r['control_headroom_factor'] for r in e2e):.1f}x "
              f"-- GIVEN descriptor fan-out across every compute unit.")
    print("\nRead with the refusals. The per-unit column is what a design gets if "
          "one descriptor\nlaunches one compute unit; fan-out is the hardware "
          "expansion that removes that factor.")

    if args.output:
        args.output.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n")
        try:
            shown = args.output.relative_to(ROOT)
        except ValueError:
            shown = args.output
        print(f"wrote {shown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
