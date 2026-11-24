"""count_hourly: a row only from a fresh scan, one row per hour per count, a gap stays a gap."""
import json
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import count_hourly as CH

NOW = time.mktime(time.strptime("2026-11-04 07:05", "%Y-%m-%d %H:%M"))


def cache(gen):
    d = lambda n: {str(i): ["r"] for i in range(n)}
    return {"generated": gen, "plans": {
        "a": {"die": "s81", "signed_designs": d(37), "signed_types": {}},
        "b": {"die": "s81_head", "signed_designs": d(4), "signed_types": d(5)},
        "c": {"die": "qwen_compute", "signed_designs": d(12)},
        "e": {"die": "qwen_kvsys", "signed_designs": d(20)},
        "f": {"die": "hbm", "signed_designs": d(12)}}}


@pytest.fixture
def env(tmp_path, monkeypatch):
    (tmp_path / "lanes").mkdir()
    monkeypatch.setattr(CH, "COORD", tmp_path)
    monkeypatch.setattr(CH, "CACHE", tmp_path / "cache.json")
    monkeypatch.setattr(CH, "STATE", tmp_path / "state")
    return tmp_path


def rows(env):
    p = env / CH.RATE
    return p.read_text().splitlines() if p.exists() else []


def put(env, gen):
    (env / "cache.json").write_text(json.dumps(cache(gen)))


def test_row_shape_matches_the_hand_rows():
    assert CH.rate_row(cache(0), "2026-11-04 05:36") == "2026-11-04 05:36 90 s81=37 head=4+5t qc=12 kv=20 hbm=12 any=90 auto"


def test_stale_cache_is_scanned_then_row_committed(env):
    put(env, NOW - 3600)
    calls = []

    def scan():
        calls.append(1)
        put(env, NOW - 1)
        return 0
    assert CH.run(NOW, scan, lambda: calls.append(2) or 0) == 0
    assert calls == [1, 2] and rows(env) == ["2026-11-04 07:05 90 s81=37 head=4+5t qc=12 kv=20 hbm=12 any=90 auto"]


def test_fresh_cache_no_second_scan(env):
    put(env, NOW - 600)
    assert CH.run(NOW, lambda: pytest.fail("scanned"), lambda: 0) == 0
    assert len(rows(env)) == 1


@pytest.mark.parametrize("rc,refresh", [(1, False), (124, False), (0, False)])
def test_failed_or_silent_scan_leaves_a_true_gap(env, rc, refresh):
    put(env, NOW - 3600)
    assert CH.run(NOW, lambda: rc, lambda: pytest.fail("committed")) == 1
    assert rows(env) == []


def test_same_counts_in_the_hour_is_not_a_new_row(env):
    put(env, NOW - 60)
    (env / CH.RATE).write_text("2026-11-04 07:01 90 s81=37 head=4+5t qc=12 kv=20 hbm=12 any=90\n")
    assert CH.run(NOW, None, lambda: pytest.fail("committed")) == 0
    assert len(rows(env)) == 1


def test_changed_counts_in_the_hour_is_a_new_row(env):
    put(env, NOW - 60)
    (env / CH.RATE).write_text("2026-11-04 07:01 89 s81=36 head=4+5t qc=12 kv=20 hbm=12 any=90\n")
    assert CH.run(NOW, None, lambda: 0) == 0
    assert len(rows(env)) == 2


def test_stop_file(env):
    put(env, NOW - 3600)
    (env / "state").mkdir()
    (env / "state" / "count_hourly.stop").write_text("")
    assert CH.run(NOW, lambda: pytest.fail("scanned"), lambda: pytest.fail("committed")) == 0


def test_older_free_text_rows_do_not_break_it(env):
    put(env, NOW - 60)
    (env / CH.RATE).write_text("time\tdie\tsigned_types\tsigned_cores\n2026-11-03 18:34 PST\tS81 0/205\n")
    assert CH.run(NOW, None, lambda: 0) == 0
    assert len(rows(env)) == 3


def test_force_scans_even_a_fresh_cache(env):
    put(env, NOW - 60)
    calls = []
    assert CH.run(NOW, lambda: calls.append(1) or 0, lambda: 0, force=True) == 0
    assert calls == [1]


def test_degraded_scan_writes_no_row(env):
    put(env, NOW - 60)
    (env / CH.RATE).write_text("2026-11-04 06:05 390 s81=64+42t head=5+23t qc=70+24t kv=62+6t hbm=90+4t auto\n")
    assert CH.run(NOW, None, lambda: pytest.fail("committed")) == 1
    assert len(rows(env)) == 1


def test_any_plan_extra_counts_old_plan_names_not_variants():
    c = {"plans": {"q": {"die": "qwen_compute", "plan_types": {"coll_ucie": "qfd_coll"}, "hard_cores": ["m1"], "signed_types": {"coll_ucie": ["r"]}}}}
    rows = [("qwen_compute", "coll_ucie__legalrows_1117", "t"), ("qwen_compute", "sta_old_a", "t"), ("qwen_compute", "sta_old_a__a2_1117", "t"),
            ("qwen_compute", "m1", "c"), ("s81", "ot_s81_svc_x", "c")]
    assert CH.any_plan_extra(c, rows) == 3          # sta_old_a, ot_s81_svc_x retired; m1 = current-plan hard core, not signed = deferred


def test_headline_splits_deferred_resign_from_retired_plan():
    row = CH.rate_row(cache(0), "2026-11-04 05:36", {"defer": {"s81": 1}, "retired": {"qc": 2, "s81": 2}})
    assert row.endswith("any=95 defer=s81:1 retired=qc:2,s81:2 auto")
    assert CH.headline(row) == "signed any plan 95 | current plan 90 | deferred re-sign 1 (s81 1) | retired-plan 4 (qc 2, s81 2)"
    assert CH.headline(CH.rate_row(cache(0), "2026-11-04 05:36")) == "signed any plan 90 | current plan 90 | deferred re-sign 0 | retired-plan 0"
    assert CH.last_total(row) == 90


def test_any_plan_extra_classifies_by_plan_name():
    c = cache(0)
    c["plans"]["a"].update(plan_types={"t_signed": "m1", "t_open": "m2"}, signed_types={"t_signed": ["r"]})
    rows = [("s81", "t_signed", "type"), ("s81", "t_open__a1_0101", "type"), ("s81", "m2", "type"), ("s81", "old_svc_x", "type"), ("qwen_compute", "gone", "type")]
    r = CH.any_plan_extra(c, rows, by_die=True)
    assert r == {"defer": {"s81": 1}, "retired": {"s81": 1, "qc": 1}}      # COUNT-PRIVATE-1124: module name m2 IS type t_open, counted once
    assert CH.any_plan_extra(c, rows) == 3


def test_repeat_run_in_the_hour_still_prints_the_summary(env, capsys):
    put(env, NOW - 60)
    (env / CH.RATE).write_text("2026-11-04 07:01 90 s81=37 head=4+5t qc=12 kv=20 hbm=12 any=90\n")
    assert CH.run(NOW, None, lambda: pytest.fail("committed")) == 0
    out = capsys.readouterr().out
    assert "already holds these counts" in out and "count_hourly: signed any plan" in out



def test_archive_element_alias_maps_misnamed_export(tmp_path):
    # ARCHIVE-ALIAS-1124: hd_tile exported as its record name hd_tile_htr_eco1124 is the signed hd_tile, not a retired design
    al = CH.load_element_alias()
    assert al.get(("s81_head", "hd_tile_htr_eco1124")) == "hd_tile"
    cache = {"plans": {"h": {"die": "s81_head", "plan_types": {"hd_tile": "ot_s81hd_tile_p"}, "signed_types": {"hd_tile": {}}}}}
    assert CH.any_plan_extra(cache, [("s81_head", "hd_tile_htr_eco1124", "t")]) == 0
    p = tmp_path / "a.tsv"
    p.write_text("die\tarchived_element\telement\treason\nqc\tx_bad\tx\tr\nshort\n")
    assert CH.load_element_alias(str(p)) == {("qc", "x_bad"): "x"}
    assert CH.load_element_alias(str(tmp_path / "missing.tsv")) == {}


def test_module_named_export_of_a_signed_type_is_not_deferred():
    # COUNT-PRIVATE-1124: ot_s81hd_ctl / qfd_qc_slw_sc / s81p_slice_station__t36 are the plan modules of signed types (18 double counts 11-24)
    c = {"plans": {"h": {"die": "s81_head", "plan_types": {"hd_ctl": "ot_s81hd_ctl"}, "signed_types": {"hd_ctl": ["r"]}}}}
    assert CH.any_plan_extra(c, [("s81_head", "ot_s81hd_ctl", "t"), ("s81_head", "ot_s81hd_ctl__a1_1117", "t")]) == 0


def _priv_cache():
    return {"plans": {"q": {"die": "qwen_compute", "plan_types": {"slw_fe_v1__clfe325744__cl08d14f0d": "qfd_fe_a", "sle_x__clfde1249e": "qfd_x",
                                                                  "coll_bare": "qfd_coll", "sle_y__pv41c959f3": "qfd_y"},
                            "signed_types": {"sle_y__pv41c959f3": ["r"]}, "signed_designs": {}}}}


def _u(el, odb="o1", src="AUTO-EXPORT-1118 intel1:/p/private/k/signoff/signoff.json"):
    return dict(die="qwen_compute", element=el, kind="t", odb_sha=odb, src=src)


def test_archived_private_signoff_counts_on_current_plan_once():
    c = _priv_cache()
    units = [_u("slw_fe_v1__clfe325744__cl08d14f0d"), _u("qfd_fe_a", "o2"), _u("sle_y__pv41c959f3", "o3")]
    c2, cr = CH.credit_archived(c, units, {}, [], [], alias={})
    assert [(d, t) for d, t, _ in cr] == [("qwen_compute", "slw_fe_v1__clfe325744__cl08d14f0d")]   # its module export is the same type; pv41 already signed
    assert "slw_fe_v1__clfe325744__cl08d14f0d" in c2["plans"]["q"]["signed_types"] and "slw_fe_v1__clfe325744__cl08d14f0d" not in c["plans"]["q"]["signed_types"]
    assert CH.rate_row(c2, "2026-11-24 12:05").startswith("2026-11-24 12:05 2 ")
    assert CH.any_plan_extra(c2, [(u["die"], u["element"], "t") for u in units]) == 0


def test_archived_credit_respects_revoked_hold_and_bare_names():
    c = _priv_cache()
    led = {"o1": ("intel1", "/p/private/k/signoff/signoff.json", "v1"), "o4": ("intel1", "/held/k/signoff/signoff.json", "v4")}
    units = [_u("sle_x__clfde1249e", "o1"), _u("coll_bare", "o5"), _u("slw_fe_v1__clfe325744__cl08d14f0d", "o4")]
    rev = [("sle_x__clfde1249e", "sha256:v1")]
    _, cr = CH.credit_archived(c, units, led, rev, ["intel1:/held/k"], alias={})
    assert cr == []                                      # PENDING-LEC by netlist sha; HOLD dir; a bare name is not proof of the current block
    _, cr = CH.credit_archived(c, [_u("sle_x__clfde1249e", "o9")], {}, rev, [], alias={})
    assert cr == []                                      # no ledger entry: netlist unknown, a revoked type stays out
    _, cr = CH.credit_archived(c, [_u("sle_x__clfde1249e", "o1")], led, [("sle_x__clfde1249e", "sha256:other")], [], alias={})
    assert len(cr) == 1                                  # another netlist of that type was revoked, this one counts
