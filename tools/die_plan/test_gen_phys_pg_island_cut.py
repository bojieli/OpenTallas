"""DIE-HEAD-5 PGCUT (opt-in partition_types.<t>.pg_island_cut): M6 PG strap cut windows over in-core island pins.
python3 -m pytest -q tools/die_plan/test_gen_phys_pg_island_cut.py"""
import copy
import filecmp
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys  # noqa: E402
import schema  # noqa: E402
from test_g2 import PAIR  # noqa: E402

# 20 x 10 macro: rst_n interior M5 pin, clk interior M5 pin, an edge M4 pin, an edge M5 pin, a PG pin
LEF = """MACRO core
  SIZE 20 BY 10 ;
  PIN rst_n
    DIRECTION INPUT ;
    USE SIGNAL ;
    PORT
      LAYER M5 ;
        RECT 5.0 3.0 5.192 3.192 ;
    END
  END rst_n
  PIN clk
    DIRECTION INPUT ;
    USE CLOCK ;
    PORT
      LAYER M5 ;
        RECT 12.0 6.0 12.192 6.192 ;
    END
  END clk
  PIN d
    DIRECTION INPUT ;
    PORT
      LAYER M4 ;
        RECT 0 4.0 0.1 4.024 ;
    END
  END d
  PIN q
    DIRECTION OUTPUT ;
    USE SIGNAL ;
    PORT
      LAYER M5 ;
        RECT 8.0 9.9 8.024 10.0 ;
    END
  END q
  PIN VDD
    USE POWER ;
    PORT
      LAYER M5 ;
        RECT 3.0 3.0 3.2 7.0 ;
    END
  END VDD
END core
"""


def _lef(d):
    p = Path(d) / "core.lef"
    p.write_text(LEF)
    return str(p)


def test_lef_interior_pins_only_interior_signal_m5():
    with tempfile.TemporaryDirectory() as d:
        pins, wh = gen_phys.lef_interior_pins(_lef(d))
    assert wh == (20.0, 10.0)
    assert pins == [("rst_n", (5.0, 3.0, 5.192, 3.192)), ("clk", (12.0, 6.0, 12.192, 6.192))]


def test_orient_rect():
    r = (5.0, 3.0, 5.192, 3.192)
    assert gen_phys._orient_rect(r, 20, 10, "R0") == r
    assert gen_phys._orient_rect(r, 20, 10, "MX") == (5.0, 10 - 3.192, 5.192, 7.0)
    assert gen_phys._orient_rect(r, 20, 10, "MY") == (20 - 5.192, 3.0, 15.0, 3.192)
    assert gen_phys._orient_rect(r, 20, 10, "R180") == (20 - 5.192, 10 - 3.192, 15.0, 7.0)


def test_cut_windows_placed_and_opt_in():
    with tempfile.TemporaryDirectory() as d:
        core = dict(inst="u_c", module="core", lef=_lef(d), origin_um=[100.0, 200.0], track_offset_um=[0.012, 0.036],
                    orient="MX")
        t = dict(outline_um=[400.0, 400.0], hard_cores=[core])
        P = SimpleNamespace(types={"hd": t})
        assert gen_phys.pg_island_cuts(P, "hd") == []                        # not opted in: nothing
        t["pg_island_cut"] = False
        assert gen_phys.pg_island_cuts(P, "hd") == []
        t["pg_island_cut"] = True
        cuts = gen_phys.pg_island_cuts(P, "hd")
    m, s = gen_phys.PG_CUT_MARGIN_UM, gen_phys.PG_CUT_SPACE_UM
    inst, pin, (x0, y0, x1, y1) = cuts[0]
    assert (inst, pin) == ("u_c", "rst_n")
    # MX: y -> 10 - y; placed at origin + track offset
    assert abs(x0 - (100.012 + 5.0 - m)) < 1e-6 and abs(x1 - (100.012 + 5.192 + m)) < 1e-6
    assert abs(y0 - (200.036 + 6.808 - s)) < 1e-6 and abs(y1 - (200.036 + 7.0 + s)) < 1e-6
    assert [c[1] for c in cuts] == ["rst_n", "clk"]
    tcl = gen_phys.pg_island_cut_tcl(cuts)
    assert tcl.count("\npgc_window ") == 2 and "odb::dbSBox_destroy" in tcl and "OT_PG_ISLAND_CUT windows=2" in tcl
    assert '"M6"' in tcl and "getWireShapeType" in tcl


def test_schema_accepts_flag():
    raw = copy.deepcopy(PAIR)
    raw["partition_types"]["fa"]["pg_island_cut"] = True
    schema.Plan(raw)


def _same_tree(a, b):
    c = filecmp.dircmp(a, b)
    assert not c.left_only and not c.right_only and not c.diff_files, (c.left_only, c.right_only, c.diff_files)
    for sub in c.common_dirs:
        _same_tree(Path(a) / sub, Path(b) / sub)


def test_kit_byte_identical_without_cut(monkeypatch):
    P0 = schema.Plan(copy.deepcopy(PAIR))
    raw = copy.deepcopy(PAIR)
    raw["partition_types"]["fa"]["pg_island_cut"] = True                    # opted in but no hard core LEF: no window
    P1 = schema.Plan(raw)
    with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
        gen_phys.write_type_kit(P0, "fa", a, [])
        gen_phys.write_type_kit(P1, "fa", b, [])
        _same_tree(Path(a) / "fa", Path(b) / "fa")
        assert "POST_PDN_TCL" not in (Path(a) / "fa" / "config.mk").read_text()
        assert not (Path(a) / "fa" / "pg_island_cut.tcl").exists()
    # with a window the kit carries the hook (after pdngen) and its Tcl
    monkeypatch.setattr(gen_phys, "pg_island_cuts", lambda P, tn, root=None: [("u", "rst_n", (1.0, 1.0, 2.0, 2.0))])
    with tempfile.TemporaryDirectory() as d:
        gen_phys.write_type_kit(P1, "fa", d, [])
        cfg = (Path(d) / "fa" / "config.mk").read_text()
        assert "export POST_PDN_TCL = /work/pg_island_cut.tcl" in cfg
        assert cfg.index("export PDN_TCL") < cfg.index("POST_PDN_TCL")
        assert "pgc_window 1.0000 1.0000 2.0000 2.0000" in (Path(d) / "fa" / "pg_island_cut.tcl").read_text()
