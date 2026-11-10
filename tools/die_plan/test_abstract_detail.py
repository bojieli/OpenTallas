"""abstract_detail: only OBS above the PG pin layer is replaced; everything else stays byte-identical."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import abstract_detail as A

BASE = """VERSION 5.8 ;
MACRO core
  CLASS BLOCK ;
  SIZE 100 BY 50 ;
  PIN a
    DIRECTION INPUT ;
    USE SIGNAL ;
    PORT
      LAYER M5 ;
        RECT  1 49.5 1.05 50 ;
    END
  END a
  PIN VSS
    DIRECTION INOUT ;
    USE GROUND ;
    PORT
      LAYER M5 ;
        RECT  10 1 10.12 49 ;
    END
  END VSS
  PIN VDD
    DIRECTION INOUT ;
    USE POWER ;
    PORT
      LAYER M5 ;
        RECT  12 1 12.12 49 ;
    END
  END VDD
  OBS
    LAYER M1 ;
     RECT  0 0 100 50 ;
    LAYER M5 ;
     RECT  0 0 100 50 ;
    LAYER M6 ;
     RECT  0 0 100 50 ;
    LAYER M7 ;
     RECT  0 0 100 50 ;
  END
END core
"""

DETAIL_OBS = """  OBS
    LAYER M1 ;
     RECT  0 0 3 3 ;
    LAYER M6 ;
     RECT  20 20 30 20.1 ;
     RECT  40 5 60 5.1 ;
    LAYER M7 ;
     RECT  50 0 50.2 50 ;
  END
END core
"""


def _detail(tmp_path, base=BASE):
    head = base.split("  OBS\n")[0]
    p = tmp_path / "detail.lef"
    p.write_text(head + DETAIL_OBS)
    return p


def test_default_layers_are_above_pg_pin_layer():
    assert A.default_layers(BASE.splitlines(True)) == ["M6", "M7"]


def test_splice_keeps_pins_and_lower_obs(tmp_path):
    b = tmp_path / "base.lef"
    b.write_text(BASE)
    out = tmp_path / "new.lef"
    rc = A.main(["splice", "--base", str(b), "--detail", str(_detail(tmp_path)), "--out", str(out)])
    assert rc == 0
    new = out.read_text()
    assert new.split("  OBS\n")[0] == BASE.split("  OBS\n")[0]
    assert "LAYER M1 ;\n     RECT  0 0 100 50 ;" in new  # lower layer stays blanket
    assert "RECT  20 20 30 20.1 ;" in new and "RECT  50 0 50.2 50 ;" in new
    m6 = new.split("LAYER M6 ;")[1].split("LAYER M7")[0]
    assert "0 0 100 50" not in m6
    assert A.main(["check", "--base", str(b), "--new", str(out)]) == 0


def test_check_rejects_pin_change(tmp_path):
    b = tmp_path / "base.lef"
    b.write_text(BASE)
    bad = tmp_path / "bad.lef"
    bad.write_text(BASE.replace("RECT  10 1 10.12 49", "RECT  10 1 10.12 48"))
    assert A.main(["check", "--base", str(b), "--new", str(bad)]) == 1


def test_splice_flags_detail_from_other_odb(tmp_path):
    b = tmp_path / "base.lef"
    b.write_text(BASE)
    other = _detail(tmp_path, BASE.replace("SIZE 100 BY 50", "SIZE 100 BY 51"))
    assert A.main(["splice", "--base", str(b), "--detail", str(other), "--out", str(tmp_path / "n.lef")]) == 1


def test_clear_pins_cuts_own_metal_and_near_wire_only():
    base = """  PIN a
    DIRECTION INPUT ;
    USE SIGNAL ;
    PORT
      LAYER M4 ;
        RECT 0 1 0.084 1.024 ;
    END
  END a
  PIN VSS
    USE GROUND ;
    PORT
      LAYER M4 ;
        RECT 5 5 6 6 ;
    END
  END VSS
""".splitlines(keepends=True)
    det = {"M4": ["        RECT 0.06 1 0.2 1.024 ;\n",   # own stub: only the part under the pin leaves
                  "        RECT 0.1 1.05 0.3 1.07 ;\n",  # neighbour 26 nm away, x from 0.1: inside the 0.048 grow
                  "        RECT 5.5 5.5 5.6 5.6 ;\n",    # under a PG pin: untouched
                  "        RECT 3 3 4 4 ;\n"],
           "M5": ["        RECT 0 1 0.084 1.024 ;\n"]}
    new, rep = A.clear_pins(det, base, 0.048, ["M4"])
    r4 = [tuple(float(v) for v in l.split()[1:5]) for l in new["M4"]]
    assert (5.5, 5.5, 5.6, 5.6) in r4 and (3, 3, 4, 4) in r4
    assert (0.132, 1, 0.2, 1.024) in r4                     # stub keeps what is beyond the grown box
    assert (0.132, 1.05, 0.3, 1.07) in r4
    assert rep["M4"]["rects_cut"] == 2 and rep["M4"]["overlap_own_pin"] == 1
    assert new["M5"] == det["M5"]                           # no pin on M5: untouched


# ---- DIE-QC-97 11-10: pin access windows (DRT-0073 class: centre clock pin on M5 under blanket M5-M7) ----
CK = """VERSION 5.8 ;
MACRO core
  CLASS BLOCK ;
  SIZE 100 BY 50 ;
  PIN ck
    DIRECTION INPUT ;
    USE SIGNAL ;
    PORT
      LAYER M5 ;
        RECT  50 25 50.048 25.48 ;
    END
  END ck
  PIN a
    DIRECTION INPUT ;
    USE SIGNAL ;
    PORT
      LAYER M4 ;
        RECT  0 10 0.084 10.024 ;
    END
  END a
  PIN VSS
    DIRECTION INOUT ;
    USE GROUND ;
    PORT
      LAYER M5 ;
        RECT  10 1 10.12 49 ;
    END
  END VSS
  OBS
    LAYER M4 ;
     RECT  0 0 100 50 ;
    LAYER M5 ;
     RECT  0 0 100 50 ;
    LAYER M6 ;
     RECT  0 0 100 50 ;
    LAYER M7 ;
     RECT  0 0 100 50 ;
  END
END core
"""
HEAD = CK.split("  OBS\n")[0]


def _lef(tmp_path, name, obs):
    """a detail export of the same ODB: same header/pins, OBS = {layer: [rect]}"""
    body = "".join("    LAYER %s ;\n" % l + "".join("     RECT  %s %s %s %s ;\n" % r for r in rs) for l, rs in obs.items())
    p = tmp_path / name
    p.write_text(HEAD + "  OBS\n" + body + "  END\nEND core\n")
    return p


# bloat-1 detail: an inflated M6 wire covers the whole ck pin; M7 one wire beside it
B1 = {"M4": [(0, 0, 100, 50)], "M5": [(0, 0, 100, 50)], "M6": [(49, 24.9, 51, 25.6), (0, 40, 100, 40.1)],
      "M7": [(50.3, 0, 50.35, 50)]}
# exact (bloat-0) export: the real M6 wire is only the strip at y 25.40-25.432, the rest over ck is free
B0 = {"M4": [(0, 0, 100, 50)], "M5": [(0, 0, 100, 50)], "M6": [(49.5, 25.4, 50.6, 25.432), (0, 40, 100, 40.032)],
      "M7": [(50.32, 0, 50.336, 50)]}


def _rects(text, layer):
    body = text.split("  OBS\n")[1].split("LAYER %s ;" % layer)[1].split("LAYER")[0].split("  END")[0]
    return [tuple(float(v) for v in ln.split()[1:5]) for ln in body.splitlines() if ln.strip().startswith("RECT")]


def test_access_report_blanket_centre_pin_has_none_edge_pin_does():
    rep = A.access_report(CK.splitlines(True))
    assert rep["top_layer"] == "M7"
    assert rep["pins"]["a"]["mode"] == "edge" and rep["pins"]["a"]["ok"]
    ck = rep["pins"]["ck"]
    assert not ck["ok"] and ck["missing"] == ["M6", "M7"] and ck["landing"] is None


def test_access_report_closed_pocket_is_not_access():
    """QC-FAIL-22 ckhole form: an M6 hole over ck under a blanket M7 lands a via (pin access passes) but cannot leave"""
    lines = CK.replace("    LAYER M6 ;\n     RECT  0 0 100 50 ;\n",
                       "    LAYER M6 ;\n     RECT  0 0 100 24 ;\n     RECT  0 26.48 100 50 ;\n"
                       "     RECT  0 24 49 26.48 ;\n     RECT  51.048 24 100 26.48 ;\n").splitlines(True)
    ck = A.access_report(lines)["pins"]["ck"]
    assert ck["landing"] is not None and ck["missing"] == ["M7"] and not ck["ok"]


def test_window_puts_exact_metal_back_and_check_recomputes(tmp_path):
    b = tmp_path / "base.lef"
    b.write_text(CK)
    out, rec = tmp_path / "new.lef", tmp_path / "receipt.json"
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = A.main(["splice", "--base", str(b), "--detail", str(_lef(tmp_path, "d1.lef", B1)), "--out", str(out),
                     "--layers", "M6", "--bloat-factor", "1", "--pin-window-um", "1.0",
                     "--window-detail", str(_lef(tmp_path, "d0.lef", B0))])
    rec.write_text(buf.getvalue())
    r = json.loads(buf.getvalue())
    assert rc == 0 and r["check_ok"], r["problems"]
    w = r["pin_window"]["windows"]["ck"]
    assert w["rect"] == [49.0, 24.0, 51.048, 26.48] and w["layers"] == ["M6", "M7"] and w["layer"] == "M5"
    new = out.read_text()
    assert new.split("  OBS\n")[0] == CK.split("  OBS\n")[0]          # pins / SIZE / PG untouched
    assert _rects(new, "M5") == [(0, 0, 100, 50)]                       # the pin's own layer is never cut
    m6 = _rects(new, "M6")
    assert (49, 24.9, 51, 25.6) not in m6                               # the bloated wire left the window ...
    assert (49.5, 25.4, 50.6, 25.432) in m6                             # ... its exact metal came back
    assert (0, 40, 100, 40.1) in m6                                     # detail outside the window unchanged
    m7 = _rects(new, "M7")                                              # kept blanket layer: cut + exact metal
    assert (0, 0, 100, 24) in m7 and (50.32, 24, 50.336, 26.48) in m7 and (0, 0, 100, 50) not in m7
    assert A.access_report(new.splitlines(True))["pins"]["ck"]["ok"]
    assert A.main(["check", "--base", str(b), "--new", str(out), "--layers", "M6", "--receipt", str(rec)]) == 0
    assert A.main(["check", "--base", str(b), "--new", str(out), "--layers", "M6"]) == 1   # M7 changed: needs receipt


def test_check_rejects_window_off_pin_or_extra_cut(tmp_path):
    b = tmp_path / "base.lef"
    b.write_text(CK)
    out = tmp_path / "new.lef"
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        A.main(["splice", "--base", str(b), "--detail", str(_lef(tmp_path, "d1.lef", B1)), "--out", str(out),
                "--layers", "M6", "--pin-window-um", "1.0", "--window-detail", str(_lef(tmp_path, "d0.lef", B0))])
    win = json.loads(buf.getvalue())["pin_window"]
    base, new = CK.splitlines(True), out.read_text().splitlines(True)
    assert A.check(base, new, ["M6"], win)[0]
    moved = json.loads(json.dumps(win))
    moved["windows"]["ck"]["rect"] = [20, 20, 30, 30]
    assert not A.check(base, new, ["M6"], moved)[0]
    low = json.loads(json.dumps(win))
    low["windows"]["ck"]["layers"] = ["M5", "M6", "M7"]
    assert not A.check(base, new, ["M6"], low)[0]
    hacked = out.read_text().replace("     RECT  0 0 100 24 ;\n", "     RECT  0 0 100 23 ;\n", 1)
    assert not A.check(base, hacked.splitlines(True), ["M6"], win)[0]  # M7 outside the window must stay the base


def test_no_window_when_the_detail_already_gives_access(tmp_path):
    b = tmp_path / "base.lef"
    b.write_text(CK)
    out = tmp_path / "new.lef"
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = A.main(["splice", "--base", str(b), "--detail", str(_lef(tmp_path, "d0.lef", B0)), "--out", str(out),
                     "--layers", "M6,M7", "--pin-window-um", "1.0", "--window-detail", str(tmp_path / "d0.lef")])
    r = json.loads(buf.getvalue())
    assert rc == 0 and r["pin_window"]["windows"] == {} and r["check_ok"]


def test_window_needs_the_exact_export(tmp_path):
    b = tmp_path / "base.lef"
    b.write_text(CK)
    import pytest
    with pytest.raises(SystemExit):
        A.main(["splice", "--base", str(b), "--detail", str(_lef(tmp_path, "d1.lef", B1)), "--out",
                str(tmp_path / "n.lef"), "--layers", "M6", "--pin-window-um", "1.0"])


def test_export_plan_names_the_pins_without_access():
    p = A.export_plan(CK.splitlines(True))
    assert p["needed"] and p["layers"] == ["M6", "M7"]
    assert p["pin_window"]["pins"] == ["ck"] and p["pin_window"]["top_layer"] == "M7"
    assert A.export_plan(BASE.splitlines(True))["pin_window"] is None   # edge pin only
