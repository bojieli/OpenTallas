#!/usr/bin/env python3
"""HA3 (HBM accelerator): cut-through collective and fused receive-path epilogue on the SM -> collective endpoint.

ISA additions (rtl/hbm_accel/collective/ot_hbm_accel_simt_sm.sv, HA3 = 1; OTG-1 itself, tools/gpu_sys/isa.py, is not
edited -- the two opcodes are registered here at import):
  COLLX d, a, b, imm  (0x49)  imm[7:0] count, [15:8] off, [23:16] nown, [24] mode, [25] fuse.  Every SM of a die
      contributes a[0:nown] as collective lanes off..off+nown-1 straight from the register (no store / barrier /
      reload); every SM receives the whole result.  fuse: d = fl(b + result) (b = the residual, read at lanes
      off..off+nown-1), and the golden-order sum of squares of d is latched for COLLSS.
  COLLSS d            (0x4A)  d = that sum of squares on every lane.
Lowering (Qwen3 reduced, tools/gpu_sys/qwen_hbm.py Program, which stays byte-identical): the two all-reduces of a layer
  baseline  store rows -> MEMBAR -> BAR -> SM0: LDG, COLL, STG, MEMBAR -> BAR -> LDG, FADD (+ rmsnorm's sum of squares)
  cut       LDS rows -> COLLX -> FADD (+ the sum of squares)
  fuse      LDS rows -> COLLX.fuse (x' = x + red, sum of squares on the arriving stream) -> COLLSS
  fuseo     fuse on the attention-output all-reduce (its sum of squares feeds the post-attention norm), cut on the
            down all-reduce (the next layer's input norm runs in the next kernel, so a fused sum there is unused)
The golden rounding points are unchanged: x' = fl(x + fl(p0 + p1)), the sum of squares in R-ARITH order (chunks of 8
sequential from +0, adjacent pairwise tree), exactly Lib.seg_sum8 over the 128-lane segment.

    python3 tools/hbm_accel_ha3.py --check --mode fuse           # functional machine vs golden, every layer + token
    python3 tools/hbm_accel_ha3.py --emit DIR --mode cut         # program + images for the RTL bench
"""
from __future__ import annotations

import argparse
import inspect
import json
import sys
import textwrap
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "gpu_sys"))
sys.path.insert(0, str(HERE))
import isa  # noqa: E402
import machine as MC  # noqa: E402
import qwen_hbm as Q  # noqa: E402
from asm import Kernel  # noqa: E402

U = np.uint32
OPS_HA3 = {"COLLX": 0x49, "COLLSS": 0x4A}


def install_isa():
    for k, v in OPS_HA3.items():
        isa.OPS[k] = v
        isa.NAMES[v] = k


install_isa()


def collx_imm(count, off, nown, mode=0, fuse=False):
    assert 0 < count <= 255 and 0 <= off <= 255 and 0 <= nown <= 255 and off + nown <= count
    return (count & 0xFF) | (off << 8) | (nown << 16) | ((mode & 1) << 24) | (int(fuse) << 25)


def collx(k: Kernel, v, count, off, nown, mode=0, fuse=False, resid=None):
    d = k._new()
    k.emit("COLLX", d, v, resid if fuse else v, collx_imm(count, off, nown, mode, fuse))
    return d


def collss(k: Kernel):
    d = k._new()
    k.emit("COLLSS", d, 0, 0, 0)
    return d


# ------------------------------------------------------------------------------------------------ golden epilogue
def chunk8_sumsq(xp):
    """R-ARITH sum of squares of a 128-lane (NL) vector: fl(x*x), chunks of 8 sequential from +0, adjacent pairwise
    tree over the chunk sums -- Lib.seg_sum8(mul(x, x), NL) at lane 0, with the machine's fail-closed FP."""
    sq = isa.fmul(xp, xp)
    nch = len(xp) // 8
    acc = np.zeros(nch, dtype=U)
    for c in range(nch):
        a = isa.fadd(U(0), sq[8 * c])
        for j in range(1, 8):
            a = isa.fadd(a, sq[8 * c + j])
        acc[c] = a
    while len(acc) > 1:
        acc = isa.fadd(acc[0::2], acc[1::2])
    return U(acc[0])


# ------------------------------------------------------------------------------------------------ functional machine
_RUN_SRC = inspect.getsource(MC.Machine._run)
_HOOK = '            elif op == "RESULT":'
assert _RUN_SRC.count(_HOOK) == 1
_RUN_SRC = textwrap.dedent(_RUN_SRC.replace(_HOOK, '''            elif op == "COLLX":
                out = yield ("COLLX", (imm, vr[a].copy(), vr[b].copy()))
                vr[d] = out[0]
                sm.c_ss = out[1]
            elif op == "COLLSS":
                vr[d] = U(getattr(sm, "c_ss", 0))
''' + _HOOK))
_ns = dict(MC.__dict__)
exec(compile(_RUN_SRC, "<ha3 _run>", "exec"), _ns)


class Machine(MC.Machine):
    """machine.Machine plus COLLX / COLLSS (every SM of every die rendezvous at a COLLX)."""
    _run = _ns["_run"]

    def launch(self, kernels, token, pos):
        runs = {}
        for d in self.dies:
            for sm in d.sms:
                sm.ur[:] = 0
                sm.ur[0], sm.ur[1], sm.ur[2], sm.ur[3] = token, pos, sm.sid, d.die
                runs[(d.die, sm.sid)] = self._run(sm, kernels[(d.die, sm.sid)])
        state = {k: next(g) for k, g in runs.items()}
        while True:
            if all(s[0] == "EXIT" for s in state.values()):
                return
            progressed = False
            for d in self.dies:
                keys = [(d.die, sm.sid) for sm in d.sms]
                if all(state[k][0] in ("BAR", "EXIT") for k in keys) and any(state[k][0] == "BAR" for k in keys):
                    if any(state[k][0] == "EXIT" for k in keys):
                        raise RuntimeError("BAR with an exited SM")
                    for k in keys:
                        state[k] = runs[k].send(None)
                    progressed = True
            colls = {k: v for k, v in state.items() if v[0] == "COLL"}
            if colls and len(colls) == len(self.dies):
                keys = sorted(colls)
                outs = self._collective([colls[k][1] for k in keys])
                for k, o in zip(keys, outs):
                    state[k] = runs[k].send(o)
                progressed = True
            cx = {k: v for k, v in state.items() if v[0] == "COLLX"}
            if cx and len(cx) == len(state):
                outs = self._collx({k: v[1] for k, v in cx.items()})
                for k, o in outs.items():
                    state[k] = runs[k].send(o)
                progressed = True
            if not progressed:
                raise RuntimeError(f"deadlock: { {k: v[0] for k, v in state.items()} }")

    def _collx(self, reqs):
        nl = self.nl
        imms = {k: v[0] for k, v in reqs.items()}
        f = lambda imm: (imm & 0xFF, (imm >> 24) & 1, (imm >> 25) & 1)
        count, mode, fuse = f(next(iter(imms.values())))
        assert all(f(i) == (count, mode, fuse) for i in imms.values()), "COLLX: SMs disagree on count/mode/fuse"
        dies = sorted({k[0] for k in reqs})
        merged, resid = {}, {}
        for dd in dies:
            v = np.zeros(nl, dtype=U)
            r = np.zeros(nl, dtype=U)
            seen = np.zeros(nl, dtype=bool)
            for (d_, s_), (imm, data, res) in reqs.items():
                if d_ != dd:
                    continue
                off, nown = (imm >> 8) & 0xFF, (imm >> 16) & 0xFF
                assert off + nown <= count and not seen[off:off + nown].any(), "COLLX: lane contract"
                seen[off:off + nown] = True
                v[off:off + nown] = data[:nown]
                r[off:off + nown] = res[off:off + nown]
            assert not fuse or seen[:count].all(), "COLLX.fuse: lanes below count not all contributed"
            # a lane no SM of the die contributed is +0 (the die's share of a gather-by-reduce)
            merged[dd], resid[dd] = v, r
        outs = self._collective([(mode, count, merged[dd]) for dd in dies])
        res = {}
        for i, dd in enumerate(dies):
            o, ss = outs[i], U(0)
            if fuse:
                assert mode == 0 and count == nl
                o = isa.fadd(resid[dd], o)
                ss = chunk8_sumsq(o)
            for k in reqs:
                if k[0] == dd:
                    res[k] = (o.copy(), ss)
        return res


# ------------------------------------------------------------------------------------------------ Qwen lowering
_LAYER_SRC = inspect.getsource(Q.Program.kernel_layer)
_AR_O = '''        self._store_rows(k, rows, lay["OPART"] + s * 64 * 4)
        k.membar()
        k.bar()
        if s == 0:
            red = k.coll(k.ldg(6, lay["OPART"], 4, 128), 0, 128)
            k.stg(red, 6, lay["ORED"], 4, 128)
            k.membar()
        k.bar()
        x = lib.add(x, k.ldg(6, lay["ORED"], 4, 128))
        gpost = k.ldg(6, lay[f"L{L_}.GPOST"], 4, 128)
        h = lib.rmsnorm_seg(x, gpost, 128, 128)
'''
_AR_D = '''        self._store_rows(k, rows, lay["DPART"] + s * 64 * 4)
        k.membar()
        k.bar()
        if s == 0:
            red = k.coll(k.ldg(6, lay["DPART"], 4, 128), 0, 128)
            k.stg(red, 6, lay["DRED"], 4, 128)
            k.membar()
        k.bar()
        x = lib.add(x, k.ldg(6, lay["DRED"], 4, 128))
'''
_NEW_O = '''        x, ss = self._ha3_ar(k, lib, rows, s, x, norm=True)
        gpost = k.ldg(6, lay[f"L{L_}.GPOST"], 4, 128)
        h = self._ha3_norm(lib, x, ss, gpost)
'''
_NEW_D = '''        x, _ = self._ha3_ar(k, lib, rows, s, x, norm=False)
'''
for _old, _new in ((_AR_O, _NEW_O), (_AR_D, _NEW_D)):
    assert _LAYER_SRC.count(_old) == 1, "baseline layer kernel changed"
    _LAYER_SRC = _LAYER_SRC.replace(_old, _new)
_qns = dict(Q.__dict__)
exec(compile(textwrap.dedent(_LAYER_SRC), "<ha3 kernel_layer>", "exec"), _qns)


class Program(Q.Program):
    """qwen_hbm.Program with the layer's two all-reduces lowered to COLLX (mode 'cut') or COLLX.fuse ('fuse')."""
    MODE = "cut"
    kernel_layer = _qns["kernel_layer"]

    def _ha3_ar(self, k, lib, rows, s, x, norm):
        v = k.lds(8, Q.TCR, rows)                       # this SM's rows, lanes 0..rows-1
        if self.MODE == "fuse" or (self.MODE == "fuseo" and norm):
            xn = collx(k, v, 128, s * 64, rows, 0, True, x)
            return xn, (collss(k) if norm else None)
        red = collx(k, v, 128, s * 64, rows)
        xn = lib.add(x, red)
        if not norm:
            return xn, None
        return xn, lib.seg_sum8(lib.mul(xn, xn), 128)

    def _ha3_norm(self, lib, x, ss, gamma):
        r = lib.rsqrt(lib.add(lib.mul(ss, lib.c(1.0 / 128)), lib.c(1e-6)))
        return lib.mul(lib.mul(x, r), gamma)


def use(mode):
    """Route qwen_hbm's check / emit through the HA3 program and machine (mode: base | cut | fuse)."""
    if mode == "base":
        Q.Program, Q.Machine = _ORIG
        return
    Program.MODE = mode
    Q.Program, Q.Machine = Program, Machine


_ORIG = (Q.Program, Q.Machine)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="fuse", choices=["base", "cut", "fuse", "fuseo"])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--npos", type=int)
    ap.add_argument("--emit")
    ap.add_argument("--out")
    ap.add_argument("--ngen", type=int, default=3)
    a = ap.parse_args()
    use(a.mode)
    if a.emit:
        m = Q.emit(a.emit, a.ngen)
        m["ha3_mode"] = a.mode
        Path(a.emit, "expected.json").write_text(json.dumps(m, indent=1) + "\n")
        print(json.dumps({k: m[k] for k in ("entries", "imem_words", "mem_bytes", "kernel_words")}),
              [st["next"] for st in m["steps"]])
    if a.check:
        sys.exit(0 if Q.check(a.npos, a.out) else 1)
