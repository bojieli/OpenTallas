#!/usr/bin/env python3
"""Exact scheduled-PC boundary and real SRAM tests; mutants must fail."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    d = root / "rtl/hbm_accel/loader/service_native"
    mem = root / "physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v"
    core = d / "ot_hbm_svc_static_pc.sv"
    boundary = d / "ot_hbm_svc_static_pc_boundary.sv"
    tb = d / "tb_hbm_svc_static_pc_boundary.sv"
    cases = [
        ("positive", None, None, None, None),
        ("sram_read_address", "core", "{bank_q,slot_q}:{read_bank,read_slot}", "{bank_q,slot_q ^ 6'd1}:{read_bank,read_slot ^ 6'd1}", "payload read mismatch"),
        ("response_stage_bypass", "boundary", "out_v <= c_out_v;", "out_v <= u_core.scheduled_read;", "read exact latency"),
        ("write_ack_stage_bypass", "boundary", ".k_wr_done(ack_q)", ".k_wr_done(k_wr_done)", "write ACK status bypassed"),
        ("write_ack_without_accept", "boundary", "wire write_response_ok = write_outstanding || accept_write;", "wire write_response_ok = 1\'b1;", "fault not closed"),
        ("kr_tag_corruption", "boundary", ".kr_tag(kr_tag_q)", ".kr_tag(kr_tag_q ^ 17'd1)", "prefetch completion timing"),
    ]
    records = []
    for name, target, before, after, reason in cases:
        c, w = core, boundary
        if target:
            path = core if target == "core" else boundary
            text = path.read_text()
            assert text.count(before) == 1, (name, "mutation site not unique")
            mutated = out / (name + ".sv")
            mutated.write_text(text.replace(before, after))
            if target == "core": c = mutated
            else: w = mutated
        exe = out / (name + ".vvp")
        subprocess.run(["iverilog", "-g2012", "-s", "tb_hbm_svc_static_pc_boundary", "-o", str(exe), str(mem), str(c), str(w), str(tb)], check=True)
        run = subprocess.run(["vvp", str(exe)], text=True, capture_output=True, timeout=30)
        log = run.stdout + run.stderr
        (out / (name + ".log")).write_text(log)
        if target:
            assert run.returncode != 0 and reason in log, (name, run.returncode, log)
        else:
            assert run.returncode == 0 and "STATIC_PC_BOUNDARY PASS" in log, log
        records.append({"name": name, "result": "rejected" if target else "PASS", "returncode": run.returncode, "log": str(out / (name + ".log"))})
        print(name, records[-1]["result"], log.strip().splitlines()[0])
    sources = [mem, core, boundary, tb, Path(__file__).resolve()]
    receipt = {"qualification": "component only; no native physical or whole-token qualification", "read_added_cycles": 2, "kr_accept_to_published_status_added_cycles": 2, "write_ack_to_published_status_added_cycles": 2, "declared_boundary_register_bits": 1313, "constant_request_bits_before_mapping": 36, "cases": records, "sources": {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}}
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
