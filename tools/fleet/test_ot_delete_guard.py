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
