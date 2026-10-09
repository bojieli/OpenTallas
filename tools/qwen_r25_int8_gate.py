#!/usr/bin/env python3
"""Run the minimum exact INT8 line/production-issuer gates, including sign mutant."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ["rtl/hbm_accel/sm/ot_hbm_accel_int8_line.sv",
           "rtl/hbm_accel/sm/ot_hbm_accel_issue_pq.sv",
           "rtl/hbm_accel/sm/ot_hbm_accel_smh.sv",
           "rtl/test/tb_hbm_int8_line.sv", "rtl/test/tb_hbm_int8_issue.sv",
           "tools/uarch_model.py", "tools/qwen_r25_int8_gate.py", "rtl/test/tb_hbm_int8_credit.sv"]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--pipe",action="store_true")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    records = []
    with tempfile.TemporaryDirectory(prefix="qwen-int8-") as tmp:
        tmp = Path(tmp)
        (tmp / "golden.hex").write_text("".join(
            f"{struct.unpack('>I', struct.pack('>f', c if c < 128 else c - 256))[0] >> 16:04x}\n"
            for c in range(256)))
        for name, top, files, defines in [
            ("credit", "tb_hbm_int8_credit", [SOURCES[0], SOURCES[7]], []),
            ("line", "tb_hbm_int8_line", [SOURCES[0], SOURCES[3]], []),
            ("issue", "tb_hbm_int8_issue", [SOURCES[0], SOURCES[1], SOURCES[4]], []),
            ("negative_prefetch", "tb_hbm_int8_issue", [SOURCES[0], SOURCES[1], SOURCES[4]], ["-DOT_INT8_MUT_PREFETCH"]),
            ("negative_sign", "tb_hbm_int8_line", [SOURCES[0], SOURCES[3]], ["-DOT_INT8_MUT_SIGN"]),
        ]:
            cmd = ["iverilog", "-g2012", *defines, *([f"-P{top}.PIPE=1"] if args.pipe else []), "-s", top, "-o", str(tmp / name)]
            cmd += [str(ROOT / f) for f in files]
            build = subprocess.run(cmd, capture_output=True, text=True)
            if build.returncode:
                raise RuntimeError(build.stderr)
            run = subprocess.run(["vvp", str(tmp / name)], cwd=tmp, capture_output=True, text=True)
            (args.out / f"{name}.log").write_text(run.stdout + run.stderr)
            expected = run.returncode != 0 if defines else run.returncode == 0
            if defines:
                expected = expected and ("beat mismatch" in run.stdout or "cross-operation prefetch" in run.stdout)
            records.append({"name": name, "returncode": run.returncode, "gate_pass": expected})
    # Extract only the independent model function, without importing unrelated
    # architecture modules into this component-level gate.
    tree = ast.parse((ROOT / "tools/uarch_model.py").read_text())
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                and n.name == ("qwen_r25_int8_pipeline_model" if args.pipe else "qwen_r25_int8_unpack_model"))
    scope = {}
    exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ("qwen_r25_int8_unpack_model","qwen_r25_fmt3_wide_model","qwen_r25_int8_pipeline_model")], type_ignores=[]), "model", "exec"), scope)
    evidence = {
        "verdict": "PASS" if all(r["gate_pass"] for r in records) else "FAIL",
        "scope": "exact conversion and finite protocol; production IL8 issuer; no physical qualification",
        "contract": "128 INT8 codes pair consecutive issuer beats, low 64 then high 64; issue interleaves rows",
        "precondition": "fmt3 operation has an even total count of real BF16 beats; all target Qwen shapes satisfy this",
        "latency": ("two registered stages" if args.pipe else "one registered stage") + ", 2 consecutive output beats per packed line; no arithmetic-order change",
        "source_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in SOURCES},
        "pipeline": bool(args.pipe), "model": scope[node.name](), "tests": records,
    }
    (args.out / "verdict.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps(evidence["tests"]))
    if evidence["verdict"] != "PASS":
        raise SystemExit(1)

if __name__ == "__main__":
    main()
