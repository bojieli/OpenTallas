"""xdie_io.py: cross-die die-IO pairing (lane S81-HEAD)."""
import xdie_io as X


def _w(part, host=False, sig=26, pitch=150.0):
    d = dict(name="io_" + part, part=part, iface="serdes", signals=sig, sites=152, pitch_um=pitch)
    if host:
        d["host"] = True
    return d


def _row(i, cls, au, am, bu, bm, lanes=12):
    return dict(id=i, cls=cls, a_unit=au, a_macros=am, b_unit=bu, b_macros=bm, lanes_per_dir=str(lanes))


def test_pass_and_host():
    H = {p: _w(p, host=p.startswith("lk_HOST")) for p in ("lk_WN0", "lk_WN1", "lk_HOST0", "lk_HOST1")}
    S = {p: _w(p) for p in ("lk_WN2", "lk_WN3")}
    rows = [_row("1", "token_return", "H2", "lk_WN0+lk_WN1", "S000", "lk_WN2+lk_WN3"),
            _row("2", "host", "H0", "lk_HOST0+lk_HOST1", "host", "host NIC")]
    errs, warns, summ = X.check(rows, dict(H=H, S=S))
    assert errs == [] and summ["circuits_checked"] == 1


def test_missing_host_flag_lanes_pitch():
    H = {p: _w(p, pitch=100.0) for p in ("lk_WN0", "lk_WN1")}
    S = {"lk_WN2": _w("lk_WN2", host=True), "lk_X": _w("lk_X")}
    rows = [_row("1", "token_return", "H2", "lk_WN0+lk_WN1", "S000", "lk_WN2+lk_WN3", lanes=13)]
    errs, warns, _ = X.check(rows, dict(H=H, S=S))
    rules = {e["rule"] for e in errs}
    assert {"missing", "lanes", "pitch", "host"} <= rules
    assert any("lk_X" in w["msg"] for w in warns)


def test_xdie_io_in_band_host():
    S = {"lk_A": dict(part="lk_A", iface="serdes", signals=26, pitch_um=150.0, host="in_band"),
         "lk_B": dict(part="lk_B", iface="serdes", signals=26, pitch_um=150.0)}
    rows = [dict(id="c1", cls="stage_hop", a_unit="S1", b_unit="S2", a_macros="lk_B", b_macros="lk_A",
                 lanes_per_dir="6")]
    errs, warns, summ = X.check(rows, {"S": S})
    assert not errs and summ["roles"]["S"]["in_band_host_windows"] == ["lk_A"] and summ["roles"]["S"]["host_windows"] == []
    S["lk_B"]["host"] = True                                          # a dedicated host window without a host circuit
    errs, _, _ = X.check(rows, {"S": S})
    assert [e["rule"] for e in errs] == ["host"]
    S["lk_B"].pop("host")
    rows[0].update(a_macros="lk_B", b_macros="lk_B")                  # in-band window wired by no circuit
    errs, _, _ = X.check(rows, {"S": S})
    assert any("in-band host windows ['lk_A']" in e["msg"] for e in errs)
