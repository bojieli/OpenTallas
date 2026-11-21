"""FLEET-WATCH-R5: kit_wave_edit event-pending / event-pending-clear."""
import json
import kit_wave_edit as E


def doc(**kw):
    return {"dies": {"kv": dict(kw), "s81": {}}}


def test_set_builds_an_add_op_with_event_and_since():
    ops = E.event_pending_ops("event-pending", "kv", "KV-D27", doc())
    assert ops[0]["op"] == "add" and ops[0]["path"] == "/dies/kv/event_pending"
    assert ops[0]["value"]["event"] == "KV-D27" and ops[0]["value"]["since"] > 0


def test_clear_removes_only_when_present():
    assert E.event_pending_ops("event-pending-clear", "kv", "", doc(event_pending={"event": "x", "since": 1})) == [{"op": "remove", "path": "/dies/kv/event_pending"}]
    assert E.event_pending_ops("event-pending-clear", "s81", "", doc()) == []


def test_unknown_die_refused():
    try:
        E.event_pending_ops("event-pending", "nope", "E", doc())
    except SystemExit as e:
        assert "unknown die" in str(e)
    else:
        raise AssertionError("no refusal")


def test_main_dispatch_sets_and_clears_through_edit(tmp_path, monkeypatch):
    (tmp_path / "autopilot").mkdir()
    (tmp_path / "autopilot/kit_wave.json").write_text(json.dumps(doc()))
    seen = []
    monkeypatch.setattr(E, "edit", lambda coord, ops, msg, dry=False, commit_cmd=None: seen.append((ops, msg)))
    assert E.main(["event-pending", "kv", "E9", "--coord", str(tmp_path)]) == 0
    assert seen[0][0][0]["value"]["event"] == "E9" and "apply gate started" in seen[0][1]
    (tmp_path / "autopilot/kit_wave.json").write_text(json.dumps(doc(event_pending={"event": "E9", "since": 1})))
    assert E.main(["event-pending-clear", "kv", "--coord", str(tmp_path)]) == 0
    assert seen[1][0] == [{"op": "remove", "path": "/dies/kv/event_pending"}]
