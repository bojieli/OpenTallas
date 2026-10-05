#!/usr/bin/env python3
"""Does the HOST-side control path dominate, or does weight movement?

tools/audit_control_path_throughput.py covers the ON-DIE control path: the
sequencer fetching, decoding and issuing to engines. It says nothing about the
path OUTSIDE the chip -- host to device command submission, kernel-graph upload,
and weight DMA -- and that omission is load-bearing, because a design whose
on-die control keeps up can still be dominated by host traffic.

This prices the outer path per generated token, from the cycle model's own
architectural counters, and separates three things that are usually conflated:

  WEIGHT MOVEMENT   HBM reads of model parameters. For a decode step at batch 1
                    this is the whole model once, and it is why decode is
                    memory-bound rather than compute-bound.
  STATE MOVEMENT    KV cache reads and writes. Present in BOTH architectures --
                    the mask-ROM design stores weights on-die but the KV cache is
                    generated at runtime and cannot be in ROM.
  HOST CONTROL      command submission and result read-back across the host
                    boundary, plus whatever share of instruction fetch is not
                    resident on the device.

The architectures differ only in the FIRST of those, which is the whole thesis:
a mask-ROM design reads no weights over HBM. So the question "does the control
plane dominate" has a different answer per architecture, and this tool gives both.

THE AMORTISATION RULE, which is the part that actually matters
-------------------------------------------------------------
A kernel graph uploaded ONCE and executed for every token costs its upload
divided by the number of tokens generated. Re-uploaded per token it costs its
full size every time. That single choice moves the host path by orders of
magnitude, and it is a software decision rather than a hardware one, so the tool
reports the break-even token count rather than a verdict.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SWEEP = ROOT / "results/abi3/cycle_characterization_feedback.json"
MODELS = ROOT / "configs/models"

#: A100 HBM2e, from this repository's own recorded source facts.
HBM_BYTES_S = 2.039e12
#: PCIe 4.0 x16 one direction, the host link an accelerator of this class gets.
#: Named explicitly because it is an ASSUMPTION, not a measurement in this repo.
HOST_LINK_BYTES_S = 31.5e9


def git_state() -> dict[str, Any]:
    def run(*a: str) -> str:
        return subprocess.run(["git", *a], cwd=ROOT, capture_output=True,
                              text=True, check=False).stdout.strip()
    return {"commit": run("rev-parse", "HEAD") or None,
            "worktree_dirty": bool(run("status", "--porcelain"))}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tokens", type=int, default=1024,
                    help="tokens generated per graph upload (default 1024)")
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()

    body_in = json.loads(SWEEP.read_text())
    c = body_in["architectural_counters"]
    qwen = json.loads((MODELS / "qwen3-8b.json").read_text())
    weight_bytes = float(qwen["active_parameters"]) * 2.0     # BF16 on the wire

    hbm_r = int(c["hbm.bytes_read"])
    hbm_w = int(c["hbm.bytes_written"])
    state_r = int(c["state.bytes_read"])
    state_w = int(c["state.bytes_written"])
    host = int(c["host.bytes_read"]) + int(c["host.bytes_written"])
    instrs = int(c["instructions.fetched"])

    #: The ROM design reads no weights over HBM. Everything else -- the KV cache,
    #: the activations, the host boundary -- is unchanged, so the ROM column is the
    #: HBM column with the weight term removed and nothing else touched.
    arch = {
        "hbm_weights": {
            "weight_bytes_per_token": hbm_r,
            "state_bytes_per_token": state_r + state_w,
            "host_bytes_per_token": host,
        },
        "rom_weights": {
            "weight_bytes_per_token": 0,
            "state_bytes_per_token": state_r + state_w,
            "host_bytes_per_token": host,
        },
    }
    for name, a in arch.items():
        total = a["weight_bytes_per_token"] + a["state_bytes_per_token"] + a["host_bytes_per_token"]
        a["total_bytes_per_token"] = total
        a["host_share"] = a["host_bytes_per_token"] / total
        a["weight_share"] = a["weight_bytes_per_token"] / total
        a["state_share"] = a["state_bytes_per_token"] / total
        a["host_vs_offchip_ratio"] = (
            (a["weight_bytes_per_token"] + a["state_bytes_per_token"])
            / a["host_bytes_per_token"])
        #: Seconds, charging weights and state to HBM and the host term to the
        #: host link, which are different and independent pipes.
        a["hbm_seconds_per_token"] = (a["weight_bytes_per_token"]
                                      + a["state_bytes_per_token"]) / HBM_BYTES_S
        a["host_seconds_per_token"] = a["host_bytes_per_token"] / HOST_LINK_BYTES_S
        a["host_is_bottleneck"] = a["host_seconds_per_token"] > a["hbm_seconds_per_token"]

    #: Graph upload. Instruction count x a conservative 16 bytes per instruction.
    graph_bytes = instrs * 16
    upload = {
        "instructions": instrs,
        "bytes_per_instruction_assumed": 16,
        "graph_bytes": graph_bytes,
        "amortised_over_tokens": args.tokens,
        "per_token_if_uploaded_once": graph_bytes / args.tokens,
        "per_token_if_reuploaded": graph_bytes,
        "reupload_penalty_factor": (graph_bytes / (graph_bytes / args.tokens)),
    }

    body = {
        "schema": "opentallas.audit.host_path_traffic.v1",
        "question": ("Per generated token, does host-side control traffic dominate, "
                     "or does weight and state movement?"),
        "git": git_state(),
        "source": str(SWEEP.relative_to(ROOT)),
        "model": {"name": "qwen3-8b",
                  "active_parameters": qwen["active_parameters"],
                  "weight_bytes_bf16": weight_bytes},
        "links": {"hbm_bytes_s": HBM_BYTES_S,
                  "host_link_bytes_s": HOST_LINK_BYTES_S,
                  "host_link_note": ("PCIe 4.0 x16 one direction. An ASSUMPTION; "
                                     "this repository measures no host link.")},
        "architectures": arch,
        "graph_upload": upload,
        "refusals": [
            "host-link-rate-is-assumed: nothing in this repository measures a host "
            "interconnect. The 31.5 GB/s is a PCIe 4.0 x16 figure taken as an "
            "assumption, and every host-seconds number scales inversely with it.",
            "counters-are-a-cycle-model: host.bytes_read/written and hbm.bytes_read "
            "come from the cycle model's architectural counters, which are "
            "identical across cost tables and were checked as such -- but they are "
            "a model of the shipped program, not a measurement of a host driver.",
            "rom-column-is-subtraction: the ROM architecture is priced by removing "
            "the weight term and changing nothing else. A real mask-ROM design "
            "also changes the on-die fabric and the refill path, which this does "
            "not model.",
            "no-prefill-and-no-batching: one decode token at batch 1. Prefill "
            "moves far more per step and batching amortises weight traffic across "
            "requests, which is exactly the regime where the ROM advantage "
            "narrows.",
            "graph-size-is-derived-not-measured: 16 bytes per instruction is a "
            "conservative stand-in for the encoded descriptor stream, not a "
            "measurement of the deployed image.",
        ],
    }

    print(f"One decode token, Qwen3-8B, from {SWEEP.relative_to(ROOT)}:\n")
    print(f"  {'':<16} {'weights':>14} {'state/KV':>14} {'host':>11} "
          f"{'host share':>11} {'offchip:host':>13}")
    for name, a in arch.items():
        print(f"  {name:<16} {a['weight_bytes_per_token']/1e9:>12.2f}GB "
              f"{a['state_bytes_per_token']/1e9:>12.2f}GB "
              f"{a['host_bytes_per_token']/1e6:>9.2f}MB "
              f"{a['host_share']*100:>10.4f}% "
              f"{a['host_vs_offchip_ratio']:>12,.0f}x")
    print()
    for name, a in arch.items():
        verdict = "HOST-BOUND" if a["host_is_bottleneck"] else "memory-bound"
        print(f"  {name:<16} HBM {a['hbm_seconds_per_token']*1e3:>7.3f} ms/token   "
              f"host {a['host_seconds_per_token']*1e3:>7.3f} ms/token   -> {verdict}")

    u = upload
    print(f"\nKernel-graph upload: {u['instructions']:,} instructions x "
          f"{u['bytes_per_instruction_assumed']} B = {u['graph_bytes']/1e3:.1f} kB")
    print(f"  uploaded once, amortised over {u['amortised_over_tokens']:,} tokens: "
          f"{u['per_token_if_uploaded_once']:.1f} B/token")
    print(f"  re-uploaded every token:                       "
          f"{u['per_token_if_reuploaded']/1e3:.1f} kB/token "
          f"({u['reupload_penalty_factor']:,.0f}x worse)")
    print("\n  Even re-uploaded every token the graph is small against 15 GB of "
          "weights. The\n  amortisation matters for the ROM design, where there is "
          "no weight traffic to hide\n  behind -- which is the architecture that "
          "needs a resident graph most.")
    print("\nRead the refusals: the host link rate is an ASSUMPTION, the counters "
          "are a cycle\nmodel of the shipped program, and the ROM column is the HBM "
          "column with the weight\nterm subtracted.")

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
