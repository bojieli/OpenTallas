"""Known defect, failing by design: the production V4.1 L0 program's softmax scale.

PC30 (L0.softmax SU scale + max) of results/rtl/hdc_v41x_fullshape_l0_program.hex is
M1_AIMM with imm1 = 0, so as encoded it multiplies every attention score by zero.
The golden scale is float32(512 ** -0.5) = 0x3d3504f3 (D = 512).  The placeholder
comes from tools/hdc_replay_v41.py, whose softmax emits `m1=I.M1_AIMM, imm1=0`
(shape only); the binder does not patch it.  Found by claude/w4-connected-l0,
whose live-chain gate (tools/v41_l0_live_chain.py) patches the word locally.

This test is strict-xfail: it starts to pass, and so fails the suite, when the
program is regenerated with the real scale, at which point the marker must be
removed.  The program is deliberately not fixed on the landing branch.
"""
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_isa_v41 as I  # noqa: E402

PROGRAM = ROOT / "results/rtl/hdc_v41x_fullshape_l0_program.hex"
SCALE_BITS = int(np.float32(512 ** -0.5).view(np.uint32))


def _pc30():
    words = [int(x, 16) for x in PROGRAM.read_text().split()]
    return I.decode(words[30], full_shape=True)


def test_pc30_is_the_softmax_max_op():
    d = _pc30()
    assert d["m1"] == I.M1_AIMM and d["red"] == I.RED_MAX
    assert SCALE_BITS == 0x3D3504F3


@pytest.mark.xfail(strict=True, reason="KNOWN DEFECT (TASKS.md): production L0 PC30 softmax scale imm1=0 "
                   "placeholder from tools/hdc_replay_v41.py; must be float32(512**-0.5)=0x3d3504f3")
def test_pc30_softmax_scale_is_inverse_sqrt_head_dim():
    assert _pc30()["imm1"] == SCALE_BITS
