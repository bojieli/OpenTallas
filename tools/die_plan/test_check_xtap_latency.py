"""XTAP-SWEEP-1 11-11: check.py xtap_latency (advisory WARN): unlocked ft hops between taps whose modeled source
latency differs by more than 50 ps."""
import sys
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check as C  # noqa: E402
import ft_xtap  # noqa: E402
import gen_phys  # noqa: E402
import schema as S  # noqa: E402

TAPS = [("clk", 100.0, 100.0), ("clk_t1", 500.0, 100.0)]


def _plan(tw, lockup=None, sites=None):
    clock = {}
    if tw is not None:
        clock["tap_window"] = tw
    if lockup is not None:
        clock["ft_hop_lockup"] = lockup
    slot = {"name": "ft5", "stations": 2, "width": 1}
    return types.SimpleNamespace(raw={"clock": clock}, types={"T": {"ft_slots": [slot], "outline_um": [600, 200]}},
                                 clock=clock, _sites=sites or [[(100.0, 100.0)], [(500.0, 100.0)]])


def _run(monkeypatch, P):
    monkeypatch.setattr(S, "tap_grid", lambda P_, tn: TAPS)
    monkeypatch.setattr(ft_xtap, "station_sites", lambda P_, tn, s: (P_._sites, 1))

    def pw(P_, tn, port):
        tab = ((P_.clock.get("tap_window") or {}).get("per_port_ps") or {}).get(tn) or {}
        return float(tab.get(port, P_.clock["tap_window"]["window_ps"]))
    monkeypatch.setattr(gen_phys, "port_window_ps", pw)
    monkeypatch.setattr(gen_phys, "tap_window_ps", lambda P_, tn=None: float(P_.clock["tap_window"]["window_ps"]))
    R = C.Report()
    summ = C.check_xtap_latency(P, R)
    return R, summ


def _tw(d_a, d_b):
    return {"window_ps": 160, "per_port_ps": {"T": {"clk": d_a, "clk_t1": d_b}}}


def test_delta_160_no_lockup_listed(monkeypatch):
    R, s = _run(monkeypatch, _plan(_tw(160, 0)))
    assert s["hops"] == 1 and s["worst_delta_ps"] == 160 and s["mode"] == "per_port"
    assert [i["level"] for i in R.items] == ["WARN", "WARN"] and not R.errors()
    assert "[xtap-count] 1 unlocked" in R.items[-1]["msg"] and "differs 160" in R.items[0]["msg"]


def test_delta_160_with_lockup_not_listed(monkeypatch):
    R, s = _run(monkeypatch, _plan(_tw(160, 0), {"types": ["T"], "xtap_flop": {"T": {"ft5": [0]}}}))
    assert s["hops"] == 0 and s["latch_only"] == 0
    assert R.items == []            # clean plan: no item, counts stay in the summary


def test_latch_only_counted_not_listed(monkeypatch):
    R, s = _run(monkeypatch, _plan(_tw(160, 0), {"types": ["T"]}))
    assert s["hops"] == 0 and s["latch_only"] == 1


def test_delta_40_not_listed(monkeypatch):
    R, s = _run(monkeypatch, _plan(_tw(40, 0)))
    assert s["hops"] == 0 and s["worst_delta_ps"] == 0


def test_same_tap_not_listed(monkeypatch):
    R, s = _run(monkeypatch, _plan(_tw(160, 0), sites=[[(100.0, 100.0)], [(120.0, 100.0)]]))
    assert s["hops"] == 0


def test_no_tap_model(monkeypatch):
    mode, hops, st = C.xtap_latency_hops(_plan(None))
    assert mode == "none" and hops == []


def test_flat_window_reports_mode(monkeypatch):
    R, s = _run(monkeypatch, _plan({"window_ps": 160}))
    assert s["mode"] == "flat" and s["hops"] == 0 and s["flat_xtap_hops"] == 1


# ---- tap sink cap (ERROR) ----
import taps as TP  # noqa: E402


def _cap_run(monkeypatch, n, clock=None):
    clock = clock or {}
    P = types.SimpleNamespace(types={"T": {"clock": clock, "outline_um": [600, 200]}})
    monkeypatch.setattr(S, "tap_grid", lambda P_, tn: TAPS)
    monkeypatch.setattr(TP, "sink_sites", lambda P_, tn: [(100.0, 100.0, 1.0)] * n + [(500.0, 100.0, 1.0)] * 10)
    R = C.Report()
    return R, C.check_tap_sink_cap(P, R)


def test_tap_3001_error(monkeypatch):
    R, s = _cap_run(monkeypatch, 3001)
    assert s["taps_over"] == 1 and s["worst"] == 3001
    e = R.errors()
    assert len(e) == 1 and "type T tap clk: 3001 clock sinks > cap 3000" in e[0]["msg"]


def test_tap_3000_clean(monkeypatch):
    R, s = _cap_run(monkeypatch, 3000)
    assert s["taps_over"] == 0 and not R.errors()


def test_tap_cap_from_plan_and_density(monkeypatch):
    R, s = _cap_run(monkeypatch, 1600, {"tap_mode": "density"})
    assert s["taps_over"] == 1                       # density cap 1500 (gen_phys._tap_cap)
    R, s = _cap_run(monkeypatch, 1600, {"tap_max_sinks": 2000})
    assert s["taps_over"] == 0


def test_tap_uncomputable_not_guessed(monkeypatch):
    P = types.SimpleNamespace(types={"T": {"clock": {}}})
    monkeypatch.setattr(S, "tap_grid", lambda P_, tn: TAPS)
    monkeypatch.setattr(TP, "sink_sites", lambda P_, tn: (_ for _ in ()).throw(ValueError("no sidecar")))
    R = C.Report()
    s = C.check_tap_sink_cap(P, R)
    assert s["uncomputable"] == 1 and s["taps_over"] == 0 and not R.errors()
