"""Per-die routed-expert image and the physical-stack bound of the weight manifest (no checkpoint).

Regression (2026-11-11, DIE-HBM-100 / TOK-VERIFY-1): the manifest placed every routed expert's WHOLE matrix (all 96
rank shards, 9.4 GiB a layer) on every die, inside a 94 GiB window that is 9 GiB past stack 2's physical bytes
(STACK_BYTES).  The full-chain token check faulted at layer 3 (wq_b at 93.97 GiB).  A die reads only its own TP96
rows of each expert (W.even), so its image holds only those, and every extent is bounded by STACK_BYTES.
"""
import json
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from hgi_sim import ds_native as N

ROOT = Path(__file__).resolve().parents[2]
RESIDENCY = ROOT / "results/arch/hbm_die_v15/checkpoint_residency/receipt.json"
GiB = 1 << 30


def expert_ops(k_exp=6):
    c = N.W.Compiler(SimpleNamespace(k_exp=k_exp, n_exp=384, limit=7, P=lambda L: f"layers.{L}."), 0)
    for slot in range(k_exp + 1):
        fmt = "fp4" if slot < k_exp else "fp8"
        c.mv(0, (slot, "w1"), "linear_q", "x", f"e{slot}.g", 2304, 5120, fmt)
        c.mv(0, (slot, "w3"), "linear_q", "x", f"e{slot}.u", 2304, 5120, fmt)
        c.local(0, "swiglu", slot=slot)
    for slot in range(k_exp + 1):
        fmt = "fp4" if slot < k_exp else "fp8"
        c.mv(0, (slot, "w2"), "linear_q", f"ea{slot}", f"e{slot}.d", 5120, 2304, fmt)
    return c.ops


class Golden:
    """checkpoint rows that carry matrix, expert and row identity"""
    def wrows(self, name, lo, hi):
        mat = int(name.split(".")[-2][1])
        expert = int(name.split(".")[-3]) if ".experts." in name else 0
        q = np.arange(lo, hi)[:, None] * 8 + np.arange(8)[None, :] + mat * 100000 + expert * 1000000
        return N.V_.Q8(q, np.full((hi - lo, 1), mat))


class ExpertImage(unittest.TestCase):
    def setUp(self):
        self.model = SimpleNamespace(k_exp=6, n_exp=384, limit=7, P=lambda L: f"layers.{L}.")
        self.layout, self.man = N.Layout(), N.Manifest()
        self.ops = expert_ops()
        self.low = N.Lower(self.model, 0, self.layout, self.man, fuse=True)
        self.recs = {r: [x for x in self.low.layer(0, self.ops, r) if x.unit == "SM"] for r in range(N.TP)}

    def test_ownership_is_the_residency_plan(self):
        """the per-die rows are the checkpoint residency plan's rank_row_intervals (the real ownership map)"""
        if not RESIDENCY.exists():
            self.skipTest("no residency receipt")
        mats = {m["key"]: m for m in json.loads(RESIDENCY.read_text())["matrices"] if m["layer"] == 0}
        for mat, n in (("w1", 2304), ("w3", 2304), ("w2", 5120)):
            m = mats[f"layers.0.ffn.experts.*.{mat}.weight"]
            self.assertEqual((m["experts"], m["source_rows"]), (384, n))
            self.assertEqual([list(x) for x in m["rank_row_intervals"]], N.W.even(n))

    def test_routed_records_per_die(self):
        """routed B: same base on every rank (local row 0), m = the rank's own rows, expert stride = image rows"""
        rows = {"w13": 2 * N.expert_rows(2304), "w2": N.expert_rows(5120)}
        self.assertEqual(rows, {"w13": 48, "w2": 54})
        for slot in range(6):
            for i, mat, n in ((slot, "w13", 2304), (7 + slot, "w2", 5120)):
                bases = set()
                for r in range(N.TP):
                    b = self.recs[r][i].desc["B"]
                    ent, ex, row, _ = self.man.find(b.base)
                    lo, hi = N.W.even(n)[r]
                    self.assertEqual(ent["key"], f"layers.0.ffn.experts.{mat}")
                    self.assertEqual((ex, row, b.indexed), (0, 0, 1))
                    self.assertEqual(b.m, (2 if mat == "w13" else 1) * (hi - lo))
                    self.assertEqual(b.dyn_mul, rows[mat] * b.stride)
                    self.assertEqual(ent["experts"] * ent["estride"], 384 * rows[mat] * b.stride)
                    bases.add(b.base)
                self.assertEqual(len(bases), 1)

    def test_wrows_reads_the_ranks_rows(self):
        wrows = N.ds_units(self.model, self.man, Golden())["_wrows"]
        w2 = next(e for e in self.man.ent if e["key"] == "layers.0.ffn.experts.w2")
        for r in (0, 1, 2, 47, 95):
            lo, hi = N.W.even(5120)[r]
            got = wrows(w2, 383, 0, hi - lo, 0, 8, 0, rank=r).q
            np.testing.assert_array_equal(got[:, 0], np.arange(lo, hi) * 8 + 200000 + 383000000)
            with self.assertRaises(N.MC.Fault):          # the 54th image row exists only on 54-row ranks
                wrows(w2, 383, 0, hi - lo + 1, 0, 8, 0, rank=r)

    def test_full_model_expert_image_fits_the_stack(self):
        """43 layers (40 + 3 MTP) of per-die routed experts fit stack 2 with room for the rest of the weights;
        the old whole-matrix image does not fit even 3 layers"""
        man = N.Manifest()
        for L in range(43):
            man.place(f"layers.{L}.ffn.experts.w13", 2 * N.expert_rows(2304), 5120, "fp4", 384, lines=True)
            man.place(f"layers.{L}.ffn.experts.w2", N.expert_rows(5120), 2304, "fp4", 384, lines=True)
        self.assertLess(man.cur - N.WBASE, 5 * GiB)          # 4.22 GiB (whole-matrix: 9.4 GiB a layer)
        old = N.Manifest()
        with self.assertRaisesRegex(N.MC.Fault, "physical bytes"):
            for L in range(43):
                old.place(f"layers.{L}.ffn.experts.w13", 4608, 5120, "fp4", 384, lines=True)
                old.place(f"layers.{L}.ffn.experts.w2", 5120, 2304, "fp4", 384, lines=True)
        self.assertLess(L, 3)

    def test_physical_stack_bound(self):
        self.assertEqual(N.MAN_END, N.WBASE + N.STACK_BYTES)
        man = N.Manifest()
        man.cur = N.WBASE + N.STACK_BYTES - 4096
        with self.assertRaises(N.MC.Fault):
            man.place("over", 1, 8192, "fp8")
        saved = N.MAN_END
        try:                                   # a stale window cannot admit bytes past the stack: place() asserts
            N.MAN_END = 94 * GiB
            with self.assertRaisesRegex(AssertionError, "physical bytes"):
                man.place("over", 1, 8192, "fp8")
        finally:
            N.MAN_END = saved
        with self.assertRaisesRegex(AssertionError, "physical bytes"):
            N.Manifest().place_at("fixed_over", N.STACK_BYTES - 64, 4, 32, "fp8")
        e = N.Manifest().place_at("fixed_ok", N.KBASE, 4, 32, "fp8")
        self.assertEqual(e["base"], N.KBASE)


if __name__ == "__main__":
    unittest.main()
