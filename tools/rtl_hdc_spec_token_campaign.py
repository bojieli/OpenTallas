#!/usr/bin/env python3
"""Whole-token RTL simulation of the vector core at the spec configuration, scaled.

The spec machine (docs/ARCH_SPEC_QWEN3.md) is 8,192 lane groups (131,072 lanes)
with a 1,024-lane stream unit on Qwen3-8B (hidden 4,096). A shipped-shape
token cannot be simulated in RTL: the weights alone are 8 GB. This campaign
simulates the reduced vehicle (hidden 128) on the core scaled to the SAME
RATIOS as the spec:
  * 32 lanes per hidden element: 4,096 lanes, 256 groups;
  * 1/128 of the lanes in the stream unit: SW = 32;
  * FP8 KV, K-split attention, the norm fold and the fused SiLU;
  * the longest provisioned context (64 positions).
In that regime every weight op is one round, which is what the spec prices.
The run also covers an intermediate point (64 groups, SW 8).

Each point builds tb_hdc_core with those parameters and runs one whole token
(4 layers and the LM head) at the last position. It records:
  * the token and its bit-exactness (logits, vector memory, KV cache) against
    the ISA machine and the golden;
  * the RTL cycles against the calibrated sequencer model (tools/hdc_timing.py)
    replaying the same program at the same parameters.
The model is what prices the shipped token, so its error at the spec's
ratios is the evidence behind the spec's HEAD figure.

    python3 tools/rtl_hdc_spec_token_campaign.py [--output PATH] [--points 64:8 256:32]
    python3 tools/rtl_hdc_spec_token_campaign.py --merge A.json B.json [--output PATH]

Verilating the core is memory-bound: 37.5 GB peak at 64 groups, so each point is
best run as its own job (--points one, --output a part) and the parts merged.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/rtl/hdc_spec_token_campaign.json"
HDC = [ROOT / f"rtl/hdc/{n}.sv" for n in (
    "ot_hdc_delay", "ot_hdc_fp32_mul_pipe", "ot_hdc_fpu", "ot_hdc_fastfp", "ot_hdc_sfu", "ot_hdc_sfu_q", "ot_hdc_reduce", "ot_hdc_reduce_q",
    "ot_hdc_matvec", "ot_hdc_stream", "ot_hdc_vstream_lane", "ot_hdc_vreduce", "ot_hdc_vstream", "ot_hdc_core")]
PIPES = [ROOT / "rtl/proto/ot_fp32_add_rne_pipe.sv", ROOT / "rtl/proto/ot_fp32_mul_rne_pipe.sv"]
ISA_SVH = ROOT / "rtl/hdc/ot_hdc_isa.svh"
TB = ROOT / "rtl/test/tb_hdc_core.sv"
HARNESS = ROOT / "rtl/test/hdc_core_harness.cpp"
TOOLS = [ROOT / f"tools/{n}.py" for n in ("hdc_golden", "hdc_isa", "hdc_program", "hdc_timing")] + [Path(__file__)]
CONTEXT = 64
BRIDGE_RTL = [ROOT / p for p in (
    "rtl/hdc/ingest/ot_hdc_ingest_fp8q.sv",
    "rtl/hdc/kv/ot_hdc_qwen_kv_write_adapter.sv",
    "rtl/hdc/kv/ot_hdc_qwen_kv_vector_bridge.sv")]
SPEC = dict(groups=8192, lanes=131072, su_width=1024, hidden=4096)
SINGLE = re.compile(r"HDC token=(\d+) pos=(\d+) next_token=(\d+) expect=(\d+) cycles=(\d+) fault=(\d+) "
                    r"logit_mismatch=(\d+) vm_mismatch=(\d+) kv_mismatch=(\d+)")
MODEL = """
import json, sys
sys.path.insert(0, "tools")
import hdc_program as P, hdc_timing as T
model, prompt, expected, cache = P.golden_state({ctx})
lay = P.Layout(model)
prog = P.build_program(lay)
_, cyc = T.simulate(prog, len(prompt) - 1, groups={g}, su_width={sw})
print(json.dumps(dict(model_cycles=cyc, instructions=len(prog))))
"""


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def point(s: Path, groups: int, sw: int, build_log: Path, kv_bridge: bool = False) -> dict:
    env = dict(os.environ, HDC_GROUPS=str(groups), HDC_SU_WIDTH=str(sw))
    img, obj = s / f"img{groups}", s / f"obj{groups}"
    generate = subprocess.run([sys.executable, str(ROOT / "tools/hdc_program.py"), "--out", str(img),
                               "--context", str(CONTEXT)], capture_output=True, text=True, env=env,
                              cwd=ROOT)
    if generate.returncode:
        build_log.parent.mkdir(parents=True, exist_ok=True)
        build_log.write_text(f"source_sha256={sha(Path(__file__))}\n"
                             f"image_generation_returncode={generate.returncode}\n"
                             f"stdout:\n{generate.stdout}\nstderr:\n{generate.stderr}\n")
        raise RuntimeError(f"Program generation failed for {groups}:{sw}; full output: {build_log}")
    gen = generate.stdout
    isa_exact = "bit-exact with golden: True" in gen
    cmd = ["verilator", "--cc", "--exe", "--build", "-O2", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED",
           "-Wno-BLKSEQ", "-Wno-VARHIDDEN", "--unroll-count", "65536",   # the testbench's per-group loops
           "--top-module", "tb_hdc_core", f"-GG={groups}", "-GSU_VEC=1",
           f"-GSW={sw}", "-Mdir", str(obj), f"-I{ISA_SVH.parent}", *map(str, HDC), *map(str, PIPES),
           *map(str, BRIDGE_RTL), str(TB), str(HARNESS), "-CFLAGS", "-O1"]
    if kv_bridge:
        cmd.insert(cmd.index("-Mdir"), "-GKV_BRIDGE=1")
    build = subprocess.run(cmd, capture_output=True, text=True, env=dict(os.environ, MAKEFLAGS="-j8"))
    if build.returncode:
        build_log.parent.mkdir(parents=True, exist_ok=True)
        build_log.write_text(f"source_sha256={sha(Path(__file__))}\n"
                             f"input_sha256={json.dumps({str(p.relative_to(ROOT)): sha(p) for p in HDC + PIPES + BRIDGE_RTL + [TB, HARNESS, ISA_SVH]})}\n"
                             f"returncode={build.returncode}\ncommand={' '.join(cmd)}\n"
                             f"stdout:\n{build.stdout}\nstderr:\n{build.stderr}\n")
        raise RuntimeError(f"Verilator build failed for {groups}:{sw}; full output: {build_log}")
    out = subprocess.run([str(obj / "Vtb_hdc_core"), f"+DIR={img}", *(img / "run.args").read_text().split()],
                         check=True, capture_output=True, text=True).stdout
    m = SINGLE.search(out)
    tok, pos, nxt, isa_tok, cyc, fault, bad_lg, bad_vm, bad_kv = map(int, m.groups())
    mod = json.loads(subprocess.run([sys.executable, "-c", MODEL.format(ctx=CONTEXT, g=groups, sw=sw)],
                                    check=True, capture_output=True, text=True, env=env, cwd=ROOT).stdout)
    bridge = re.search(r"KV_BRIDGE written_byte_mismatches=(\d+) fault=(\d+) drained=(\d+)", out)
    return {"groups": groups, "lanes": 16 * groups, "su_width": sw, "position": pos, "token": tok,
            "next_token": nxt, "isa_next_token": isa_tok, "isa_logits_bit_exact_with_golden": isa_exact,
            "rtl_cycles": cyc, "model_cycles": mod["model_cycles"], "instructions": mod["instructions"],
            "model_error_pct": round(100.0 * (mod["model_cycles"] - cyc) / cyc, 3),
            "fault": fault, "logit_mismatches": bad_lg, "vector_memory_mismatches": bad_vm,
            "kv_cache_mismatches": bad_kv,
            "kv_bridge": ({"written_byte_mismatches": int(bridge[1]), "fault": int(bridge[2]),
                           "drained": bool(int(bridge[3]))} if bridge else None),
            "pass": "PASS" in out and nxt == isa_tok and fault == 0 and bad_lg + bad_vm + bad_kv == 0
            and isa_exact and (not kv_bridge or (bridge is not None and bridge[1] == "0" and
                                                  bridge[2] == "0" and bridge[3] == "1"))}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--output", type=Path, default=OUT)
    ap.add_argument("--points", nargs="+", default=["64:8", "256:32"], help="groups:su_width")
    ap.add_argument("--merge", nargs="+", type=Path, help="combine the points of part records (same inputs)")
    ap.add_argument("--kv-bridge", action="store_true", help="exercise packed KV write boundary from vector core")
    a = ap.parse_args()
    pts = []
    if a.merge:
        parts = [json.loads(p.read_text()) for p in a.merge]
        assert all(p["input_sha256"] == parts[0]["input_sha256"] for p in parts), "parts from different sources"
        pts = sorted((pt for p in parts for pt in p["points"]), key=lambda pt: pt["groups"])
    else:
        with tempfile.TemporaryDirectory() as scratch:
            for p in a.points:
                g, sw = map(int, p.split(":"))
                pts.append(point(Path(scratch), g, sw,
                                 a.output.with_name(f"{a.output.stem}.g{g}.build_error.log"), a.kv_bridge))
                print(json.dumps(pts[-1]), flush=True)
    spec_ratio = dict(lanes_per_hidden=SPEC["lanes"] // SPEC["hidden"], lanes_per_su_lane=SPEC["lanes"] // SPEC["su_width"])
    rec = {
        "schema": "opentallas.hdc-spec-token-campaign.v1",
        "status": "pass" if all(p["pass"] for p in pts) and
                  (a.kv_bridge or all(abs(p["model_error_pct"]) <= 2.0 for p in pts))
        else "fail",
        "claim_boundary": ("whole-token vector core with the elastic packed-KV write bridge, using direct KV reads "
                          "for compute and checking every emitted K-tail/V-sector byte; timing model is not calibrated "
                          "for bridge drain stalls" if a.kv_bridge else
                          "whole-token RTL simulation (Verilator) of the reduced vehicle on the vector core scaled "
                          "to the spec's lane ratios, behavioural memories, KV on core; the shipped token's cycles "
                          "are the calibrated model's, whose error at these ratios is recorded here"),
        "vehicle": "qwen3-reduced-v1 (hidden 128, 4 layers, 8/2 heads, head_dim 16, ffn 384, vocab 4096)",
        "kv_format": "fp8_e4m3", "context": CONTEXT, "spec": SPEC, "spec_ratios": spec_ratio,
        "points": pts, "kv_bridge": a.kv_bridge,
        "input_sha256": {str(p.relative_to(ROOT)): sha(p) for p in
                         (ISA_SVH, *HDC, *PIPES, *BRIDGE_RTL, TB, HARNESS, *TOOLS)},
    }
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(rec, indent=1) + "\n")
    print(rec["status"])
    return 0 if rec["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
