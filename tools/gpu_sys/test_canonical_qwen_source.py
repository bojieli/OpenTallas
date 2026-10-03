"""Compiler integration tests; stub kernels do not qualify model arithmetic."""
import gzip
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from canonical_qwen_source import (CanonicalKernel, CanonicalQwen, FAMILIES, KernelLaunch,
                                   LoweringError, NATIVE, emit, link)


def test_kernel():
    k = CanonicalKernel("compiler-control-test")
    k.const(1)
    k.exit()
    return k


def handlers(replace=None):
    def lower(op):
        return [KernelLaunch(rank, 0, test_kernel()) for rank in op.binding["participants"]]
    result = {family: lower for family in FAMILIES}
    if replace:
        result.update(replace)
    return result


class CanonicalLinkTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).resolve().parents[2] / NATIVE
        cls.source = CanonicalQwen.load(path)

    def test_real_source_all_pcs_and_bindings_reach_backend(self):
        seen = []
        def lower(op):
            seen.append(op.pc)
            self.assertIs(op.source, self.source)
            self.assertEqual(op.instruction["id"], op.pc)
            self.assertEqual(tuple(v["version"] for v in op.inputs), tuple(op.native["reads"]))
            self.assertEqual(tuple(v["version"] for v in op.outputs), tuple(op.native["writes"]))
            self.assertIn("exp", op.source.native["microcode"])
            return [KernelLaunch(r, 0, test_kernel()) for r in op.binding["participants"]]
        words, commands = link(self.source, {f: lower for f in FAMILIES})
        self.assertEqual(seen, list(range(1737)))
        self.assertEqual(set(c["pc"] for c in commands), set(range(1737)))
        self.assertEqual(len(words), 2 * len(commands))
        for c in commands:
            self.assertIs(c["provider_binding"], self.source.native["operations"][c["pc"]]["provider_binding"])
            self.assertTrue(all(commands[i]["pc"] < c["pc"] for i in c["wait_commands"]))

    def test_collective_ranks_launch_together_then_join(self):
        def lower(op):
            result = [KernelLaunch(r, 0, test_kernel()) for r in op.binding["participants"]]
            result += [KernelLaunch(r, 0, test_kernel(), phase=1) for r in op.binding["participants"]]
            return result
        _, commands = link(self.source, handlers({"EMBED": lower}))
        a, b, c, d = commands[:4]
        self.assertEqual((a["wait_commands"], b["wait_commands"]), ([], []))
        self.assertEqual(c["wait_commands"], [0, 1])
        self.assertEqual(d["wait_commands"], [0, 1])
        self.assertEqual(commands[4]["wait_commands"], [2, 3])

    def test_missing_handler_refuses_before_any_lowering(self):
        calls = []
        h = {f: lambda op: calls.append(op.pc) for f in FAMILIES if f != "PV"}
        with self.assertRaisesRegex(LoweringError, "missing canonical lowerers: PV"):
            link(self.source, h)
        self.assertEqual(calls, [])

    def test_empty_lowering_does_not_emit_partial_files(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "program"
            with self.assertRaisesRegex(LoweringError, "empty lowering"):
                emit(self.source, handlers({"MATRIX": lambda op: []}), out)
            self.assertFalse(out.exists())

    def test_address_overflow_is_not_masked(self):
        def lower(op):
            k = test_kernel()
            k.ins[0] = ("MOVI", k.ins[0][1], 0, 0, 1 << 32)
            return [KernelLaunch(0, 0, k)]
        with self.assertRaisesRegex(LoweringError, "immediate outside"):
            link(self.source, handlers({"EMBED": lower}))

    def test_emit_checks_before_historical_assembler_mask(self):
        k = CanonicalKernel("bounds")
        with self.assertRaisesRegex(LoweringError, "immediate outside"):
            k.emit("LDG", imm=1 << 32)
        with self.assertRaisesRegex(LoweringError, "register field outside"):
            k.emit("LDG", a=256)
        with self.assertRaisesRegex(LoweringError, "constant outside"):
            k.const(1 << 32)
        k.emit("UADDI", imm=-1)
        self.assertEqual(k.ins[0][4], 0xffffffff)

    def test_missing_rank_refused(self):
        with self.assertRaisesRegex(LoweringError, "missing participant rank"):
            link(self.source, handlers({"EMBED": lambda op: [KernelLaunch(0, 0, test_kernel())]}))

    def test_out_of_range_physical_sm_refused(self):
        with self.assertRaisesRegex(LoweringError, "incorrect physical SM"):
            link(self.source, handlers({"EMBED": lambda op: [KernelLaunch(0, 32, test_kernel())]}))

    def test_simultaneous_same_sm_refused(self):
        with self.assertRaisesRegex(LoweringError, "simultaneous kernels"):
            link(self.source, handlers({"EMBED": lambda op: [KernelLaunch(0, 0, test_kernel())] * 2}))

    def test_skipped_phase_refused(self):
        with self.assertRaisesRegex(LoweringError, "skipped launch phase"):
            link(self.source, handlers({"EMBED": lambda op: [KernelLaunch(0, 0, test_kernel(), 2)]}))

    def test_reduced_shape_refused(self):
        with patch.dict(self.source.program["config"], hidden_size=256):
            with self.assertRaisesRegex(LoweringError, "reduced or different model"):
                CanonicalQwen(self.source.native)

    def test_changed_home_refused(self):
        op = self.source.native["operations"][0]
        with patch.dict(op["provider_binding"]["inputs"], {op["reads"][0]: ["wrong-home"]}):
            with self.assertRaisesRegex(LoweringError, "changed homes"):
                CanonicalQwen(self.source.native)

    def test_mutated_source_refused(self):
        # Small wrong source fails the hash before any lowering or execution.
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "wrong.json.gz"
            with gzip.open(path, "wt") as f:
                json.dump({"operations": []}, f)
            with self.assertRaisesRegex(LoweringError, "source hash mismatch"):
                CanonicalQwen.load(path)


if __name__ == "__main__":
    unittest.main()
