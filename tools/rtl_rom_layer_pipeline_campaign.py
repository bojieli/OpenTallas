#!/usr/bin/env python3
"""Simulate the layer-per-package ROM pipeline and check its timing law.

docs/ANALYTICAL_REPORT.md's redesigned ROM machine pipelines layers across
packages: per-user latency is the sum of stage services plus link hops, and a
pipeline full of different users delivers one token per stage service.  This
campaign runs four ot_rom_layer_stage packages joined by ot_rom_pkg_link under
Icarus, scoreboards every token's hidden state against a reference model, and
checks

    first-token latency = STAGES * stage_service + (STAGES + 1) * link_latency (+/-1)
    arrival interval    = stage_service, for every later token

where stage_service = k * EXPERT_WORDS / BANKS + reader and handshake cycles.
Functional stand-ins (router, arithmetic) are stated in the RTL header.
"""
import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [ROOT / "rtl/rom/ot_rom_striped_expert_reader.sv", ROOT / "rtl/rom/ot_rom_pkg_link.sv",
           ROOT / "rtl/rom/ot_rom_layer_stage.sv"]
TB = ROOT / "rtl/test/tb_rom_layer_pipeline.sv"
OUT = ROOT / "results/rtl/rom_layer_pipeline_campaign.json"
# Must match the testbench.
STAGES, TOKENS, BANKS, EXPERT_WORDS, SELECT, SENSE, CHANNEL = 4, 8, 8, 64, 6, 2, 60
READ = SELECT * EXPERT_WORDS // BANKS + SENSE + 2           # striped reader, as in its campaign
STAGE_SERVICE = READ + 4                                    # accept, start, done and send handshakes
LINK = 2 + CHANNEL + 2 + 1   # TX, channel, RX, registered output
LINT_FLAGS = ("-Wall", "-Wno-DECLFILENAME", "-Wno-UNUSED", "-Wno-WIDTH", "-Wno-BLKSEQ")
TOKEN = re.compile(r"TOKEN tag=(\d+) latency=(\d+) arrival=(\d+) interval=(\d+)")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run() -> dict:
    with tempfile.TemporaryDirectory() as scratch:
        image = Path(scratch) / "tb.vvp"
        subprocess.run(["iverilog", "-g2012", "-o", str(image), *map(str, SOURCES), str(TB)], check=True)
        sim = subprocess.run(["vvp", "-n", str(image)], check=True, capture_output=True, text=True)
    lint = subprocess.run(["verilator", "--lint-only", *LINT_FLAGS, "--top-module", "ot_rom_layer_stage",
                           str(SOURCES[0]), str(SOURCES[2])], capture_output=True, text=True)
    tokens = [dict(zip(("tag", "latency", "arrival", "interval"), map(int, m.groups())))
              for m in map(TOKEN.match, sim.stdout.splitlines()) if m]
    expected_first = STAGES * STAGE_SERVICE + (STAGES + 1) * LINK
    intervals = [t["interval"] for t in tokens[1:]]
    ok = (len(tokens) == TOKENS and "SUMMARY tokens=8 errors=0" in sim.stdout
          and abs(tokens[0]["latency"] - expected_first) <= 1
          and all(i == STAGE_SERVICE for i in intervals)
          and [t["tag"] for t in tokens] == list(range(TOKENS))
          and lint.returncode == 0)
    return {
        "schema": "opentallas.rom-layer-pipeline-campaign.v1",
        "status": "pass" if ok else "fail",
        "claim_boundary": "functional RTL of a four-package layer pipeline: striped-bank reads, "
                          "accumulate-on-arrival, cut-through package links. Router and arithmetic are "
                          "stated stand-ins; no macro, PHY, area, timing closure or energy.",
        "parameters": {"stages": STAGES, "tokens": TOKENS, "banks": BANKS, "expert_words": EXPERT_WORDS,
                       "selected_experts": SELECT, "channel_cycles": CHANNEL, "clock_hz": 1e9},
        "stage_service_cycles": STAGE_SERVICE,
        "link_latency_cycles": LINK,
        "first_token_latency_cycles": tokens[0]["latency"] if tokens else None,
        "expected_first_token_latency_cycles": expected_first,
        "steady_arrival_interval_cycles": sorted(set(intervals)),
        "users_in_flight": round(expected_first / STAGE_SERVICE, 2),
        "tokens": tokens,
        "verilator_lint": {"returncode": lint.returncode, "flags": list(LINT_FLAGS),
                           "messages": lint.stderr.strip().splitlines()[:20]},
        "input_sha256": {str(p.relative_to(ROOT)): sha(p) for p in (*SOURCES, TB, Path(__file__))},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    result = run()
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(result["status"], "first", result["first_token_latency_cycles"], "expected",
          result["expected_first_token_latency_cycles"], "interval", result["steady_arrival_interval_cycles"])
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
