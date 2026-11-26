import landing_remap as LM
import origin_raw as OR


def _plan():
    br = lambda n, cons, last: dict(name=n, consumers=cons, stages=[dict(original="rst_rl_9"), dict(original=last)])
    t = {"outline_um": [100.0, 200.0], "buses": [{"name": "i_a", "face": "W", "window_um": [10, 30]}, {"name": "i_b", "face": "N", "window_um": [40, 60]}],
         "clock": {"tap_mode": "grid", "tap_um": [50.0, 100.0], "landing_origin_rect_um": [0, 0, 10, 10],
                   "landing_contract": {"bands": {"i_a": {}, "i_b": {}}},
                   "landing_raw_branches": [br("o", ["origin"], "rst_n_t1"), br("fs", ["fstart:x"], "rst_n_t1"), br("z", ["fstart:y"], "rst_n_t5")]}}
    return {"partition_types": {"T": t}}


def test_write_origin_raw_records_pick_and_moves_finals(monkeypatch):
    import clock_landings as CL
    monkeypatch.setattr(CL, "ring_taps", lambda plan, tn: [(5.0, 25.0), (50.0, 195.0)])
    monkeypatch.setattr(CL, "plan_origin_xy", lambda t, p=None: (0.0, 0.0))
    p = _plan()
    rec = LM.write_origin_raw(p, ["T"])
    ck = p["partition_types"]["T"]["clock"]
    assert ck["landing_origin_raw"] == "rst_n_t0" and rec["T"]["how"] == "nearest" and rec["T"]["was"] == "rst_n_t1"
    assert [b["stages"][-1]["original"] for b in ck["landing_raw_branches"]] == ["rst_n_t0", "rst_n_t0", "rst_n_t5"]
    assert rec["T"]["finals"] == 2


def test_written_value_is_what_the_bind_function_picks():
    cands = OR.plan_candidates(_plan()["partition_types"]["T"], [(5.0, 25.0), (50.0, 195.0)])
    ok, net, how = OR.check("rst_n_t0", cands, (0.0, 0.0))
    assert ok and net == "rst_n_t0"
