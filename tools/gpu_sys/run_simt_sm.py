#!/usr/bin/env python3
"""Unit gate of the SIMT SM (rtl/gpu_sys/ot_gpu_simt_sm.sv): random OTG-1 programs covering every implemented
opcode (lane-wise FP/integer/convert ops on special values, shuffles, uniform ops, a counted loop, shared-memory
contiguous and gather/scatter access, global loads/stores of F32/BF16/E4M3 elements at contiguous, strided and
unaligned-start addresses, the tensor core over several op shapes, barrier, collective, RESULT), run on the
Python reference (tools/gpu_sys/machine.py) and on the RTL (Verilator 5.050), diffing every vector register,
uniform register, shared-memory word and memory byte.

    python3 tools/gpu_sys/run_simt_sm.py [--cases 6] [--out results/rtl/hbm_system_rtl_20261003/simt_sm.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import isa  # noqa: E402
from isa import enc  # noqa: E402
from machine import Machine  # noqa: E402

VERILATOR = Path(os.environ.get("OPENTALLAS_TOOL_ROOT", Path.home() / ".local/opentallas-tools")) / "verilator-5.050/bin/verilator"
SM_SRC = ["rtl/gpu_sys/ot_gpu_simt_sm.sv", "rtl/gpu_sys/ot_gpu_bd_line.sv", "rtl/gpu_sys/ot_gpu_simt_lane.sv", "rtl/gpu_sys/ot_gpu_simt_divlane.sv", "rtl/gpu/ot_gpu_sm.sv", "rtl/gpu/ot_gpu_bulk_copy.sv", "rtl/gpu/ot_gpu_fadd.sv",
          "rtl/hdc/ot_hdc_fp32_add_lat.sv", "rtl/hdc/ot_hdc_fp32_mul_lat.sv", "rtl/hdc/ot_hdc_fastfp.sv",
          "rtl/gpu/ot_gpu_tree.sv", "rtl/gpu/ot_gpu_issue.sv", "rtl/gpu/ot_gpu_stack.sv", "rtl/gpu/ot_gpu_tc_col.sv",
          "rtl/hdc/ot_hdc_fpu.sv", "rtl/hdc/ot_hdc_fp32_mul_pipe.sv", "rtl/proto/ot_fp32_add_rne_pipe.sv",
          "rtl/hdc/ot_hdc_sfu.sv", "rtl/hdc/ot_hdc_delay.sv", "rtl/hdc/ot_hdc_prefix.sv",
           "rtl/abi3/ot_a3_fp32_div_rne_pipe.sv", "rtl/abi3/ot_a3_fp32_sqrt_rne.sv",
           "rtl/gpu/ot_gpu_sm_bd.sv", "rtl/gpu/ot_gpu_bd_col.sv", "rtl/hdc/v41/ot_hdc_blockdot.sv",
           "rtl/v41rom/ot_v41_bterm.sv", "rtl/v41rom/ot_v41_bterm2.sv"]
TB = "rtl/test/gpu_sys/tb_gpu_simt_sm.sv"
MEMB = 131072
NL = 128


def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


def build(work):
    obj = Path(work) / "obj_sm"
    exe = obj / "Vtb_gpu_simt_sm"
    if exe.exists():
        return exe
    cmd = [str(VERILATOR), "--binary", "--timing", "-O2", "-j", "16", "-Wno-fatal", "-Wno-lint", "-Wno-style",
           "-Wno-WIDTH", "--x-assign", "0", "--x-initial", "0", "--top-module", "tb_gpu_simt_sm", "--Mdir", str(obj)] + \
          [str(ROOT / s) for s in SM_SRC + [TB]]
    subprocess.run(cmd, check=True, cwd=ROOT, stdout=subprocess.DEVNULL)
    return exe


def special_f32(rng, n):
    """Finite FP32 bit patterns: normals over a moderate range, subnormals, +-0, values near E4M3 / BF16 ties."""
    kind = rng.integers(0, 6, n)
    v = (rng.standard_normal(n) * np.exp2(rng.integers(-12, 12, n))).astype(np.float32)
    v = np.where(kind == 0, np.float32(0.0), v)
    v = np.where(kind == 1, np.float32(-0.0), v)
    sub = (rng.integers(1, 1 << 23, n).astype(np.uint32) | (rng.integers(0, 2, n).astype(np.uint32) << 31)).view(np.float32)
    v = np.where(kind == 2, sub, v)
    near = (np.round(rng.standard_normal(n) * 16) / 16).astype(np.float32) * np.float32(2.0) ** rng.integers(-9, 9, n)
    v = np.where(kind == 3, near.astype(np.float32), v)
    return v.view(np.uint32)


class Prog:
    def __init__(self):
        self.w = []

    def __call__(self, op, d=0, a=0, b=0, imm=0):
        self.w.append(enc(op, d, a, b, imm))


def gen_case(rng, kind):
    """Returns (program words, memory image bytes, token, pos)."""
    mem = np.zeros(MEMB, dtype=np.uint8)
    data = special_f32(rng, 4096)
    mem[0:16384] = data.view(np.uint8)
    P = Prog()
    P("UMOVI", 6, 0, 0, 0)
    # seed 32 registers with loaded vectors (F32 at offsets) and 8 with immediates
    for r in range(32):
        P("LDG", r, 6, 127, int(rng.integers(0, 120)) * 128)
    for r in range(32, 40):
        P("MOVI", r, 0, 0, int(special_f32(rng, 1)[0]))
    P("LANEID", 40)
    if kind == "alu":
        ints = ["XOR", "AND", "OR", "SHR", "SHL", "IADD", "ISUB", "UGT", "ULT", "FCMPGT", "IMUL"]
        for _ in range(600):
            c = rng.integers(0, 10)
            d = int(rng.integers(41, 200))
            a, b = (int(x) for x in rng.integers(0, 40, 2))
            if c < 3:
                P(["FADD", "FMUL"][int(rng.integers(0, 2))], d, a, b)
            elif c < 6:
                P(ints[int(rng.integers(0, len(ints)))], d, a, int(rng.integers(0, 41)))
            elif c < 8:
                P(["F2I", "CVTBF16", "CVTE4M3"][int(rng.integers(0, 3))], d, a)
            else:
                P("SHFL", d, a, int(rng.integers(0, 41)))
        # dependent chains through the FP pipes and the ALU (hazards, WAW)
        P("MOVI", 219, 0, 0, 0x3F400000)                     # 0.75: keeps the multiply chain finite
        for r in range(200, 210):
            P("FADD", r, int(rng.integers(0, 32)), int(rng.integers(0, 32)))
        for _ in range(200):
            d = int(rng.integers(200, 210))
            c = int(rng.integers(0, 3))
            if c == 0:
                P("FADD", d, int(rng.integers(200, 210)), int(rng.integers(0, 32)))
            elif c == 1:
                P("FMUL", d, int(rng.integers(200, 210)), 219)
            else:
                P("CVTBF16", d, int(rng.integers(200, 210)))
        # uniform ops and a counted loop
        P("UMOVI", 9, 0, 0, 5)
        P("UMOVI", 10, 0, 0, 0)
        loop = len(P.w)
        P("UADDI", 10, 10, 0, 3)
        P("FADD", 220, 220, 1)
        P("UADDI", 9, 9, 0, 0xFFFFFFFF)
        P("BNZ", 0, 9, 0, loop)
        P("UMULI", 11, 10, 0, 7)
        P("UADD", 12, 11, 10)
        P("UFROMV", 13, 5, 0, 77)
        P("MOVU", 221, 12)
        P("MOVU", 222, 13)
        P("MOVU", 223, 0)
        P("MOVU", 224, 1)
    elif kind == "lsu":
        P("UMOVI", 8, 0, 0, 0)
        for _ in range(60):
            esz = [4, 2, 1][int(rng.integers(0, 3))]
            cnt = int(rng.integers(1, 129))
            strided = int(rng.integers(0, 3)) == 0
            stride = int(rng.integers(1, 9)) * esz
            base = 20000 + int(rng.integers(0, 2000)) * esz
            src = int(rng.integers(0, 40))
            if esz == 1:
                P("CVTE4M3", 230, src)
                src = 230
            elif esz == 2:
                P("CVTBF16", 230, src)
                src = 230
            if strided:
                P("UMOVI", 15, 0, 0, stride)
            amode = 6 | (isa.ESZ[esz] << 4) | (int(strided) << 6)
            P("STG", src, amode, cnt - 1, base)
            d = int(rng.integers(100, 200))
            P("LDG", d, amode, cnt - 1, base)
        # shared memory: contiguous and gather/scatter
        for _ in range(40):
            r = int(rng.integers(0, 40))
            cnt = int(rng.integers(1, 129))
            base = int(rng.integers(0, 4000)) * 4
            P("STS", r, 8, cnt - 1, base)
            P("LDS", int(rng.integers(100, 200)), 8, int(rng.integers(0, 128)), int(rng.integers(0, 4000)) * 4)
        P("MOVI", 201, 0, 0, 4 * 37)
        P("IMUL", 202, 40, 201)                      # lane * 148 bytes
        for _ in range(20):
            P("STSX", int(rng.integers(0, 40)), 202, int(rng.integers(0, 128)), int(rng.integers(0, 4000)) * 4)
            P("LDSX", int(rng.integers(100, 200)), 202, 0, int(rng.integers(0, 4000)) * 4)
        P("BAR")
        P("COLL", 203, 5, 0, 77)
        P("COLL", 204, 6, 1, 128)
        P("UMOVI", 7, 0, 0, 0xBEEF)
        P("RESULT", 0, 7)
        P("MEMBAR")
    elif kind == "tc":
        L = 16
        wcur = 32768
        P("UMOVI", 8, 0, 0, 0)
        # activations: normal-range values (the BF16 product lanes fail closed on an inexact subnormal product)
        mem[16384:16384 + 2048] = (rng.standard_normal(512).astype(np.float32)).view(np.uint8)
        for r in range(3):
            P("LDG", r, 6, 127, 16384 + r * 512)
        for opn in range(4):
            split = int(rng.choice([16, 32, 64, 128]))
            K = int(rng.choice([128, 192, 256])) if split <= 64 else 128
            if K % split:
                K = 128
            rows = int(rng.integers(1, 40))
            c = K // split
            gn = -(-split // L)
            if gn * c > 16:
                split, c, gn = 16, K // 16, 1
            w = (rng.standard_normal((rows, K)) * 0.1).astype(np.float32)
            wb = (w.view(np.uint32) >> 16).astype(np.uint16)
            lines = []
            for rb in range(0, rows, 8):
                for g in range(gn):
                    for t in range(c):
                        for s in range(8):
                            r = rb + s
                            if r >= rows:
                                continue
                            ln = np.zeros(L, dtype=np.uint16)
                            for j in range(L):
                                ch = g * L + j
                                if ch < split:
                                    ln[j] = wb[r, ch * c + t]
                            lines.append(ln)
            blob = np.concatenate(lines).view(np.uint8)
            assert wcur + len(blob) < MEMB
            mem[wcur:wcur + len(blob)] = blob
            # x: K values from registers 0..; stage to SMEM and gather each x-store word
            for i in range(-(-K // NL)):
                P("CVTBF16", 230 + i, i)
                P("STS", 230 + i, 8, min(NL, K - i * NL) - 1, i * NL * 4)
            P("MOVI", 233, 0, 0, 4 * c)
            P("IMUL", 234, 40, 233)
            for g in range(gn):
                for t in range(c):
                    P("LDSX", 235, 234, 0, (g * L * c + t) * 4)
                    P("TCX", 0, 235, 0, g * c + t)
            P("UMOVI", 4, 0, 0, wcur)
            P("UMOVI", 5, 0, 0, 0x4000 + opn * 0x400)
            P("TCMMA", 4, 5, gn, (c << 16) | rows)
            if opn % 2:
                P("TCWAIT")
            wcur = (wcur + len(blob) + 127) // 128 * 128
        P("TCWAIT")
        for opn in range(4):
            P("LDS", 240 + opn, 8, 127, 0x4000 + opn * 0x400)
    elif kind == "ds":
        # DeepSeek-V4.1 additions: FMNMX, IMULHI, E2M1 / E4M3-code conversions, div.rn / sqrt.rn, block-scaled MMA
        for _ in range(150):
            d = int(rng.integers(41, 180))
            a_, b_ = (int(x) for x in rng.integers(0, 40, 2))
            P(["FMAX", "FMIN", "IMULHI", "CVTE2M1", "CVTE4M3B"][int(rng.integers(0, 5))], d, a_, b_)
        mem[16384:16384 + 2048] = np.abs(rng.standard_normal(512) * 4 + 0.1).astype(np.float32).view(np.uint8)
        for r in range(3):
            P("LDG", 180 + r, 6, 127, 16384 + r * 512)
        P("FDIV", 185, 0, 180)
        P("FDIV", 186, 181, 182)
        P("FSQRT", 187, 181)
        P("FADD", 188, 186, 187)
        P("FSQRT", 189, 183)            # zero lanes beyond the load
        # block-scaled MMA: random E4M3 / E2M1 code lines (no NaN codes) with block exponents
        P("UMOVI", 8, 0, 0, 0)
        wcur = 40960
        for opn, fp4 in enumerate((0, 1, 0)):
            rows = int(rng.integers(1, 20))
            g = int(rng.integers(1, 3))
            c = int(rng.integers(1, 5))
            n = 0
            blob = []
            for rb in range(0, rows, 8):
                for gg in range(g):
                    for t in range(c):
                        for s_ in range(8):
                            if rb + s_ >= rows:
                                continue
                            codes = rng.integers(0, 16 if fp4 else 0x7F, (8, 32)).astype(np.uint8)
                            if not fp4:
                                codes |= (rng.integers(0, 2, (8, 32)).astype(np.uint8) << 7)
                            ex = rng.integers(-12, 2, 8).astype(np.int16)
                            line = np.zeros(288, dtype=np.uint8)
                            line[:256] = codes.reshape(-1)
                            line[256:272] = ex.view(np.uint8)
                            blob.append(line)
            blob = np.concatenate(blob)
            assert wcur + len(blob) < MEMB
            mem[wcur:wcur + len(blob)] = blob
            for w_ in range(g * c):
                for r_, base in ((200, 0), (201, 0)):
                    P("MOVI", 202, 0, 0, int(rng.integers(0, 1 << 30)))
                    P("IMULHI", r_, 40, 202)
                    P("IMUL", r_, r_, 202)
                    P("MOVI", 203, 0, 0, 0x7E)
                    P("AND", r_, r_, 203)          # codes 0..0x7E (no NaN), positive
                P("TCXB", 0, 200, 201, w_)
                P("MOVI", 204, 0, 0, int(rng.integers(0, 6)))
                P("ISUB", 205, 204, 40)            # exponent 0..5 - lane: small negative values
                P("TCXE", 0, 205, 0, w_)
            P("UMOVI", 4, 0, 0, wcur)
            P("UMOVI", 5, 0, 0, 0x5000 + opn * 0x200)
            P("TCBMMA", 4, 5, g, rows | (fp4 << 12) | (c << 16))
            P("TCWAIT")
            P("LDS", 210 + opn, 8, 127, 0x5000 + opn * 0x200)
            wcur = (wcur + len(blob) + 127) // 128 * 128
    P("EXIT")
    return P.w, mem, int(rng.integers(0, 4096)), int(rng.integers(0, 32))


def run_python(words, mem, token, pos):
    isa.FP_ERR[0] = 0
    m = Machine(nd=1, nsm=1, nl=NL, mem_bytes=MEMB)
    m.dies[0].mem[:] = mem
    m.launch({(0, 0): words}, token, pos)
    sm = m.dies[0].sms[0]
    return sm, m.dies[0].mem, isa.FP_ERR[0]


def run_case(exe, work, idx, kind, rng, maxlat):
    words, mem, token, pos = gen_case(rng, kind)
    d = Path(work) / f"case{idx}_{kind}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "prog.hex").write_text("\n".join(f"{w:016x}" for w in words) + "\n")
    (d / "mem.hex").write_text("\n".join(f"{b:02x}" for b in mem) + "\n")
    (d / "cfg.hex").write_text("\n".join(f"{v:08x}" for v in (token, pos, len(words), int(os.environ.get('SIMT_MAXCYC', 2_000_000)), 0, 0, 0, 0)) + "\n")
    sm, pmem, fperr = run_python(words, mem.copy(), token, pos)
    with (d / "sim.log").open("w") as f:
        subprocess.run([str(exe), f"+DIR={d}", f"+SEED={idx + 1}", f"+MAXLAT={maxlat}"], check=True, cwd=d, stdout=f)
    vr, ur, smem, rmem, meta = {}, {}, {}, np.zeros(MEMB, dtype=np.uint8), {}
    for line in (d / "rtl_out.txt").read_text().splitlines():
        t = line.split()
        if t[0] == "#":
            meta = dict(fault=int(t[2]), result_seen=int(t[4]), result=int(t[5]),
                        **dict(zip(t[6::2], (int(x) for x in t[7::2]))))
        elif t[0] == "v":
            vr[int(t[1])] = int(t[2], 16)
        elif t[0] == "u":
            ur[int(t[1])] = int(t[2], 16)
        elif t[0] == "s":
            smem[int(t[1])] = int(t[2], 16)
        elif t[0] == "m":
            a = int(t[1])
            rmem[a:a + 32] = np.frombuffer(bytes.fromhex(t[2])[::-1], dtype=np.uint8)
    bad = []
    for r in range(256):
        pv = int.from_bytes(sm.vr[r].astype("<u4").tobytes(), "little")
        if vr.get(r) != pv:
            lanes = [l for l in range(NL) if ((vr.get(r, 0) >> (32 * l)) & 0xFFFFFFFF) != int(sm.vr[r][l])]
            bad.append(f"v{r} lanes {lanes[:6]} rtl {((vr.get(r, 0) >> (32 * lanes[0])) & 0xFFFFFFFF):08x} py {int(sm.vr[r][lanes[0]]):08x}")
    for u in range(16):
        if ur.get(u) != int(sm.ur[u]):
            bad.append(f"u{u} rtl {ur.get(u)} py {int(sm.ur[u])}")
    nm = int(np.sum(rmem != pmem))
    if nm:
        bad.append(f"memory bytes differ: {nm} first at {int(np.argmax(rmem != pmem))}")
    ns = sum(1 for i in range(8192) if smem.get(i) != int(sm.smem[i]))
    if ns:
        bad.append(f"smem words differ: {ns}")
    if meta.get("fault"):
        bad.append("rtl fault")
    if fperr:
        bad.append(f"python FP fail-closed lanes {fperr} (generator must keep operands finite)")
    if kind == "lsu" and (meta.get("result") != 1 or meta.get("result_value", meta.get("result")) is None):
        pass
    return dict(case=idx, kind=kind, instructions=len(words), rtl_cycles=meta.get("cycles"),
                rtl_instr=meta.get("instr"), tc_rows=meta.get("tc_rows"), pass_=not bad, diffs=bad[:12])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", type=int, default=6)
    ap.add_argument("--maxlat", type=int, default=40)
    ap.add_argument("--work", default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    work = a.work or tempfile.mkdtemp(prefix="simt_sm_")
    exe = build(work)
    rng = np.random.default_rng(20261003)
    kinds = ["alu", "lsu", "tc", "ds"]
    res = [run_case(exe, work, i, kinds[i % len(kinds)], rng, a.maxlat) for i in range(a.cases)]
    for r in res:
        print(("PASS" if r["pass_"] else "FAIL"), r["kind"], "case", r["case"], "instr", r["instructions"], "cycles",
              r["rtl_cycles"], *r["diffs"][:4])
    ok = all(r["pass_"] for r in res)
    rec = dict(schema="opentallas.gpu_sys.simt_sm.v1", tool="tools/gpu_sys/run_simt_sm.py",
               simulator=subprocess.run([str(VERILATOR), "--version"], capture_output=True, text=True).stdout.strip(),
               source_sha256={p: sha(p) for p in SM_SRC + [TB, "tools/gpu_sys/run_simt_sm.py", "tools/gpu_sys/isa.py",
                                                         "tools/gpu_sys/machine.py"]},
               cases=res, status="pass" if ok else "fail")
    if a.out:
        Path(a.out).write_text(json.dumps(rec, indent=1) + "\n")
    print("TB_GPU_SIMT_SM", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
