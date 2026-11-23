"""RELAY-ANCHOR (DIE-QC-97 11-10): plan relay names re-picked by recorded site when a reset-tree input renumbers the
tree (TAPREACH-1 sle_ctl__cl67434795 rst_rl_228; cand16 slw_sc_v1 rst_rl_97)."""
import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import reset_anchor as RA  # noqa: E402
import schema  # noqa: E402

FIX = HERE / "examples" / "reset_anchor" / "sle_ctl_tapreach.json"


def _tree(rows):
    return {"relays": [dict(q=q, depth=d, xy=list(xy)) for q, d, xy in rows]}


def _type(*names):
    stages = [dict(xy_um=[10.0 * i, 0.0], raw_reset=n) for i, n in enumerate(names)]
    return {"clock": {"landing_writer_start": {"depth": len(stages), "branches": {"b_o": {"stages": stages}}},
                      "landing_local_resets": [dict(name="l0", raw=names[0], xy_um=[1.0, 1.0],
                                                    consumers=["u_cland_x"])]}}


OLD = _tree([("rst_rl_0", 1, (0, 0)), ("rst_rl_1", 2, (100, 0)), ("rst_rl_2", 2, (0, 100)), ("rst_rl_3", 3, (100, 100))])
# the same sites after an input change re-ordered the build (a new relay rst_rl_1 at depth 1 in front)
NEW = _tree([("rst_rl_0", 1, (0, 0)), ("rst_rl_1", 1, (300, 0)), ("rst_rl_2", 2, (100, 0)),
             ("rst_rl_3", 2, (0, 100)), ("rst_rl_4", 3, (100, 104))])
NOPORT = lambda tree: set()  # noqa: E731


def _anchored(*names, tree=OLD, tol=50.0):
    t = _type(*names)
    t["clock"][RA.KEY] = RA.record(t, tree, HERE, tol)
    return t


def _names(t):
    return [c[k] for c, k in RA.refs(t)]


def test_renumbered_tree_is_repicked_by_site():
    t = _anchored("rst_rl_1", "rst_rl_2", "rst_rl_3")
    # without the anchor the plan names point at the wrong relays (rst_rl_1 is now depth 1 at 300,0)
    by = {r["q"]: r for r in NEW["relays"]}
    assert by["rst_rl_1"]["depth"] != t["clock"][RA.KEY]["relays"]["rst_rl_1"]["depth"]
    rec = RA.resolve("T", t, NEW, HERE, ported_fn=NOPORT)
    assert _names(t) == ["rst_rl_2", "rst_rl_3", "rst_rl_4", "rst_rl_2"]
    assert [(m["name"], m["to"]) for m in rec["remaps"]] == [("rst_rl_1", "rst_rl_2"), ("rst_rl_2", "rst_rl_3"),
                                                              ("rst_rl_3", "rst_rl_4")]
    assert rec["remaps"][2]["moved_um"] == 4.0 and rec["refs_rewritten"] == 4
    # idempotent: the in-memory anchor follows the new names
    assert RA.resolve("T", t, NEW, HERE, ported_fn=NOPORT)["remaps"] == []


def test_unchanged_tree_is_byte_identical():
    t = _anchored("rst_rl_1", "rst_rl_3")
    before = hashlib.sha256(json.dumps(t, sort_keys=True).encode()).hexdigest()
    rec = RA.resolve("T", t, copy.deepcopy(OLD), HERE, ported_fn=lambda tr: pytest.fail("no re-pick expected"))
    assert rec["remaps"] == [] and rec["kept"] == 2
    assert hashlib.sha256(json.dumps(t, sort_keys=True).encode()).hexdigest() == before


def test_no_anchor_is_untouched():
    t = _type("rst_rl_1")
    snap = copy.deepcopy(t)
    assert RA.resolve("T", t, NEW, HERE, ported_fn=NOPORT) is None and t == snap
    raw = {"partition_types": {"T": t}}
    assert RA.resolve_plan(raw, None, HERE, tree_fn=lambda tn: pytest.fail("no tree for unanchored plans")) == ([], [])


def test_no_relay_within_tolerance_fails_closed():
    t = _anchored("rst_rl_3", tol=2.0)          # rst_rl_3 moved 4 um in NEW
    with pytest.raises(RA.AnchorError, match="no relay within the recorded site tolerance"):
        RA.resolve("T", t, NEW, HERE, ported_fn=NOPORT)
    t = _anchored("rst_rl_3")
    gone = _tree([(r["q"], r["depth"], r["xy"]) for r in NEW["relays"] if r["depth"] != 3])
    with pytest.raises(RA.AnchorError, match="no same-depth relay"):
        RA.resolve("T", t, gone, HERE, ported_fn=NOPORT)
    raw = {"partition_types": {"T": _anchored("rst_rl_3", tol=2.0)}}
    rec, err = RA.resolve_plan(raw, None, HERE, tree_fn=lambda tn: NEW, ported_fn=NOPORT)
    assert rec == [] and len(err) == 1 and err[0].startswith("RESET_ANCHOR T:")


def test_ported_relay_is_never_a_target_and_unanchored_name_fails():
    t = _anchored("rst_rl_1", tol=250.0)
    rec = RA.resolve("T", t, NEW, HERE, ported_fn=lambda tr: {"rst_rl_2"})
    assert rec["remaps"][0]["to"] == "rst_rl_3" and rec["remaps"][0]["moved_um"] == 200.0
    with pytest.raises(RA.AnchorError):                # the same with tol 50: the only free relay is too far
        RA.resolve("T", _anchored("rst_rl_1"), NEW, HERE, ported_fn=lambda tr: {"rst_rl_2"})
    t = _anchored("rst_rl_1")
    t["clock"]["landing_local_resets"][0]["raw"] = "rst_rl_0"
    with pytest.raises(RA.AnchorError, match="lacks referenced relay"):
        RA.resolve("T", t, NEW, HERE, ported_fn=NOPORT)


def test_record_rejects_names_not_in_tree():
    with pytest.raises(RA.AnchorError, match="not in the tree"):
        RA.record(_type("rst_rl_9"), OLD, HERE, 10)


def test_schema_accepts_anchor_and_rejects_unknown_key():
    s = schema.SCHEMA["properties"]["partition_types"]["additionalProperties"]["properties"]["clock"]["properties"]
    anc = _anchored("rst_rl_1")["clock"][RA.KEY]
    errs = []
    schema._check(anc, s[RA.KEY], "$", errs)
    assert errs == []
    schema._check(dict(anc, extra=1), s[RA.KEY], "$", errs)
    assert errs == ["$: unknown key 'extra'"]


def test_sle_ctl_tapreach_matches_the_cand12_hand_repick():
    """MEASURED fixture: plan_pv sle_ctl__cl67434795 references, anchored on the 11-06 bins tree (501 relays), resolved on
    the TAPREACH-1 bins tree (513).  Before: rst_rl_228 is not even a relay; after: every name equals RELAY-REMAP-1."""
    fx = json.loads(FIX.read_text())
    t = {"clock": copy.deepcopy(fx["clock"])}
    t["clock"][RA.KEY] = fx["anchor"]
    tree = fx["tree_B"]
    by = {r["q"]: r for r in tree["relays"]}
    assert "rst_rl_228" in _names(t) and "rst_rl_228" not in by
    rec = RA.resolve(fx["type"], t, tree, HERE, ported_fn=lambda tr: set(fx["ported_B"]))
    assert "sink_bins" in rec["changed_inputs"]
    got = {n: next((m["to"] for m in rec["remaps"] if m["name"] == n), n) for n in fx["anchor"]["relays"]}
    assert got == {n: fx["expect_map"][n] for n in got}
    assert got["rst_rl_228"] == "rst_rl_211"
    assert all(n in by and by[n]["depth"] == fx["anchor"]["relays"][o]["depth"]
               for o, n in got.items())


def test_snapshot_is_the_solve_time_tree_and_anchors_like_it():
    t = _type("rst_rl_1", "rst_rl_3")
    assert RA.snapshot(t) is None
    t["clock"]["landing_contract"] = {"collector_tree": dict(depth=3, relays=copy.deepcopy(OLD["relays"]))}
    snap = RA.snapshot(t)
    assert snap["relays"] == OLD["relays"]
    assert RA.record(t, snap, HERE, 50.0) == RA.record(t, OLD, HERE, 50.0)
    # the anchor taken from the snapshot re-picks onto a renumbered tree like one taken from the solve-time tree
    t["clock"][RA.KEY] = RA.record(t, snap, HERE, 50.0)
    RA.resolve("T", t, NEW, HERE, ported_fn=NOPORT)
    assert _names(t) == ["rst_rl_2", "rst_rl_4", "rst_rl_2"]
    t["clock"]["landing_contract"]["collector_tree"]["relays"][0].pop("xy")
    assert RA.snapshot(t) is None


def test_bound_tree_reads_the_relays_a_bind_of_record_emitted():
    """plan_pv bind_pv rtl/sle_ctl__cl67434795.sv lines 4526-4530 (11-09): relay sites from the generator comments"""
    sv = """    wire rst_rl_228;
    ot_dp_rrelay u_rrl_228 (.clk(clk), .d(rst_rl_211), .q(rst_rl_228));  // raw pad tap None depth 5 @ (366.7, 946.1)
    wire rn_rst_rl_228;
    ot_dp_rrelay u_srl_228 (.clk(clk), .d(rn_rst_rl_211), .q(rn_rst_rl_228));  // run pad tap None depth 5 @ (366.7, 946.1)
    ot_dp_rrelay u_rrl_229 (.clk(clk), .d(rst_rl_228), .q(rst_rl_229));  // raw wire tap None depth 6 @ (366.7, 946.1)
    ot_dp_rrelay u_rrl_9 (.clk(clk), .d(rst_rl_8), .q(rst_n_t3));  // raw tap tap 3 depth 2 @ (1.0, 2.0)
"""
    bt = RA.bound_tree(sv)
    assert bt["relays"] == [dict(q="rst_rl_228", depth=5, xy=[366.7, 946.1]), dict(q="rst_rl_229", depth=6, xy=[366.7, 946.1])]
    assert RA.bound_tree("module m; endmodule") is None


def test_record_cli_anchors_every_good_type_and_lists_failures(tmp_path, monkeypatch, capsys):
    """TAP-GRID-R5 11-22: record is per type; a stale reference (rst_rl_9 not in the tree) fails only its own type."""
    import reset_tree as RT
    raw = {"partition_types": {"A": _type("rst_rl_1"), "BAD": _type("rst_rl_9"), "C": _type("rst_rl_2", "rst_rl_3")}}
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps(raw))
    monkeypatch.setattr(schema, "Plan", lambda r, f: object())
    monkeypatch.setattr(RT, "for_type", lambda P, tn: OLD)
    monkeypatch.setattr(RT, "relay_um", lambda P: 50.0)
    out = tmp_path / "out.json"
    rc = RA.main(["reset_anchor.py", "record", str(plan), str(out), "--root", str(HERE)])
    got = json.loads(out.read_text())["partition_types"]
    assert rc == 1
    assert set(got["A"]["clock"][RA.KEY]["relays"]) == {"rst_rl_1"}
    assert set(got["C"]["clock"][RA.KEY]["relays"]) == {"rst_rl_2", "rst_rl_3"}
    assert RA.KEY not in got["BAD"]["clock"]
    text = capsys.readouterr().out
    assert "FAILED BAD:" in text and "1 type(s) NOT anchored" in text and "BAD" in text.splitlines()[-1]
    rc_ok = RA.main(["reset_anchor.py", "record", str(plan), str(out), "--types", "A,C", "--root", str(HERE)])
    assert rc_ok == 0


def test_record_repick_keeps_depth_after_names_disappear(tmp_path, monkeypatch):
    import reset_tree as RT

    base = _anchored("rst_rl_1", "rst_rl_3")
    raw = {"partition_types": {"T": base, "BAD": copy.deepcopy(base)}}
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps(raw))
    out = tmp_path / "out.json"
    moved = _tree([("rst_rl_5", 2, (100, 4)), ("rst_rl_6", 3, (100, 100))])
    monkeypatch.setattr(schema, "Plan", lambda r, f: object())
    monkeypatch.setattr(RT, "for_type", lambda P, tn: moved if tn == "T" else _tree([]))
    monkeypatch.setattr(RT, "relay_um", lambda P: 50.0)
    monkeypatch.setattr(RT, "rtl_lines", lambda tree: [])
    rc = RA.main(["reset_anchor.py", "record", str(plan), str(out), "--source", "auto", "--repick"])
    got = json.loads(out.read_text())["partition_types"]
    assert rc == 1 and got["BAD"] == base
    assert _names(got["T"]) == ["rst_rl_5", "rst_rl_6", "rst_rl_5"]
    assert [a["depth"] for a in got["T"]["clock"][RA.KEY]["relays"].values()] == [2, 3]


# ---- RESET-ANCHOR-TAPGUARD-1123: record --source tree must not re-anchor renumbered names


def _record_cli(tmp_path, monkeypatch, raw, tree, *extra):
    import reset_tree as RT
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps(raw))
    monkeypatch.setattr(schema, "Plan", lambda r, f: object())
    monkeypatch.setattr(RT, "for_type", lambda P, tn: tree)
    monkeypatch.setattr(RT, "relay_um", lambda P: 50.0)
    monkeypatch.setattr(RA, "ported", lambda tr: set())
    out = tmp_path / "out.json"
    rc = RA.main(["reset_anchor.py", "record", str(plan), str(out), "--root", str(HERE), *extra])
    return rc, json.loads(out.read_text())["partition_types"]


def test_tap_digest_covers_added_taps_and_legacy_form():
    t = _type("rst_rl_1")
    base = RA.tap_rows_sha(t)
    assert base == RA.tap_rows_sha(t, legacy=True)           # no added_taps: both forms agree (old records stay valid)
    t["clock"]["added_taps"] = [dict(name="clk_t9", xy=[1.0, 2.0])]
    assert RA.tap_rows_sha(t) != base and RA.tap_rows_sha(t, legacy=True) == base
    assert RA.input_shas(t, HERE)["taps"] == RA.tap_rows_sha(t)


def test_rerecord_on_renumbered_tree_is_refused_and_keeps_the_old_anchor(tmp_path, monkeypatch, capsys):
    """the S81 J9 slice C class: names anchored on OLD, tree renumbered (rst_rl_1 is now depth 1): refused, anchor unchanged"""
    t = _anchored("rst_rl_1", "rst_rl_2", "rst_rl_3")
    t["clock"]["added_taps"] = [dict(name="clk_t9", xy=[300.0, 0.0])]       # the tap row that renumbered the tree
    old = copy.deepcopy(t["clock"][RA.KEY])
    rc, got = _record_cli(tmp_path, monkeypatch, {"partition_types": {"S": t, "U": _type("rst_rl_0")}}, NEW)
    text = capsys.readouterr().out
    assert rc == 1
    assert got["S"]["clock"][RA.KEY] == old                  # good anchor kept: the bind re-picks it by depth + site
    assert RA.KEY in got["U"]["clock"]                       # other types still anchored
    assert "REFUSED S:" in text and "another depth" in text and "rst_rl_1 anchored depth 2" in text
    assert "1 type(s) REFUSED" in text and text.splitlines()[-1].endswith("S")


def test_rerecord_repick_follows_depth_and_allow_keeps_old_behaviour(tmp_path, monkeypatch, capsys):
    t = _anchored("rst_rl_1", "rst_rl_2", "rst_rl_3")
    rc, got = _record_cli(tmp_path, monkeypatch, {"partition_types": {"S": copy.deepcopy(t)}}, NEW, "--repick")
    assert rc == 0
    s = got["S"]
    assert _names(s) == ["rst_rl_2", "rst_rl_3", "rst_rl_4", "rst_rl_2"]
    assert {n: a["depth"] for n, a in s["clock"][RA.KEY]["relays"].items()} == {"rst_rl_2": 2, "rst_rl_3": 2, "rst_rl_4": 3}
    assert "re-picked 3 relay name(s)" in capsys.readouterr().out
    rc, got = _record_cli(tmp_path, monkeypatch, {"partition_types": {"S": copy.deepcopy(t)}}, NEW, "--allow-tap-change", "S")
    assert rc == 0 and got["S"]["clock"][RA.KEY]["relays"]["rst_rl_1"]["depth"] == 1      # by name (pre-1123)


def test_rerecord_unchanged_tree_passes_even_after_a_tap_change(tmp_path, monkeypatch):
    t = _anchored("rst_rl_1", "rst_rl_3")
    t["clock"]["tap_pitch_um"] = 99                                          # tap rows changed, relays did not move
    rc, got = _record_cli(tmp_path, monkeypatch, {"partition_types": {"S": t}}, OLD)
    assert rc == 0 and got["S"]["clock"][RA.KEY]["inputs"]["taps"] == RA.tap_rows_sha(t)


def test_rerecord_after_tap_change_refuses_unanchored_new_names(tmp_path, monkeypatch, capsys):
    t = _anchored("rst_rl_1")
    t["clock"]["tap_pitch_um"] = 99
    t["clock"]["landing_local_resets"][0]["raw"] = "rst_rl_2"           # a name the anchor never saw
    rc, got = _record_cli(tmp_path, monkeypatch, {"partition_types": {"S": t}}, OLD)
    assert rc == 1 and "rst_rl_2 not anchored" in capsys.readouterr().out
    t["clock"]["tap_pitch_um"] = t["clock"].pop("tap_pitch_um")         # same rows: a new name alone is fine
    t2 = _anchored("rst_rl_1")
    t2["clock"]["landing_local_resets"][0]["raw"] = "rst_rl_2"
    rc, _ = _record_cli(tmp_path, monkeypatch, {"partition_types": {"S": t2}}, OLD)
    assert rc == 0


def test_rerecord_legacy_digest_warns_and_refuses_a_site_move(tmp_path, monkeypatch, capsys):
    t = _anchored("rst_rl_3")
    t["clock"]["added_taps"] = [dict(name="clk_t9", xy=[1.0, 1.0])]
    t["clock"][RA.KEY]["inputs"]["taps"] = RA.tap_rows_sha(t, legacy=True)     # a pre-1123 record
    moved = _tree([("rst_rl_0", 1, (0, 0)), ("rst_rl_1", 2, (100, 0)), ("rst_rl_2", 2, (0, 100)), ("rst_rl_3", 3, (100, 140))])
    rc, got = _record_cli(tmp_path, monkeypatch, {"partition_types": {"S": copy.deepcopy(t)}}, moved)
    text = capsys.readouterr().out
    assert rc == 1 and "pre-1123 tap digest" in text and "REFUSED S:" in text
    rc, got = _record_cli(tmp_path, monkeypatch, {"partition_types": {"S": copy.deepcopy(t)}}, OLD)
    assert rc == 0 and "pre-1123 tap digest" in capsys.readouterr().out
