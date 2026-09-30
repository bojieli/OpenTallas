#!/usr/bin/env python3
"""W17 runtime-composition equivalence gate of the adopted V4.1 ROM field (spine + W10 element pairs + multi-root
return), against the flat RTL, on real DeepSeek-V4.1-Flash layer-0 weight slices.

    python3 tools/v41_field_rt_gate.py --snapshot <HF snapshot dba1be0a...> --workdir DIR \
        [--np 16 --regions 4 --nbf 4] [--result results/rtl/w17_field_rt_gate.json]

Flat reference: rtl/v41die/ot_v41_fieldtop.sv (spine, vector memory, ot_v41_field) in one Verilator model.
Composition:    the same top with RT_CUT (field removed) + ot_v41_pair (two builds: FP8/FP4-only and BF16-capable,
                V41_RT: ROM and configuration words served by the host) instantiated per pair + ot_v41_retn per
                return node + ot_v41_ret_root per region, wired by rtl/test/v41_runtime/v41_field_rt_gate.cpp.
Checks: (1) every public port of the top equal on every cycle; (2) every vector-memory write equals golden
linear_q / csum(mul(w, bf16(x))) under R-ARITH chunk8 (tools/hdc_golden_v41.py) bit for bit, FP32 or BF16 by the
phase's row format, every row of every position; (3) the wrong-edge negative control (consumers see same-edge
values) fails.  Simulation only: no hardware is added by the composition.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden_v41 as G  # noqa: E402
import v41_die_images as I  # noqa: E402
from rtl_v41_rom_array import Ckpt, Mat  # noqa: E402

VERILATOR = os.path.expanduser("~/.local/opentallas-tools/verilator-5.050/bin/verilator")
RT = ROOT / "rtl/test/v41_runtime"
W10 = [ROOT / f"rtl/v41rom/{n}.sv" for n in ("ot_v41_ret", "ot_v41_rom_elem", "ot_v41_bterm", "ot_v41_chain",
                                              "ot_v41_segtree", "ot_v41_bf16_lanes")]
COMMON = [ROOT / f"rtl/hdc/{n}.sv" for n in ("ot_hdc_fpu", "ot_hdc_fp32_mul_pipe", "ot_hdc_delay", "ot_hdc_cg")] + \
         [ROOT / "rtl/proto/ot_fp32_add_rne_pipe.sv", ROOT / "rtl/hdc/v41/ot_hdc_actquant.sv"]
VIA_ROM = ROOT / "physical/asap7_memory_macros/ot_rom_8192x274_m8/ot_rom_8192x274_m8.v"
RT_ROM = RT / "ot_rom_8192x274_m8_rt.sv"
DIE = [ROOT / f"rtl/v41die/{n}.sv" for n in ("ot_v41_pair", "ot_v41_retn", "ot_v41_field", "ot_v41_spine", "ot_v41_fieldtop")]
HOST = [RT / "v41_field_rt_gate.cpp", ROOT / "rtl/test/qwen_runtime/qwen_rt_matvec.hpp"]
SOURCES = sorted(set(W10 + COMMON + [VIA_ROM, RT_ROM] + DIE + HOST +
                     [Path(__file__), ROOT / "tools/v41_die_images.py", ROOT / "tools/rtl_v41_rom_array.py",
                      ROOT / "tools/v41_rom_ksplit_bankmap.py", ROOT / "tools/hdc_golden_v41.py",
                      ROOT / "tools/hdc_golden.py"]))
SEED = 20260930
PHW = 4
VAW = 16


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def phases(ck: Ckpt):
    """(name, matrices, (fmt rows < rsplit FP32?, fmt rows >= rsplit FP32?), rsplit, positions)."""
    L = "layers.0."
    return [
        ("fp8_wq_a", [Mat(ck, L + "attn.wq_a", "fp8", 16, 5120, r0=320)], (False, False), 0, 1),
        ("fp8_wq_b", [Mat(ck, L + "attn.wq_b", "fp8", 32, 1280, r0=4096)], (False, False), 0, 1),
        ("fp8_wo_b_kquarter_fp32", [Mat(ck, L + "attn.wo_b", "fp8", 12, 2048, r0=100, k0=2048)], (True, True), 0, 1),
        ("fp4_expert110_w1_w3", [Mat(ck, L + "ffn.experts.110.w1", "fp4", 12, 5120, r0=0),
                                 Mat(ck, L + "ffn.experts.110.w3", "fp4", 12, 5120, r0=500)], (False, False), 0, 1),
        ("mixed_down_fp4_e141_w2_fp8_shared_w2", [Mat(ck, L + "ffn.experts.141.w2", "fp4", 16, 2304, r0=1280),
                                                  Mat(ck, L + "ffn.shared_experts.w2", "fp8", 16, 2304, r0=1280)],
         (False, False), 0, 1),
        ("bf16_router_gate_fp32_bf16", [Mat(ck, L + "ffn.gate", "bf16", 8, 5120, r0=96)], (True, False), 4, 1),
        ("bf16_l2_compressor_wkv_fp32", [Mat(ck, "layers.2.attn.compressor.wkv", "bf16", 4, 5120, r0=384)], (True, True), 0, 1),
        ("fp8_wq_b_mtp2", [Mat(ck, L + "attn.wq_b", "fp8", 16, 1280, r0=9000)], (False, False), 0, 2),
    ]


def build(a, out: Path):
    steps = []

    def run(name, cmd, cwd=out):
        t0 = time.monotonic()
        p = subprocess.run(["/usr/bin/time", "-f", "%M", "-o", str(out / f"{name}.rss"), *map(str, cmd)],
                           cwd=cwd, capture_output=True, text=True)
        (out / f"{name}.log").write_text(p.stdout + p.stderr)
        rss = (out / f"{name}.rss").read_text().split() if (out / f"{name}.rss").exists() else []
        steps.append(dict(name=name, seconds=round(time.monotonic() - t0, 2), returncode=p.returncode,
                          max_rss_kib=int(rss[-1]) if rss and rss[-1].isdigit() else None))
        if p.returncode:
            raise SystemExit(f"{name} failed; see {out / (name + '.log')}\n{(p.stdout + p.stderr)[-3000:]}")
        return p.stdout

    vroot = re.search(r"VERILATOR_ROOT\s*=\s*(\S+)", subprocess.check_output([VERILATOR, "-V"], text=True)).group(1)
    common = [str(p) for p in COMMON + W10]
    top_p = [f"-GNP={a.np}", f"-GR={a.regions}", f"-GNBF={a.nbf}", f"-GPHW={PHW}", f"-GVAW={VAW}"]
    models = [
        ("flat", "ot_v41_fieldtop", DIE + [VIA_ROM], top_p, []),
        ("cut", "ot_v41_fieldtop", [ROOT / "rtl/v41die/ot_v41_spine.sv", ROOT / "rtl/v41die/ot_v41_fieldtop.sv"],
         top_p, ["-DRT_CUT"]),
        ("pq", "ot_v41_pair", [ROOT / "rtl/v41die/ot_v41_pair.sv", RT_ROM], [f"-GPHW={PHW}", "-GBF16=0", "-GXF=4"],
         ["-DV41_RT"]),
        ("pb", "ot_v41_pair", [ROOT / "rtl/v41die/ot_v41_pair.sv", RT_ROM], [f"-GPHW={PHW}", "-GBF16=1", "-GXF=8"],
         ["-DV41_RT"]),
        ("retn", "ot_v41_retn", [ROOT / "rtl/v41die/ot_v41_retn.sv"], ["-GRD=64", "-GRST=1", "-GBYPASS=1"], []),
        ("root", "ot_v41_ret_root", [], ["-GD=128", "-GQD=128"], []),
    ]
    for prefix, top, files, params, extra in models:
        mdir = out / prefix
        if a.reuse and (mdir / f"V{prefix}__ALL.a").exists():
            continue
        run(f"verilate_{prefix}", [VERILATOR, "--cc", "-O3", "-Wno-fatal", "-Wno-lint", "-Wno-style",
                                   "-Wno-TIMESCALEMOD", "--top-module", top, "--prefix", f"V{prefix}", "--Mdir", mdir,
                                   *params, *extra, *map(str, files), *common])
        run(f"build_{prefix}", ["make", "-C", mdir, "-f", f"V{prefix}.mk", f"-j{a.jobs}", f"V{prefix}__ALL.a",
                                "OPT_FAST=-O2", "OPT_SLOW=-O1"])
    archives, includes = [], {f"-I{vroot}/include", f"-I{vroot}/include/vltstd", f"-I{RT}",
                              f"-I{ROOT / 'rtl/test/qwen_runtime'}"}
    for prefix, *_ in models:
        archives += sorted((out / prefix).rglob("*.a"))
        includes.add(f"-I{out / prefix}")
    runtime = [f"{vroot}/include/verilated.cpp", f"{vroot}/include/verilated_threads.cpp",
               f"{vroot}/include/verilated_dpi.cpp"]
    gate = out / "gate"
    run("link", ["g++", "-std=c++20", "-O2", "-pthread", f"-DNP={a.np}", f"-DNR={a.regions}", f"-DNBF={a.nbf}",
                 f"-DPHW={PHW}", f"-DVAW={VAW}", *sorted(includes), RT / "v41_field_rt_gate.cpp",
                 "-Wl,--start-group", *archives, "-Wl,--end-group", *runtime, "-o", gate])
    return gate, steps


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--snapshot", type=Path, required=True)
    ap.add_argument("--workdir", type=Path, required=True)
    ap.add_argument("--np", type=int, default=16)
    ap.add_argument("--regions", type=int, default=4)
    ap.add_argument("--nbf", type=int, default=8)
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--reuse", action="store_true")
    ap.add_argument("--result", type=Path)
    a = ap.parse_args()
    G.set_arith("chunk8")
    out = a.workdir.resolve()
    img = out / "img"
    out.mkdir(parents=True, exist_ok=True)
    pins0 = {str(p.relative_to(ROOT)): sha(p) for p in SOURCES}
    ck = Ckpt(a.snapshot)
    rng = np.random.default_rng(SEED)
    fld = I.Field(a.np, a.regions, a.nbf)
    vm = np.zeros(1 << VAW, dtype=np.uint32)
    ops, expect, cases = [], {}, []
    xptr, optr = 0, 32768
    for name, mats, fmts, rsplit, npos in phases(ck):
        ph = I.add_phase(fld, mats, fmts, rsplit)
        K, bf = ph["K"], ph["bf"]
        xps = K
        for p in range(npos):
            if bf:                                   # FP32 x: the element rounds it to BF16 (golden mv)
                x = (rng.standard_normal(K) * 0.37).astype(np.float32)
            else:                                    # BF16-valued x (golden linear_q consumers)
                x = G.to_bf16((rng.standard_normal(K) * 0.5).astype(G.F))
            vm[xptr + p * xps: xptr + p * xps + K] = G.bits(np.asarray(x, dtype=G.F))
            gold = I.golden_phase(mats, np.asarray(x, dtype=G.F))
            for tag, (f32, b16) in gold.items():
                fp32 = fmts[0] if tag < rsplit else fmts[1]
                expect[optr + tag + p * ph["nrows"]] = f32 if fp32 else (b16 << 16)
        ops.append((ph["index"], npos - 1, xptr, xps, optr, ph["nrows"]))
        cases.append(dict(name=name, phase=ph["index"], positions=npos, rows=ph["nrows"], K=K, bf16=bf,
                          stream_beats=ph["nbeat"], t_phase_model=ph["t_phase_model"], t_read=ph["t_read"],
                          segments_per_pair_max=ph["segments_per_pair_max"], matrices=ph["matrices"]))
        xptr += npos * xps
        optr += npos * ph["nrows"]
        assert xptr < 32768 and optr < (1 << VAW)
    I.write_field(fld, img, PHW)
    (img / "vm.hex").write_text("".join(f"{int(v):08x}\n" for v in vm))
    (out / "ops.txt").write_text("".join(" ".join(map(str, o)) + "\n" for o in ops))
    gate, steps = build(a, out)
    env = dict(os.environ, RT_THREADS=str(a.threads))
    t0 = time.monotonic()
    p = subprocess.run([str(gate), str(img), str(out / "ops.txt")], cwd=out, capture_output=True, text=True, env=env)
    sim_s = time.monotonic() - t0
    (out / "simulate.log").write_text(p.stdout + p.stderr)
    m = subprocess.run([str(gate), str(img), str(out / "ops.txt"), "--wrong-edge"], cwd=out, capture_output=True,
                       text=True, env=env)
    (out / "mutant.log").write_text(m.stdout + m.stderr)
    lines = p.stdout.splitlines()
    verdict = lines[-1] if lines else p.stderr[-400:]
    writes = {}
    for ln in lines:
        t = ln.split()
        if t and t[0] == "W":
            writes[int(t[1])] = int(t[2], 16)
    op_cycles = [int(re.search(r"cycles=(\d+)", ln).group(1)) for ln in lines if ln.startswith("OP ")]
    wrong = sorted(ad for ad, v in expect.items() if writes.get(ad) != v)
    extra = sorted(set(writes) - set(expect))
    for c, cy in zip(cases, op_cycles):
        c["cycles_rtl"] = cy
    passed = p.returncode == 0 and verdict.startswith("PASS")
    mutant_rejected = m.returncode != 0 and "FAIL case=" in m.stdout
    golden_ok = not wrong and not extra and len(expect) > 0
    pins1 = {str(q.relative_to(ROOT)): sha(q) for q in SOURCES}
    rec = dict(
        schema="opentallas.rtl.w17_field_rt_gate.v1",
        status="pass" if (passed and mutant_rejected and golden_ok and pins0 == pins1) else "fail",
        claim_boundary=("Simulation-only decomposition equivalence of the W17 ROM-field front end (spine, per-element "
                        "configuration ROM, multi-root return) with W10's element at a small field: every public port "
                        "of the runtime composition equals the flat RTL on every cycle, and every row equals the golden "
                        "bit for bit, on real layer-0 checkpoint slices. Not a full-shape layer, token or physical result."),
        params=dict(np=a.np, regions=a.regions, nbf=a.nbf, phw=PHW, vaw=VAW, bst=2, rst=1, vrd=64, nseg=8, nch=16,
                    mtp=1, early=1, bypass=1, xf_q=4, xf_bf=8, rd=64, root_d=128),
        verdict=verdict, negative_control=(m.stdout.strip().splitlines() or [""])[-1],
        negative_control_rejected=mutant_rejected, golden_rows=len(expect), golden_mismatch=len(wrong),
        golden_first_mismatch=[(ad, writes.get(ad), expect[ad]) for ad in wrong[:5]], unexpected_writes=len(extra),
        cases=cases, simulate_seconds=round(sim_s, 2), threads=a.threads, steps=steps,
        checkpoint_revision=a.snapshot.name, checkpoint_header_sha256=ck.pins, seed=SEED,
        simulator=subprocess.check_output([VERILATOR, "--version"], text=True).strip(),
        source_sha256=pins0, source_stable=pins0 == pins1, gate_binary_sha256=sha(gate))
    target = a.result or (out / "result.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({k: rec[k] for k in ("status", "verdict", "negative_control", "golden_rows", "golden_mismatch",
                                          "unexpected_writes", "simulate_seconds")}, indent=1))
    for c in cases:
        print(c["name"], c["rows"], c.get("cycles_rtl"), c["t_phase_model"])
    return 0 if rec["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
