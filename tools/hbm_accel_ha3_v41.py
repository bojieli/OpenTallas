#!/usr/bin/env python3
"""HA3 on the DeepSeek-V4.1 reduced HBM system (tools/gpu_sys/v41_hbm.py, which stays byte-identical): the z exchange
(attention, grouped wo_a output, 256 lanes) and both y exchanges (attention and MoE output, 160 lanes) of every
layer lowered to the cut-through COLLX of tools/hbm_accel_ha3.py instead of
    STG part -> MEMBAR -> BAR -> SM0: per 128-lane chunk LDG, AND own-mask, COLL, STG -> MEMBAR -> BAR -> LDG.
Every SM contributes its own lanes straight from the register; lanes a die does not own are +0 (the baseline's
ownership mask), so each lane of the result is fl(owner + 0) on the same in-switch reduction as before.  The other
collectives (hyper-connection mixes, indexer, MoE activations, Engram) keep the legacy COLL path.

    python3 tools/hbm_accel_ha3_v41.py --check --npos 1          # functional machine vs golden, every layer + token
    python3 tools/hbm_accel_ha3_v41.py --emit DIR [--nprompt 1 --ngen 1]
"""
from __future__ import annotations

import argparse
import inspect
import json
import sys
import textwrap
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "gpu_sys"))
sys.path.insert(0, str(HERE))
import hbm_accel_ha3 as H  # noqa: E402  (ISA registration, COLLX machine)
import v41_hbm as V41  # noqa: E402

NL = V41.NL

_SRC = inspect.getsource(V41.Gen.attend_core)
_OLD = '''        self.stg(z, self.A("Z") + 256 * g, 64)
        self.allreduce("Z", 256, lambda d, i: i // 128 == d)
        z = [self.ldg(self.A("Z")), self.ldg(self.A("Z") + 512)]
'''
assert _SRC.count(_OLD) == 1, "baseline attend_core changed"
_SRC = _SRC.replace(_OLD, '''        z = self._ha3_z(z)
''')
_ns = dict(V41.__dict__)
exec(compile(textwrap.dedent(_SRC), "<ha3 attend_core>", "exec"), _ns)


class Gen(V41.Gen):
    attend_core = _ns["attend_core"]

    def _ha3_z(self, z):
        """z exchange: SM g's 64 lanes are lanes 64g.. of 256; chunk q (128 lanes) is die q's."""
        g, k = self.g, self.k
        out = []
        for q in range(2):
            mine = g // 2 == q
            out.append(H.collx(k, z, 128, 64 * (g % 2) if mine else 0, 64 if mine else 0))
        return out

    def y_exchange(self, y):
        """y exchange: SM g's 40 lanes are lanes 40g.. of 160 (chunk 0: lanes 0..127, chunk 1: 128..159)."""
        g, k, lib = self.g, self.k, self.lib
        off = 40 * g
        n0 = max(0, min(40, 128 - off))
        c0 = H.collx(k, y, 128, off if n0 else 0, n0)
        if off + 40 > 128:
            sh = 128 - off                                     # lanes of y that went to chunk 0
            y1 = lib.shfl(y, lib.op("IADD", lib.lane(), lib.u(sh)))
            c1 = H.collx(k, y1, 32, 0, 40 - sh)
        else:
            c1 = H.collx(k, y, 32, 0, 0)
        return c0, c1


def use(mode):
    if mode == "base":
        V41.Gen, V41.Machine = _ORIG
        return
    if mode != "cut":
        raise ValueError("DS lowering: modes base | cut")
    V41.Gen, V41.Machine = Gen, H.Machine


_ORIG = (V41.Gen, V41.Machine)


def emit(case, mode, ngen=1, nprompt=None):
    use(mode)
    return V41.emit(case, ngen, nprompt)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="cut", choices=["base", "cut"])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--npos", type=int, default=1)
    ap.add_argument("--emit")
    ap.add_argument("--ngen", type=int, default=1)
    ap.add_argument("--nprompt", type=int, default=1)
    a = ap.parse_args()
    use(a.mode)
    if a.emit:
        m = V41.emit(a.emit, a.ngen, a.nprompt)
        print(json.dumps({k: m[k] for k in ("kernel_words", "imem_words", "mem_bytes")}), [s["next"] for s in m["steps"]])
    if a.check:
        sys.exit(0 if V41.check(a.npos) else 1)
