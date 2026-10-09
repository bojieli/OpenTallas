#!/usr/bin/env python3
"""sys-takeover 2026-10-09: qfd_native_collective_binding bench (rtl/test/tb_qfd_coll_native.sv): four dies, each
sequencer model (ckd 0.9 GHz) -> ot_qwen_die_io_xfifo NCOLL=1 (546-b forward, 516-b return, return-space credit
gate) -> ot_rom_oneshot_die_m (ck 1.2 GHz) on a UCIe ring; every returned word checked against tools/hdc_golden.fold.
    coll_native_bench.py pos  OUT     every case, fast and slow (CONS 25 %) sequencer consumers: 'COLL_NATIVE_PASS'
    coll_native_bench.py gate OUT     mutant: forward credits ignore the return reservation (slow consumer must FAIL)
    coll_native_bench.py trunc OUT    mutant: return word field truncated (data bit 0 dropped at the xfifo)
    coll_native_bench.py credit OUT   mutant: the return reservation is never released
A mutant run prints 'COLL_NATIVE_NEG_DETECTED' and exits 1 when any case fails, else 'COLL_NATIVE_NEG_MISSED' / 0."""
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import rtl_hdc_package_tp_campaign as C  # noqa: E402

XF = ROOT / "rtl/physical/ot_qwen_die_io_xfifo.sv"
CX = ROOT / "rtl/physical/ot_qwen_die_coll_xfifo.sv"
SRC = [ROOT / "rtl/hdc/ot_hdc_prefix.sv", ROOT / "rtl/hdc/ot_hdc_fastfp.sv", ROOT / "rtl/hdc/ot_hdc_fp32_add_lat.sv",
       ROOT / "rtl/rom/ot_rom_oneshot_die_m.sv", ROOT / "rtl/rom/ot_rom_oneshot_allreduce.sv",
       ROOT / "rtl/proto/ot_fp32_add_rne_pipe.sv",
       ROOT / "rtl/physical/ot_qwen_die_coll_xfifo.sv", ROOT / "rtl/physical/ot_qwen_die_cdc_ch.sv", ROOT / "rtl/physical/ot_qwen_async_fifo_w.sv",
       ROOT / "rtl/lib/ot_async_fifo.sv", ROOT / "rtl/lib/ot_reset_sync.sv", ROOT / "rtl/test/tb_qfd_coll_native.sv"]
CASES = [  # name, msgs, words, gap %, modes, consumer %
    ("reduce_8w", 32, 8, 0, "r", 100),
    ("mixed_gaps", 32, 8, 30, "m", 100),
    ("gather_1w_slow", 32, 1, 10, "g", 25),
    ("mixed_slow", 32, 8, 0, "m", 25),
    ("reduce_320w", 2, 320, 0, "r", 100),
    # Qwen3-8B TP4 shape (tools/hdc_program.py: an all-reduce is 256 words = one 4,096-element FP32 vector at 16 lanes;
    # two per layer; the lm-head argmax all-gathers one word)
    ("qwen_ar_256w", 1, 256, 0, "r", 100),
    ("qwen_layer_2x256w", 2, 256, 0, "r", 100),
    ("qwen_argmax_1w", 1, 1, 0, "g", 100),
]
MUT = {"trunc": (".i_d(i_coll_seq), .i_cr(), .w_fault(wf_cq)", ".i_d({i_coll_seq[WCQ-1:1], 1'b0}), .i_cr(), .w_fault(wf_cq)"),
       "credit": ("ocr_q <= o_coll_seq_v;", "ocr_q <= 1'b0;")}


def build(w: Path, mode: str) -> Path:
    src = [str(XF)] + [str(s) for s in SRC]
    if mode in MUT:                       # the mutation goes into the coll_xfifo (the NCOLL port block)
        a, b = MUT[mode]
        t = CX.read_text()
        assert t.count(a) == 1, a
        mut = w / "coll_xfifo_mut.sv"
        mut.write_text(t.replace(a, b))
        src = [str(mut) if s == str(CX) else s for s in src]
    obj = w / "obj"
    cmd = ["verilator", "--cc", "--exe", "--build", "-O2", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED", "-Wno-BLKSEQ",
           "-Wno-TIMESCALEMOD", "-Wno-MULTIDRIVEN", "--top-module", "tb_qfd_coll_native", "-Mdir", str(obj),
           f"-GCQ_AD={os.environ.get('NCOLL_CQ_AD', '64')}"] + \
          (["+define+OT_NCOLL_MUT_NOREFUND_CHECK"] if mode == "gate" else []) + src + \
          [str(ROOT / "physical/sys_takeover/coll_native_harness.cpp"), "-CFLAGS", "-O1", "-j", "8"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        print(r.stdout[-2000:] + r.stderr[-2000:])
        print("COLL_NATIVE_BENCH_ERROR build")
        sys.exit(2)
    return obj / "Vtb_qfd_coll_native"


def main():
    mode, w = sys.argv[1], Path(sys.argv[2])
    w.mkdir(parents=True, exist_ok=True)
    exe = build(w, mode)
    fails = []
    for i, (name, nmsg, words, gap, mk, cons) in enumerate(CASES):
        if mode == "gate" and cons == 100:
            continue
        if len(sys.argv) > 3 and name not in sys.argv[3].split(","):
            continue
        rng = np.random.default_rng(300 + i)
        modes = {"r": [0] * nmsg, "g": [1] * nmsg, "m": list(rng.integers(0, 2, nmsg))}[mk]
        vec = w / f"v_{name}"
        C.unit_vectors(vec, nmsg, words, modes, 3000 + i)
        txt = subprocess.run([str(exe), f"+VEC={vec}", f"+NMSG={nmsg}", f"+WORDS={words}", f"+GAP={gap}", f"+CONS={cons}",
                              f"+SEED={11 + i}"], capture_output=True, text=True, timeout=7200).stdout
        (w / f"{name}.log").write_text(txt)
        ok = "NCOLL_NATIVE PASS" in txt
        line = next((l for l in txt.splitlines() if l.startswith("NCOLL_NATIVE PASS")), "") or \
            next((l for l in txt.splitlines() if l.startswith("NCOLL_NATIVE msgs")), "no result")
        print(f"case {name} {'PASS' if ok else 'FAIL'} {line}")
        if not ok:
            fails.append(name)
    if mode == "pos":
        print("COLL_NATIVE_PASS" if not fails else f"COLL_NATIVE_FAIL {fails}")
        sys.exit(0 if not fails else 1)
    print("COLL_NATIVE_NEG_DETECTED" if fails else "COLL_NATIVE_NEG_MISSED")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
