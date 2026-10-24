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
