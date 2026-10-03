#!/usr/bin/env python3
"""Phase-merge A/B on the flat W17-runtime V4.1 ROM-field RTL (rtl/w17_runtime/v41die/ot_v41_fieldtop: spine + vector
memory + ot_v41_field with W10 element pairs; the reference model of tools/w17_runtime_v41_field_rt_gate.py), on real DeepSeek-V4.1-Flash layer-0 slices.

The full-shape program issues two same-x weight-op pairs as two field phases each:
  * routed/shared expert gate/up: w1 then w3 (tools/hdc_replay_v41.py project_gate_up; L20 PCs 84/85, 97/98 ...);
  * attention: wq_a then wkv (L20 PCs 7/8);
while the model (decode_critical_path a_proj / shared_gu / experts_gu; v41_rom_ksplit_bankmap phases a_proj, gu)
prices each pair as ONE phase.  This bench runs every matrix as its own phase and each pair as one phase, checks
every written row against golden linear_q (R-ARITH chunk8) bit for bit, and reports each op's RTL cycles.

    python3 phase_merge_flat.py --snapshot MINI --workdir DIR --result OUT.json [--np 16 --regions 4 --nbf 8]
               [--bst 2] [--reuse]

The phase placement, images and golden are the runtime gate's own (tools/w17_runtime_v41_field_rt_gate.py,
tools/w17_runtime_v41_die_images.py); the per-element runtime composition is not built (the flat RTL is the
reference it is gated against).
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden_v41 as G  # noqa: E402
import w17_runtime_v41_die_images as I  # noqa: E402
import w17_runtime_v41_field_rt_gate as Gt  # noqa: E402
from rtl_v41_rom_array import Ckpt, Mat  # noqa: E402

L = "layers.0."
NONE = (False, False)


def phases(ck):
    w1 = lambda: Mat(ck, L + "ffn.experts.110.w1", "fp4", 12, 5120, r0=0)
    w3 = lambda: Mat(ck, L + "ffn.experts.110.w3", "fp4", 12, 5120, r0=500)
    qa = lambda: Mat(ck, L + "attn.wq_a", "fp8", 8, 5120, r0=320)
    kv = lambda: Mat(ck, L + "attn.wkv", "fp8", 8, 5120, r0=128)
    return [
        ("split_expert110_w1", [w1()]), ("split_expert110_w3", [w3()]), ("merged_expert110_w1_w3", [w1(), w3()]),
        ("split_wq_a", [qa()]), ("split_wkv", [kv()]), ("merged_wq_a_wkv", [qa(), kv()]),
    ]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", type=Path, required=True)
    ap.add_argument("--workdir", type=Path, required=True)
    ap.add_argument("--result", type=Path, required=True)
    ap.add_argument("--np", type=int, default=16)
    ap.add_argument("--regions", type=int, default=4)
    ap.add_argument("--nbf", type=int, default=8)
    ap.add_argument("--bst", type=int, default=2)
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--reuse", action="store_true")
    a = ap.parse_args()
    G.set_arith("chunk8")
    out = a.workdir.resolve()
    img = out / "img"
    out.mkdir(parents=True, exist_ok=True)
    srcs = sorted(set(Gt.SOURCES + [Path(__file__).resolve(), HERE / "flat_bench.cpp"]) -
                  {ROOT / "rtl/w17_runtime/test/v41_runtime/v41_field_rt_gate.cpp"})
    pins0 = {str(p.relative_to(ROOT)): sha(p) for p in srcs}
    ck = Ckpt(a.snapshot)
    rng = np.random.default_rng(Gt.SEED)
    fld = I.Field(a.np, a.regions, a.nbf)
    vm = np.zeros(1 << Gt.VAW, dtype=np.uint32)
    ops, expect, cases = [], {}, []
    xptr, optr = 0, 32768
    xcache = {}
    for name, mats in phases(ck):
        ph = I.add_phase(fld, mats, NONE, 0)
        K = ph["K"]
        # one x per family of pairs (the split ops and the merged op read the SAME x, as in the program)
        fam = name.split("_", 1)[1].replace("w1_w3", "").replace("w1", "").replace("w3", "")
        fam = "expert" if "expert" in name else "attn"
        if fam not in xcache:
            x = G.to_bf16((rng.standard_normal(K) * 0.5).astype(G.F))
            vm[xptr: xptr + K] = G.bits(np.asarray(x, dtype=G.F))
            xcache[fam] = (xptr, x)
            xptr += K
        xb, x = xcache[fam]
        gold = I.golden_phase(mats, np.asarray(x, dtype=G.F))
        for tag, (f32, b16) in gold.items():
            expect[optr + tag] = b16 << 16
        ops.append((ph["index"], 0, xb, K, optr, ph["nrows"]))
        cases.append(dict(name=name, phase=ph["index"], rows=ph["nrows"], K=K, stream_beats=ph["nbeat"],
                          t_phase_model=ph["t_phase_model"], t_read=ph["t_read"],
                          segments_per_pair_max=ph["segments_per_pair_max"], matrices=ph["matrices"],
                          obase=optr))
        optr += ph["nrows"]
    I.write_field(fld, img, Gt.PHW)
    (img / "vm.hex").write_text("".join(f"{int(v):08x}\n" for v in vm))
    (out / "ops.txt").write_text("".join(" ".join(map(str, o)) + "\n" for o in ops))
    steps = []
    mdir = out / "flat"
    vroot = re.search(r"VERILATOR_ROOT\s*=\s*(\S+)", subprocess.check_output([Gt.VERILATOR, "-V"], text=True)).group(1)

    def run(name, cmd):
        t0 = time.monotonic()
        p = subprocess.run(list(map(str, cmd)), cwd=out, capture_output=True, text=True)
        (out / f"{name}.log").write_text(p.stdout + p.stderr)
        steps.append(dict(name=name, seconds=round(time.monotonic() - t0, 2), returncode=p.returncode))
        if p.returncode:
            raise SystemExit(f"{name} failed:\n{(p.stdout + p.stderr)[-3000:]}")

    if not (a.reuse and (mdir / "Vflat__ALL.a").exists()):
        run("verilate_flat", [Gt.VERILATOR, "--cc", "-O3", "-Wno-fatal", "-Wno-lint", "-Wno-style", "-Wno-TIMESCALEMOD",
                              "--top-module", "ot_v41_fieldtop", "--prefix", "Vflat", "--Mdir", mdir,
                              f"-GNP={a.np}", f"-GR={a.regions}", f"-GNBF={a.nbf}", f"-GPHW={Gt.PHW}",
                              f"-GVAW={Gt.VAW}", f"-GBST={a.bst}", *map(str, Gt.DIE + [Gt.VIA_ROM]),
                              *map(str, Gt.COMMON + Gt.W10)])
        run("build_flat", ["make", "-C", mdir, "-f", "Vflat.mk", f"-j{a.jobs}", "Vflat__ALL.a", "OPT_FAST=-O2",
                           "OPT_SLOW=-O1"])
    binp = out / "flat_bench"
    run("link", ["g++", "-std=c++20", "-O2", "-pthread", f"-DNR={a.regions}", f"-DVAW={Gt.VAW}",
                 f"-I{vroot}/include", f"-I{vroot}/include/vltstd", f"-I{mdir}", HERE / "flat_bench.cpp",
                 *sorted(mdir.rglob("*.a")), f"{vroot}/include/verilated.cpp", f"{vroot}/include/verilated_threads.cpp",
                 f"{vroot}/include/verilated_dpi.cpp", "-o", binp])
    t0 = time.monotonic()
    p = subprocess.run([str(binp), str(img), str(out / "ops.txt")], cwd=out, capture_output=True, text=True)
    sim_s = time.monotonic() - t0
    (out / "simulate.log").write_text(p.stdout + p.stderr)
    lines = p.stdout.splitlines()
    writes = {}
    for ln in lines:
        t = ln.split()
        if t and t[0] == "W":
            writes[int(t[1])] = int(t[2], 16)
    opl = [ln for ln in lines if ln.startswith("OP ")]
    for c, ln in zip(cases, opl):
        g = dict(re.findall(r"(\w+)=(\d+)", ln))
        c.update(phase_cycles_rtl=int(g["cycles"]), wall_cycles_rtl=int(g["wall"]), wait_ready=int(g["wait_ready"]))
        rows = range(c["obase"], c["obase"] + c["rows"])
        c["golden_mismatch"] = sum(writes.get(r) != expect[r] for r in rows)
    wrong = sorted(ad for ad, v in expect.items() if writes.get(ad) != v)
    extra = sorted(set(writes) - set(expect))
    by = {c["name"]: c for c in cases}

    def ab(s1, s2, m):
        split = by[s1]["wall_cycles_rtl"] + by[s2]["wall_cycles_rtl"]
        merged = by[m]["wall_cycles_rtl"]
        return dict(split=[s1, s2], merged=m, split_wall_cycles=split, merged_wall_cycles=merged,
                    saved_cycles=split - merged, rows_bit_identical_split_vs_merged=all(
                        writes.get(by[s1 if t < by[s1]["rows"] else s2]["obase"] + (t if t < by[s1]["rows"] else t - by[s1]["rows"]))
                        == writes.get(by[m]["obase"] + t) for t in range(by[m]["rows"])))
    pins1 = {str(q.relative_to(ROOT)): sha(q) for q in srcs}
    passed = p.returncode == 0 and lines and lines[-1].startswith("PASS") and not wrong and not extra
    rec = dict(
        schema="opentallas.uarch.free_levers.phase_merge_flat.v1",
        status="pass" if passed and pins0 == pins1 else "fail",
        claim_boundary=("Flat-RTL (ot_v41_fieldtop) per-op cycles of split versus merged same-x weight phases at a "
                        "small field (NP pairs, BST broadcast stages), golden linear_q rows bit for bit on real "
                        "layer-0 checkpoint slices.  Not a full-shape layer, token, runtime-composition or physical "
                        "result; default-off proposal, nothing adopted."),
        params=dict(np=a.np, regions=a.regions, nbf=a.nbf, phw=Gt.PHW, vaw=Gt.VAW, bst=a.bst, vrd=64),
        verdict=lines[-1] if lines else p.stderr[-400:], golden_rows=len(expect), golden_mismatch=len(wrong),
        unexpected_writes=len(extra), cases=cases,
        ab=dict(expert_gate_up=ab("split_expert110_w1", "split_expert110_w3", "merged_expert110_w1_w3"),
                attn_a_proj=ab("split_wq_a", "split_wkv", "merged_wq_a_wkv")),
        simulate_seconds=round(sim_s, 2), steps=steps, checkpoint_header_sha256=ck.pins, seed=Gt.SEED,
        simulator=subprocess.check_output([Gt.VERILATOR, "--version"], text=True).strip(),
        source_sha256=pins0, source_stable=pins0 == pins1)
    a.result.parent.mkdir(parents=True, exist_ok=True)
    a.result.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({k: rec[k] for k in ("status", "verdict", "golden_rows", "golden_mismatch", "ab")}, indent=1))
    for c in cases:
        print(c["name"], c["rows"], c["stream_beats"], c.get("phase_cycles_rtl"), c.get("wall_cycles_rtl"),
              c["golden_mismatch"])
    return 0 if rec["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
