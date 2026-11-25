import raw_origin_sync as R


def _plan():
    br = lambda n, last: dict(name=n, stages=[dict(original="rst_rl_73"), dict(original=last)], consumers=[n])
    return {"partition_types": {"v1": {"clock": {"landing_raw_branches": [br("origin", "rst_n_t1"), br("fstart:a", "rst_n_t1"), br("x", "rst_n_t9")]}},
                                "v2": {"clock": {"landing_raw_branches": [br("origin", "rst_n_t1")]}}}}


def test_parse_and_rewrite_only_planned_node():
    p = _plan()
    errs = ["EMIT v1: v1: origin reset phase/equation differs: rst_n_t4 != rst_n_t1", "EMIT v2: other failure"]
    assert R.parse_errors(errs) == [("v1", "origin", "rst_n_t4", "rst_n_t1")]
    rep = R.sync(p, errs)
    last = [b["stages"][-1]["original"] for b in p["partition_types"]["v1"]["clock"]["landing_raw_branches"]]
    assert last == ["rst_n_t4", "rst_n_t4", "rst_n_t9"]
    assert rep["v1"]["changed"] == 2 and not rep["v1"]["unfixed"]
    assert p["partition_types"]["v2"]["clock"]["landing_raw_branches"][0]["stages"][-1]["original"] == "rst_n_t1"


def test_unmatched_planned_node_is_reported():
    p = _plan()
    rep = R.sync(p, ["EMIT v1: v1: origin reset phase/equation differs: rst_n_t4 != rst_n_t7"])
    assert rep["v1"]["unfixed"]


def test_types_filter():
    p = _plan()
    assert R.sync(p, ["EMIT v1: v1: origin reset phase/equation differs: rst_n_t4 != rst_n_t1"], {"v2"}) == {}
