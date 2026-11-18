"""FLOW-HEALTH-1 11-16 (FABLE-FLOW-0015 a b c): missing-input fail key releases only when the input appears or the config is repointed;
SKEW covers the live wave trees; DEDUP members and an unarchivable record reach a terminal state."""
import json
import time

import autopilot as AP
import flow_health as FH
import kit_wave as KW

MISS = ("FLOW[missing_input]: KIT_INPUT_MISSING: a kit input exists on no die host; restore it or repoint the die config @kit_snap: KIT_INPUT_MISSING: 8 "
        "original-kit file(s) named by this type's child views exist on no die host: /srv/opentallas-scratch3/claude/s81-t51-recut/pg/x_native_e "
        "(named by /srv/opentallas-scratch2/claude/s81-b3-clk/v/view.json), /srv/opentallas-scratch3/claude/s81-t51-recut/pg/x_native_w")


def cfg(src="s1", overlay="o1", plan="p1"):
    return {"dies": {"s81": {"src_sha": src, "_src_overlay": overlay, "_plan_sha": plan, "event": "e", "enabled": True, "gen_host": "epyc9"}}}


def rec(item="slice_station__t51"):
    return {"die": "s81", "item": item, "block_sha": "b1", "stage": "kit_snap"}


def test_a_missing_input_ignores_a_tool_merge_and_releases_when_the_input_appears(monkeypatch):
    st = {}
    monkeypatch.setattr(KW, "path_exists_somewhere", lambda c, d, p, **k: False)
    KW.note_fail_key(cfg(), st, rec(), "FLOW", MISS)
    e = st["fail_keys"]["s81|slice_station__t51"]
    assert e["type"] == "missing_input" and e["missing"] == ["/srv/opentallas-scratch3/claude/s81-t51-recut/pg/x_native_e",
                                                             "/srv/opentallas-scratch3/claude/s81-t51-recut/pg/x_native_w"]
    monkeypatch.setattr(KW, "stage_tools_digest", lambda *a, **k: "tools-after-the-23:29-merge")        # the merge that re-armed it
    bl, why, chg = KW.fail_key_gate(cfg(), st, "s81", "slice_station__t51", "b1")
    assert bl and chg == []
    monkeypatch.setattr(KW, "path_exists_somewhere", lambda c, d, p, **k: p.endswith("_w"))             # one of the inputs is restored
    assert KW.fail_key_gate(cfg(), st, "s81", "slice_station__t51", "b1")[2] == ["input"]
    monkeypatch.setattr(KW, "path_exists_somewhere", lambda c, d, p, **k: False)
    assert KW.fail_key_gate(cfg(src="s2"), st, "s81", "slice_station__t51", "b1")[2] == ["src"]          # repointed config
    assert KW.fail_key_gate(cfg(), st, "s81", "slice_station__t51", "b2")[2] == ["block"]


def test_a_missing_input_inside_a_snapshot_releases_only_on_a_newer_snapshot_that_holds_it(tmp_path, monkeypatch):
    # KV 7yhr hub_C a2 11-16: kit_topology read <store>/snaps/550ac.../root/<tree>/plan_of_record/eW_sidecar.json, absent from the snapshot
    import os
    old, new, oth = "a" * 40, "b" * 40, "c" * 40
    logical = "/srv/x/tree/plan_of_record/eW_sidecar.json"
    store = tmp_path / "kit-store"
    for sid in (old, new, oth):
        (store / "snaps" / sid / "root/srv/x/tree/plan_of_record").mkdir(parents=True)
        (store / "snaps" / sid / "root/srv/x/tree/plan_of_record/e_other.json").write_text("{}")
        (store / "snaps" / sid / "MANIFEST.json").write_text("{}")
    miss = f"{store}/snaps/{old}/root{logical}"
    why = f"FLOW[missing_input]: KIT_NOT_SELF_CONTAINED: kit recipe must copy the file into the kit at staging @kit_topology: {miss}"
    assert KW.snapshot_logical(miss) == (str(store), old, logical) and KW.snapshot_logical("/srv/x/tree/a.json") is None
    st = {}
    monkeypatch.setattr(KW, "path_exists_somewhere", lambda c, d, p, **k: False)
    KW.note_fail_key(cfg(), st, dict(rec("hub_C"), stage="kit_topology"), "FLOW", why)
    e = st["fail_keys"]["s81|hub_C"]
    assert e["type"] == "missing_input" and e["missing"] == [miss]
    c = cfg()
    c["dies"]["s81"]["gen_host"] = None                                  # local store only
    t0 = e["ts"]
    for sid in (old, new, oth):
        os.utime(store / "snaps" / sid / "MANIFEST.json", (t0 - 100, t0 - 100))
    gate = lambda: (KW.SNAP_FIXED.clear(), KW.fail_key_gate(c, st, "s81", "hub_C", "b1"))[1]
    assert gate()[0]                                                     # nothing newer, file nowhere: blocked
    os.utime(store / "snaps" / oth / "MANIFEST.json", (t0 + 50, t0 + 50))
    assert gate()[0]                                                     # a newer snapshot with the same hole (only e_other): blocked
    (store / "snaps" / new / "root/srv/x/tree/plan_of_record/eW_sidecar.json").write_text("{}")
    assert gate()[0]                                                     # the file is in a snapshot made BEFORE the fail: blocked
    os.utime(store / "snaps" / new / "MANIFEST.json", (t0 + 60, t0 + 60))
    assert gate() == (False, "", ["snapshot"])                           # a newer snapshot holds it: released
    e["missing"] = [miss[:-len("W_sidecar.json")]]                       # stored error text cut after ".../plan_of_record/e"
    assert gate() == (False, "", ["snapshot"])
    (store / "snaps" / new / "root/srv/x/tree/plan_of_record/eW_sidecar.json").unlink()
    assert gate()[0]                                                     # the cut prefix matches only a file the failed snapshot also has


def test_a_other_classes_release_on_a_tool_change_only_when_the_failure_names_the_file(monkeypatch):
    st = {}
    KW.note_fail_key(cfg(), st, rec(), "INFRA", "INFRA: tool or source skew @gen: File tools/die_plan/gen_phys.py line 9 AttributeError: module 'x' has no attribute 'y'")
    monkeypatch.setattr(KW, "stage_tools_digest", lambda *a, **k: "new")
    assert KW.fail_key_gate(cfg(), st, "s81", "slice_station__t51", "b1")[2] == ["tools"]


def test_b_skew_trees_are_the_live_wave_trees(tmp_path):
    k = tmp_path / "a1"
    k.mkdir()
    (k / "spec.json").write_text(json.dumps({"src": "/srv/x/live_src_on_a_row"}))
    state = {"items": {"s81|a|b": {"die": "s81", "item": "a", "status": "RUNNING", "dir": str(k), "updated": time.time()},
                       "s81|old|b": {"die": "s81", "item": "old", "status": "FAIL", "dir": str(k), "updated": time.time() - 99 * 3600}}}
    cfgd = {"dies": {"s81": {"enabled": True, "gen_host": "h1", "src": "/srv/x/die_src",
                             "item_inputs": {"a": {"src": "/srv/x/in_a"}, "old": {"src": "/srv/x/old_plan_tree"}, "never": {"src": "/srv/x/never"}}}}}
    trees, hosts = FH.trees_of(cfgd, state)
    got = {t for _, t in trees}
    assert got == {"/srv/x/die_src", "/srv/x/live_src_on_a_row", "/srv/x/in_a"}
    assert {t for _, t in FH.trees_of(cfgd)[0]} == {"/srv/x/die_src", "/srv/x/in_a", "/srv/x/old_plan_tree", "/srv/x/never"}      # no state: as before


def test_c_dedup_members_wait_in_a_terminal_state_while_the_owner_key_stands(monkeypatch, tmp_path):
    class AP_:
        AP_DIR = tmp_path
        DRY = False
        logs = []
        log = staticmethod(lambda m: AP_.logs.append(m))
    st = {"items": {"s81|own|e|b": {"die": "s81", "item": "col_h9_r2__t1__clb8d86cd5__pv8d57997d", "status": "FAIL", "class": "FLOW", "updated": 5, "block_sha": "b1"},
                    "s81|mem|e|b": {"die": "s81", "item": "col_h9_r2__t1__clb8d86cd5__pvf0595d0f", "status": "DEDUP",
                                    "dedup_owner": "col_h9_r2__t1__clb8d86cd5__pv8d57997d"}}}
    monkeypatch.setattr(KW, "fail_key_gate", lambda *a, **k: (True, "same key", []))
    monkeypatch.setattr(KW, "DEDUP_DEFAULT", {"s81": ["col_h*"]})      # S81-COL-FLOW-1118: dedup is opt-in now (r703 / r705)
    notices = {}
    KW.dedup_step(AP_, cfg(), st, notices, str(tmp_path))
    KW.dedup_step(AP_, cfg(), st, notices, str(tmp_path))
    assert st["items"]["s81|mem|e|b"]["status"] == "DEDUP-WAIT"
    assert len([m for m in AP_.logs if "DEDUP-WAIT" in m]) == 1 and not any("DEDUP RELEASE" in m for m in AP_.logs)
    monkeypatch.setattr(KW, "fail_key_gate", lambda *a, **k: (False, "", ["src"]))                 # the owner's inputs changed
    KW.dedup_step(AP_, cfg(), st, notices, str(tmp_path))
    assert "s81|mem|e|b" not in st["items"] and any("DEDUP RELEASE" in m for m in AP_.logs)


def test_c_unarchivable_record_gets_a_terminal_state(monkeypatch):
    src = open(AP.__file__).read()
    assert '"SIGNED-NOT-ARCHIVED"' in src
    j = {"id": "x"}
    post = [AP.archive_backoff(j, "FileNotFoundError: No such file or directory: /srv/gone", now=10 + i) for i in range(3)]
    assert post == [False, False, True]
