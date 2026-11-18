"""HALO-1 follow-up: a halo ring must not cover fixed cells (endcaps / tapcells) or DPL-0004 stops the kit at 3_5."""
import shutil
import subprocess
from pathlib import Path

import pytest

import gen_phys as GP

SRC = Path(__file__).with_name("macro_halo_carve.tcl")
needs_tclsh = pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh")


def carve(tmp_path, rect, cells):
    f = tmp_path / "t.tcl"
    f.write_text(f"source {SRC}\nforeach r [mhc_carve {{{rect}}} {{{cells}}}] {{ puts $r }}\n")
    out = subprocess.run(["tclsh", str(f)], capture_output=True, text=True, check=True).stdout
    return [tuple(int(v) for v in ln.split()) for ln in out.splitlines() if ln.strip()]


def area(rs):
    return sum((c - a) * (d - b) for a, b, c, d in rs)


@needs_tclsh
def test_no_fixed_cell_keeps_the_ring(tmp_path):
    assert carve(tmp_path, "0 0 100 50", "{200 0 210 10}") == [(0, 0, 100, 50)]


@needs_tclsh
def test_endcap_column_over_many_rows_is_one_cut(tmp_path):
    # left strip of a ring: 4 rows, each with an endcap at x 40..50 -> one piece left of the column, one right of it
    cells = " ".join(f"{{40 {y} 50 {y + 10}}}" for y in (0, 10, 20, 30))
    assert sorted(carve(tmp_path, "0 0 100 40", cells)) == [(0, 0, 40, 40), (50, 0, 100, 40)]


@needs_tclsh
def test_pieces_never_cover_a_cell_and_cover_everything_else(tmp_path):
    cells = [(10, 0, 20, 10), (60, 10, 70, 20), (95, 15, 120, 30), (-5, 35, 5, 45)]
    rs = carve(tmp_path, "0 0 100 40", " ".join("{%d %d %d %d}" % c for c in cells))
    for a, b, c, d in rs:
        assert 0 <= a < c <= 100 and 0 <= b < d <= 40
        for x0, y0, x1, y1 in cells:
            assert not (c > x0 and a < x1 and d > y0 and b < y1)
    clipped = 10 * 10 + 10 * 10 + 5 * 15 + 5 * 5
    assert area(rs) == 100 * 40 - clipped


def test_kit_gets_the_post_tapcell_hook_only_with_a_halo_row():
    src = Path(GP.__file__).read_text()
    assert "export POST_TAPCELL_TCL = /work/macro_halo_carve.tcl" in src
    assert GP.macro_halo_ring({"hard_cores": [{"inst": "a", "halo_um": 4.32}]})
    assert not GP.macro_halo_ring({"hard_cores": [{"inst": "a", "halo_um": 0}, {"inst": "b"}]})
