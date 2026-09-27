#!/usr/bin/env python3
"""Source-pinned SW8/SW16 KV ingress and physical-sector boundary gates."""
import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUTS = [ROOT / p for p in (
    "rtl/hdc/ingest/ot_hdc_ingest_fp8q.sv",
    "rtl/hdc/kv/ot_hdc_qwen_kv_write_adapter.sv",
    "rtl/hdc/kv/ot_hdc_qwen_kv_vector_bridge.sv",
    "rtl/hdc/kv/ot_hdc_qwen_hbm_sector_bridge.sv",
    "rtl/test/tb_hdc_qwen_kv_vector_bridge.sv",
    "rtl/test/tb_hdc_qwen_hbm_sector_bridge.sv",
    "rtl/hdc/kv/ot_hdc_qwen_kv_phys_arbiter.sv",
    "rtl/test/tb_hdc_qwen_kv_phys_arbiter.sv",
    "rtl/hdc/kv/ot_hdc_kv_walk.sv",
    "rtl/hdc/kv/ot_hdc_kv_stream.sv",
    "rtl/hdc/kv/ot_hdc_qwen_kv_tail_read_mux.sv",
    "rtl/hdc/kv/ot_hdc_qwen_kv_tail_bank_port.sv",
    "rtl/hdc/kv/ot_hdc_qwen_kv_tail_group_port.sv",
    "rtl/hdc/kv/ot_hdc_qwen_kv_system.sv",
    "rtl/test/tb_hdc_qwen_kv_system_tail.sv",
    Path(__file__).relative_to(ROOT),
)]


def run(sources: list[Path], top: str, out: Path, sw: int | None = None,
        v_mode: bool = False, split_mode: bool = False, hbm_split_mode: bool = False) -> dict:
    cmd = ["iverilog", "-g2012", "-s", top]
    if sw is not None:
        cmd += [f"-P{top}.SW={sw}"]
    if v_mode:
        cmd += [f"-P{top}.V_MODE=1"]
    if split_mode:
        cmd += [f"-P{top}.SPLIT_MODE=1"]
    if hbm_split_mode:
        cmd += [f"-P{top}.HBM_SPLIT_MODE=1"]
    cmd += ["-o", str(out), *(str(p) for p in sources)]
    build = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if build.returncode:
        return {"status": "fail", "phase": "build", "returncode": build.returncode,
                "stderr": build.stderr[-2000:]}
    sim = subprocess.run(["vvp", str(out)], cwd=ROOT, capture_output=True, text=True)
    return {"status": "pass" if sim.returncode == 0 and "PASS " in sim.stdout else "fail",
            "phase": "simulation", "returncode": sim.returncode, "stdout": sim.stdout.strip(),
            "stderr": sim.stderr[-2000:]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=ROOT / "results/rtl/qwen_kv_system_bridge_boundaries.json")
    args = ap.parse_args()
    q, w, v, s, b_v, b_s, arb, b_arb, walk, stream, mux, tail, group, system, b_system = INPUTS[:15]
    with tempfile.TemporaryDirectory(prefix="qwen_kv_bridge_") as td:
        td = Path(td)
        runs = {f"vector_sw{sw}": run([q, w, v, b_v], "tb_hdc_qwen_kv_vector_bridge",
                                        td / f"v{sw}", sw) for sw in (8, 16)}
        runs["physical_sector"] = run([s, b_s], "tb_hdc_qwen_hbm_sector_bridge", td / "sector")
        runs["physical_arbiter"] = run([arb, b_arb], "tb_hdc_qwen_kv_phys_arbiter", td / "arbiter")
        for sw in (8, 16):
            runs[f"system_tail_sw{sw}"] = run(
                [walk, stream, mux, tail, group, q, w, v, s, arb, system, b_system],
                "tb_hdc_qwen_kv_system_tail", td / f"system_tail{sw}", sw)
            runs[f"system_v_sector_sw{sw}"] = run(
                [walk, stream, mux, tail, group, q, w, v, s, arb, system, b_system],
                "tb_hdc_qwen_kv_system_tail", td / f"system_v{sw}", sw, v_mode=True)
            runs[f"system_split_tail_sw{sw}"] = run(
                [walk, stream, mux, tail, group, q, w, v, s, arb, system, b_system],
                "tb_hdc_qwen_kv_system_tail", td / f"system_split{sw}", sw, split_mode=True)
            runs[f"system_split_hbm_sw{sw}"] = run(
                [walk, stream, mux, tail, group, q, w, v, s, arb, system, b_system],
                "tb_hdc_qwen_kv_system_tail", td / f"system_split_hbm{sw}", sw,
                split_mode=True, hbm_split_mode=True)
            runs[f"system_split_v_sw{sw}"] = run(
                [walk, stream, mux, tail, group, q, w, v, s, arb, system, b_system],
                "tb_hdc_qwen_kv_system_tail", td / f"system_split_v{sw}", sw,
                v_mode=True, split_mode=True)
    rec = {"schema": "opentallas.qwen-kv-system-bridge-boundaries.v1",
           "status": "pass" if all(x["status"] == "pass" for x in runs.values()) else "fail",
           "scope": "A full 1,024-element vector V instruction buffers under held-off HBM writes; "
                    "SW8/SW16 banked K output and logical 16-byte to physical 32-byte HBM "
                    "read/partial-write RMW and shared-port response routing are verified. "
                    "Actual streamer K-tail reads through vector FP8 banks and dependent V-sector reads "
                    "through the physical HBM port are verified at SW8/SW16 after vector writes. "
                    "A full vector token through this system remains open.",
           "runs": runs,
           "input_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in INPUTS}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rec, indent=2) + "\n")
    print(f"{args.output}: {rec['status']}")
    return 0 if rec["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
