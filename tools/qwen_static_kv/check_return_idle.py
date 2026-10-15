#!/usr/bin/env python3
"""Actual dual-clock return-ring idle bench and two occupancy mutants."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SRC = Path("rtl/qwen_sys/static_kv_20261014/qkd_static_kv_return_slots.sv")
BENCH = Path("rtl/test/qwen_static_kv/tb_static_return_idle.sv")

def main():
    results = []
    with tempfile.TemporaryDirectory(prefix="qkv-return-idle-") as td:
        for phase in (137, 637):
            for mutant in (0, 1, 2):
                source = (ROOT / SRC).read_text()
                if mutant == 1:
                    source = source.replace("(published==done_sync2)", "1'b1")
                if mutant == 2:
                    source = source.replace("(pub_sync2==consumed)", "1'b1")
                staged = Path(td) / f"ring{mutant}.sv"
                staged.write_text(source)
                exe = str(Path(td) / f"gate{phase}_{mutant}")
                compiled = subprocess.run(["iverilog", "-g2012", "-s", "tb_static_return_idle",
                    f"-Ptb_static_return_idle.PHASE_PS={phase}", "-o", exe, str(staged), str(ROOT / BENCH)],
                    capture_output=True, text=True)
                if compiled.returncode:
                    raise RuntimeError(compiled.stderr)
                run = subprocess.run(["vvp", exe], capture_output=True, text=True)
                if (run.returncode == 0) != (mutant == 0):
                    raise RuntimeError(run.stdout + run.stderr)
                if mutant and "IDLE outstanding publication lost" not in run.stdout:
                    raise RuntimeError("mutant failed for an unrelated reason: " + run.stdout)
                results.append(dict(phase_ps=phase, mutant=mutant, exit_code=run.returncode, output=run.stdout))
    print(json.dumps(dict(status="PASS_COMPONENT_ONLY", cases=results,
        source_sha256={str(p): hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
                       for p in (SRC, BENCH, Path(__file__).relative_to(ROOT))},
        boundary="Two local-domain observations require parent synchronization and upstream quiet; no whole-KV drain or physical adoption claim."), indent=2))

if __name__ == "__main__":
    main()
