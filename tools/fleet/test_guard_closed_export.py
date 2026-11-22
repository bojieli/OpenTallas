"""CLEAN-AGGR-R2 (COORD / FABLE-FLOW-2000 item 5): autopilot/closed units are kept until every signed / LOCAL_PASS record is exported, and never
retired while on hold (COUNT-REVOKED / open re-LEC).  LOCAL_PASS counts as signed for attempt dirs too."""
import hashlib, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ot_delete_guard as g


def unit(tmp, verdict="SIGNED", uid="abc123def456"):
    u = tmp / "claude" / "autopilot" / "closed" / "qwen_compute" / "slw_x__eb1e73448b"
    (u / "kit" / "signoff").mkdir(parents=True)
    raw = json.dumps({"verdict": verdict, "name": "dp_slw_x"}).encode()
    (u / "kit" / "signoff" / "signoff.json").write_bytes(raw)
    (u / "AUTOPILOT.json").write_text(json.dumps({"id": uid}))
    return u, hashlib.sha256(raw).hexdigest()


def test_signed_unexported_refused(tmp_path):
    u, sha = unit(tmp_path)
    assert "not exported" in g.closed_unit_refusal(str(u), exported=set(), hold=set())
    assert g.closed_unit_refusal(str(u), exported={sha}, hold=set()) is None


def test_local_pass_is_signed(tmp_path):
    u, sha = unit(tmp_path, "LOCAL_PASS_NEEDS_PARENT")
    assert "not exported" in g.closed_unit_refusal(str(u), exported=set(), hold=set())
    assert g.closed_unit_refusal(str(u), exported={sha}, hold=set()) is None


def test_unsigned_closed_unit_allowed(tmp_path):
    u, _ = unit(tmp_path, "NOT SIGNED")
    assert g.closed_unit_refusal(str(u), exported=set(), hold=set()) is None


def test_missing_or_stale_list_fails_closed(tmp_path):
    u, sha = unit(tmp_path)
    assert g.load_exported(str(tmp_path / "none.txt")) is None
    stale = tmp_path / "exp.txt"
    stale.write_text("# built %d\n%s\n" % (time.time() - 100 * 3600, sha))
    assert g.load_exported(str(stale)) is None
    fresh = tmp_path / "exp2.txt"
    fresh.write_text("# built %d\n%s\n" % (time.time(), sha))
    assert g.load_exported(str(fresh)) == {sha}
    g.EXPORTED_LIST = str(tmp_path / "none.txt")
    assert "missing or stale" in g.closed_unit_refusal(str(u), exported=None, hold=set())


def test_parent_of_closed_unit_checked(tmp_path):
    u, sha = unit(tmp_path)
    assert "not exported" in g.closed_unit_refusal(str(u.parent), exported=set(), hold=set())


def test_hold_by_id_and_name(tmp_path):
    u, sha = unit(tmp_path)
    assert "hold" in g.closed_unit_refusal(str(u), exported={sha}, hold={"abc123def456"})
    assert "hold" in g.closed_unit_refusal(str(u), exported={sha}, hold={"slw_x__eb1e73448b"})


def test_non_closed_target_untouched(tmp_path):
    d = tmp_path / "claude" / "lane"
    (d / "signoff").mkdir(parents=True)
    (d / "signoff" / "signoff.json").write_text('{"verdict": "SIGNED"}')
    assert g.closed_unit_refusal(str(d), exported=set(), hold=set()) is None


def test_attempt_signed_counts_local_pass(tmp_path):
    ad = tmp_path / "attempt_3"
    (ad / "gen" / "signoff").mkdir(parents=True)
    (ad / "gen" / "signoff" / "signoff.json").write_text('{"verdict": "LOCAL_PASS_NEEDS_PARENT"}')
    assert g.attempt_signed(str(ad))



def _attempt(tmp, rec, sub="kit/signoff_eco_1/signoff.json"):
    a = tmp / "claude" / "kw43-wave-1109n" / "runs" / "qwen_compute" / "kit-wave" / "qwen_compute" / "ev" / "items" / "sle_x" / "attempt_2"
    f = a / sub
    f.parent.mkdir(parents=True)
    raw = json.dumps(rec).encode()
    f.write_bytes(raw)
    return a, hashlib.sha256(raw).hexdigest()


def test_signed_unexported_attempt_refused_anywhere_clean_aggr_r3(tmp_path):
    a, sha = _attempt(tmp_path, {"verdict": "SIGNED", "host": "dear-crayfish"})
    assert "not exported" in g.signed_unexported_refusal(str(a), exported=set(), host="dear-crayfish")
    assert g.signed_unexported_refusal(str(a), exported={sha}, host="dear-crayfish") is None
    assert g.signed_unexported_refusal(str(a), exported=set(), host="other-host") is None        # a copy: its origin host keeps it


def test_sealed_return_final_odb_on_other_host_is_kept_until_export(tmp_path):
    # AP c7ce90ba4af9: hub producer, exact ECO checkpoint returned to epyc2.
    a, _ = _attempt(tmp_path, {"verdict": "NOT SIGNED"})
    odb = a / "kit" / "eco_1" / "run" / "results" / "asap7" / "x" / "base" / "6_final.odb"
    odb.parent.mkdir(parents=True)
    odb.write_bytes(b"routed")
    raw = json.dumps({"verdict": "SIGNED", "host": "tolerant-swine", "inputs": {"odb": str(odb)}}).encode()
    (a / "kit/signoff_eco_1/signoff.json").write_bytes(raw)
    sha = hashlib.sha256(raw).hexdigest()
    assert "not exported" in g.signed_unexported_refusal(str(a), exported=set(), host="dear-crayfish")
    assert g.signed_unexported_refusal(str(a), exported={sha}, host="dear-crayfish") is None

    # A metadata-only foreign copy, or a DB symlink to another target, is irrelevant here.
    odb.unlink()
    assert g.signed_unexported_refusal(str(a), exported=set(), host="dear-crayfish") is None
    external = tmp_path / "6_final.odb"
    external.write_bytes(b"other target")
    odb.symlink_to(external)
    assert g.signed_unexported_refusal(str(a), exported=set(), host="dear-crayfish") is None


def test_signed_copy_in_input_dir_and_unsigned_not_refused_clean_aggr_r3(tmp_path):
    a, _ = _attempt(tmp_path, {"verdict": "SIGNED"}, sub="gen/k/ft_physical/child/signoff.json")
    assert g.signed_unexported_refusal(str(a), exported=set(), host="h") is None
    b, _ = _attempt(tmp_path / "b", {"verdict": "FAIL_POSTCTS"})
    assert g.signed_unexported_refusal(str(b), exported=set(), host="h") is None


def test_refuse_calls_signed_unexported_with_stale_list_failing_closed_clean_aggr_r3(tmp_path, monkeypatch):
    a, _ = _attempt(tmp_path, {"verdict": "LOCAL_PASS"})
    monkeypatch.setattr(g, "EXPORTED_LIST", str(tmp_path / "missing.txt"))
    why = g.refuse(str(a), protected=set(), ptext="", current={}, allow=set())
    assert why and "exported_records.txt missing or stale" in why


def test_superseded_private_override_and_ref_tile_repo_views_clean_aggr_r3(tmp_path, monkeypatch):
    import json as _j, os as _o, time as _t
    t = tmp_path / "kw45" / "src_s81_pin_x_work_r2"
    t.mkdir(parents=True)
    cur = {"src_s81_": {"tree": "src_s81_cur", "adopted_at": _t.time() - 3600}}
    assert g.newer_than_current(str(t), cur)
    monkeypatch.setenv("OT_DELETE_SUPERSEDED_PRIVATE", str(t) + ":/x/y")
    assert g.newer_than_current(str(t), cur) == ""
    other = tmp_path / "kw45" / "src_s81_pin_x_r3"
    other.mkdir()
    monkeypatch.setenv("OT_DELETE_SUPERSEDED_PRIVATE", str(other))
    assert g.newer_than_current(str(other), cur)
    # ref_tile views inside a source tree are repo content, not this host's results
    v = t / "physical" / "ref_tile" / "a" / "views" / "b"
    v.mkdir(parents=True)
    (t / "physical" / "die_plan").mkdir()
    (v / "signoff.json").write_text(_j.dumps({"verdict": "SIGNED", "host": ""}))
    assert g.own_signed_records(str(t)) == []
    # without die_plan (not a source tree) the record still counts
    lone = tmp_path / "lane" / "physical" / "ref_tile" / "a"
    lone.mkdir(parents=True)
    (lone / "signoff.json").write_text(_j.dumps({"verdict": "SIGNED", "host": ""}))
    assert len(g.own_signed_records(str(tmp_path / "lane"))) == 1
