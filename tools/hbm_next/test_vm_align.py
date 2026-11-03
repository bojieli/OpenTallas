#!/usr/bin/env python3
"""TOK-HBM-1/TOK-HBM-2 11-02: opt-in VM/HBM-home congruence (four-stack ruling A).  Default stays 8 words
(value phases) and dense packing (expert regions)."""
import inspect, sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import vm_value_phase as VP
import vm_canonical_stream as VC
import vm_expert_entry as VE


class VmAlignTest(unittest.TestCase):
    def test_defaults_unchanged(self):
        self.assertEqual(inspect.signature(VP.build).parameters["align"].default, 8)
        self.assertEqual(inspect.signature(VC.compile_stream).parameters["vm_align"].default, 8)

    def test_align_must_be_whole_sectors(self):
        for bad in (0, 4, 12, 63):
            with self.assertRaisesRegex(ValueError, "whole number of sectors"):
                VP.build([], 0, 0, 0, 0, None, [], align=bad)


    def test_expert_default_dense(self):
        self.assertIsNone(inspect.signature(VE.layout).parameters["align"].default)
        self.assertIsNone(inspect.signature(VE.lower).parameters["align"].default)

    def test_expert_align_must_be_whole_regions(self):
        for bad in (8, 16, 48, 100):
            with self.assertRaisesRegex(ValueError, "whole number of 32-word regions"):
                VE.layout([], 0, 0, align=bad)

    def test_stream_passes_align_to_expert_only_when_opted_in(self):
        src = inspect.getsource(VC.compile_stream)
        self.assertIn("expert_lower(records,source,end,align=None if vm_align==8 else vm_align)", src)


if __name__ == "__main__":
    unittest.main()
