#!/usr/bin/env python3
"""Compare actual legacy/local ring macros at the same compiled clock edge."""
import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CORE = "rtl/rom/ot_coll_tp8_local_roots.sv"
OLD = "rtl/rom/ot_coll_tp8_static.sv"
SMALL = "physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v"
WIDE = "physical/asap7_memory_macros/ot_sram_1r1w_32x546_m1/ot_sram_1r1w_32x546_m1.v"
BENCH = "rtl/test/tb_coll_ring_quarters.sv"


def extract(text, name):
    match = re.search(r"(?ms)^(?:\(\*[^\n]*\*\) )?module " + name + r"\b.*?\bendmodule", text)
    if match is None:
        raise ValueError("actual module absent: " + name)
    return match.group(0) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ref", default="3acb6219e")
    ap.add_argument("--out", required=True)
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--only")
    ap.add_argument("--exclude", nargs="*", default=[])
    args = ap.parse_args()
    out = Path(args.out).resolve();out.mkdir(parents=True, exist_ok=True)
    ref = subprocess.check_output(["git", "rev-parse", args.ref], cwd=ROOT, text=True).strip()
    sources = {path: subprocess.check_output(["git", "show", ref + ":" + path], cwd=ROOT, text=True)
               for path in (CORE, OLD, SMALL, WIDE)}
    sources[BENCH] = (ROOT / BENCH).read_text()
    sources["tools/qwen_coll_ring_quarter_bench.py"] = Path(__file__).read_text()
    pins = {path: hashlib.sha256(text.encode()).hexdigest() for path, text in sources.items()}
    quarter = extract(sources[CORE], "ot_coll_local_ring_quarter")
    private_reg = extract(sources[CORE], "ot_coll_local_rep_reg")
    legacy = extract(sources[OLD], "ot_coll_static_ring") + extract(sources[OLD], "ot_coll_rep_reg")
    cases = [(variant, offset) for variant in ("positive", "wrong_bank", "wrong_offset", "wrong_metadata")
             for offset in (2, 20, 32, 33, 55, 64)]
    if args.only:
        cases = [case for case in cases if f"{case[0]}_{case[1]}" == args.only]
        if not cases:
            raise ValueError("unknown case: " + args.only)
    cases = [case for case in cases if f"{case[0]}_{case[1]}" not in args.exclude]

    def run(case):
        variant, offset = case;name = f"{variant}_{offset}"
        case_out = out / name;case_out.mkdir(parents=True, exist_ok=True)
        dut = quarter
        if variant == "wrong_bank":
            old, new, count = "ra[5]?2'b10:2'b01", "ra[5]?2'b01:2'b10", 2
        elif variant == "wrong_offset":
            old, new, count = "wa-AW'(OFF-1)", "wa-AW'(OFF-2)", 1
        elif variant == "wrong_metadata":
            old, new, count = "{{(128-W){1'b0}},wd}", "{{(128-W){1'b0}},(wd ^ W'((W==34)?1:0))}", 1
        else:
            old, new, count = None, None, 0
        if old:
            if dut.count(old) != count:
                raise ValueError("mutant source changed: " + name)
            dut = dut.replace(old, new)
        executed = dut + private_reg + legacy
        (case_out / "actual_compiled_helpers.sv").write_text(executed)
        with tempfile.TemporaryDirectory(prefix="ring-quarter-") as temporary:
            temporary = Path(temporary)
            helpers = temporary / "helpers.sv";helpers.write_text(executed)
            small = temporary / "small.v";small.write_text(sources[SMALL])
            wide = temporary / "wide.v";wide.write_text(sources[WIDE])
            binary = temporary / "sim.vvp"
            command = ["iverilog", "-g2012", "-s", "tb_coll_ring_quarters", f"-Ptb_coll_ring_quarters.OFF={offset}",
                       "-o", str(binary), str(ROOT / BENCH), str(helpers), str(small), str(wide)]
            result = subprocess.run(command, capture_output=True, text=True)
            (case_out / "compile.log").write_text(result.stdout + result.stderr)
            if result.returncode:
                return dict(name=name, compile_exit=result.returncode, ok=False)
            binary_pin = hashlib.sha256(binary.read_bytes()).hexdigest()
            result = subprocess.run(["vvp", str(binary)], capture_output=True, text=True)
            (case_out / "run.log").write_text(result.stdout + result.stderr)
            line = next((line for line in result.stdout.splitlines() if line.startswith("RING_QUARTERS off=")), None)
            if line is None:
                return dict(name=name, compile_exit=0, exit=result.returncode, ok=False)
            measured = {key: int(value) for key, value in re.findall(r"(\w+)=(\d+)", line)}
            # The read-bank selector is absent for B=1; these are explicit
            # insensitive controls, rather than falsely reported rejections.
            expect_pass = variant == "positive" or (variant == "wrong_bank" and offset <= 32)
            ok = (measured["checks"] == 6144 and measured["known_checks"] >= 6000 and
                  measured["all_bits_one"] == 1 and measured["all_bits_zero"] == 1 and
                  measured["unknown_errors"] == 0 and
                  ((expect_pass and result.returncode == 0 and measured["errors"] == 0) or
                   (not expect_pass and result.returncode != 0 and measured["errors"] > 0)))
            record = dict(name=name, offset=offset, variant=variant, expect_pass=expect_pass,
                          compile_exit=0, exit=result.returncode, measured=measured,
                          binary_sha256=binary_pin, executed_helpers_sha256=hashlib.sha256(executed.encode()).hexdigest(), ok=ok)
            (case_out / "receipt.json").write_text(json.dumps(record, indent=2) + "\n")
            print(name, "PASS" if ok else "UNEXPECTED", measured["errors"], flush=True)
            return record

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        results = list(pool.map(run, cases))
    receipt = dict(schema="opentallas.qwen.ring_quarter_unit.v1", source_ref=ref, source_pins=pins,
                   logical_bits=546, quarter_widths=[128, 128, 128, 128, 34], cycles_per_case=6144,
                   actual_macros=[SMALL, WIDE], extra_edges=0, qualified_native=False, qualified_physical=False,
                   scope="Actual legacy ring and actual packed quarters; same compiled edge, mid-run reset and full-depth wrap, full-rate writes, all546bits exercise0and1. No core/generator edit or inherited phase4 qualification.",
                   results=results, ok=all(result["ok"] for result in results))
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return 0 if receipt["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
