"""CLEAN-AGGR-1121 (OWNER 11-21 "apply all the aggressive cleanup rules"): records (tree_switch markers, handoff / candidate json) protect only CURRENT source trees, the
candidate of the next event (written after the die's adoption) and wave attempts a live / queued row lists; the 11-17 provenance cache no longer protects past its 72 h;
kw45/snap_<die>/<tree> snapshots are whole trees of their own; a routed unsigned attempt is protected by its result only within the 2 h grace."""
import datetime, importlib.util, json, os, sys, time

HERE = os.path.dirname(os.path.realpath(__file__))


def _load(name):
    sp = importlib.util.spec_from_file_location(name, os.path.join(HERE, name + ".py"))
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


B = _load("build_protected_live")
G = _load("ot_delete_guard")
K = "/srv/opentallas-scratch2/claude/kw45/"
W = "/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave"


def _coord(tmp_path, adopted):
    c = tmp_path / "coord"
    (c / "autopilot").mkdir(parents=True); (c / "lanes/handoff").mkdir(parents=True)
    cfg = {"dies": {
        "s81": {"src": K + "src_s81_pin_x_d8j6r1_work", "rollback_tree": K + "src_s81_pin_x_d8j6_work", "work_root": W,
                "bound_trees": [{"src": K + "src_s81_pin_x_d8j6_work", "plan": K + "src_s81_pin_x_d8j6_work/physical/die_plan/s81/plan.json"}]},
        "qwen_compute": {"src": K + "snap_qwen_compute/qwen_compute_v2r10"}}}
    (c / "autopilot/kit_wave.json").write_text(json.dumps(cfg))
    (c / "autopilot/kit_wave_state.json").write_text(json.dumps({"items": {
        "s81|t1|x": {"status": "RUNNING", "attempt": 7, "work": W + "/s81/ev2/items/t1"},
        "s81|t2|x": {"status": "CANCELLED", "attempt": 4, "work": W + "/s81/ev1/items/t2"}}}))
    for die in ("s81", "qwen_compute"):
        f = c / ("lanes/handoff/tree_switch_%s.json" % die)
        f.write_text(json.dumps({"tree": cfg["dies"][die]["src"]}))
        os.utime(f, (adopted, adopted))
    return c, cfg


def test_record_scope_current_trees_next_candidate_and_live_attempts(tmp_path):
    now = time.time(); adopted = now - 10 * 3600
    c, cfg = _coord(tmp_path, adopted)
    h = c / "lanes/handoff"
    old = h / "S81_D8J_source_candidate.json"; old.write_text(json.dumps({"src": K + "src_s81_pin_x_d8j_work", "plan": K + "src_s81_pin_x_d8j_work/p.json"}))
    os.utime(old, (adopted - 3600, adopted - 3600))                                  # written before the current adoption: superseded event
    nxt = h / "S81_J7_source_candidate.json"; nxt.write_text(json.dumps({"src": K + "src_s81_pin_x_j7_work"}))
    os.utime(nxt, (now - 600, now - 600))                                            # the next event, applying now
    rows = h / "KV-PV-R3-fault-rows.json"; rows.write_text(json.dumps({"rows": [W + "/s81/ev1/items/t2/attempt_4", W + "/s81/ev2/items/t1/attempt_7/gen",
                                                                                  "/srv/opentallas-scratch2/claude/lane-x/private_kit/items/k/attempt_2",
                                                                                  K + "src_s81_pin_x_d8j6_work/physical/a.json",
                                                                                  K + "snap_qwen_compute/qwen_compute_n46_s0/x", "/srv/opentallas-scratch2/claude/lane-y/report"]}))
    os.utime(rows, (now - 600, now - 600))
    rows_old = h / "QC-OLD-rows.json"; rows_old.write_text(json.dumps({"src": K + "snap_qwen_compute/qwen_compute_n43_s3"})); os.utime(rows_old, (adopted - 60, adopted - 60))
    live = set(); B.live_attempt_paths(str(c), live, os.path.normpath)
    scope = B.RecordScope(str(c), cfg, os.path.normpath, live)
    out = set()
    B.event_paths(str(c), out, os.path.normpath, now=now, scope=scope)
    assert K + "src_s81_pin_x_d8j_work" not in out and K + "src_s81_pin_x_d8j_work/p.json" not in out
    assert K + "src_s81_pin_x_j7_work" in out
    assert W + "/s81/ev1/items/t2/attempt_4" not in out                                 # CANCELLED row: a fault-row list no longer protects it
    assert W + "/s81/ev2/items/t1/attempt_7/gen" in out                                 # live row
    assert "/srv/opentallas-scratch2/claude/lane-x/private_kit/items/k/attempt_2" in out  # not a wave attempt: unchanged
    assert K + "src_s81_pin_x_d8j6_work/physical/a.json" in out                         # rollback / bound tree is current
    assert K + "snap_qwen_compute/qwen_compute_n46_s0/x" in out                         # written after the QC adoption
    assert K + "snap_qwen_compute/qwen_compute_n43_s3" not in out
    assert "/srv/opentallas-scratch2/claude/lane-y/report" in out
    assert scope.dropped["event"] == 4
    # markers: an old proposal marker of a superseded tree no longer protects it; the die marker keeps the current tree
    prop = h / "tree_switch_s81_F2s3_proposal.json"; prop.write_text(json.dumps({"tree": K + "src_s81_pin_x_f2s3_work"})); os.utime(prop, (adopted - 7200, adopted - 7200))
    s = B.build(str(c), [str(h)], os.path.normpath, scope)
    assert K + "src_s81_pin_x_f2s3_work" not in s and K + "src_s81_pin_x_d8j6r1_work" in s
    assert B.build(str(c), [str(h)], os.path.normpath) >= {K + "src_s81_pin_x_f2s3_work"}   # no scope: old behaviour


def test_prov_cache_age(tmp_path):
    f = tmp_path / "prov.json"
    f.write_text(json.dumps({"time": time.time() - 4 * 86400, "paths": {"/srv/opentallas-scratch2/claude/a/b/c": {}}}))
    out = set(); B.prov_cache_paths(str(f), out, os.path.normpath); assert out == set()
    f.write_text(json.dumps({"time": time.time() - 3600, "paths": {"/srv/opentallas-scratch2/claude/a/b/c": {}}}))
    out = set(); B.prov_cache_paths(str(f), out, os.path.normpath); assert out == {"/srv/opentallas-scratch2/claude/a/b/c"}


def test_current_trees_snap_prefix(tmp_path):
    c, cfg = _coord(tmp_path, time.time() - 3600)
    ct = B.current_trees(str(c))
    assert ct["qwen_compute_"]["tree"] == "qwen_compute_v2r10" and ct["src_qc_"]["tree"] == "qwen_compute_v2r10"


def test_snap_tree_roots():
    m = G.TREE_ROOT.match(K + "snap_qwen_compute/qwen_compute_n43_s3")
    assert m and not m.group("rest")
    m = G.TREE_ROOT.match(K + "snap_qwen_compute/qwen_compute_n43_s3/physical")
    assert m and m.group("rest") == "physical"
    prot = {K + "snap_qwen_compute/qwen_compute_v2r10"}
    assert G.refuse(K + "snap_qwen_compute/qwen_compute_n43_s3", protected=prot, ptext="", current={}, allow=set()) is None
    assert G.refuse(K + "snap_qwen_compute/qwen_compute_v2r10", protected=prot, ptext="", current={}, allow=set()).startswith("protected")
    assert G.refuse(K + "snap_qwen_compute", protected=prot, ptext="", current={}, allow=set()).startswith("protected")
    assert G.refuse(K + "snap_qwen_compute/qwen_compute_n43_s3/physical", protected=prot, ptext="", current={}, allow=set()).startswith("partial")


def test_routed_unsigned_grace(tmp_path, monkeypatch):
    base = tmp_path / "w/items/t1/attempt_3"
    db = base / "gen/t1/run/results/asap7/t1/base/6_final.odb"
    db.parent.mkdir(parents=True); db.write_text("x")
    t = str(base)
    assert G.routed_unsigned_refusal(t)                                             # fresh routed unsigned result: refused
    os.utime(db, (time.time() - 3 * 3600, time.time() - 3 * 3600))
    assert G.routed_unsigned_refusal(t) is None                                     # past the 2 h grace: only list / live checks protect it
    monkeypatch.setattr(G, "ROUTED_GRACE_H", 5.0)
    assert G.routed_unsigned_refusal(t)


def test_bound_trees_need_a_tree_reading_row(tmp_path):
    c, cfg = _coord(tmp_path, time.time() - 3600)
    cfg["dies"]["s81"]["bound_trees"] = [{"src": K + "src_s81_pin_x_d8h_work", "plan_sha256": "aaaa1111"},
                                         {"src": K + "src_s81_pin_x_d8i_work", "plan_sha256": "bbbb2222"},
                                         {"src": K + "src_s81_pin_x_d8j5_work", "plan_sha256": "cccc3333"}]
    (c / "autopilot/kit_wave.json").write_text(json.dumps(cfg))
    (c / "autopilot/kit_wave_state.json").write_text(json.dumps({"items": {
        "a": {"status": "RUNNING", "plan_sha": "aaaa", "attempt": 1, "work": W + "/s81/e/items/a"},
        "a2": {"status": "ENQUEUED", "plan_sha": "bbbb", "attempt": 1, "work": W + "/s81/e/items/a2"},
        "b": {"status": "ROUTE-HELD", "plan_sha": "bbbb2222", "attempt": 2, "work": W + "/s81/e/items/b"},
        "c": {"status": "CANCELLED", "plan_sha": "cccc3333", "attempt": 2, "work": W + "/s81/e/items/c"}}}))
    scope = B.RecordScope(str(c), cfg, os.path.normpath, set())
    s = B.build(str(c), [], os.path.normpath, scope)
    assert K + "src_s81_pin_x_d8h_work" in s                                        # an unstarted row still gens from it
    assert K + "src_s81_pin_x_d8i_work" not in s and K + "src_s81_pin_x_d8j5_work" not in s
    assert scope.dropped["bound_tree"] == 2
    assert K + "src_s81_pin_x_d8h_work" in scope.current and K + "src_s81_pin_x_d8i_work" not in scope.current
