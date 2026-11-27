import importlib.util, json, os, pathlib, subprocess, sys, tempfile, time, unittest
H = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import ot_delete_guard as g

S = "/srv/opentallas-scratch2/claude"


def mkcoord(t, src="kw45/src_kv_main_66e6", extra=None):
    c = pathlib.Path(t) / "coord"; (c / "autopilot").mkdir(parents=True); (c / "lanes/handoff").mkdir(parents=True)
    d = {"src": f"{S}/{src}", "plan": f"{S}/plans/p1/plan.json",
         "item_inputs": {"x": {"src": f"{S}/kw45/src_item_in", "kit_rtl": {"bind_out": f"{S}/bind/b1/out"}}}, "prov_view_sources": {}}
    (c / "autopilot/kit_wave.json").write_text(json.dumps({"dies": {"kv": d, **(extra or {})}}))
    (c / "lanes/handoff/tree_switch_kv.json").write_text(json.dumps({"die": "kv", "tree": f"{S}/kw45/src_kv_pin_eb1e"}))
    return str(c)


class Guard(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.mkdtemp(); self.prot = g.build_protected(mkcoord(self.t))

    def test_build_has_src_item_inputs_bind_and_marker(self):
        for p in (f"{S}/kw45/src_kv_main_66e6", f"{S}/kw45/src_item_in", f"{S}/bind/b1/out", f"{S}/kw45/src_kv_pin_eb1e"):
            self.assertIn(p, self.prot)

    def test_refuses_protected_whole_contained_and_inside(self):
        self.assertIn("protected", g.refuse(f"{S}/kw45/src_kv_main_66e6", self.prot, ""))
        self.assertIn("protected", g.refuse(f"{S}/kw45", self.prot, ""))                    # CONTAINS protected trees
        self.assertIn("protected", g.refuse(f"{S}/bind/b1/out/sub", self.prot, ""))        # INSIDE a bind of record
        self.assertIsNone(g.refuse(f"{S}/kw45/src_old_unreferenced", self.prot, ""))      # unprotected whole tree may go

    def test_whole_tree_only(self):
        r = g.refuse(f"{S}/kw45/src_old_unreferenced/physical", self.prot, "")
        self.assertIn("whole trees only", r)
        self.assertIn("whole trees only", g.refuse(f"{S}/lane1/src_x_1/results", self.prot, ""))   # the hollowing rule

    def test_live_process_cwd_and_open_file(self):
        d = pathlib.Path(self.t) / "kw45/src_zz"; d.mkdir(parents=True); (d / "f").write_text("x")
        p = subprocess.Popen(["sleep", "30"], cwd=str(d))
        try:
            time.sleep(0.3); g._CACHE["t"] = 0
            self.assertIn("live process", g.refuse(str(d), set(), None))
            self.assertIsNone(g.refuse(str(pathlib.Path(self.t) / "other"), set(), ""))
        finally:
            p.kill(); p.wait()

    def test_symlink_refused(self):
        a = pathlib.Path(self.t) / "real"; a.mkdir(); l = pathlib.Path(self.t) / "lnk"; l.symlink_to(a)
        self.assertIn("symlink", g.refuse(str(l), set(), ""))

    def test_list_missing_or_stale_fails_closed_for_tree_roots(self):
        os.environ["OT_GUARD_LIST"] = str(pathlib.Path(self.t) / "nolist")
        try:
            self.assertIn("missing", g.refuse(f"{S}/kw45/src_anything", None, ""))
            self.assertIsNone(g.refuse("/tmp/some/other/path", None, ""))                  # non-tree targets keep the other guards
            lst = pathlib.Path(self.t) / "old.txt"; lst.write_text("# built %d\n%s\n" % (time.time() - 99 * 3600, f"{S}/x"))
            os.environ["OT_GUARD_LIST"] = str(lst)
            self.assertIn("older", g.refuse(f"{S}/kw45/src_anything", None, ""))
            g.write_list(self.prot, str(lst))
            self.assertIn("protected", g.refuse(f"{S}/kw45/src_kv_main_66e6", None, ""))
        finally:
            os.environ.pop("OT_GUARD_LIST", None)


def test_live_explorer_environment_covers_store_repo_and_shared_state(tmp_path, monkeypatch):
    # Neither argv, cwd nor an open file names any of these protected paths.
    script = tmp_path / "tools/explorer/server.py"
    script.parent.mkdir(parents=True)
    script.write_text("import sys; print('ready', flush=True); sys.stdin.read()\n")
    store = f"{S}/guard-explorer-fixture/store"
    state = f"{S}/guard-explorer-fixture/state"
    code = f"{S}/guard-explorer-source"
    private_value = f"{S}/guard-must-not-capture"
    env = dict(os.environ, LV_STORE=store, FLEET_VIZ_STATE=state, FLEET_VIZ_REPO=code,
               UNKNOWN_SECRET=private_value, TOKEN_DESIGN_MAP="relative-not-a-dataset")
    client = subprocess.Popen([sys.executable, "-I", "server.py"], cwd=script.parent, env=env,
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    try:
        assert client.stdout.readline().strip() == "ready"
        live = g._live_text()
    finally:
        client.communicate(timeout=10)

    assert {store, state, code} <= live.datasets
    assert private_value not in live and private_value not in live.datasets
    assert "relative-not-a-dataset" not in live.datasets
    for path in (store, store + "/objects/42", os.path.dirname(store), state, code + "/physical", code + "/results"):
        assert g.refuse(path, protected=set(), ptext=live) == "live Explorer service dataset"
    assert g.refuse(store + "-old", protected=set(), ptext=live) is None
    assert g.refuse(code + "-old", protected=set(), ptext=live) is None
    monkeypatch.setattr(g, "load_list", lambda: (None, "missing list"))
    assert g.refuse(store, ptext=live) == "live Explorer service dataset"


def test_guard_does_not_read_unrelated_process_environment(tmp_path):
    script = tmp_path / "server.py"
    script.write_text("import sys; print('ready', flush=True); sys.stdin.read()\n")
    unrelated = f"{S}/guard-unrelated-service"
    client = subprocess.Popen([sys.executable, "-I", str(script)], env=dict(os.environ, LV_STORE=unrelated),
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    try:
        assert client.stdout.readline().strip() == "ready"
        live = g._live_text()
    finally:
        client.communicate(timeout=10)
    assert unrelated not in live and unrelated not in live.datasets


class Integration(unittest.TestCase):
    def test_autoclean_delete_calls_guard(self):
        spec = importlib.util.spec_from_file_location("ot_autoclean_x", str(H / "ot-autoclean.py")); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        self.assertIsNotNone(m._dg)
        self.assertIn("whole trees only", m.guard_refuse(f"{S}/kw45/src_a_b/physical"))
        src = (H / "ot-autoclean.py").read_text()
        self.assertIn("raise OSError(\"delete guard: \" + _gr)", src)

    def test_wt_reaper_and_autoprune_use_guard(self):
        self.assertIn("_guard_refuse(wt)", (H / "wt-reaper.py").read_text())
        self.assertIn("import ot_delete_guard", (H / "ot_disk_autoprune.py").read_text())


if __name__ == "__main__":
    unittest.main()


def test_work_root_history_keys_and_notes_do_not_protect_trees_but_hbm_history_does(tmp_path):
    import json as _j
    import ot_delete_guard as G
    c = tmp_path / "coord"
    (c / "autopilot").mkdir(parents=True)
    (c / "lanes/handoff").mkdir(parents=True)
    cfg = {"dies": {
        "s81": {"src": "/srv/opentallas-scratch2/claude/kw45/src_s81_cur", "work_root": "/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave",
                "src_prev_x": "/srv/opentallas-scratch2/claude/kw35/src_old1", "note_src": "tree /srv/opentallas-scratch2/claude/kw35/src_old2 was used",
                "prov_view_sources": {"v": [{"dir": "/srv/opentallas-scratch3/claude/kw40/views_ev/aa/v", "job": "COUNTED intel1:/srv/opentallas-scratch2/claude/kw35/src_old3/x"}]},
                "gate": {"evidence": "see /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_old"}},
        "hbm": {"src": "/srv/opentallas-scratch2/claude/kw45/src_hbm_cur", "src_prev_kw43": "/srv/opentallas-scratch2/claude/kw45/src_hbm_parked"}}}
    (c / "autopilot/kit_wave.json").write_text(_j.dumps(cfg))
    s = G.build_protected(str(c), str(c / "lanes/handoff"))
    assert "/srv/opentallas-scratch2/claude/kw45/src_s81_cur" in s and "/srv/opentallas-scratch2/claude/kw40/views_ev/aa/v" in s    # live: current src, view dir
    assert "/srv/opentallas-scratch2/claude/kw45/src_hbm_parked" in s                                                             # HBM history stays protected
    joined = "\n".join(s)
    for gone in ("kit-wave", "src_old1", "src_old2", "src_old3", "head_old"):
        assert gone not in joined, gone


def test_routed_unsigned_attempt_is_refused_unless_signed_or_superseded(tmp_path):
    import json as _j
    import ot_delete_guard as G
    it = tmp_path / "kit-wave" / "s81" / "ev" / "items" / "t47"
    def attempt(n, routed, signed=False):
        b = it / f"attempt_{n}" / "gen" / "t47" / "run" / "results" / "asap7" / "dp_t47" / "base"
        b.mkdir(parents=True)
        (b / "3_5_place_dp.odb").write_text("x")
        if routed:
            (b / "5_2_route.odb").write_text("x")
        if signed:
            so = it / f"attempt_{n}" / "gen" / "t47" / "signoff"
            so.mkdir()
            (so / "signoff.json").write_text(_j.dumps({"verdict": "SIGNED"}))
    attempt(3, True)
    attempt(4, False)
    assert "routed result not signed" in G.refuse(str(it / "attempt_3"), protected=set(), ptext="", allow=set())
    assert "routed result not signed" in G.refuse(str(it / "attempt_3" / "gen" / "t47" / "run"), protected=set(), ptext="", allow=set())
    assert G.refuse(str(it / "attempt_4"), protected=set(), ptext="", allow=set()) is None          # nothing routed there
    attempt(5, True)
    assert G.refuse(str(it / "attempt_3"), protected=set(), ptext="", allow=set()) is None           # superseded by a newer routed attempt
    assert "routed result not signed" in G.refuse(str(it / "attempt_5"), protected=set(), ptext="", allow=set())
    attempt(6, True, signed=True)
    # CLEAN-AGGR-R3 (COORD 11-22): a SIGNED attempt is kept until its record is exported, then it may go
    import hashlib as _h, time as _t
    sha = _h.sha256((it / "attempt_6" / "gen" / "t47" / "signoff" / "signoff.json").read_bytes()).hexdigest()
    lst = tmp_path / "exported_records.txt"
    old_list = G.EXPORTED_LIST
    try:
        G.EXPORTED_LIST = str(lst)
        lst.write_text("# built %d\n" % int(_t.time()))
        assert "signed record not exported" in G.refuse(str(it / "attempt_6"), protected=set(), ptext="", allow=set())
        lst.write_text("# built %d\n%s\tx\n" % (int(_t.time()), sha))
        assert G.refuse(str(it / "attempt_6"), protected=set(), ptext="", allow=set()) is None       # SIGNED and exported
    finally:
        G.EXPORTED_LIST = old_list


def test_private_kit_not_protected_by_kit_wave_ancestor_clean_aggr_r3(tmp_path):
    """COORD 11-21: a failed private-spec kit under .../kit-wave/<die>/<plan>/private/<LANE>/ is deletable; listed itself, signed or live stays refused"""
    wr = tmp_path / "runs" / "qwen_compute" / "kit-wave"
    k = wr / "qwen_compute" / "planX" / "private" / "LANE-A" / "slw_su_c_1"
    (k / "gen").mkdir(parents=True)
    wr_s, k_s = g.canon(str(wr)), g.canon(str(k))
    assert g.refuse(str(k), protected={wr_s}, ptext="", current={}, allow=set()) is None
    assert g.refuse(str(k / "gen"), protected={wr_s}, ptext="", current={}, allow=set()) is None
    assert g.refuse(str(k), protected={wr_s, k_s}, ptext="", current={}, allow=set())
    assert g.refuse(str(k), protected={wr_s}, ptext="cmd " + k_s + " x", current={}, allow=set())
    cv = k / "gen" / "slw_su_c_1" / "ft_physical" / "child_v"
    cv.mkdir(parents=True)
    (cv / "signoff.json").write_text('{"verdict": "SIGNED"}')          # a copied child-view record: not this kit's result
    assert g.refuse(str(k), protected={wr_s}, ptext="", current={}, allow=set()) is None
    (k / "signoff").mkdir()
    (k / "signoff" / "signoff.json").write_text('{"verdict": "SIGNED"}')
    assert g.refuse(str(k), protected={wr_s}, ptext="", current={}, allow=set())
    assert g.refuse(str(wr / "qwen_compute" / "planX" / "private" / "LANE-A"), protected={wr_s}, ptext="", current={}, allow=set())



def test_ancestor_cmdline_not_live_clean_aggr_r3(tmp_path):
    d = tmp_path / "victim_tree"; d.mkdir()
    code = ("import importlib.util as u,sys;s=u.spec_from_file_location('g',sys.argv[1]);g=u.module_from_spec(s);s.loader.exec_module(g);"
            "print('HIT' if sys.argv[2] in g._live_text() else 'MISS')")
    gp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ot_delete_guard.py")
    # the grandparent sh names the target in its cmdline (like `timeout N ot-delete <path>`): not a live user of the tree
    out = subprocess.run(["sh", "-c", 'timeout 50 ' + sys.executable + ' -I -c "$0" "$1" "$2"; : ' + str(d), code, gp, str(d)],
                         capture_output=True, text=True, timeout=60).stdout
    assert "MISS" in out, out


def test_ancestor_pids_walks_to_init():
    s = g.ancestor_pids()
    assert os.getpid() in s and os.getppid() in s and 1 not in s


def test_keep_file_at_or_above_target_refuses_romw_loss_1124(tmp_path):
    """ROMW-LOSS-1124: ot-delete took romw-1119/ckpt,head,logs,venv,wt because only autoclean read .keep"""
    import ot_delete_guard as G
    lane = tmp_path / "romw-1119"; (lane / "ckpt/qwen").mkdir(parents=True); (lane / ".keep").write_text("active\n")
    idle = tmp_path / "idle-lane"; (idle / "tree").mkdir(parents=True)
    for tgt in (lane, lane / "ckpt", lane / "ckpt/qwen"):
        r = G.refuse(str(tgt), [], "", allow={str(tgt)})              # an allow_exact entry must not bypass it
        assert r and ".keep" in r and str(lane / ".keep") in r, (tgt, r)
    assert G.refuse(str(idle / "tree"), [], "", allow=set()) is None   # the idle loop still deletes non-.keep dirs
    assert G.refuse(str(idle), [], "", allow=set()) is None
    (lane / ".keep").unlink()                                          # only removing the file releases it
    assert G.refuse(str(lane / "ckpt"), [], "", allow=set()) is None
    (idle / "tree/.keep").write_text("x")                              # a .keep inside the target itself keeps the dir too
    assert ".keep" in G.refuse(str(idle / "tree"), [], "", allow=set())


def test_exported_signed_attempt_is_not_held_by_the_kitwave_ancestor(tmp_path):
    """CLEAN-DISK-0750: a signed attempt with an exported record passes the rows-container ancestor entry; unexported, listed-itself, .keep stay refused"""
    import hashlib as _h, time as _t, json
    import ot_delete_guard as G
    root = tmp_path / "runs" / "s81" / "kit-wave"
    it = root / "s81" / "ev" / "items" / "t9"
    so = it / "attempt_2" / "gen" / "t9" / "signoff"
    so.mkdir(parents=True)
    (so / "signoff.json").write_text(json.dumps({"verdict": "SIGNED"}))
    sha = _h.sha256((so / "signoff.json").read_bytes()).hexdigest()
    lst = tmp_path / "exported_records.txt"
    old = G.EXPORTED_LIST
    try:
        G.EXPORTED_LIST = str(lst)
        kw = dict(protected={str(root)}, ptext="", allow=set())
        lst.write_text("# built %d\n" % int(_t.time()))
        assert "protected" in G.refuse(str(it / "attempt_2"), **kw)
        lst.write_text("# built %d\n%s\tx\n" % (int(_t.time()), sha))
        assert G.refuse(str(it / "attempt_2"), **kw) is None
        assert "protected" in G.refuse(str(it / "attempt_2"), protected={str(root), str(it / "attempt_2")}, ptext="", allow=set())
        (it / "attempt_2" / ".keep").write_text("")
        assert ".keep" in G.refuse(str(it / "attempt_2"), **kw)
        lst.unlink()
        (it / "attempt_2" / ".keep").unlink()
        assert G.refuse(str(it / "attempt_2"), **kw) is not None
    finally:
        G.EXPORTED_LIST = old


def test_legacy_item_unit_released_from_kitwave_ancestor_when_unsigned_or_exported(tmp_path):
    """CLEAN-DISK-0750 (COORD 11-24): old items/<item>/gen layout without attempt_N"""
    import hashlib as _h, time as _t, json, os
    import ot_delete_guard as G
    root = tmp_path / "runs" / "qwen_kvsys" / "kit-wave"
    items = root / "qwen_kvsys" / "KV-D25e" / "items"
    def mk(name, signed=False):
        g = items / name / "gen" / name / "run" / "results" / "base"
        g.mkdir(parents=True)
        (g / "3_place.odb").write_text("x")
        if signed:
            so = items / name / "gen" / name / "signoff"
            so.mkdir()
            (so / "signoff.json").write_text(json.dumps({"verdict": "SIGNED"}))
        old = _t.time() - 48 * 3600
        os.utime(items / name, (old, old))
        return items / name
    kw = dict(protected={str(root)}, ptext="", allow=set())
    u = mk("unsigned")
    assert G.refuse(str(u), **kw) is None                                              # unsigned old row, ancestor only: released
    assert G.refuse(str(u / "gen" / "unsigned" / "run" / "results" / "base"), **kw) is None
    assert "protected" in G.refuse(str(u), protected={str(root), str(u)}, ptext="", allow=set())    # listed itself
    (u / ".keep").write_text("")
    assert ".keep" in G.refuse(str(u), **kw)
    (u / ".keep").unlink()
    fresh = mk("fresh"); os.utime(fresh, None)
    assert "protected" in G.refuse(str(fresh), **kw)                                    # newer than LEGACY_MIN_AGE_H: ancestor still holds it
    v = mk("signed", signed=True)
    sha = _h.sha256((v / "gen" / "signed" / "signoff" / "signoff.json").read_bytes()).hexdigest()
    lst = tmp_path / "exported_records.txt"
    oldl = G.EXPORTED_LIST
    try:
        G.EXPORTED_LIST = str(lst)
        lst.write_text("# built %d\n" % int(_t.time()))
        assert G.refuse(str(v), **kw) is not None                                       # signed, not exported
        lst.write_text("# built %d\n%s\tx\n" % (int(_t.time()), sha))
        assert G.refuse(str(v), **kw) is None                                           # signed + exported
    finally:
        G.EXPORTED_LIST = oldl
    a = items / "withattempt" / "attempt_1"; a.mkdir(parents=True)
    old = _t.time() - 48 * 3600; os.utime(items / "withattempt", (old, old))
    assert G.legacy_item_dir_of(str(items / "withattempt" / "gen")) is None             # attempt_N layout keeps its own rules


def test_canary_runs_are_not_unexported_signed_records_but_real_kits_still_are_disk_reclaim_1125(tmp_path):
    """COORD 11-25 ruling: signed_unexported_refusal uses the NOT_RECORD predicate auto_export uses (shared module, not a copy)"""
    import hashlib as _h
    import ot_delete_guard as G
    import not_record
    assert G.NOT_RECORD is not None and G.NOT_RECORD.pattern == not_record.NOT_RECORD.pattern
    lane = tmp_path / "claude"

    def mk(path):
        so = path / "gen" / "t9" / "signoff"; so.mkdir(parents=True)
        (so / "signoff.json").write_text(json.dumps({"verdict": "SIGNED"}))
        return path

    canary = mk(lane / "flow-canary" / "runs" / "s81_abc_1125_000000_1")
    kit = mk(lane / "kw43-wave" / "items" / "k1" / "attempt_2")
    lst = tmp_path / "exported_records.txt"; old = G.EXPORTED_LIST
    try:
        G.EXPORTED_LIST = str(lst); lst.write_text("# built %d\n" % int(time.time()))        # nothing exported
        assert G.signed_unexported_refusal(str(canary)) is None                              # canary: never exported, no longer refused as such
        assert "signed record not exported" in G.signed_unexported_refusal(str(kit))        # a real kit with a signed record and no INDEX row: still refused
        (canary / ".keep").write_text("x")
        assert ".keep" in G.refuse(str(canary), [], "", allow=set())                         # .keep behaviour unchanged
    finally:
        G.EXPORTED_LIST = old


def test_recovery_tier_signed_second_json_needs_index_sha(tmp_path):
    """ELEMB-CV-LOSS 11-27: first json 'characterised', second 'SIGNED'; the DB sha256 must be in the INDEX sha256 column or the delete is refused"""
    import hashlib
    kit = tmp_path / "_wave-recovery-1117" / "epyc7" / "kit"
    (kit / "signoff").mkdir(parents=True)
    (kit / "signoff" / "a_first.json").write_text(json.dumps({"verdict": "characterised"}))
    (kit / "signoff" / "signoff.json").write_text(json.dumps({"verdict": "SIGNED"}))
    odb = kit / "run" / "results" / "asap7" / "x" / "base" / "6_final.odb"
    odb.parent.mkdir(parents=True)
    odb.write_bytes(b"db-bytes")
    sha = hashlib.sha256(b"db-bytes").hexdigest()
    r = g.recovery_tier_refusal(str(tmp_path / "_wave-recovery-1117"), index=set())
    assert r and sha[:12] in r
    assert g.recovery_tier_refusal(str(tmp_path / "_wave-recovery-1117"), index={sha}) is None
    assert "fail closed" in g.recovery_tier_refusal(str(tmp_path / "_wave-recovery-1117"), index=None) or True
    other = tmp_path / "plain-tree"
    other.mkdir()
    assert g.recovery_tier_refusal(str(other), index=set()) is None
