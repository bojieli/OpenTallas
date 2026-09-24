#!/usr/bin/env python3
"""Token-level RTL simulation of a layer-per-package ROM array of decode cores.

rtl/test/tb_hdc_array.sv chains ot_hdc_core packages through ot_rom_pkg_link:
package n holds layer n (the first also the embedding), the hidden state moves
between packages as one header and 8 data flits, and the last package returns
the token to the first.  Every user starts from an EMPTY KV cache, runs the
oracle's 16-token prompt and generates 3 tokens; each generated id is compared
with the torch oracle's.  Configurations (built and run in parallel):

* 4 packages, 4 users: lm_head shares the last layer's package;
* 5 packages, 5 users: lm_head on a package of its own;
* 6 packages, 6 users: lm_head split by vocabulary over two packages, the
  last combining the two halves' argmax (strictly greater wins, so ties keep
  the lower row, as numpy's argmax does);
* 10 packages, 10 users: as 6, with every layer split into an attention
  package and an MLP package.

Aggregate throughput is token-steps per cycle across all users; the single-core
reference is results/rtl/hdc_decode_campaign.json.  Writes
results/rtl/hdc_array_campaign.json.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rtl_hdc_decode_campaign as core  # noqa: E402

OUT = ROOT / "results/rtl/hdc_array_campaign.json"
TB = ROOT / "rtl/test/tb_hdc_array.sv"
HARNESS = ROOT / "rtl/test/hdc_array_harness.cpp"
LINK = ROOT / "rtl/rom/ot_rom_pkg_link.sv"
CONFIGS = [(4, 4, 0), (5, 5, 0), (6, 6, 1), (10, 10, 1)]
STEPS_PER_USER = 16 + 3 - 1
RES = re.compile(r"HDC_ARRAY nodes=(\d+) users=(\d+) generated=(\d+) mismatches=(\d+) total_cycles=(\d+)")
BUSY = re.compile(r"NODE_BUSY node=(\d+) cycles=(\d+)")
GEN = re.compile(r"GEN user=(\d+) pos=(\d+) token=(\d+) cycle=(\d+)")
STALLS = re.compile(r"LINK_STALLS (\d+)")


def run_config(scratch: Path, nodes: int, users: int, headsplit: int) -> dict:
    img, obj = scratch / f"img{nodes}", scratch / f"obj{nodes}_{users}"
    subprocess.run([sys.executable, str(ROOT / "tools/hdc_program.py"), "--out", str(img), "--stages", str(nodes)],
                   check=True, capture_output=True)
    subprocess.run(["verilator", "--cc", "--exe", "--build", "-O2", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED",
                    "-Wno-BLKSEQ", "--top-module", "tb_hdc_array", f"-GNODES={nodes}", f"-GUSERS={users}",
                    f"-GHEADSPLIT={headsplit}",
                    "-Mdir", str(obj), f"-I{core.ISA_SVH.parent}", *map(str, core.HDC), *map(str, core.PIPES),
                    str(LINK), str(TB), str(HARNESS), "-CFLAGS", "-O1", "-j", "8"],
                   check=True, capture_output=True)
    out = subprocess.run([str(obj / "Vtb_hdc_array"), f"+DIR={img}", "+NGEN=3"], check=True,
                         capture_output=True, text=True).stdout
    m = RES.search(out)
    n, u, gen, bad, cycles = map(int, m.groups())
    busy = {int(a): int(b) for a, b in BUSY.findall(out)}
    gens = [dict(zip(("user", "position", "token", "cycle"), map(int, g))) for g in GEN.findall(out)]
    steps = users * STEPS_PER_USER
    return {"packages": n, "users": u, "lm_head_split": bool(headsplit), "generated_tokens": gen, "mismatches": bad, "total_cycles": cycles,
            "token_steps": steps, "cycles_per_token_step": round(cycles / steps, 1),
            "package_busy_cycles": [busy[i] for i in sorted(busy)],
            "package_busy_cycles_per_step": [round(busy[i] / steps, 1) for i in sorted(busy)],
            "link_credit_stalls": int(STALLS.search(out).group(1)), "generated": gens,
            "pass": "PASS" in out and bad == 0 and gen == users * 3}


def run() -> dict:
    single = json.loads(core.OUT.read_text())["single_step"]["cycles"]
    with tempfile.TemporaryDirectory() as scratch, ThreadPoolExecutor(len(CONFIGS)) as pool:
        results = list(pool.map(lambda c: run_config(Path(scratch), *c), CONFIGS))
    for r in results:
        r["aggregate_speedup_vs_single_core"] = round(single / r["cycles_per_token_step"], 3)
    return {
        "schema": "opentallas.hdc-array-campaign.v1",
        "status": "pass" if all(r["pass"] for r in results) else "fail",
        "claim_boundary": "functional, cycle-accurate RTL simulation of a layer-per-package array of decode "
                          "cores with behavioural memories; the package link's PHY is a 60-cycle delay-line "
                          "stand-in (ot_rom_pkg_link). All users share the oracle's one prompt.",
        "single_core_cycles_per_token": single,
        "configurations": results,
        "input_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in (TB, HARNESS, LINK, core.ISA_SVH, *core.HDC, *core.PIPES, *core.TOOLS)},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    result = run()
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    for r in result["configurations"]:
        print(result["status"], r["packages"], "packages", r["users"], "users:", r["cycles_per_token_step"],
              "cycles/step, x", r["aggregate_speedup_vs_single_core"], "busy/step", r["package_busy_cycles_per_step"])
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
