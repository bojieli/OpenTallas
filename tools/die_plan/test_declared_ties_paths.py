"""DIE-S81-92 / KIT-OPS-6 11-15: DeclaredTies rows may carry 'paths' (regexes on the bound cell path): per-instance ties."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dead_inputs as DI  # noqa: E402

ROW = dict(types=["t1"], module="m", port="d", bits=[0, 7], value="0", proof="bench")


def test_module_wide_row_ties_every_instance():
    D = DI.DeclaredTies({"declared_ties": [dict(ROW)]})
    assert D.allows("t1", "m", "d", 3, 0) and D.allows("t1", "m", "d", 3, 0, "top/u_pbuf_mem")
    assert not D.allows("t2", "m", "d", 3, 0) and not D.allows("t1", "m", "d", 8, 0) and not D.allows("t1", "m", "d", 3, 1)


def test_per_path_row_ties_only_matching_instances():
    D = DI.DeclaredTies({"declared_ties": [dict(ROW, paths=[r"u_dead_lane\d+$"])]})
    assert D.allows("t1", "m", "d", 3, 0, "top/u_dead_lane2")
    assert not D.allows("t1", "m", "d", 3, 0, "top/u_pbuf_mem")          # u_pbuf_mem must not be tied
    assert not D.allows("t1", "m", "d", 3, 0)                              # no path given: a per-path row never matches


def test_malformed_rows_still_refused():
    with pytest.raises(ValueError):
        DI.DeclaredTies({"declared_ties": [dict(ROW, extra=1)]})
    with pytest.raises(ValueError):
        DI.DeclaredTies({"declared_ties": [dict(ROW, value="2")]})


def test_bind_passes_the_cell_path():
    s = (Path(__file__).resolve().parent / "bind.py").read_text()
    assert "pn, i, s[1], self.F.cells[ci].path)" in s
