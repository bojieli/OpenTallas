import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from opentallas.roofline import (  # noqa: E402
    CimCellAccounting,
    Technology,
    taalas_hc1_anchor,
)
from opentallas.schema import ModelProfile  # noqa: E402

TECH = Technology.load(ROOT / "configs/hardware/technology.json")
WIDTH = TECH.graded("rom", "cim_bits_per_cell")
LLAMA = ModelProfile.load(ROOT / "configs/models/anchors/llama-3.1-8b.json")


@pytest.mark.parametrize("bits,cells", [(3.0, 1), (4.0, 1), (6.0, 2), (8.0, 2), (16.0, 4)])
def test_each_element_takes_its_own_nibble_cells(bits, cells):
    assert CimCellAccounting(bits, WIDTH).cells_per_weight() == cells


def test_block_scales_pack_at_cell_width():
    # MXFP4: 4-bit elements plus 8-bit scales per 32 weights is 4 bits per cell.
    mx = CimCellAccounting(4.0, WIDTH, scale_bits=0.25)
    assert mx.cells_per_weight() == pytest.approx(1.0625)
    assert mx.bits_per_cell().value == pytest.approx(4.0)


def test_hc1_mixture_is_a_three_six_blend():
    # 3.5 average bits of a 3/6 mixture is one sixth 6-bit weights.
    mix = CimCellAccounting(3.5, WIDTH, hc1_mixture=True)
    assert mix.cells_per_weight() == pytest.approx(7 / 6)
    with pytest.raises(Exception):
        CimCellAccounting(7.0, WIDTH, hc1_mixture=True).cells_per_weight()


def test_legacy_path_is_per_bit_and_cells_scale_both_densities_together():
    per_bit = TECH.rom_bits_per_mm2_for("N6", "per_stream").value
    per_bit_bw = TECH.rom_read_bytes_s_per_mm2_for("N6", "per_stream").value
    cells = CimCellAccounting(4.0, WIDTH)
    assert TECH.rom_bits_per_mm2_for("N6", "per_stream", cells).value == pytest.approx(4 * per_bit)
    assert TECH.rom_read_bytes_s_per_mm2_for("N6", "per_stream", cells).value == pytest.approx(
        4 * per_bit_bw
    )
    # Storage-plus-MAC cells are the reference and never take the cell rule.
    assert TECH.rom_bits_per_mm2_for("N6", "batched", cells).value == TECH.rom_bits_per_mm2("N6").value


def test_hc1_gate_fails_per_bit_and_passes_per_weight_cell():
    assert not taalas_hc1_anchor(TECH, LLAMA, per_bit_cim=True).passed
    check = taalas_hc1_anchor(TECH, LLAMA)
    assert check.passed and 1.0 < check.ratio < 2.0
