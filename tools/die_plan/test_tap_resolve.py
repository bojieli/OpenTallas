"""tap_resolve: criterion (insertion spread between material taps, not sink count) and the append-only solver."""
import random
import tap_resolve as TR


def test_log_parse_takes_last_iteration():
    log = ("OT_TAP_BALANCE it0 target 250: clk=420(397-523,4161) clk_t14=96(86-128,409)\n"
           "noise\nOT_TAP_BALANCE it2 target 250: clk=420(397-523,4161) clk_t14=233(223-282,409) clk_t6=532(453-602,22199)\n")
    m = TR.parse_cts_log(log)
    assert m["clk_t14"] == (233.0, 223.0, 282.0, 409) and m["clk_t6"][3] == 22199


def test_criterion_is_spread_not_sink_count():
    # one tap clocks nearly everything (QC sle_hc0 class): one tree, no split whatever its size
    one = TR.criterion({"clk": 480.0, "clk_t1": 250.0}, {"clk": 13082, "clk_t1": 40}, 80.0)
    assert one["verdict"] == "OK" and one["material_taps"] == 1
    # lepe class: several material taps at different insertions
    bad = TR.criterion({"clk": 420.0, "clk_t6": 532.0, "clk_t9": 233.0}, {"clk": 4161, "clk_t6": 22199, "clk_t9": 1333}, 80.0)
    assert bad["verdict"] == "SPLIT" and bad["spread_ps"] == 299.0 and bad["slowest"] == "clk_t6"
    # many taps, equal insertion: fine even when the loads differ
    assert TR.criterion({"a": 250.0, "b": 262.0}, {"a": 9000, "b": 900}, 80.0)["verdict"] == "OK"


def test_solver_appends_legal_taps_and_keeps_existing():
    rnd = random.Random(7)
    pts = [(rnd.uniform(300, 700), rnd.uniform(50, 350)) for _ in range(6000)] + [(rnd.uniform(20, 60), rnd.uniform(20, 60)) for _ in range(300)]
    exist = [(17.28, 17.28), (982.0, 17.28)]
    box = (450.0, 150.0, 550.0, 250.0)          # a macro in the middle of the cluster
    legal = TR.make_legal((1000.0, 400.0), 8.64, [box])
    added = TR.solve(exist, pts, legal, target=1400, radius=160.0)
    assert added and all(legal(x, y, []) for x, y in added)
    assert not any(box[0] < x < box[2] and box[1] < y < box[3] for x, y in added)
    s = TR.tap_stats(exist + added, pts, 160.0)
    assert max(q[0] for q in s) <= 1400 and sum(q[1] for q in s) < TR.FAR_MIN
    assert s[0][0] >= 300 and len(added) <= 12   # the corner cluster stays on its own tap; no tap explosion


def test_solver_is_a_no_op_when_taps_fit():
    pts = [(100.0 + i % 10, 100.0 + i // 10) for i in range(200)]
    assert TR.solve([(105.0, 110.0)], pts, TR.make_legal((400.0, 400.0), 8.64, []), target=1400, radius=160.0) == []
