"""DIE-HBM-10: rc_slice (opt-in) -- the default rc abstract is unchanged; W/C/E slices tile 8501.76 um on the 8.64 lattice,
each with its own clk/rst_n in its middle window and exactly its PCs' pins."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import hbm_phy_gen as G  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def test_default_rc_views_byte_identical(tmp_path):
    s = G.generate_rc(tmp_path)
    ref = ROOT / "physical/asap7_memory_macros" / s["name"]
    for f in (f"{s['name']}.lef", f"{s['name']}_bb.v", f"{s['name']}_tt.lib"):
        assert (tmp_path / s["name"] / f).read_bytes() == (ref / f).read_bytes(), f


def test_slices_tile_on_lattice(tmp_path):
    ws = []
    for lo, hi in ((0, 7), (8, 23), (24, 31)):
        s = G.generate_rc_slice(tmp_path, lo, hi)
        w = s["footprint"]["width_um"]; ws.append(w)
        assert abs(w / 8.64 - round(w / 8.64)) < 1e-9
        n = hi - lo + 1
        assert s["pins"]["signal_pins"] == 2 + n * (328 + 257)
        assert s["footprint"]["height_um"] == G.rc_full_geometry()[1]
        lef = (tmp_path / s["name"] / f"{s['name']}.lef").read_text()
        assert lef.count("  PIN clk\n") == 1 and lef.count("  PIN rst_n\n") == 1
        win = s["pins"]["pseudo_channel_window_um"]
        x = float(lef.split("  PIN clk\n")[1].split("RECT ")[1].split()[0])
        assert int(x // win) == n // 2
    assert [round(w, 2) for w in ws] == [2125.44, 4250.88, 2125.44]
    assert round(sum(ws), 2) == 8501.76


def test_slice_rejects_split_channel():
    import pytest
    with pytest.raises(SystemExit):
        G.generate_rc_slice(None, 1, 8)
