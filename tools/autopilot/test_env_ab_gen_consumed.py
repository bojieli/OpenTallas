"""GEN-CONSUMED-1122: OT_GRT_CONG_ITERS is consumed as GLOBAL_ROUTE_ARGS -congestion_iterations N, not as an OT_* export."""
import env_provenance as E

REC = {"wave_env": {}, "env": {"OT_GRT_CONG_ITERS": "50"}, "ab": {"keys": ["OT_GRT_CONG_ITERS"]}}
CFG_OK = "export GLOBAL_ROUTE_ARGS = -congestion_report_iter_step 5 -verbose -congestion_iterations 50\n"
CFG_BAD = "export GLOBAL_ROUTE_ARGS = -congestion_report_iter_step 5 -verbose -congestion_iterations 10\n"


def test_cong_iters_consumed_via_global_route_args():
    assert E.ab_not_consumed(REC, E.config_ot(CFG_OK), CFG_OK) == []


def test_cong_iters_other_value_still_refused():
    nc = E.ab_not_consumed(REC, E.config_ot(CFG_BAD), CFG_BAD)
    assert [k for k, _, _ in nc] == ["OT_GRT_CONG_ITERS"]


def test_cong_iters_missing_refused_and_old_call_unchanged():
    assert [k for k, _, _ in E.ab_not_consumed(REC, {}, "")] == ["OT_GRT_CONG_ITERS"]
    assert [k for k, _, _ in E.ab_not_consumed(REC, {})] == ["OT_GRT_CONG_ITERS"]


def test_default_30_needs_no_flag():
    rec = dict(REC, env={"OT_GRT_CONG_ITERS": "30"})
    assert E.ab_not_consumed(rec, {}, "") == []
