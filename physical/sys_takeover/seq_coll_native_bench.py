#!/usr/bin/env python3
"""sys-takeover 2026-10-09: the Qwen ROM native collective END TO END (rtl/test/tb_qfd_seq_coll_native.sv): four dies of
generated sequencer master ot_qfd_sp_constants_sequencer_nc (ot_qwen_tp_seq_w12_nc) + vector memory master
ot_qfd_sp_vector_memory + ot_qwen_die_io_xfifo NCOLL=1 + ot_rom_oneshot_die_m on a UCIe ring.  Each case runs NSTEP
steps of {ALL-REDUCE of VM rows [VW, VW+NW), ARGMAX}; step s > 1 re-reduces what step s-1 wrote back into the VM.
Golden: tools/hdc_golden.fold (rank order) per row, rank-order argmax (strictly greater wins; ties keep the lower die).
    seq_coll_native_bench.py pos      OUT [cases]  -> 'SEQ_COLL_NATIVE_PASS'
    seq_coll_native_bench.py nocredit OUT          mutant: the sequencer sends without a forward credit
    seq_coll_native_bench.py wbaddr   OUT          mutant: the VM write-back goes one row off
    seq_coll_native_bench.py fixedlat OUT          mutant: the base w12 one-edge VM read assumption (ignores vm_qv)
A mutant prints 'SEQ_COLL_NATIVE_NEG_DETECTED' (exit 1) when any case fails, else 'SEQ_COLL_NATIVE_NEG_MISSED' (exit 0)."""
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden as G  # noqa: E402
import rtl_hdc_package_tp_campaign as C  # noqa: E402

N, LANES, NWB = 4, 16, 18
SRC = ["rtl/qwen_sys/missing_masters_20261007/gen/ot_qfd_sp_constants_sequencer_nc.sv",
       "rtl/qwen_sys/missing_masters_20261007/gen/ot_qwen_rom_core_ctrl.sv",
       "rtl/qwen_sys/missing_masters_20261007/ot_qfd_spine_masters.sv", "rtl/rom/ot_qwen_tp_seq_w12_nc.sv",
       "rtl/hdc/ot_hdc_dyn_ttiles.sv", "rtl/hdc/ot_hdc_qwen_int8_embed_decode.sv", "rtl/hdc/ot_hdc_cg.sv",
       "rtl/hdc/ot_hdc_delay.sv", "rtl/qwen_sys/missing_masters_20261007/ot_qfd_split_exact.sv",
       "rtl/qwen_sys/rtl_finish_20261007/ot_qfd_sp_vector_memory.sv",
       "rtl/physical/ot_qwen_die_io_xfifo.sv", "rtl/physical/ot_qwen_die_coll_xfifo.sv", "rtl/physical/ot_qwen_die_cdc_ch.sv",
       "rtl/physical/ot_qwen_async_fifo_w.sv", "rtl/lib/ot_async_fifo.sv", "rtl/lib/ot_reset_sync.sv",
       "rtl/hdc/ot_hdc_prefix.sv", "rtl/hdc/ot_hdc_fastfp.sv", "rtl/hdc/ot_hdc_fp32_add_lat.sv",
       "rtl/rom/ot_rom_oneshot_die_m.sv", "rtl/rom/ot_rom_oneshot_allreduce.sv", "rtl/proto/ot_fp32_add_rne_pipe.sv",
       "rtl/test/tb_qfd_seq_coll_native.sv"]
CASES = [  # name, VW, NW (0 = 256 rows), steps
    ("ar256_argmax_x2", 0, 0, 2),
    ("ar40_vw200_wrap_x2", 200, 40, 2),     # vw + k wraps the 8-bit VM word address
]
MUT = {"nocredit": "OT_SEQNC_MUT_NOCREDIT", "wbaddr": "OT_SEQNC_MUT_WBADDR", "fixedlat": "OT_SEQNC_MUT_FIXEDLAT",
       "overlap": "OT_SEQNC_MUT_OVERLAP"}   # overlap: VM reads forced into the core segment window


def okey(v):
    v = int(v)
    return (~v) & 0xFFFFFFFF if v >> 31 else v | 0x80000000


def vectors(path: Path, vw, nwd, nstep, seed, row0=37984):
    rng = np.random.default_rng(seed)
    nw = 256 if nwd == 0 else nwd
    rows = [(vw + k) % 256 for k in range(nw)]
    part = C.rand_f32(rng, N * 256 * LANES).reshape(N, 256, LANES)
    cancel = rng.random((256, LANES)) < 0.1                 # cancellations, as the unit cases
    part[1][cancel] = part[0][cancel] ^ np.uint32(0x80000000)
    vm = part.copy()
    sums = np.zeros((8, 256, LANES), dtype=np.uint32)
    for s in range(nstep):
        f = G.from_bits(vm[:, rows])
        r = G.bits(G.fold([f[d] for d in range(N)]))
        for d in range(N):
            vm[d, rows] = r
        sums[s, rows] = r
    am = np.zeros((8 * N, 2), dtype=np.uint64)
    exp = np.zeros((8, 2), dtype=np.uint64)
    for s in range(nstep):
        vals = rng.integers(0, 2 ** 32, N, dtype=np.uint64)
        if s == 1:
            vals[2] = vals[1]                                 # a tie: the lower die must win
            vals[1] = vals[3] = np.uint64(0x7F7FFFFF)
        idx = rng.integers(0, 2 ** 16, N, dtype=np.uint64)
        best = 0
        for d in range(1, N):
            if okey(vals[d]) > okey(vals[best]):
                best = d
        for d in range(N):
            am[s * N + d] = (vals[d], idx[d])
        exp[s] = (vals[best], (int(idx[best]) + row0 * best) % (1 << NWB))
    path.mkdir(parents=True, exist_ok=True)

    def hexw(arr):
        return "".join("".join(f"{int(x):08x}" for x in row[::-1]) + "\n" for row in arr.reshape(-1, LANES))
    (path / "part.hex").write_text(hexw(part))
    (path / "sum.hex").write_text(hexw(sums))
    (path / "am.hex").write_text("".join(f"{int(v):08x}{int(i):08x}\n" for v, i in am))
    (path / "exp.hex").write_text("".join(f"{int(v):08x}{int(t):08x}\n" for v, t in exp))
    return row0


def build(w: Path, mode: str) -> Path:
    obj = w / "obj"
    cmd = ["verilator", "--cc", "--exe", "--build", "-O2", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED", "-Wno-BLKSEQ",
           "-Wno-TIMESCALEMOD", "-Wno-MULTIDRIVEN", "-Wno-CASEINCOMPLETE", "-Wno-UNOPTFLAT", "-Irtl/hdc",
           "--top-module", "tb_qfd_seq_coll_native", "-Mdir", str(obj)] + \
          ([f"+define+{MUT[mode]}"] if mode in MUT else []) + [str(ROOT / s) for s in SRC] + \
          [str(ROOT / "physical/sys_takeover/seq_coll_native_harness.cpp"), "-CFLAGS", "-O1", "-j", "8"]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    if r.returncode:
        print(r.stdout[-3000:] + r.stderr[-3000:])
        print("SEQ_COLL_NATIVE_BENCH_ERROR build")
        sys.exit(2)
    return obj / "Vtb_qfd_seq_coll_native"


def main():
    mode, w = sys.argv[1], Path(sys.argv[2]).resolve()
    w.mkdir(parents=True, exist_ok=True)
    exe = build(w, mode)
    fails = []
    for i, (name, vw, nwd, nstep) in enumerate(CASES):
        if len(sys.argv) > 3 and name not in sys.argv[3].split(","):
            continue
        vec = w / f"v_{name}"
        row0 = vectors(vec, vw, nwd, nstep, 500 + i)
        txt = subprocess.run([str(exe), f"+VEC={vec}", f"+NSTEP={nstep}", f"+VW={vw}", f"+NWD={nwd}", f"+ROW0={row0}"],
                             capture_output=True, text=True, timeout=7200).stdout
        (w / f"{name}.log").write_text(txt)
        ok = "SEQ_COLL_NATIVE PASS" in txt
        info = [l for l in txt.splitlines() if l.startswith("step ") or l.startswith("SEQ_COLL_NATIVE steps")]
        print(f"case {name} {'PASS' if ok else 'FAIL'} " + " | ".join(info))
        if not ok:
            fails.append(name)
    if mode == "pos":
        print("SEQ_COLL_NATIVE_PASS" if not fails else f"SEQ_COLL_NATIVE_FAIL {fails}")
        sys.exit(0 if not fails else 1)
    print("SEQ_COLL_NATIVE_NEG_DETECTED" if fails else "SEQ_COLL_NATIVE_NEG_MISSED")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
