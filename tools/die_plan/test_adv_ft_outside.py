import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_ft_outside as A  # noqa: E402


def _t(y):
    return {"outline_um": [100.0, 100.0], "ft_slots": [{"name": "ft7", "bit_site_cell_um": [1.4, 0.27],
            "bit_sites_um": [[[10.0, 20.0]], [[10.0, y]]], "regs_um": [[10.0, 20.0], [10.0, y]]}]}


def test_inside_passes():
    assert A.findings({"partition_types": {"a": _t(99.0)}}, "p") == []


def test_mutant_outside_reported():
    f = A.findings({"partition_types": {"a": _t(100.5)}}, "p")
    assert len(f) == 1 and "ft7" in f[0] and "1 site" in f[0] and "1 reg" in f[0]


def test_site_height_counts():
    assert A.findings({"partition_types": {"a": _t(99.9)}}, "p")      # 99.9 + 0.27 > 100
