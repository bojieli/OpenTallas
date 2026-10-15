#!/usr/bin/env python3
"""Source-pinned phase-4 local leaf equivalence with actual SRAM macro models.

The reference implements original-parent SV logic independently in the bench.
This is a common-phase component test, not a native/die or physical result.
"""
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
LEGACY = "rtl/rom/ot_coll_tp8_static.sv"
MACRO = "physical/asap7_memory_macros/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v"
BENCH = "rtl/test/tb_coll_local_leaves.sv"
HELPERS = ("ot_coll_local_sring_data", "ot_coll_local_sring_meta", "ot_coll_local_sx_quarter",
           "ot_coll_local_output", "ot_coll_local_pair_capture", "ot_coll_local_fold_capture")


def source(ref, path):
    return subprocess.check_output(["git", "show", ref + ":" + path], cwd=ROOT, text=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ref", default="1b53a196d")
    ap.add_argument("--out", required=True)
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--only", help="one named case")
    args = ap.parse_args()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    ref = subprocess.check_output(["git", "rev-parse", args.ref], cwd=ROOT, text=True).strip()
    sources = {path: source(ref, path) for path in (CORE, LEGACY, MACRO)}
    sources[BENCH] = (ROOT / BENCH).read_text()
    sources["tools/qwen_coll_local_leaf_bench.py"] = Path(__file__).read_text()
    pins = {path: hashlib.sha256(text.encode()).hexdigest() for path, text in sources.items()}
    legacy = sources[LEGACY]
    # Refuse silently using the old reference against a different parent law.
    for token in ("cc - 9'(LS + 1)", "gd_r[gr] ? hi_q", "tfv_r[kq] ? rf_d", "td_r - PK + 2'd3",
                  "if (tbv_r[gr])", "ps_e[gs] ? {4{32'h7fc00000}}"):
        if token not in legacy:
            raise ValueError("original reference law changed: " + token)
    helper_text = []
    for name in HELPERS:
        match = re.search(r"(?ms)^\(\* keep_hierarchy = 1 \*\) module " + name + r"\b.*?\bendmodule", sources[CORE])
        if match is None:
            raise ValueError("actual phase-4 helper absent: " + name)
        helper_text.append(match.group(0))
    actual = "\n".join(helper_text) + "\n"
    (out / "executed_helpers.sv").write_text(actual)
    (out / "source_pins.json").write_text(json.dumps(dict(source_ref=ref, pins=pins,
        executed_helpers_sha256=hashlib.sha256(actual.encode()).hexdigest()), indent=2) + "\n")
    cases = {
        "positive": (None, None, 0, []),
        "wrong_read_offset": (".r_addr_in(cc-9'(LS+1))", ".r_addr_in(cc-9'(LS))", 2, []),
        "wrong_gather_select": (None, None, 0, ["-DOT_TP8S_MUT_GATHER"]),
        "wrong_rank": ("wire[1:0]jr=td_r-pkg_q+2'd3;", "wire[1:0]jr=td_r-pkg_q+2'd2;", 1, []),
        "wrong_output_mux": ("q<=tfv_q?(tfo_q?rr:dr):gather;", "q<=tfv_q?(tfo_q?dr:rr):gather;", 1, []),
        "wrong_pair_order": ("lo<=die_q?peer_data:local_data;hi<=die_q?local_data:peer_data;",
                             "lo<=die_q?local_data:peer_data;hi<=die_q?peer_data:local_data;", 1, []),
        "wrong_error_payload": ("32'h7fc00000", "32'h7fc00001", 1, []),
        "wrong_ring_metadata": ("tc_v?tc_o:g_od,!tc_v", "tc_v?!tc_o:g_od,!tc_v", 1, []),
    }
    if args.only:
        cases = {args.only: cases[args.only]}

    def run(item):
        name, (old, new, expected_count, defines) = item
        text = actual
        if old is not None:
            if text.count(old) != expected_count:
                raise ValueError(name + ": mutant source replacement count changed")
            text = text.replace(old, new)
        with tempfile.TemporaryDirectory(prefix="coll-local-" + name + "-") as temporary:
            directory = Path(temporary)
            helper = directory / "helpers.sv"
            helper.write_text(text)
            macro = directory / "macro.v"
            macro.write_text(sources[MACRO])
            binary = directory / "bench.vvp"
            command = ["iverilog", "-g2012", "-s", "tb_coll_local_leaves", *defines,
                       "-o", str(binary), str(ROOT / BENCH), str(helper), str(macro)]
            result = subprocess.run(command, capture_output=True, text=True)
            (out / (name + ".compile.log")).write_text(result.stdout + result.stderr)
            if result.returncode:
                return dict(name=name, compile_exit=result.returncode, ok=False)
            binary_sha = hashlib.sha256(binary.read_bytes()).hexdigest()
            result = subprocess.run(["vvp", str(binary)], capture_output=True, text=True)
            (out / (name + ".log")).write_text(result.stdout + result.stderr)
            line = next((line for line in result.stdout.splitlines() if line.startswith("LOCAL_LEAVES checks=")), None)
            if line is None:
                return dict(name=name, compile_exit=0, exit=result.returncode, ok=False)
            measured = {key: int(value) for key, value in re.findall(r"(\w+)=(\d+)", line)}
            data_errors = sum(measured[key] for key in ("ring_errors", "sx_errors", "output_errors", "pair_errors", "fold_errors"))
            errors = data_errors + measured["meta_errors"]
            expected_positive = name == "positive"
            ok = (measured["checks"] == 6000 and measured["known_ring_checks"] >= 4900 and
                  all(measured["pk" + str(pk)] > 0 for pk in range(4)) and
                  ((expected_positive and result.returncode == 0 and errors == 0) or
                   (not expected_positive and result.returncode != 0 and data_errors > 0)))
            return dict(name=name, compile_exit=0, exit=result.returncode, measured=measured,
                        binary_sha256=binary_sha, executed_helpers_sha256=hashlib.sha256(text.encode()).hexdigest(),
                        compile_defines=defines, ok=ok)

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        results = list(pool.map(run, cases.items()))
    receipt = dict(schema="opentallas.qwen.local_leaf_unit.v1", source_ref=ref, source_pins=pins,
                   actual_macro=MACRO, helpers=list(HELPERS), cycles_per_case=6000,
                   scope=__doc__, clocks="Common compiled edge; physical phase, pin/reset/clock and native whole-die gates remain open",
                   workload="Full512data/640ringbits, all3SXfaces x4quarters, metadata/nonmetadataquarters, PK0..3, counter/select/metadata resets staggered midrun, full-rate bits including IEEE special encodings",
                   extra_edges=0, results=results, ok=all(result["ok"] for result in results))
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(results, indent=2), flush=True)
    return 0 if receipt["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
