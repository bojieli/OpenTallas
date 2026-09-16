#!/usr/bin/env python3
"""Run the reduced Qwen3 deployment to a TOKEN in RTL, and record the comparison.

WHY THIS TOOL EXISTS.  The token was reachable before it was recorded.  A run of
``tools/stage_reduced_token_run.py`` plus the shipped-prefix top emits a token
id, and that had been reproduced by hand more than once -- but nothing committed
it, so the G1 ladder's own certificate still reads

    certificate.token_ids_match_oracle   False
    reduced_configuration.rtl_emitted    []

because it measures rung G1f, which refuses for unrelated reasons.  A claim that
lives only in a shell history is not evidence, and the certificate is built to
say so: "The oracle's ids are read for comparison only and are never copied into
the emitted field."  This tool is the missing wiring.

WHAT IT ESTABLISHES.  The reduced Qwen3 deployment, entered at its prefill
entrypoint, executes to CONTROL.COMPLETE in cycle-accurate RTL over the
production engines and emits a token id, and that id is compared against
``results/abi3/qwen3_reduced_reference_oracle.json`` -- an oracle produced by a
separate process that reads the fixture's shard off disk and runs the released
reference implementation over it.

WHAT IT DOES NOT ESTABLISH.  Numerics at shipped dimension: this is the reduced
fixture, hidden 128 and vocabulary 4,096, and a shipped Qwen3 token is about
13.9 days of cycle-accurate simulation at this project's measured 39,915 MACs/s.
The decode case's token is RECORDED BUT NOT ASSERTED: that case is entered on a
staged KV cache rather than on the prefill's own output, so its id is evidence
that a selection happened on the state it was given and is not the oracle's
second token.  Only the prefill comparison is a token claim.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "opentallas.rtl.abi3_reduced_token_campaign.v1"
ORACLE = ROOT / "results/abi3/qwen3_reduced_reference_oracle.json"
WORKLOAD_ID = "TA-QW-REDUCED-EOS-1"
#: One reduced fixture, two weight stores.  The same program, the same oracle,
#: the same vehicle: what differs is where a weight column comes from, which is
#: the whole point of running both.
DEPLOYMENTS: dict[str, str] = {
    "rom": "build/abi3/qwen3-reduced-rom",
    "hbm": "build/abi3/qwen3-reduced-hbm",
}
CHECKPOINT = "build/models/qwen3-reduced-v1"
DRIVER = "rtl/test/a3_reduced_token_driver.cpp"

#: The pinned simulator.  /usr/bin/verilator is 4.038 on this machine and has no
#: --binary, so taking it from PATH turns a tool-version accident into a design
#: fact.
TOOL_ROOT = Path(os.environ.get("OPENTALLAS_TOOL_ROOT",
                                Path.home() / ".local/opentallas-tools"))
VERILATOR = TOOL_ROOT / "verilator-5.050/bin/verilator"

#: The vehicle, in elaboration order.  It is the shipped prefix top over the
#: production RTL: no engine is stubbed and no bridge variant is substituted.
VEHICLE_SOURCES: tuple[str, ...] = (
    "rtl/ot_fp32_rne_pkg.sv",
    "rtl/ot_fp32_rsqrt_rne.sv",
    "rtl/ot_ta_command_decoder.sv",
    "rtl/ot_ta_rope_bf16_sram_engine.sv",
    "rtl/abi3/ot_a3_format_pkg.sv",
    "rtl/abi3/ot_a3_engine_pkg.sv",
    "rtl/abi3/ot_a3_pkg.sv",
    "rtl/abi3/ot_a3_instruction_decoder.sv",
    "rtl/abi3/ot_a3_program_header.sv",
    "rtl/abi3/ot_a3_shared_divider.sv",
    "rtl/abi3/ot_a3_symbol_file.sv",
    "rtl/abi3/ot_a3_loop_stack.sv",
    "rtl/abi3/ot_a3_view_resolver.sv",
    "rtl/abi3/ot_a3_resolver_bank.sv",
    "rtl/abi3/ot_a3_event_scoreboard.sv",
    "rtl/abi3/ot_a3_issue_record_store.sv",
    "rtl/abi3/ot_a3_dependence_table.sv",
    "rtl/abi3/ot_a3_state_controller.sv",
    "rtl/abi3/ot_a3_microsequencer.sv",
    "rtl/abi3/ot_a3_device_top.sv",
    "rtl/abi3/ot_a3_mac_lane.sv",
    "rtl/proto/ot_mac_bf16_fp32_pipe.sv",
    "rtl/abi3/ot_a3_mac_lane_pipe.sv",
    "rtl/abi3/ot_a3_selection_argmax.sv",
    "rtl/abi3/ot_a3_dma_index_mover.sv",
    "rtl/abi3/ot_a3_vector_add.sv",
    "rtl/abi3/ot_a3_vector_convert.sv",
    "rtl/abi3/ot_a3_vector_scale.sv",
    "rtl/abi3/ot_a3_vector_hadamard.sv",
    "rtl/abi3/ot_a3_vector_index_score.sv",
    "rtl/abi3/ot_a3_vector_compress_project.sv",
    "rtl/abi3/ot_a3_vector_mhc_post.sv",
    "rtl/abi3/ot_a3_engine_array.sv",
    "rtl/abi3/ot_a3_vector_rms_norm.sv",
    "rtl/abi3/ot_a3_vector_rope.sv",
    "rtl/abi3/ot_a3_rope_lane_pipe.sv",
    "rtl/abi3/ot_a3_fp32_div_rne.sv",
    "rtl/abi3/ot_a3_fp32_transcendental_cr_rne.sv",
    "rtl/abi3/ot_a3_qwen_gqa.sv",
    "rtl/abi3/ot_a3_vector_silu_mul.sv",
    "rtl/abi3/ot_a3_selection_token_append.sv",
    "rtl/proto/ot_fp32_add_rne_pipe.sv",
    "rtl/abi3/ot_a3_route_weight_normalize.sv",
    "rtl/abi3/ot_a3_route_window_index.sv",
    "rtl/abi3/ot_a3_place_table.sv",
    "rtl/abi3/ot_a3_engine_issue_bridge.sv",
    "rtl/test/a3_engine_completion_adapter.sv",
    "rtl/test/a3_shipped_prefix_top.sv",
)

#: The reduced fixture's geometry, as parameters rather than as a second RTL.
#: These are qwen3-reduced-v1's own config: 8 query heads, 2 KV heads, head
#: width 16, hidden 128, vocabulary 4,096.
GEOMETRY: tuple[str, ...] = (
    "GQA_QUERY_HEADS=8",
    "GQA_KV_HEADS=2",
    "GQA_HEAD_WIDTH=16",
    "GQA_SCALE_CODE=0x3e800000",
    "EMBEDDING_WIDTH=128",
    "QWEN_VOCABULARY=4096",
    "DEEPSEEK_VOCABULARY=4096",
    "EMBEDDING_TOKEN_INDEXED=1",
    "GATHER_PLACEMENT_ADDRESSED=1",
    #: No injected results anywhere: every value the argmax reads was computed
    #: by the engines in this elaboration.
    "ENABLE_RESULT_INJECTION=0",
)

#: PREFILL IS A SPAN-16 RUN and the bridge has to be built for it.  Without
#: MAX_SEQUENCE_SPAN the span-16 prefill refuses at instruction 1 with
#: TRAP_DESCRIPTOR after resolving three views -- which is what a rebuild at the
#: decode parameters looks like, and cost an hour to recognise as a missing
#: parameter rather than a regression.
def _cases() -> tuple[dict[str, object], ...]:
    """Both stores, both entrypoints.

    PREFILL IS A SPAN-16 BUILD and the bridge has to be elaborated for it.
    Without MAX_SEQUENCE_SPAN and INDEX_VIEW_ADDRESSED the span-16 prefill
    refuses at instruction 1 with TRAP_DESCRIPTOR after resolving three views --
    which reads exactly like a regression and is a missing parameter.
    """
    out: list[dict[str, object]] = []
    for store, deployment in DEPLOYMENTS.items():
        out.append({
            "name": f"{store}-prefill",
            "store": store,
            "deployment": deployment,
            "case": "qwen3-reduced-rom-single-chip/prefill",
            "params": ("MAX_SEQUENCE_SPAN=16", "INDEX_VIEW_ADDRESSED=1"),
            "prompt_tokens": str(ORACLE),
            "token_is_asserted": True,
            "why": ("the workload's first generated token: the span-16 prefill "
                    "over the prompt the oracle records, from this store"),
        })
        out.append({
            "name": f"{store}-decode",
            "store": store,
            "deployment": deployment,
            "case": "qwen3-reduced-rom-single-chip/decode",
            "params": (),
            "prompt_tokens": None,
            "token_is_asserted": False,
            "why": ("a decode step entered on a STAGED KV cache rather than on "
                    "the prefill's own output, so its id is not the oracle's "
                    "second token and is recorded without being asserted"),
        })
    return tuple(out)


#: The case record supplies the REQUEST -- entrypoint id, phase, symbol bindings
#: -- and never the store; ``entry_pc`` and the generation policy come from each
#: deployment's own manifest.  So one committed case drives both stores, which is
#: why the HBM rows name a rom-single-chip case and are not mislabelled.
CASES: tuple[dict[str, object], ...] = _cases()

COUNTER_RE = re.compile(r"^\s{2}(?P<key>[a-z_/ ]+?)\s{2,}(?P<value>.+)$", re.M)
PASS_RE = re.compile(r"^(?P<verdict>PASS|FAIL) reduced end-to-end: "
                     r"retired (?P<retired>\d+) vs golden (?P<golden>\d+), "
                     r"issued (?P<issued>\d+) vs (?P<issued_golden>\d+)", re.M)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_state() -> dict[str, object]:
    def run(*a: str) -> str:
        return subprocess.run(["git", *a], cwd=ROOT, capture_output=True,
                              text=True, check=False).stdout.strip()
    return {"commit": run("rev-parse", "HEAD") or None,
            "worktree_dirty": bool(run("status", "--porcelain"))}


def bank_sizes(driver: Path) -> dict[str, int]:
    """The staged bank extents the vehicle is elaborated to hold."""
    wanted = ("index_words", "source_words", "result_words", "weight_bytes")
    out: dict[str, int] = {}
    for line in driver.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0] in wanted:
            out[parts[0]] = int(parts[1])
    missing = [k for k in wanted if k not in out]
    if missing:
        raise SystemExit(f"{driver} states no {', '.join(missing)}")
    return out


def stage(case: dict[str, object], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, "tools/pack_reduced_deployment_images.py",
                    "--deployment", str(case["deployment"]), "--out-dir", str(out_dir)],
                   cwd=ROOT, check=True, capture_output=True)
    argv = [sys.executable, "tools/stage_reduced_token_run.py",
            "--deployment", str(case["deployment"]), "--checkpoint", CHECKPOINT,
            "--case", str(case["case"]), "--out-dir", str(out_dir)]
    if case["prompt_tokens"]:
        argv += ["--prompt-tokens", str(case["prompt_tokens"])]
    subprocess.run(argv, cwd=ROOT, check=True, capture_output=True)


def build(case: dict[str, object], out_dir: Path, work: Path) -> dict[str, object]:
    banks = bank_sizes(out_dir / "driver.txt")
    params = list(GEOMETRY) + list(case["params"]) + [
        f"INDEX_WORDS={banks['index_words']}",
        f"SOURCE_WORDS={banks['source_words']}",
        f"RESULT_WORDS={banks['result_words']}",
        f"MATMUL_WEIGHT_BYTES={banks['weight_bytes']}",
    ]
    obj = work / f"obj_{case['name']}"
    binary = f"tok_{case['name']}"
    argv = [str(VERILATOR), "--cc", "--exe", "--build", "-j", "6",
            "-Wno-fatal", "-Wno-DECLFILENAME", "-Wno-PINMISSING",
            "-Wno-WIDTHEXPAND", "-Wno-WIDTHTRUNC",
            "--top-module", "ot_a3_shipped_prefix_top", "--Mdir", str(obj),
            *[f"-G{p}" for p in params], "-o", binary,
            *[str(ROOT / s) for s in VEHICLE_SOURCES], str(ROOT / DRIVER)]
    done = subprocess.run(argv, cwd=work, capture_output=True, text=True,
                          timeout=3600)
    if done.returncode != 0:
        raise SystemExit(f"{case['name']}: elaboration failed\n"
                         f"{done.stdout[-2000:]}{done.stderr[-2000:]}")
    shutil.copy2(obj / binary, out_dir / binary)
    return {"banks": banks, "parameters": params, "binary": binary}


def run_case(out_dir: Path, binary: str) -> dict[str, object]:
    done = subprocess.run([f"./{binary}"], cwd=out_dir, capture_output=True,
                          text=True, timeout=7200)
    log = done.stdout + done.stderr
    counters = {m.group("key").strip().replace("/", "_").replace(" ", "_"):
                m.group("value").strip()
                for m in COUNTER_RE.finditer(log)}
    verdict = PASS_RE.search(log)
    return {
        "counters": counters,
        "log_sha256": hashlib.sha256(log.encode()).hexdigest(),
        "log_tail": "\n".join(log.strip().splitlines()[-24:]),
        "returncode": done.returncode,
        "self_check": None if verdict is None else {
            "golden_issued": int(verdict.group("issued_golden")),
            "golden_retired": int(verdict.group("golden")),
            "issued": int(verdict.group("issued")),
            "retired": int(verdict.group("retired")),
            "verdict": verdict.group("verdict"),
        },
        "selected_token": (int(counters["selected_token"])
                           if "selected_token" in counters else None),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    if args.output.exists() and not args.force:
        raise SystemExit(f"refusing to overwrite {args.output}; pass --force")
    if not VERILATOR.is_file():
        raise SystemExit(f"the pinned simulator is absent: {VERILATOR}")

    oracle = json.loads(ORACLE.read_text(encoding="utf-8"))
    oracle_ids = [int(t) for t in
                  oracle["results"][WORKLOAD_ID]["generated_token_ids"]]
    args.work.mkdir(parents=True, exist_ok=True)

    records = []
    for case in CASES:
        out_dir = args.work / f"stage_{case['name']}"
        stage(case, out_dir)
        built = build(case, out_dir, args.work)
        result = run_case(out_dir, str(built["binary"]))
        emitted = result["selected_token"]
        expected = oracle_ids[0] if case["token_is_asserted"] else None
        agrees = (None if expected is None else emitted == expected)
        records.append({
            "agrees_with_oracle": agrees,
            "case": case["case"],
            "elaboration": {"banks": built["banks"],
                            "parameters": built["parameters"]},
            "execution": result,
            "expected_token": expected,
            "name": case["name"],
            "selected_token": emitted,
            "store": case["store"],
            "deployment": case["deployment"],
            "token_is_asserted": bool(case["token_is_asserted"]),
            "why": case["why"],
        })

    asserted = [r for r in records if r["token_is_asserted"]]
    status = "pass" if (asserted and all(r["agrees_with_oracle"] for r in asserted)
                        and all((r["execution"]["self_check"] or {}).get("verdict")
                                == "PASS" for r in records)) else "fail"
    body = {
        "schema": SCHEMA,
        "status": status,
        "certificate": {
            "prefill_token_matches_oracle":
                bool(asserted and all(r["agrees_with_oracle"] for r in asserted)),
            "stores_agree": (
                len({r["selected_token"] for r in asserted}) == 1
                if asserted else False
            ),
            "every_case_reached_completion":
                all((r["execution"]["self_check"] or {}).get("verdict") == "PASS"
                    for r in records),
            "result_injection_disabled": True,
        },
        "checkpoint": CHECKPOINT,
        "deployments": {
            store: {
                "path": path,
                "program_sha256": sha256(ROOT / path / "program.bin"),
                "descriptors_sha256": sha256(ROOT / path / "descriptors.bin"),
            }
            for store, path in DEPLOYMENTS.items()
        },
        "does_not_establish": [
            "numerics at shipped dimension: this is the reduced fixture at "
            "hidden 128 and vocabulary 4,096, and one shipped Qwen3 token is "
            "about 13.9 days of cycle-accurate simulation at this project's "
            "measured 39,915 MACs/s",
            "the decode case's token as an oracle id: that case is entered on a "
            "staged KV cache rather than the prefill's own output, so it is "
            "recorded and not asserted",
            "any of the other eight cells of the model x store matrix",
            "a rate: the cycle counts are a cost measurement, not a TPOT",
        ],
        "establishes": [
            "the reduced Qwen3 deployment executes to CONTROL.COMPLETE in "
            "cycle-accurate RTL over the production engines, with result "
            "injection disabled, and emits a token id",
            "that id equals the first generated token of the reduced reference "
            "oracle, which a separate process produced by reading the fixture's "
            "shard off disk and running the released reference implementation",
        ],
        "git": git_state(),
        "oracle": {
            "generated_token_ids": oracle_ids,
            "path": str(ORACLE.relative_to(ROOT)),
            "sha256": sha256(ORACLE),
            "workload_id": WORKLOAD_ID,
        },
        "records": records,
        "simulator": {"path": str(VERILATOR), "version": "5.050"},
        "sources": [{"path": s, "sha256": sha256(ROOT / s)}
                    for s in VEHICLE_SOURCES] +
                   [{"path": DRIVER, "sha256": sha256(ROOT / DRIVER)}],
        "vehicle": "rtl/test/a3_shipped_prefix_top.sv",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")

    for r in records:
        sc = r["execution"]["self_check"] or {}
        mark = ("matches oracle" if r["agrees_with_oracle"]
                else ("recorded, not asserted" if not r["token_is_asserted"]
                      else "DOES NOT MATCH"))
        print(f"  {r['name']:14s} token={r['selected_token']} "
              f"retired={sc.get('retired')}/{sc.get('golden_retired')} "
              f"issued={sc.get('issued')}/{sc.get('golden_issued')} "
              f"{sc.get('verdict')}  {mark}")
    print(f"reduced token campaign: {status.upper()} -> {args.output}")
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
