import itertools
import origin_raw as O

C = [("rst_n_t4", (500.0, 10.0)), ("rst_n_t1", (20.0, 10.0)), ("rst_n_t10", (20.0, 10.0)), ("rst_n_t4", (500.0, 10.0))]


def test_plan_value_wins():
    assert O.pick_origin_raw(C, (0, 0), "rst_n_t4") == ("rst_n_t4", "plan")


def test_unknown_plan_value_warns_and_uses_rule():
    net, how = O.pick_origin_raw(C, (0, 0), "rst_n_t99")
    assert net == "rst_n_t1" and how == "plan-unknown"


def test_nearest_ties_by_natural_name():
    assert O.pick_origin_raw(C, (0, 0)) == ("rst_n_t1", "nearest")      # t1 and t10 tie on distance: t1 < t10 naturally


def test_dict_order_mutant():
    """every visit order of the bands gives the same node (the old next(iter(...)) did not)"""
    for perm in itertools.permutations(C):
        assert O.pick_origin_raw(list(perm), (0, 0))[0] == "rst_n_t1"
        assert O.pick_origin_raw(list(perm), None)[0] == "rst_n_t1"
    assert len({O.pick_origin_raw(list(p), (0, 0), legacy_first=True)[0] for p in itertools.permutations(C)}) > 1


def test_unsited_and_empty():
    assert O.pick_origin_raw([("rst_n_t3", None), ("rst_n_t2", None)], (0, 0)) == ("rst_n_t2", "name")
    assert O.pick_origin_raw([], (0, 0)) == (None, "none")


def test_check_compares_plan_with_rule():
    assert O.check("rst_n_t1", C, (0, 0))[0] and not O.check("rst_n_t4", C, (0, 0))[0]


def test_empty_candidates_fall_back_to_nearest_tree_node():
    fb = [("rst_n_t7", (400.0, 0.0)), ("rst_n_t2", (30.0, 0.0))]
    assert O.pick_origin_raw([], (0, 0), fallback=fb) == ("rst_n_t2", "fallback-nearest")
    assert O.pick_origin_raw([], None, fallback=fb) == (None, "none")


def test_band_reset_site_and_plan_candidates():
    t = {"outline_um": (100.0, 200.0), "buses": [{"name": "i_a", "face": "W", "window_um": [10, 30]}, {"name": "i_b", "face": "N", "window_um": [40, 60]}],
         "clock": {"landing_contract": {"bands": {"i_b": {}, "i_a": {}, "i_nogeom": {}}}}}
    taps = [(5.0, 25.0), (50.0, 195.0)]
    assert O.band_reset_site(t, "i_a", taps) == (0, [5.0, 25.0])
    assert O.band_reset_site(t, "i_b", taps) == (1, [50.0, 195.0])
    assert O.band_reset_site(t, "i_nogeom", taps) is None
    assert O.plan_candidates(t, taps) == [("rst_n_t0", (5.0, 25.0)), ("rst_n_t1", (50.0, 195.0))]
    assert O.band_reset_site(t, "i_a", [])[0] == 0
