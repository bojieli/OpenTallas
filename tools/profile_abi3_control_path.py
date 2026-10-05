#!/usr/bin/env python3
"""Attribute every cycle of a reduced-Qwen3 RTL token to control or datapath.

WHY.  The ABI 3.0 machine's recurring overhead has been its CONTROL path, and the
figure quoted for it -- "7.9 M cycles for ~1.3 M MACs, about six cycles of control
and service per MAC" -- was a ratio of two totals, not a measurement of where the
cycles went.  This tool measures it on the same vehicle and the same staged
deployment the token campaign runs (tools/rtl_abi3_reduced_token_campaign.py):

  * it stages the case exactly as the campaign does,
  * elaborates the same sources with the same parameters, plus
    rtl/test/a3_control_profile.vlt (marks five internal registers public) and
    -DOT_A3_PROFILE (compiles rtl/test/a3_control_profile.h into the driver),
  * runs to CONTROL.COMPLETE, and parses one bucket per cycle:

      engine     the issue bridge is in S_START/S_ENGINE_WAIT -- an engine owns
                 the cycle, INCLUDING its internal walk control
      admission  the bridge is in any other non-idle state (descriptor fetches,
                 placement and admission checks, index reads, response)
      adapter    bridge idle, completion adapter replaying views or completing
      frontend   both idle: the microsequencer is fetching, decoding, waiting,
                 resolving views, checking dependences, looping

    plus MAC-active cycles inside `engine` and one timeline per issue (issue,
    bridge accept, engine start/end, bridge done, engine cycles, work count).

The per-issue record is what separates "engine datapath" from "engine-internal
control": an operator whose engine cycles are orders of magnitude above its work
count is spending them in its own walk, not in arithmetic.

It does not change the vehicle: without the .vlt and the define, the driver is
byte-for-byte the campaign's behaviour, and the profile reads registers only.

    python3 tools/profile_abi3_control_path.py --case rom-decode \\
        --work /tmp/prof --output /tmp/prof/profile.json
    python3 tools/profile_abi3_control_path.py --case rom-decode \\
        --log /tmp/prof/stage_rom-decode/profile.log --output /tmp/prof/profile.json
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

import rtl_abi3_reduced_token_campaign as campaign  # noqa: E402

SCHEMA = "opentallas.rtl.abi3_control_path_profile.v1"
VLT = "rtl/test/a3_control_profile.vlt"
HEADER = "rtl/test/a3_control_profile.h"

#: (family, sub) as the bridge latches them, rtl/abi3/ot_a3_engine_issue_bridge.sv.
OPERATORS: dict[tuple[int, int], str] = {
    (0x10, 0x02): "DMA.GATHER",
    (0x10, 0x03): "DMA.SCATTER",
    (0x20, 0x00): "TENSOR.MATMUL",
    (0x20, 0x03): "TENSOR.EMBED_LOOKUP",
    (0x30, 0x00): "VECTOR.RMS_NORM",
    (0x30, 0x01): "VECTOR.HEAD_RMS_NORM",
    (0x30, 0x02): "VECTOR.ROPE",
    (0x30, 0x03): "VECTOR.ADD",
    (0x30, 0x04): "VECTOR.SILU_MUL",
    (0x40, 0x01): "ATTENTION.GQA",
    (0x70, 0x00): "SELECTION.ARGMAX",
    (0x70, 0x01): "SELECTION.TOKEN_APPEND",
}

#: The microsequencer's state encoding, rtl/abi3/ot_a3_microsequencer.sv.
SEQ_STATES = (
    "IDLE CHECK_PC FETCH_WAIT DECODE_PUSH DECODE_WAIT PRED_REQ PRED_WAIT "
    "PRED_SYM PRED_EVAL PRED_HAZARD PRED_OBJECT WAIT_REQ WAIT_WAIT WAIT_EVAL "
    "DISPATCH LOOP_WAIT LOOP_SYM LOOP_OP LOOP_DONE ENG_WAIT SCHED_WAIT RESOLVE "
    "HAZARD HAZARD_STALL VIEW_PUB ISSUE STATE_SYM STATE_DONE DRAIN TRAP_WAIT "
    "FAULT_DRAIN FAULT_READ FAULT_WAIT FAULT_APPLY COMMIT DISCARD DONE"
).split()
#: The issue bridge's, rtl/abi3/ot_a3_engine_issue_bridge.sv.
BRIDGE_STATES = (
    "IDLE OP_WAIT INDEX_WAIT SOURCE_WAIT OUTPUT_WAIT NUM_WAIT START ENGINE_WAIT "
    "RESPONSE RMS_INPUT_WAIT MAP_VIEW_WAIT MAP_NUM_WAIT MAP_POLICY_WAIT "
    "MAP_INDEX_ISSUE MAP_INDEX_WAIT MAP_ADMIT EMBED_INDEX_ISSUE EMBED_INDEX_WAIT"
).split()
ADAPTER_STATES = ("IDLE", "REPLAY", "RUN", "GAP")

CASES = {
    f"{c['store']}-{c['name'].split('-', 1)[1]}": c for c in campaign.CASES
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(case: dict, stage_dir: Path, work: Path) -> Path:
    banks = campaign.bank_sizes(stage_dir / "driver.txt")
    params = list(campaign.GEOMETRY) + list(case["params"]) + [
        f"INDEX_WORDS={banks['index_words']}",
        f"SOURCE_WORDS={banks['source_words']}",
        f"RESULT_WORDS={banks['result_words']}",
        f"MATMUL_WEIGHT_BYTES={banks['weight_bytes']}",
    ]
    obj = work / "obj_profile"
    argv = [str(campaign.VERILATOR), "--cc", "--exe", "--build", "-j", "8",
            "-Wno-fatal", "-Wno-DECLFILENAME", "-Wno-PINMISSING",
            "-Wno-WIDTHEXPAND", "-Wno-WIDTHTRUNC",
            "--top-module", "ot_a3_shipped_prefix_top", "--Mdir", str(obj),
            "-CFLAGS", "-DOT_A3_PROFILE", "-CFLAGS", f"-I{ROOT / 'rtl/test'}",
            *[f"-G{p}" for p in params], "-o", "tokprof", str(ROOT / VLT),
            *[str(ROOT / s) for s in campaign.VEHICLE_SOURCES],
            str(ROOT / campaign.DRIVER)]
    done = subprocess.run(argv, cwd=work, capture_output=True, text=True)
    if done.returncode != 0:
        raise SystemExit(f"elaboration failed\n{done.stderr[-3000:]}")
    shutil.copy2(obj / "tokprof", stage_dir / "tokprof")
    return stage_dir / "tokprof"


def parse(log: str) -> dict:
    totals: dict[str, int] = {}
    hist = collections.defaultdict(dict)
    issues = []
    for line in log.splitlines():
        if line.startswith("PROFILE_ISSUE "):
            kv = {k: int(v) for k, v in
                  (f.split("=") for f in line.split()[1:])}
            issues.append(kv)
        elif line.startswith("PROFILE "):
            parts = line.split()
            if len(parts) == 3:
                totals[parts[1]] = int(parts[2])
            else:
                hist[parts[1]][int(parts[2])] = int(parts[3])
    counters = {m.group("key").strip().replace("/", "_").replace(" ", "_"):
                m.group("value").strip()
                for m in campaign.COUNTER_RE.finditer(log)}
    verdict = campaign.PASS_RE.search(log)
    return {"totals": totals, "hist": dict(hist), "issues": issues,
            "counters": counters,
            "self_check": verdict.group("verdict") if verdict else None}


def summarise(p: dict) -> dict:
    t = p["totals"]
    cycles = t["cycles"]
    per_op = collections.OrderedDict()
    for is_ in p["issues"]:
        name = OPERATORS.get((is_["fam"], is_["sub"]),
                             f"0x{is_['fam']:02x}.0x{is_['sub']:02x}")
        o = per_op.setdefault(name, {"launches": 0, "engine_cycles": 0,
                                     "mac_active_cycles": 0, "work": 0,
                                     "bridge_cycles_outside_engine": 0})
        o["launches"] += 1
        o["engine_cycles"] += is_["engine_cycles"]
        o["mac_active_cycles"] += is_["mac_cycles"]
        o["work"] += is_["work"]
        o["bridge_cycles_outside_engine"] += (
            is_["t_bridge_end"] - is_["t_bridge"] - is_["engine_cycles"])
    for o in per_op.values():
        o["share_of_token_cycles"] = o["engine_cycles"] / cycles
        o["engine_cycles_per_work_unit"] = (o["engine_cycles"] / o["work"]
                                            if o["work"] else None)
        o["engine_cycles_per_launch"] = o["engine_cycles"] / o["launches"]
    per_op = dict(sorted(per_op.items(), key=lambda kv: -kv[1]["engine_cycles"]))
    iss = p["issues"]
    gaps = [iss[i]["t_bridge"] - iss[i - 1]["t_bridge_end"]
            for i in range(1, len(iss))]
    n = len(iss)
    control = t["admission"] + t["adapter"] + t["frontend"]
    return {
        "cycles": cycles,
        "buckets": {k: {"cycles": t[k], "share": t[k] / cycles}
                    for k in ("engine", "admission", "adapter", "frontend")},
        "control_outside_engines": {"cycles": control, "share": control / cycles,
                                    "per_issue": control / n},
        "mac_active_cycles": t["mac_active"],
        "mac_active_share": t["mac_active"] / cycles,
        "issues": n,
        "per_issue_latency_cycles": {
            "sequencer_issue_to_bridge_accept_mean":
                sum(i["t_bridge"] - i["t_issue"] for i in iss) / n,
            "bridge_accept_to_engine_start_mean":
                sum(i["t_engine"] - i["t_bridge"] for i in iss) / n,
            "engine_end_to_bridge_idle_mean":
                sum(i["t_bridge_end"] - i["t_engine_end"] for i in iss) / n,
            "bridge_idle_to_next_bridge_accept_mean": sum(gaps) / len(gaps),
            "bridge_idle_to_next_bridge_accept_max": max(gaps),
        },
        "per_operator": per_op,
        "sequencer_state_cycles_while_nothing_in_flight": {
            SEQ_STATES[k]: v for k, v in
            sorted(p["hist"].get("seq_state_frontend", {}).items())},
        "bridge_state_cycles": {
            BRIDGE_STATES[k] if k < len(BRIDGE_STATES) else str(k): v
            for k, v in sorted(p["hist"].get("bridge_state", {}).items())},
        "adapter_state_cycles": {
            ADAPTER_STATES[k]: v for k, v in
            sorted(p["hist"].get("adapter_state", {}).items())},
        "selected_token": int(p["counters"].get("selected_token", -1)),
        "self_check": p["self_check"],
        "reported_cycles_including_drain": int(p["counters"].get("cycles", -1)),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--case", choices=sorted(CASES), default="rom-decode")
    ap.add_argument("--work", type=Path)
    ap.add_argument("--log", type=Path, help="parse an existing profile log")
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    case = CASES[args.case]
    if args.log is None:
        if args.work is None:
            raise SystemExit("--work is required unless --log is given")
        stage_dir = args.work / f"stage_{args.case}"
        campaign.stage(case, stage_dir)
        binary = build(case, stage_dir, args.work)
        done = subprocess.run([str(binary)], cwd=stage_dir, capture_output=True,
                              text=True)
        log = done.stdout + done.stderr
        args.log = stage_dir / "profile.log"
        args.log.write_text(log, encoding="utf-8")
    log = args.log.read_text(encoding="utf-8")
    body = {
        "schema": SCHEMA,
        "case": args.case,
        "deployment": case["deployment"],
        "log_sha256": hashlib.sha256(log.encode()).hexdigest(),
        "summary": summarise(parse(log)),
        "sources": {s: sha256(ROOT / s) for s in
                    (*campaign.VEHICLE_SOURCES, campaign.DRIVER, VLT, HEADER)},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
    s = body["summary"]
    print(f"{args.case}: {s['cycles']} cycles, engine share "
          f"{s['buckets']['engine']['share']:.4f}, control outside engines "
          f"{s['control_outside_engines']['cycles']}, token {s['selected_token']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
