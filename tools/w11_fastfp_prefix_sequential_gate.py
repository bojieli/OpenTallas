#!/usr/bin/env python3
"""Bounded two-state sequential integration gate for a generated KSA substitution.

This gate neither replaces a build's source list nor qualifies hardware or all
FP arithmetic. Independent all-input proofs of the actual KSA remain required.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import resource
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
PIN = "4e38326d6f361bc85e660f48c59c355e2bb95274"
SOURCE = "rtl/hdc/ot_hdc_fastfp.sv"
SOURCE_SHA = "446f5d582511eb0e3afd806123e4e2238265a7bda87d487b8cc703f0f048f611"
TB = "rtl/test/tb_w11_fastfp_prefix_sequential_gate.sv"
HARNESS = "rtl/test/w11_fastfp_prefix_sequential_gate.cpp"
SEEDS = (0x12345678, 0x9E3779B9, 0xC001D00D)
ADDITION = "    assign {cout, s} = {1'b0, a} + {1'b0, b} + {{W{1'b0}}, cin};\n"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def substitute_ksa(source):
    """Change the one KSA body; its signature and all other text stay exact."""
    start = source.index("module ot_hdc_ksa ")
    body = source.index(");\n", start) + len(");\n")
    end = source.index("endmodule", body)
    return source[:body] + ADDITION + source[end:]


def namespace(source, prefix):
    names = re.findall(r"\bmodule\s+(\w+)", source)
    if len(names) != len(set(names)):
        raise ValueError("duplicate source module")
    pattern = re.compile(r"\b(?:" + "|".join(map(re.escape, names)) + r")\b")
    return pattern.sub(lambda m: prefix + m[0], source)


def generated(source, variant="candidate"):
    if variant == "reference":
        return namespace(source, "gate_ref_")
    changed = substitute_ksa(source)
    if variant == "carry_mutant":
        changed = changed.replace(ADDITION, ADDITION.replace("{{W{1'b0}}, cin}", "{(W+1){1'b0}}"))
    elif variant == "reset_mutant":
        reset = "if (!rst_n) begin y <= 32'd0; err <= E_NONE; valid_out <= 1'b0; end"
        if changed.count(reset) != 2:
            raise ValueError("reset mutation source shape changed")
        changed = changed.replace(reset, reset.replace("y <= 32'd0", "y <= 32'd1"))
    elif variant != "candidate":
        raise ValueError("unknown variant")
    return namespace(changed, "gate_sim_")


def limited_child():
    # Per-child ceiling; --build -j 2 is the only worker pool.
    resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3, 4 * 1024**3))


def run_command(command, log, timeout):
    with log.open("w") as stream:
        started = time.monotonic()
        result = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT,
                                timeout=timeout, preexec_fn=limited_child)
    return {"command": command, "returncode": result.returncode,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "log": str(log), "log_sha256": digest(log.read_bytes())}


def run_gate(work, output, random_cycles=8192):
    work = work.resolve()
    output = output.resolve()
    if work.exists() or output.exists():
        raise ValueError("fresh work directory and new record required; never overwrite verdicts")
    if not 1 <= random_cycles <= 32768:
        raise ValueError("bounded random-cycle aperture 1..32768 per seed")
    source_raw = (ROOT / SOURCE).read_bytes()
    if digest(source_raw) != SOURCE_SHA:
        raise ValueError("reference source differs from exact pinned source")
    pinned = subprocess.check_output(["git", "show", PIN + ":" + SOURCE], cwd=ROOT)
    if pinned != source_raw:
        raise ValueError("reference pin mismatch")
    work.mkdir(parents=True)
    source = source_raw.decode()
    reference = generated(source, "reference").encode()
    (work / "reference.sv").write_bytes(reference)
    evidence_paths = (TB, HARNESS, "tools/w11_fastfp_prefix_sequential_gate.py",
                      "tests/test_w11_fastfp_prefix_sequential_gate.py")
    record = {
        "schema": "w11_fastfp_prefix_sequential_gate_v1", "status": "RUNNING",
        "reference_commit": PIN, "reference_path": SOURCE, "reference_sha256": SOURCE_SHA,
        "gate_sources": {p: digest((ROOT / p).read_bytes()) for p in evidence_paths},
        "tools": {"verilator": subprocess.check_output(["verilator", "--version"], text=True).strip(),
                  "compiler": subprocess.check_output(["g++", "--version"], text=True).splitlines()[0]},
        "workers": 2, "child_address_space_limit_bytes": 4 * 1024**3,
        "build_timeout_seconds": 180, "simulation_timeout_seconds": 30,
        "random_cycles_per_seed": random_cycles, "seeds": list(SEEDS),
        "simulation_semantics": "Verilator two-state, default zero initialization of unreset state on both sides; compare every output on every sampled clock including bubbles and reset, plus asynchronous reset assertions.",
        "candidate_change": "Only KSA body replaced with W+1-bit zero-extended addition; module identifiers renamed into reference/candidate namespaces. All other candidate text exact after reversing namespace.",
        "combinational_formal_proof": {"required_separately": True, "owner": "Hubble", "intaken_by_this_gate": False},
        "sequential_formal_proof": False,
        "all_input_FP_equivalence": False, "golden_arithmetic_qualification": False,
        "full_die_qualification": False, "hardware_credit": False, "adoption": False,
        "runs": [],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        for variant in ("candidate", "carry_mutant", "reset_mutant"):
            directory = work / variant
            directory.mkdir()
            candidate = generated(source, variant).encode()
            (directory / "candidate.sv").write_bytes(candidate)
            build_command = ["verilator", "--cc", "--exe", "--build", "-j", "2", "-O1",
                             "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNOPTFLAT", "-Wno-UNUSED",
                             "--top-module", "tb_w11_fastfp_prefix_sequential_gate", "--prefix", "Vgate",
                             "-Mdir", str(directory / "obj"), str(work / "reference.sv"),
                             str(directory / "candidate.sv"), str(ROOT / TB), str(ROOT / HARNESS),
                             "-CFLAGS", "-O1 -std=c++11"]
            entry = {"variant": variant, "reference_generated_sha256": digest(reference),
                     "candidate_generated_sha256": digest(candidate),
                     "build": run_command(build_command, directory / "build.log", 180), "simulations": []}
            record["runs"].append(entry)
            if entry["build"]["returncode"]:
                raise RuntimeError("build failed: " + variant)
            for seed in SEEDS if variant == "candidate" else SEEDS[:1]:
                command = [str(directory / "obj/Vgate"), str(seed), str(random_cycles)]
                simulation = run_command(command, directory / ("seed_" + str(seed) + ".log"), 30)
                text = Path(simulation["log"]).read_text()
                results = [line[7:] for line in text.splitlines() if line.startswith("RESULT ")]
                if len(results) != 1:
                    raise RuntimeError("missing structured verdict: " + variant)
                simulation["result"] = json.loads(results[0])
                entry["simulations"].append(simulation)
                wanted = "PASS" if variant == "candidate" else "FAIL"
                expected_rc = 0 if variant == "candidate" else 1
                if simulation["returncode"] != expected_rc or simulation["result"]["status"] != wanted:
                    raise RuntimeError("unexpected verdict: " + variant)
                if variant != "candidate":
                    mismatch = simulation["result"]["first_mismatch"]["property"]
                    if variant == "carry_mutant" and "tuple" not in mismatch:
                        raise RuntimeError("carry mutant failed for unrelated property")
                    if variant == "reset_mutant" and "tuple" not in mismatch and "reset" not in mismatch:
                        raise RuntimeError("reset mutant failed for unrelated property")
        if (ROOT / SOURCE).read_bytes() != source_raw:
            raise RuntimeError("reference source changed during run")
        record["status"] = "PASS_BOUNDED_DIRECTED_RANDOM_SEQUENTIAL_GATE"
    except Exception as exc:
        record["status"] = "FAIL"
        record["error"] = str(exc)
        raise
    finally:
        output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--random-cycles", type=int, default=8192)
    args = parser.parse_args()
    result = run_gate(args.work, args.output, args.random_cycles)
    print(result["status"])
