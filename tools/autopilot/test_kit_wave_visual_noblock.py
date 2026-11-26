"""Placement render and exact required review policy at the route boundary."""
import pytest

import kit_wave as K

POLICY = {"event": "J", "items": ["t1"], "required": True}
CFG = {"dies": {"s81": {"event": "J", "review_before_route": POLICY}}}
ROW = {"die": "s81", "event": "J", "item": "t1", "attempt": 1, "kit": "epyc9:/k", "status": "PASS",
       "geom_verdict": "PASS", "geom_dir": "epyc9:/k/geom"}


@pytest.fixture
def verdict(monkeypatch):
    box = {"v": None}
    monkeypatch.setattr(K, "exact_kit_visual_verdict", lambda *_a, **_k: box["v"])
    monkeypatch.setattr(K.FG, "stops_off_die", lambda *_a, **_k: True)
    return box


@pytest.mark.parametrize("gv", ["PASS", "PASS-COND"])
def test_required_review_blocks_after_auto_geom_pass(verdict, gv):
    row = dict(ROW, geom_verdict=gv)
    for pending in (None, "PENDING"):
        verdict["v"] = pending
        assert K.route_hold_reason(CFG, row).startswith("WAIT-VISUAL")
    verdict["v"] = "ISSUES"
    assert K.route_hold_reason(CFG, row).startswith("WAIT-FORM")
    verdict["v"] = "OK"
    assert K.route_hold_reason(CFG, row) is None


def test_event_advisory_review_keeps_routing_after_auto_geom_pass(verdict):
    verdict["v"] = "ISSUES"
    cfg = {"dies": {"legacy": {"event": "J", "review_before_route": dict(POLICY, required=False)}}}
    row = dict(ROW, die="legacy")
    assert K.route_hold_reason(cfg, row) is None
    assert row["visual_pending"].startswith("WAIT-VISUAL (advisory)")


def test_bad_verdict_still_holds(verdict):
    verdict["v"] = "BAD"
    assert K.required_route_hold(CFG, dict(ROW)).startswith("WAIT-FORM")
    assert K.route_hold_reason(CFG, dict(ROW)).startswith("WAIT-FORM")


@pytest.mark.parametrize("geom", [{"geom_verdict": "FAIL"}, {"geom_verdict": None}, {"geom_dir": None}])
def test_no_auto_geom_pass_keeps_required_hold(verdict, geom):
    row = dict(ROW, **geom)
    assert K.required_route_hold(CFG, row).startswith("WAIT-VISUAL")
    verdict["v"] = "ISSUES"
    assert K.required_route_hold(CFG, dict(row)).startswith("WAIT-FORM")


def test_route_mode_visual_hold(monkeypatch):
    monkeypatch.setattr(K, "minimal_profile", lambda: False)
    monkeypatch.setattr(K, "verdict_applies", lambda *_a, **_k: True)
    box = {}
    monkeypatch.setattr(K, "visual_verdicts", lambda: box)
    cfg = {"dies": {"hbm": {}}}
    rec = dict(ROW, die="hbm", kind="type")            # hbm keeps holds unless its own AUTO-GEOM passed
    assert K.visual_hold(cfg, dict(rec)) is None
    assert K.visual_hold(cfg, dict(rec, geom_verdict="PASS-COND")) is None      # granted geom FAIL still has its render
    assert K.visual_hold(cfg, dict(rec, geom_verdict=None)).startswith("WAIT-VISUAL")
    box[("hbm", "t1", 1)] = "ISSUES"
    assert K.visual_hold(cfg, dict(rec)) is None
    assert K.visual_hold(cfg, dict(rec, geom_dir=None)).startswith("WAIT-FORM")
    box[("hbm", "t1", 1)] = "BAD"
    assert K.visual_hold(cfg, dict(rec)).startswith("WAIT-FORM")


def test_placed_geometry_defers_routing_only_in_captured_takeover_spec():
    spec = {"item": "t1", "event": "J", "geom_mem_gb": 24}
    checkpoint = "/exact/3_place.odb"
    inherited = K.placed_geom_check(spec, checkpoint, "10x20")
    assert inherited["grt"] is True
    assert "--grt-deferred" not in inherited["rules_args"]

    placed = K.placed_geom_check(dict(spec, geom_grt_deferred=True), checkpoint, "10x20")
    assert placed["grt"] is False
    assert placed["odb"] == checkpoint
    assert placed["rules_args"] == ["--all-kits", "--outline", "10x20", "--title",
                                    "t1 KIT-WAVE J 3_place", "--grt-deferred"]
    assert placed["grt_wall_s"] == inherited["grt_wall_s"]


@pytest.mark.parametrize("takeover", [False, True])
def test_required_viewed_is_for_the_current_attempt_and_kit(monkeypatch, tmp_path, takeover):
    if takeover:
        monkeypatch.setenv("AP_REQUIRE_VIEWED_WAVE_ROUTE", "1")
    else:
        monkeypatch.delenv("AP_REQUIRE_VIEWED_WAVE_ROUTE", raising=False)
    monkeypatch.setattr(K.Path, "home", lambda: tmp_path)
    review = tmp_path / "coord/lanes/GEOM-REVIEW.md"
    review.parent.mkdir(parents=True)
    review.write_text(
        "- 2026-11-23 07:10 PST GEOM VERDICT [LANE viewed] s81/t1 a1: GOOD kit=epyc9:/k\n"
        "- 2026-11-23 07:11 PST GEOM VERDICT [LANE viewed] s81/t1 a1: GOOD kit=epyc8:/k\n"
        "- 2026-11-23 07:11 PST GEOM VERDICT [LANE viewed] s81/t1 a2: GOOD kit=epyc9:/k\n"
        "- 2026-11-23 07:11 PST GEOM VERDICT [AUTO-VISUAL-REVIEW] s81/t1 a1: GOOD kit=epyc9:/k\n"
    )
    build_start = K.verdict_line_ts("- 2026-11-23 07:11 PST ") + 17
    row = dict(ROW, started=build_start)
    cfg = {"dies": {"s81": {"event": "J"}}} if takeover else CFG
    assert K.route_hold_reason(cfg, row).startswith("WAIT-VISUAL")
    if not takeover:
        assert K.route_hold_reason(cfg, dict(row, event="older")) is None
        assert K.route_hold_reason(cfg, dict(row, item="unscoped")).startswith("WAIT-VISUAL")

    with review.open("a") as out:
        out.write("- 2026-11-23 07:12 PST GEOM VERDICT [LANE viewed] s81/t1 a1: ISSUES kit=epyc9:/k\n")
    assert K.route_hold_reason(cfg, row).startswith("WAIT-FORM")

    with review.open("a") as out:
        out.write("- 2026-11-23 07:15 PST GEOM VERDICT [LANE viewed] s81/t1 a1: OK kit=epyc9:/k\n")
    assert K.route_hold_reason(cfg, row) is None
    assert not K.strict_wave_route_review("hbm")


def test_geometry_only_private_goal_defers_global_route():
    checkpoint = "/scratch/kit/run/results/asap7/top/base/3_place.odb"
    spec = dict(item="top", event="first", geom_mem_gb=8, private={"lane": "TEST"}, goal="geom")
    for config in (
        K.placed_geom_check(spec, checkpoint, "10x20"),
        K.placed_geom_check(dict(spec, goal="route"), checkpoint, "10x20", "geom"),
    ):
        assert config["grt"] is False
        assert "--grt-deferred" in config["rules_args"]
    routed = K.placed_geom_check(spec, checkpoint, "10x20", "route")
    assert routed["grt"] is True


@pytest.mark.parametrize("die", ["s81", "s81_head", "qwen_compute", "qwen_kvsys"])
def test_current_active_wave_type_requires_view_without_event_flag(verdict, die):
    cfg = {"dies": {die: {"event": "new-plan"}}}
    row = dict(ROW, die=die, event="new-plan")
    assert K.route_hold_reason(cfg, row).startswith("WAIT-VISUAL")
    assert K.route_hold_reason(cfg, dict(row, event="old-plan")) is None
    assert K.route_hold_reason(cfg, dict(row, kind="core")) is None
    verdict["v"] = "GOOD"
    assert K.route_hold_reason(cfg, row) is None


@pytest.mark.parametrize("goal", ["place", "cts", "grt", "route", "auto", "finish"])
def test_private_active_type_defers_all_geometry_grt_until_review(goal):
    spec = dict(die="s81", kind="type", private={"lane": "TEST"}, item="top", event="current", geom_mem_gb=8)
    assert not K.placed_geom_check(spec, "/exact/3_place.odb", "10x20", goal)["grt"]


def test_current_explicit_route_hold_survives_visual_good_and_stops_off(verdict):
    hold = {"id": "known-pg", "route": True, "plan_sha": "p", "items": ["t1"],
            "release": [], "reason": "repair exact PG continuity", "owner": "QC"}
    die = {"event": "J", "plan_sha256": "p", "hold_records": [hold],
           "route_hold_items": {"*": "old advisory"}}
    cfg = {"stops_off": True, "dies": {"s81": die}}
    row = dict(ROW)
    assert K.required_route_hold(cfg, row).startswith("WAIT-VISUAL")
    verdict["v"] = "GOOD"
    assert K.required_route_hold(cfg, row).startswith("WAIT-STRUCTURE: route hold known-pg:")
    assert K.route_hold_reason(cfg, row) == K.required_route_hold(cfg, row)
    assert K.route_hold_reason(cfg, dict(row, item="unrelated")) is None
    assert K.route_hold_reason(cfg, dict(row, event="old")) is None
    assert K.route_hold_reason(cfg, dict(row, kind="core")) is None
    for change in ({"plan_sha": "retired"}, {"release": ["proof:PG"]}, {"migrated": True}):
        die["hold_records"] = [dict(hold, **change)]
        assert K.route_hold_reason(cfg, row) is None
    die["hold_records"] = [hold]
    cfg["_lane_activity"] = {"QC": 1}
    cfg["_now"] = 7 * 3600
    assert K.route_hold_reason(cfg, row) is None


def test_scoped_route_record_is_authorable_under_stops_off():
    import kit_wave_edit as KWE
    orig = {"stops_off": True, "dies": {"s81": {"event": "J", "plan_sha256": "p"}}}
    hold = {"id": "pg", "route": True, "plan_sha": "p", "items": ["t1"], "release": []}
    with_hold = {"stops_off": True, "dies": {"s81": dict(orig["dies"]["s81"], hold_records=[hold])}}
    assert KWE.noop_hold_record_problems(orig, with_hold) == []
    hold["plan_sha"] = "retired"
    assert len(KWE.noop_hold_record_problems(orig, with_hold)) == 1
