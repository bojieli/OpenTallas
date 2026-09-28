"""The ISA EGATHER must use each 32-column Engram scale block."""
from types import SimpleNamespace
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import hdc_isa_v41 as I  # noqa: E402
import hdc_program_v41 as P  # noqa: E402


def test_isa_egather_uses_per_32_column_scales():
    machine = P.Machine.__new__(P.Machine)
    machine.m = SimpleNamespace(engram=SimpleNamespace(layer_ids=[0]))
    machine.lay = SimpleNamespace(
        ecodes=np.full((2, 64), 0x38, dtype=np.uint8),  # E4M3 value 1.0
        eexp=np.array([[0, 1], [2, 3]], dtype=np.uint8),
    )
    machine.eh = [np.array([0, 1], dtype=np.int64)]
    machine.vm = np.zeros(128, dtype=np.float32)
    machine.xu(dict(xu_op=I.XU_EGATHER, xu_layer=0, xu_src=0, xu_dst=0))
    np.testing.assert_array_equal(machine.vm,
                                  np.repeat(np.array([1, 2, 4, 8], dtype=np.float32), 32))
