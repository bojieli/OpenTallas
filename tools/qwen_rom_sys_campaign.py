#!/usr/bin/env python3
"""Qwen3 ROM full-system RTL campaign (rtl/qwen_sys, rtl/test/qwen_sys).

Builds and runs, under Verilator (and Icarus for the AR256 equivalence):

  unit benches
    link     ot_qwen_d2d_link: in-order exactly-once delivery of records and
             engine credits under injected bit errors (CRC + ACK/NAK + go-back-N
             replay + replay timer), and link_fault on a broken channel;
    kv       ot_qwen_sys_kv_svc against the WR_ACK HBM model: random tokens of
             element writes and block reads vs a reference, the HBM image at
             the end, and the negative cases (corrupted response tag, read of an
             unfilled word);
    ctrl     reset sequencer order and boot faults, CSR fault aggregation and
             split, collective tag at positions 5 / 261, stray record, watchdog;
    seq_eq   tb_qwen_tp4_ar256 (the AR256 gate's bench) with the W12 sequencer
             and with ot_qwen_tp_seq_sys at defaults: identical stdout; and with
             TAG_FULL = 1 (40-bit tag): PASS;
  system     tb_qwen_rom_sys around ot_qwen_rom_sys_top: host rings -> 4 dies
             -> tokens, every step on every die, every completion, every die's
             HBM KV and VM against tools/hdc_program.py --tp 4 (bit-exact with
             tools/hdc_golden.py), for 1 and 2 users, with and without link bit
             errors; plus two fault-injection runs (HBM tag corruption, a broken
             board link) that must end in an error completion naming the source.
  static     the system sources tie no readiness input high.

Writes results/rtl/qwen_rom_system_rtl_20261003/campaign.json (refuses to
overwrite) and the logs beside it.

    python3 tools/qwen_rom_sys_campaign.py --work /tmp/qsys --out results/rtl/qwen_rom_system_rtl_20261003
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

os.environ.setdefault("HDC_SU_WIDTH", "1")   # the scalar stream unit's reduction order (as the TP campaign)
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

CORE = ["rtl/hdc/ot_hdc_delay.sv", "rtl/hdc/ot_hdc_fp32_mul_pipe.sv", "rtl/hdc/ot_hdc_fpu.sv",
        "rtl/hdc/ot_hdc_fastfp.sv", "rtl/hdc/ot_hdc_sfu.sv", "rtl/hdc/ot_hdc_sfu_q.sv", "rtl/hdc/ot_hdc_reduce.sv",
        "rtl/hdc/ot_hdc_reduce_q.sv", "rtl/hdc/ot_hdc_matvec.sv", "rtl/hdc/ot_hdc_stream.sv",
        "rtl/hdc/ot_hdc_vstream_lane.sv", "rtl/hdc/ot_hdc_vreduce.sv", "rtl/hdc/ot_hdc_vstream.sv",
        "rtl/hdc/ot_hdc_core.sv", "rtl/proto/ot_fp32_add_rne_pipe.sv", "rtl/proto/ot_fp32_mul_rne_pipe.sv"]
SYS = ["rtl/qwen_sys/ot_qwen_rom_sys_top.sv", "rtl/qwen_sys/ot_qwen_sys_die.sv", "rtl/qwen_sys/ot_qwen_sys_kv_svc.sv",
       "rtl/qwen_sys/ot_qwen_d2d_link.sv", "rtl/qwen_sys/ot_qwen_tp_seq_sys.sv", "rtl/qwen_sys/ot_qwen_sys_pkg_ctl.sv",
       "rtl/qwen_sys/ot_qwen_sys_rst_seq.sv", "rtl/qwen_sys/ot_qwen_sys_csr.sv", "rtl/qwen_sys/ot_qwen_sys_rom.sv",
       "rtl/rom/ot_rom_oneshot_allreduce.sv", "rtl/link/ot_link_crc32.sv", "rtl/lib/ot_reset_sync.sv",
       "rtl/host/ot_host_if.sv", "rtl/hdc/kv/ot_qwen_hbm_model_ack.sv", "rtl/test/qwen_sys/ot_qwen_d2d_chan.sv"]
HARNESS = "rtl/test/qwen_sys/qsys_harness.cpp"
HARNESS2 = "rtl/test/qwen_sys/qsys_harness2.cpp"     # sclk / fclk from one 3.6 GHz VCO (+CLK=slow|split)
CORE2 = "build/qwen_sys/ot_hdc_core_2clk.sv"           # emitted by tools/qwen_rom_sys_core2clk_emit.py
BENCHES = {
    "link": ("tb_qwen_d2d_link", ["rtl/test/qwen_sys/tb_qwen_d2d_link.sv", "rtl/test/qwen_sys/ot_qwen_d2d_chan.sv",
                                  "rtl/qwen_sys/ot_qwen_d2d_link.sv", "rtl/link/ot_link_crc32.sv"]),
    "kv": ("tb_qwen_sys_kv_svc", ["rtl/test/qwen_sys/tb_qwen_sys_kv_svc.sv", "rtl/qwen_sys/ot_qwen_sys_kv_svc.sv",
                                  "rtl/hdc/kv/ot_qwen_hbm_model_ack.sv"]),
    "kv_pf": ("tb_qwen_sys_kv_svc", ["rtl/test/qwen_sys/tb_qwen_sys_kv_svc.sv", "rtl/qwen_sys/ot_qwen_sys_kv_svc.sv",
                                     "rtl/hdc/kv/ot_qwen_hbm_model_ack.sv"]),
    "ctrl": ("tb_qwen_sys_ctrl", ["rtl/test/qwen_sys/tb_qwen_sys_ctrl.sv", "rtl/qwen_sys/ot_qwen_sys_rst_seq.sv",
                                  "rtl/qwen_sys/ot_qwen_sys_csr.sv", "rtl/qwen_sys/ot_qwen_tp_seq_sys.sv",
                                  "rtl/lib/ot_reset_sync.sv"]),
}
SYS_FILES = ([f for f in CORE if f != "rtl/hdc/ot_hdc_core.sv"] +
             [CORE2, "rtl/hdc/ot_hdc_me_2clk.sv", "rtl/common/ot_ratio_cdc_fifo.sv", "rtl/hdc/ot_hdc_cg.sv"] +
             SYS + ["rtl/test/qwen_sys/tb_qwen_rom_sys.sv"])
# system variants: (ME_CDC, KV_PREFETCH)
VARIANTS = {"c0p0": (0, 0), "c1p0": (1, 0), "c0p1": (0, 1), "c1p1": (1, 1)}
AR256 = ["rtl/rom/ot_rom_oneshot_allreduce.sv", "rtl/proto/ot_fp32_add_rne_pipe.sv", "rtl/test/tb_qwen_tp4_ar256.sv"]
# ports that must never be tied high in the system top (rom_bridge_gaps Z-list / DA6)
READY_PORTS = ["kv_ok", "kv_write_drained", "w_ok", "emb_ok", "me_mem_ok", "c_ready", "h_req_rdy", "tx_ready",
               "up_ready", "eng_done", "ready"]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def sh(cmd, cwd=ROOT, timeout=None, env=None):
    t0 = time.monotonic()
    p = subprocess.run([str(c) for c in cmd], cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env)
    return p.returncode, p.stdout + p.stderr, round(time.monotonic() - t0, 2)


VERILATOR = os.environ.get("VERILATOR", os.path.expanduser("~/.local/opentallas-tools/verilator-5.050/bin/verilator"))


def vbuild(top, files, mdir: Path, extra=(), jobs=24, harness=HARNESS):
    """Verilator 5 (--build -j); the bench's top class is passed to the harness as QSYS_TOP / QSYS_TOPH."""
    mdir.parent.mkdir(parents=True, exist_ok=True)
    cmd = [VERILATOR, "--cc", "--exe", "--build", "-j", str(jobs), "-O2", "-Wno-fatal", "-Wno-lint", "-Wno-style",
           "-Wno-WIDTH", "-Wno-BLKSEQ", "-Wno-MULTIDRIVEN", "-Wno-TIMESCALEMOD", "-Wno-PINMISSING",
           "-Wno-INITIALDLY", "--top-module", top, "-Mdir", mdir, "-Irtl/hdc", *extra,
           "-CFLAGS", f'-DQSYS_TOP=V{top} -DQSYS_TOPH=\\"V{top}.h\\"', *files, harness]
    t0 = time.monotonic()
    rc, out, _ = sh(cmd)
    (mdir.parent / f"{mdir.name}.build.log").write_text(out)
    if rc:
        raise RuntimeError(f"verilator {top} {extra}: {out[-3000:]}")
    return mdir / f"V{top}", time.monotonic() - t0


def run(binary: Path, args, log: Path, timeout=None):
    rc, out, t = sh([binary, *args], cwd=binary.parent, timeout=timeout)
    log.write_text(out)
    return {"args": list(args), "returncode": rc, "wall_s": t, "pass": ("PASS" in out.splitlines()[-3:] or
            any(l.strip() == "PASS" for l in out.splitlines())) and "FAIL" not in [l.strip() for l in out.splitlines()],
            "log": log.name, "log_sha256": sha(log), "summary": [l for l in out.splitlines()
                                                                 if re.match(r"(LINK|KVSVC|CTRL|TAG|WATCHDOG|BOOT|SOFT|SYS|DIE|COUNTERS|FAULT_STATUS|CQ|BREAK|TIMEOUT|STEP_MISMATCH|QWEN_AR256)", l)][:60]}


def ar256_vectors(work: Path):
    import numpy as np
    import hdc_golden as G
    rng = np.random.default_rng(20261001)
    parts = rng.uniform(-4, 4, (4, 256, 16)).astype(np.float32)
    parts[:, 0, 0] = np.array([2**24, 1, -(2**24), 1], dtype=np.float32)
    parts[:, 0, 1] = np.array([0.0, -0.0, 0.0, -0.0], dtype=np.float32)
    expected = G.bits(G.fold(parts))

    def emit(path, array):
        path.write_text("".join("".join(f"{int(v):08x}" for v in row[::-1]) + "\n" for row in array))
    work.mkdir(parents=True, exist_ok=True)
    for d in range(4):
        emit(work / f"part_die{d}.hex", G.bits(parts[d]))
    emit(work / "sum.hex", expected)


def seq_equivalence(work: Path, out: Path):
    """The AR256 bench with the pinned W12 sequencer, with the successor at defaults, and with TAG_FULL."""
    vec = work / "ar256_vec"
    ar256_vectors(vec)
    tb = (ROOT / "rtl/test/tb_qwen_tp4_ar256.sv").read_text()
    variants = {
        "w12": tb,
        "sys_default": tb.replace("ot_qwen_tp_seq_w12 #(", "ot_qwen_tp_seq_sys #("),
        "sys_tag_full": tb.replace("localparam integer N = 4, FW = 512, TAGW = 34;",
                                   "localparam integer N = 4, FW = 512, TAGW = 2 + 2 * 18 + 6;")
                          .replace("ot_qwen_tp_seq_w12 #(", "ot_qwen_tp_seq_sys #(.TAG_FULL(1), .STRAY_FAULT(1), .WDOG(4096), "),
    }
    assert variants["sys_default"] != tb and "TAG_FULL(1)" in variants["sys_tag_full"]
    res = {}
    for name, text in variants.items():
        f = work / f"tb_ar256_{name}.sv"
        f.write_text(text)
        seqsrc = "rtl/rom/ot_qwen_tp_seq_w12.sv" if name == "w12" else "rtl/qwen_sys/ot_qwen_tp_seq_sys.sv"
        binary = work / f"ar256_{name}.vvp"
        rc, o, _ = sh(["iverilog", "-g2012", "-s", "tb_qwen_tp4_ar256", "-o", binary, seqsrc, *AR256[:2], f])
        if rc:
            raise RuntimeError(f"iverilog {name}: {o[-2000:]}")
        res[name] = {}
        for case, split, inject in [("split128", 1, 0), ("one256", 0, 0), ("bad_last", 0, 1)]:
            rc, o, t = sh(["vvp", "-n", binary, f"+VEC={vec}", f"+SPLIT={split}", f"+INJECT_LAST={inject}"])
            log = out / f"seq_eq_{name}_{case}.log"
            log.write_text(o)
            line = [l for l in o.splitlines() if l.startswith("QWEN_AR256")]
            res[name][case] = {"returncode": rc, "line": line[0] if line else None, "log_sha256": sha(log)}
    same = all(res["w12"][c]["line"] == res["sys_default"][c]["line"] and res["w12"][c]["line"] for c in res["w12"])
    full_pass = all((res["sys_tag_full"][c]["line"] or "").startswith("QWEN_AR256 PASS") for c in res["sys_tag_full"])
    return {"cases": res, "default_identical_to_w12": same, "tag_full_pass": full_pass,
            "pass": same and full_pass}


def static_ready_check():
    """No readiness input of the system top's blocks is tied to a constant 1."""
    hits = []
    for f in SYS + ["rtl/qwen_sys/ot_qwen_sys_die.sv"]:
        text = (ROOT / f).read_text()
        for port in READY_PORTS:
            for m in re.finditer(r"\.(%s)\s*\(\s*1'b1\s*\)" % port, text):
                hits.append(f"{f}: .{m.group(1)}(1'b1)")
    return {"ports": READY_PORTS, "tied_high": hits, "pass": not hits}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--jobs", type=int, default=24)
    ap.add_argument("--skip-system", action="store_true")
    ap.add_argument("--img", type=Path, help="existing tools/hdc_program.py --tp 4 images (else generated)")
    a = ap.parse_args()
    res_path = a.out / "campaign.json"
    if res_path.exists():
        raise SystemExit("refusing to overwrite an existing verdict")
    a.out.mkdir(parents=True, exist_ok=True)
    a.work.mkdir(parents=True, exist_ok=True)
    srcs = sorted({*CORE, *SYS, *[f for _, fs in BENCHES.values() for f in fs], *AR256, HARNESS,
                   "rtl/rom/ot_qwen_tp_seq_w12.sv", "rtl/hdc/ot_hdc_isa.svh", "tools/hdc_golden.py",
                   "tools/hdc_program.py", "tools/hdc_isa.py", "tools/qwen_rom_sys_campaign.py",
                   "tools/qwen_rom_sys_core2clk_emit.py", HARNESS2, *[f for f in SYS_FILES if f != CORE2]})
    pins = {f: sha(ROOT / f) for f in srcs}
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "--", *srcs], cwd=ROOT, capture_output=True,
                           text=True).stdout.strip()
    result = {"schema": "opentallas.qwen-rom-system-rtl-campaign.v1", "git_head": head,
              "sources_dirty_at_launch": dirty.splitlines(), "source_sha256": pins, "status": "fail",
              "vehicle": "qwen3-reduced-v1 (hidden 128, 4 layers, 8/2 heads, head_dim 16, ffn 384, vocab 4096), TP-4",
              "claim_boundary": ("Functional, cycle-accurate RTL simulation (Verilator 5.050) of the Qwen3 ROM system "
                                 "top at the REDUCED vehicle shape: four ot_hdc_core dies (scalar stream unit, single "
                                 "clock), real link layers over simulated channels, KV in per-die HBM models (sim-only "
                                 "timing models with tagged write-done), the host interface driven by a register-level "
                                 "host. No full-shape token, no timing/P&R/SS-FF claim, no near-HBM attention on this "
                                 "token path. ME_CDC variants run the matrix engines at 1.2 GHz and the rest at 0.9 GHz (3:4, one PLL) through the "
                                 "ot_ratio_cdc_fifo crossings; the host and the links stay on the 0.9 GHz clock.")}
    t0 = time.monotonic()
    # images
    img = a.img or a.work / "img"
    if not (img / "expect.json").exists():
        rc, o, t = sh([sys.executable, "tools/hdc_program.py", "--tp", "4", "--ngen", "3", "--out", img])
        (a.out / "images.log").write_text(o)
        if rc:
            raise SystemExit("image generation failed")
    exp = json.loads((img / "expect.json").read_text())
    result["golden"] = {"single_step": exp["single_step"], "generated": exp["end_to_end"]["generated"],
                        "oracle": exp["end_to_end"]["oracle"],
                        "logits_bit_exact_every_step": exp["end_to_end"]["logits_bit_exact"],
                        "image_sha256": {p.name: sha(p) for p in sorted(img.glob("*.hex"))}}
    # the two-clock core variant (a build product of the pinned core)
    rc, o, _ = sh([sys.executable, "tools/qwen_rom_sys_core2clk_emit.py", "--out", ROOT / "build/qwen_sys"])
    if rc:
        raise SystemExit("core emit failed: " + o)
    result["core2clk"] = json.loads((ROOT / "build/qwen_sys/ot_hdc_core_2clk.json").read_text())
    # builds (parallel)
    bins = {}
    with cf.ThreadPoolExecutor(8) as ex:
        futs = {k: ex.submit(vbuild, top, files, a.work / f"obj_{k}", ("-GPREFETCH=1",) if k == "kv_pf" else (), a.jobs)
                for k, (top, files) in BENCHES.items()}
        if not a.skip_system:
            for v, (cdc, pf) in VARIANTS.items():
                futs[f"sys_{v}"] = ex.submit(vbuild, "tb_qwen_rom_sys", SYS_FILES, a.work / f"obj_sys_{v}",
                                             (f"-GME_CDC={cdc}", f"-GKV_PREFETCH={pf}"), a.jobs, HARNESS2)
        for k, f in futs.items():
            bins[k], bt = f.result()
            result.setdefault("build_wall_s", {})[k] = round(bt, 1)
    runs = {}
    jobs = []
    for fp in (0, 101, 37, 5, 3):
        jobs.append(("link", f"link_flip{fp}", [f"+FLIP={fp}"]))
    jobs.append(("link", "link_break", ["+BREAK"]))
    for p in ("0", "1"):
        kvb = "kv" if p == "0" else "kv_pf"
        jobs += [(kvb, f"kv_p{p}_ntok200", ["+NTOK=200"]), (kvb, f"kv_p{p}_tag_flip50", ["+TAG_FLIP=50"]),
                 (kvb, f"kv_p{p}_tag_flip700", ["+TAG_FLIP=700"]), (kvb, f"kv_p{p}_read_invalid", ["+READ_INVALID"])]
    jobs += [("ctrl", "ctrl_normal", []), ("ctrl", "ctrl_link_never", ["+LINK_NEVER"]),
             ("ctrl", "ctrl_hbm_bad", ["+HBM_BAD"])]
    if not a.skip_system:
        d = f"+DIR={img}"
        for v, (cdc, pf) in VARIANTS.items():
            clk = "+CLK=split" if cdc else "+CLK=slow"
            b = f"sys_{v}"
            jobs += [(b, f"{b}_users1", [d, clk, "+USERS=1"]),
                     (b, f"{b}_users2", [d, clk, "+USERS=2"]),
                     (b, f"{b}_users4_flip97", [d, clk, "+USERS=4", "+FLIP=97"]),
                     (b, f"{b}_users1_flip23", [d, clk, "+USERS=1", "+FLIP=23"])]
            if cdc:
                jobs += [(b, f"{b}_users1_fphase1", [d, clk, "+USERS=1", "+FPHASE=1"]),
                         (b, f"{b}_users1_fphase2", [d, clk, "+USERS=1", "+FPHASE=2"])]
        jobs += [("sys_c0p0", "sys_fault_hbm_tag", [d, "+CLK=slow", "+USERS=1", "+HBM_TAG_FLIP=400", "+EXPECT_FAULT=14"]),
                 ("sys_c0p0", "sys_fault_link_break", [d, "+CLK=slow", "+USERS=1", "+BREAK=60000", "+EXPECT_FAULT=5"]),
                 ("sys_c1p1", "sys_c1p1_fault_hbm_tag", [d, "+CLK=split", "+USERS=1", "+HBM_TAG_FLIP=900", "+EXPECT_FAULT=14"])]
    with cf.ThreadPoolExecutor(64) as ex:
        futs = {name: ex.submit(run, bins[b], args, a.out / f"{name}.log") for b, name, args in jobs}
        for name, f in futs.items():
            runs[name] = f.result()
    result["runs"] = runs
    result["seq_equivalence"] = seq_equivalence(a.work, a.out)
    result["static_ready"] = static_ready_check()
    result["source_stable"] = pins == {f: sha(ROOT / f) for f in srcs}
    result["wall_s"] = round(time.monotonic() - t0, 1)
    ok = (all(r["pass"] for r in runs.values()) and result["seq_equivalence"]["pass"]
          and result["static_ready"]["pass"] and result["source_stable"])
    result["status"] = "pass" if ok else "fail"
    with res_path.open("x") as f:
        f.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "runs": {k: v["pass"] for k, v in runs.items()},
                      "seq_equivalence": result["seq_equivalence"]["pass"],
                      "static_ready": result["static_ready"]["pass"]}, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
