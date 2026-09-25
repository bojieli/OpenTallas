#!/usr/bin/env python3
"""RTL campaign of the ROM-array package as a 4-die tensor group.

The selected ROM-array topology (docs/ARCHITECTURE_ATLAS.html 6.6-6.8,
results/roofline/critical_path/decode_critical_path.json) makes every package
ONE tensor group of four dies on UCIe: every weight matrix is split over the
dies, and partial results are combined by ONE-SHOT fixed-order collectives
(every die sends its partial to the other three and sums all four in rank
order, so all four hold the same bits after one link crossing).  Packages are
chained in a ring as a layer pipeline.

This campaign runs, under Verilator:

1. the one-shot unit alone (rtl/test/tb_rom_oneshot_allreduce.sv around
   rtl/rom/ot_rom_oneshot_allreduce.sv): random binary32 partials (mixed
   exponents, cancellations, subnormals, zeros) all-reduced and all-gathered,
   every output word of every die against tools/hdc_golden.fold; random send
   gaps and per-die start skew; long 320-word streams (the V4.1 20 KB
   all-reduce) for the sustained rate at two FIFO depths; and fail-closed
   cases (a NaN, an infinity, and a sum past the finite range) in which every
   die must fault;
2. the reduced Qwen3 vehicle on 4-die packages (rtl/test/tb_hdc_package_tp.sv:
   4 ot_hdc_core + ot_rom_tp_seq, the one-shot unit and one ot_rom_pkg_ctrl
   per package): one package holding the whole model, and a ring of four
   packages (one layer each), with one and with four users, from an EMPTY KV
   cache through the oracle's prompt to 3 generated tokens.  Every step's
   {token, logit} on every die, the generated tokens, every die's KV cache
   (every user) and, for the single package, every die's vector memory are
   checked bit for bit against the ISA-level tensor group of
   tools/hdc_program.py --tp 4, itself bit-exact with
   tools/hdc_golden.Model.decode_token_tp at every step;
3. the one-core-per-package ring (tools/rtl_hdc_array_campaign.py, 4 packages)
   at the same sources, for the speed-up; the single-core reference is
   results/rtl/hdc_decode_campaign.json end_to_end.

Link model (ot_rom_ucie_link): configs/hardware/technology.json
links.rom_package_ucie, hop 10 ns (range 3-30 ns) and 4 TB/s per die pair and
direction, converted to cycles at the 0.9 ns physical target.  The package
ring keeps tb_hdc_array's 60-cycle board link.

Writes results/rtl/hdc_package_tp_campaign.json.
"""
import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden as G  # noqa: E402
import rtl_hdc_array_campaign as array  # noqa: E402
import rtl_hdc_decode_campaign as core  # noqa: E402

OUT = ROOT / "results/rtl/hdc_package_tp_campaign.json"
TECH = ROOT / "configs/hardware/technology.json"
ALLREDUCE = ROOT / "rtl/rom/ot_rom_oneshot_allreduce.sv"
SEQ = ROOT / "rtl/rom/ot_rom_tp_seq.sv"
TB_UNIT = ROOT / "rtl/test/tb_rom_oneshot_allreduce.sv"
TB = ROOT / "rtl/test/tb_hdc_package_tp.sv"
HARNESS = ROOT / "rtl/test/hdc_package_tp_harness.cpp"
ADDER = ROOT / "rtl/proto/ot_fp32_add_rne_pipe.sv"
CLOCK_NS = 0.9
TP = 4
STEPS_PER_USER = 16 + 3 - 1
LANES = 16

RES = re.compile(r"PKG_TP nodes=(\d+) dies=(\d+) users=(\d+) generated=(\d+) steps_checked=(\d+) mismatches=(\d+) "
                 r"kv_mismatches=(\d+) vm_mismatches=(\d+) total_cycles=(\d+)")
DIE = re.compile(r"DIE node=(\d+) die=(\d+) busy_cycles=(\d+) coll_cycles=(\d+) kv_mismatches=(\d+) "
                 r"vm_mismatches=(\d+)")
GEN = re.compile(r"GEN user=(\d+) pos=(\d+) token=(\d+) cycle=(\d+)")
STALLS = re.compile(r"LINK_STALLS (\d+) COLL_STALLS (\d+)")
UNIT = re.compile(r"ONESHOT n=(\d+) depth=(\d+) lat=(\d+) msgs=(\d+) words=(\d+) gap=(\d+) skew=(\d+) "
                  r"inject=(-?\d+) mismatches=(\d+) out_err=(\d+) fault=(\d+) code=(\d+) words_out=(\d+) "
                  r"first=(-?\d+) last=(\d+) link_stalls=(\d+)")


def sh(cmd, **kw) -> str:
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode:
        raise RuntimeError(f"{cmd[0]} failed ({r.returncode}):\n{r.stdout[-3000:]}\n{r.stderr[-3000:]}")
    return r.stdout


def link_params() -> dict:
    """UCIe hop and rate in cycles of the 0.9 ns physical target."""
    u = json.loads(TECH.read_text())["links"]["rom_package_ucie"]
    f = 1.0 / (CLOCK_NS * 1e-9)
    hop = u["hop_latency_s"]
    return {"source": "configs/hardware/technology.json links.rom_package_ucie", "clock_ns": CLOCK_NS,
            "hop_latency_s": hop["value"], "hop_range_s": [hop["range_low"], hop["range_high"]],
            "bytes_s": u["bytes_s"]["value"],
            "lat_cycles": math.ceil(hop["value"] * f),
            "lat_cycles_range": [math.ceil(hop["range_low"] * f), math.ceil(hop["range_high"] * f)],
            "bytes_per_cycle": int(u["bytes_s"]["value"] / f),
            "note": "the unit moves one 64-byte word (16 binary32 lanes, the vector-memory word) per cycle "
                    "per die, far below the link's bytes per cycle: the rate limit never binds here, and the "
                    "unit's LANES parameter, not the link, sets the collective bandwidth"}


# -- 1. the one-shot unit ------------------------------------------------------------------------
def rand_f32(rng, n):
    """Binary32 values with spread exponents, zeros, subnormals and signs."""
    e = rng.integers(90, 160, n)
    e[rng.random(n) < 0.03] = 0                    # subnormal
    m = rng.integers(0, 1 << 23, n)
    s = rng.integers(0, 2, n)
    b = (s << 31) | (e << 23) | m
    b[rng.random(n) < 0.02] = 0
    return b.astype(np.uint32)


def unit_vectors(path: Path, nmsg, words, modes, seed, big=False):
    rng = np.random.default_rng(seed)
    part = rand_f32(rng, nmsg * TP * words * LANES).reshape(nmsg, TP, words, LANES)
    # cancellations: die 1 negates die 0 on some lanes; die 3 repeats die 2 on others
    cancel = rng.random((nmsg, words, LANES)) < 0.1
    part[:, 1][cancel] = part[:, 0][cancel] ^ np.uint32(0x80000000)
    rep = rng.random((nmsg, words, LANES)) < 0.1
    part[:, 3][rep] = part[:, 2][rep]
    if big:
        part[0, :, 0, 3] = np.uint32(0x7F000000)   # four 1.7e38: the sum overflows
    f = G.from_bits(part)
    sums = G.fold([f[:, d] for d in range(TP)])     # [nmsg, words, LANES]
    path.mkdir(parents=True, exist_ok=True)

    def hexw(arr):
        return "".join("".join(f"{int(x):08x}" for x in row[::-1]) + "\n" for row in arr.reshape(-1, LANES))
    (path / "part.hex").write_text(hexw(part))
    (path / "sum.hex").write_text(hexw(G.bits(sums)))
    (path / "mode.hex").write_text("".join(f"{m}\n" for m in modes))


UNIT_CASES = [
    # name, depth, msgs, words, gap %, skew, modes ('r' reduce / 'm' mixed), inject, inject value, big
    ("reduce_8w", 16, 64, 8, 0, 0, "r", -1, None, False),
    ("reduce_8w_gaps_skew", 16, 64, 8, 30, 7, "r", -1, None, False),
    ("mixed_gather_gaps_skew", 16, 64, 8, 30, 3, "m", -1, None, False),
    ("gather_1w", 16, 64, 1, 10, 5, "g", -1, None, False),
    ("reduce_320w_depth16", 16, 4, 320, 0, 0, "r", -1, None, False),
    ("reduce_320w_depth32", 32, 4, 320, 0, 0, "r", -1, None, False),
    ("fault_nan", 16, 4, 8, 0, 0, "r", 1, "7fc00000", False),
    ("fault_inf", 16, 4, 8, 0, 0, "r", 2, "ff800000", False),
    ("fault_overflow", 16, 4, 8, 0, 0, "r", 0, "7f000000", True),
    ("fault_tag_mismatch", 16, 4, 8, 0, 0, "r", -1, None, False),
]


def unit_build(scratch: Path, depth: int, lat: int, bpc: int) -> Path:
    obj = scratch / f"unit_obj_d{depth}"
    sh(["verilator", "--cc", "--exe", "--build", "-O2", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED", "-Wno-BLKSEQ",
        "--top-module", "tb_rom_oneshot_allreduce", f"-GDEPTH={depth}", f"-GLAT={lat}", f"-GBPC={bpc}",
        "-Mdir", str(obj), str(ADDER), str(ALLREDUCE), str(TB_UNIT), str(unit_harness(scratch)),
        "-CFLAGS", "-O1", "-j", "8"])
    return obj / "Vtb_rom_oneshot_allreduce"


def unit_harness(scratch: Path) -> Path:
    h = scratch / "unit_harness.cpp"
    h.write_text('#include "Vtb_rom_oneshot_allreduce.h"\n#include "verilated.h"\n'
                 "int main(int argc, char** argv) { Verilated::commandArgs(argc, argv);\n"
                 "  auto* t = new Vtb_rom_oneshot_allreduce; t->clk = 0;\n"
                 "  while (!Verilated::gotFinish()) { t->clk = !t->clk; t->eval(); }\n"
                 "  t->final(); delete t; return 0; }\n")
    return h


def run_unit(scratch: Path, lp: dict) -> list:
    lat, bpc = lp["lat_cycles"], lp["bytes_per_cycle"]
    exes = {d: unit_build(scratch, d, lat, bpc) for d in sorted({c[1] for c in UNIT_CASES})}
    out = []
    for i, (name, depth, nmsg, words, gap, skew, mk, inj, ival, big) in enumerate(UNIT_CASES):
        rng = np.random.default_rng(100 + i)
        modes = {"r": [0] * nmsg, "g": [1] * nmsg, "m": list(rng.integers(0, 2, nmsg))}[mk]
        vec = scratch / f"unit_{name}"
        unit_vectors(vec, nmsg, words, modes, 1000 + i, big)
        args = [str(exes[depth]), f"+VEC={vec}", f"+NMSG={nmsg}", f"+WORDS={words}", f"+GAP={gap}",
                f"+SKEW={skew}", f"+SEED={7 + i}", f"+INJECT={inj}"] + ([f"+IVAL={ival}"] if ival else []) + \
            (["+TAGBAD=2"] if name == "fault_tag_mismatch" else [])
        txt = sh(args)
        m = UNIT.search(txt)
        if not m:
            raise RuntimeError(f"unit {name}: no result\n{txt[-2000:]}")
        g = m.groups()
        first, last = int(g[13]), int(g[14])
        words_in = nmsg * words
        rec = {"case": name, "fifo_depth": depth, "lat_cycles": lat, "messages": nmsg, "words_per_message": words,
               "gap_percent": gap, "skew_cycles_per_die": skew,
               "gather_messages": int(sum(modes)), "reduce_messages": nmsg - int(sum(modes)),
               "inject_message": inj, "inject_value": ival, "mismatches": int(g[8]), "error_words": int(g[9]),
               "fault_bits": g[10], "fault_code_bits": g[11], "words_out_all_dies": int(g[12]),
               "cycles_first_send_to_last_result": last - first,
               "link_hold_cycles": int(g[15]), "pass": "PASS" in txt}
        if name == "fault_tag_mismatch":
            rec["tag_mismatch_message"] = 2
        elif inj < 0 and not gap and mk == "r":
            rec["words_per_cycle_per_die"] = round(words_in / (last - first), 4)
        out.append(rec)
    return out


# -- 2. packages of four dies -------------------------------------------------------------------
PKG_CONFIGS = [
    # (packages, users, extra user counts on the same build, LAT override or None)
    (1, 1, (), None),
    (1, 4, (), None),
    (4, 4, (1,), None),
    (1, 1, (), "low"),
    (1, 1, (), "high"),
]


def images(scratch: Path) -> Path:
    img = scratch / "img_tp"
    sh([sys.executable, str(ROOT / "tools/hdc_program.py"), "--tp", str(TP), "--stages", "4", "--out", str(img)])
    return img


def pkg_sources():
    return [*core.HDC, *core.PIPES, ROOT / "rtl/rom/ot_rom_pkg_link.sv", ROOT / "rtl/rom/ot_rom_pkg_ctrl.sv",
            ALLREDUCE, SEQ, TB, HARNESS]


def run_pkg(scratch: Path, img: Path, lp: dict, nodes: int, users: int, fewer: tuple, lat_sel) -> list:
    lat = {None: lp["lat_cycles"], "low": lp["lat_cycles_range"][0], "high": lp["lat_cycles_range"][1]}[lat_sel]
    tag = f"n{nodes}_u{users}_l{lat}"
    obj = scratch / f"obj_{tag}"
    exp = json.loads((img / "expect.json").read_text())
    kv_words = exp["kv_elems"] // 16
    sh(["verilator", "--cc", "--exe", "--build", "-O2", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED",
        "-Wno-BLKSEQ", "--top-module", "tb_hdc_package_tp", f"-GNODES={nodes}", f"-GUSERS={users}",
        f"-GD={TP}", f"-GLAT={lat}", f"-GBPC={lp['bytes_per_cycle']}", f"-GKVHALF={kv_words // 2}",
        f"-GKVLAYER={kv_words // 2 // 4}", "-Mdir", str(obj), f"-I{core.ISA_SVH.parent}",
        *map(str, pkg_sources()[:-1]), str(HARNESS), "-CFLAGS", "-O1", "-j", "8"])
    out = []
    for active in (users, *fewer):
        txt = sh([str(obj / "Vtb_hdc_package_tp"), f"+DIR={img}", "+NGEN=3", f"+NUSERS={active}"])
        (scratch / f"out_{tag}_u{active}.txt").write_text(txt)
        m = RES.search(txt)
        if not m:
            raise RuntimeError(f"{tag}: no result\n{txt[-3000:]}")
        n, dies, u, gen, checked, bad, kvb, vmb, cycles = map(int, m.groups())
        dies_rec = [dict(zip(("package", "die", "busy_cycles", "collective_cycles", "kv_mismatches",
                              "vm_mismatches"), map(int, x))) for x in DIE.findall(txt)]
        busy = sum(x["busy_cycles"] for x in dies_rec)
        coll = sum(x["collective_cycles"] for x in dies_rec)
        ls, cs = map(int, STALLS.search(txt).groups())
        gens = [dict(zip(("user", "position", "token", "cycle"), map(int, g))) for g in GEN.findall(txt)]
        steps = u * STEPS_PER_USER
        out.append({
            "packages": n, "dies_per_package": dies, "users": u, "ucie_lat_cycles": lat,
            "ucie_lat_setting": lat_sel or "nominal",
            "generated_tokens": gen, "generated": gens,
            "generated_ids_per_user": sorted({tuple(g2["token"] for g2 in gens if g2["user"] == uu)
                                              for uu in range(u)}),
            "steps_checked_bit_exact": checked, "mismatches": bad, "kv_mismatches": kvb,
            "vector_memory_mismatches": vmb, "vector_memory_checked": n == 1,
            "total_cycles": cycles, "token_steps": steps,
            "cycles_per_token_step": round(cycles / steps, 1),
            "cycles_per_user_step": round(cycles / STEPS_PER_USER, 1),
            "die_busy_cycles": busy, "die_collective_cycles": coll,
            "collective_share_of_die_busy": round(coll / busy, 4) if busy else None,
            "collective_cycles_per_step_per_die": round(coll / (len(dies_rec) / n) / steps / n, 1) if dies_rec else None,
            "board_link_credit_stalls": ls, "collective_hold_cycles": cs,
            "dies": dies_rec,
            "pass": "PASS" in txt and bad == 0 and kvb == 0 and vmb == 0 and gen == u * 3
                    and checked == u * STEPS_PER_USER * (1 if n else 0)})
    return out


def baseline(scratch: Path) -> list:
    """One core per package, 4 packages (layer each, lm_head with the last), 4 users and 1."""
    return array.run_config(scratch, 4, 4, 0, False, "p2p", False, 0, (1,))


def sources():
    return sorted({*pkg_sources(), TB_UNIT, ADDER, TECH, ROOT / "tools/hdc_golden.py",
                   ROOT / "tools/hdc_program.py", ROOT / "tools/hdc_isa.py", Path(__file__),
                   array.TB, array.HARNESS, array.LINK, array.ROUTER, array.CTRL, core.ISA_SVH})


def run(keep=None) -> dict:
    lp = link_params()
    with tempfile.TemporaryDirectory() as tmp:
        scratch = keep or Path(tmp)
        scratch.mkdir(parents=True, exist_ok=True)
        img = images(scratch)
        expect = json.loads((img / "expect.json").read_text())
        with ThreadPoolExecutor(len(PKG_CONFIGS) + 2) as pool:
            unit_f = pool.submit(run_unit, scratch, lp)
            base_f = pool.submit(baseline, scratch)
            pkg_f = [pool.submit(run_pkg, scratch, img, lp, *c) for c in PKG_CONFIGS]
            unit = unit_f.result()
            base = base_f.result()
            pkgs = [r for f in pkg_f for r in f.result()]
    single = json.loads(core.OUT.read_text())
    single_e2e = single["end_to_end"]["total_cycles"]

    def find(rs, n, u, lat="nominal"):
        return next(r for r in rs if r["packages"] == n and r["users"] == u and r.get("ucie_lat_setting", lat) == lat)
    b4, b1 = (next(r for r in base if r["users"] == u) for u in (4, 1))
    comparisons = {
        "single_core_end_to_end_cycles": single_e2e,
        "one_package_1_user": {
            "tensor_group_cycles": find(pkgs, 1, 1)["total_cycles"],
            "single_core_cycles": single_e2e,
            "speedup": round(single_e2e / find(pkgs, 1, 1)["total_cycles"], 3)},
        "ring_4_packages_4_users": {
            "tensor_group_cycles": find(pkgs, 4, 4)["total_cycles"],
            "one_core_per_package_cycles": b4["total_cycles"],
            "tensor_group_cycles_per_token_step": find(pkgs, 4, 4)["cycles_per_token_step"],
            "one_core_per_package_cycles_per_token_step": b4["cycles_per_token_step"],
            "speedup": round(b4["total_cycles"] / find(pkgs, 4, 4)["total_cycles"], 3)},
        "ring_4_packages_1_user": {
            "tensor_group_cycles": find(pkgs, 4, 1)["total_cycles"],
            "one_core_per_package_cycles": b1["total_cycles"],
            "tensor_group_cycles_per_token_step": find(pkgs, 4, 1)["cycles_per_token_step"],
            "one_core_per_package_cycles_per_token_step": b1["cycles_per_token_step"],
            "speedup": round(b1["total_cycles"] / find(pkgs, 4, 1)["total_cycles"], 3)},
        "ucie_latency_sensitivity_1_package_1_user": [
            {"lat_cycles": r["ucie_lat_cycles"], "setting": r["ucie_lat_setting"], "total_cycles": r["total_cycles"],
             "collective_share_of_die_busy": r["collective_share_of_die_busy"]}
            for r in pkgs if r["packages"] == 1 and r["users"] == 1],
    }
    ok = all(r["pass"] for r in unit) and all(r["pass"] for r in pkgs) and all(r["pass"] for r in base)
    return {
        "schema": "opentallas.hdc-package-tp-campaign.v1",
        "status": "pass" if ok else "fail",
        "claim_boundary": "functional, cycle-accurate RTL simulation (Verilator) of ROM-array packages built as "
                          "4-die tensor groups: decode cores, tensor-group sequencers, the one-shot collective "
                          "engines and the package controller are synthesizable RTL; memories are behavioural; "
                          "the die-to-die UCIe PHY is a delay-and-rate model (ot_rom_ucie_link) and the "
                          "package-to-package link the tb_hdc_array delay line (60 cycles). Cycles only; the "
                          "clock is claimed by the ASAP7 records.",
        "vehicle": "qwen3-reduced-v1 (hidden 128, 4 layers, 8/2 heads, head_dim 16, ffn 384, vocab 4096)",
        "tensor_split": {
            "dies": TP,
            "column_split": "q/k/v rows by query head (2 per die; the die's KV head, shared by two dies, is "
                            "computed by both, bit-identically), gate/up rows (96 per die)",
            "row_split": "o_proj input columns (the die's heads), down_proj input columns (its 96 FFN rows); "
                         "partials all-reduced before the residual add",
            "vocabulary_split": "lm_head rows (1024 per die); argmax all-gathered, rank order, strictly "
                                "greater wins",
            "replicated": "embedding, RMSNorms, residuals, RoPE tables",
            "collectives_per_token": {"all_reduce_128_fp32": expect["allreduces_per_token"], "argmax_all_gather": 1},
            "arithmetic": "hdc_golden.Model.decode_token_tp: a row-split matrix's partial is the die's own "
                          "K-slice (its own split_for), the four partials are added ((p0+p1)+p2)+p3; a "
                          "column-split matrix keeps every output's K but may take another split_for",
            "rounding_effect": "the FP32 hidden state differs from the one-core golden (1,293 of 2,048 "
                               "final-norm elements over the 16 prompt steps differ), but every BF16-rounded "
                               "matrix input and every BF16 KV entry is identical, so the logits are "
                               "bit-identical to the one-core golden at every step and the tokens are the "
                               "oracle's",
        },
        "golden": {"single_step_pos15": expect["single_step"], "end_to_end": {
            k: v for k, v in expect["end_to_end"].items() if k != "steps"},
            "program_words_per_die": expect["prog_words"], "segments_per_die": expect["segments"],
            "weight_rom_words_per_die": expect["wrom_words"]},
        "ucie_link": lp,
        "one_shot_unit": unit,
        "packages": pkgs,
        "one_core_per_package_baseline": base,
        "comparison": comparisons,
        "input_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources()},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, default=OUT)
    parser.add_argument("--keep", type=Path, help="debug: build and run in this directory and keep it")
    args = parser.parse_args()
    result = run(args.keep)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    for r in result["one_shot_unit"]:
        print("unit", "PASS" if r["pass"] else "FAIL", r["case"], r.get("words_per_cycle_per_die", ""),
              r["cycles_first_send_to_last_result"])
    for r in result["packages"]:
        print("pkg", "PASS" if r["pass"] else "FAIL", r["packages"], "packages", r["users"], "users lat",
              r["ucie_lat_cycles"], ":", r["total_cycles"], "cycles", r["cycles_per_token_step"], "/step, coll share",
              r["collective_share_of_die_busy"])
    print(json.dumps(result["comparison"], indent=1))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
