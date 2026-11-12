"""LAND-RING-2 11-12: opt-in OT_CLAND_STRIP_DENS (plan budgets.cland_strip_density(_types)) sets each N/S ring_ff face
strip's row pitch from the ring's own FIRM flop density, clamped to the band depth (QC 11-12 census: rows-1 strips are
~2.6 flops/um2 and carry the type's GRT overflow; the same rings at rows 2-3 route)."""
import re
import shutil

import pytest

import gen_phys as GP
import schema as S
import test_landing_pinslot as T

tcl = pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh unavailable")
DEEP = "2 0 3.2 5.4"          # 1.2 um wide (one column pitch of DFFHQNx1 family), 20 rows deep; pins on the N face


def _run(monkeypatch, dens, **kw):
    monkeypatch.delenv("OT_CLAND_STRIP_ROWS", raising=False)
    if dens is None:
        monkeypatch.delenv("OT_CLAND_STRIP_DENS", raising=False)
    else:
        monkeypatch.setenv("OT_CLAND_STRIP_DENS", dens)
    return T.run("1", tag=kw.pop("tag", "ring:i+ff"), pin_xy=kw.pop("pin_xy", T.NPIN), **kw)


def _rows(placed):
    cols = {}
    for x, y in placed.values():
        cols.setdefault(x, []).append(y)
    return {x: sorted(v) for x, v in cols.items()}


@tcl
def test_unset_and_zero_are_byte_identical(monkeypatch):
    base, out0 = _run(monkeypatch, None, rect=DEEP)
    zero, outz = _run(monkeypatch, "0", rect=DEEP)
    assert base == zero and out0 == outz and "strip density" not in out0


@tcl
def test_low_density_ring_keeps_its_rows(monkeypatch):
    base, _ = _run(monkeypatch, None, rect=DEEP)
    same, out = _run(monkeypatch, "100", rect=DEEP)
    assert same == base
    assert re.search(r"OT_CLAND strip density ring:i\+x\+ff: [\d.]+ flops/um2 at rows 1, target 100 -> rows 1 \(was 1, needs 1,", out), out


@tcl
def test_dense_strip_spreads_over_the_band_depth(monkeypatch):
    base, _ = _run(monkeypatch, None, rect=DEEP)
    new, out = _run(monkeypatch, "1.0", rect=DEEP)
    m = re.search(r"flops/um2 at rows 1, target 1.0 -> rows (\d+) \(was 1, needs (\d+), band fits (\d+)", out)
    assert m and int(m.group(1)) == min(int(m.group(2)), int(m.group(3))) and int(m.group(1)) > 1, out
    assert len(new) == T.BITS * T.SLOTS
    T._no_overlap(new)
    r = int(m.group(1))
    for ys in _rows(new).values():
        # each column's flops sit r rows apart, from the N (pin) edge down
        assert all(b - a == 270 * r for a, b in zip(ys, ys[1:])), ys
    # deeper strip, same columns under the pins
    assert min(y for x, y in new.values()) < min(y for x, y in base.values())
    assert sorted({x for x, y in new.values()}) == sorted({x for x, y in base.values()})


@tcl
def test_rows_clamped_to_what_the_band_fits(monkeypatch):
    shallow = "2 2.7 3.2 5.4"   # 10 rows: the rows-1 strip already fills most of it
    base, _ = _run(monkeypatch, None, rect=shallow)
    new, out = _run(monkeypatch, "0.01", rect=shallow)
    m = re.search(r"-> rows (\d+) \(was 1, needs (\d+), band fits (\d+)", out)
    assert m and int(m.group(2)) > int(m.group(3)) and int(m.group(1)) == int(m.group(3)), out
    assert len(new) == T.BITS * T.SLOTS
    assert all(2700 <= y <= 5400 - 270 for x, y in new.values())


@tcl
def test_asked_strip_rows_is_a_floor(monkeypatch):
    monkeypatch.setenv("OT_CLAND_STRIP_ROWS", "3")
    monkeypatch.setenv("OT_CLAND_STRIP_DENS", "100")
    _, out = T.run("1", tag="ring:i@2.0+x+ff", pin_xy=T.NPIN, rect=DEEP)
    assert re.search(r"-> rows (\d+) \(was (\d+),", out) and "strip rows ring:i@2.0+x+ff:" in out
    m = re.search(r"-> rows (\d+) \(was (\d+),", out)
    assert int(m.group(1)) == int(m.group(2)) >= 2


def test_gen_phys_budget_resolution():
    assert GP._cland_strip_density({}, "sle_ctl__cla4f6f12f") is None
    assert GP._cland_strip_density({"cland_strip_density": 0}, "t") is None
    assert GP._cland_strip_density({"cland_strip_density": 1}, "t") == 1.0
    b = {"cland_strip_density_types": {"sle_hc1": 0.8, "keep": 0}, "cland_strip_density": 1.0}
    assert GP._cland_strip_density(b, "sle_hc1__cl22c1ff36") == 0.8
    assert GP._cland_strip_density(b, "keep") is None          # 0 opts the type out of the plan-wide value
    assert GP._cland_strip_density(b, "other") == 1.0
    assert GP._cland_strip_density({"cland_strip_density_types": {"a": 1}}, "b") is None


def test_schema_declares_the_knobs():
    props = S.SCHEMA["properties"]["budgets"]["properties"]
    assert props["cland_strip_density"] == {"type": "number", "minimum": 0}
    assert props["cland_strip_density_types"]["additionalProperties"]["minimum"] == 0
