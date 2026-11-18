import json, os, tempfile, unittest
import build_protected_live as B

R = "/srv/opentallas-scratch2/claude/"


def mk(cfg, markers=(), prose=""):
    d = tempfile.mkdtemp(); os.makedirs(d + "/autopilot"); os.makedirs(d + "/lanes/handoff")
    json.dump(cfg, open(d + "/autopilot/kit_wave.json", "w"))
    for i, m in enumerate(markers):
        json.dump(m, open(d + "/lanes/handoff/tree_switch_%d.json" % i, "w"))
    open(d + "/lanes/COORD-REVIEW-QUEUE.md", "w").write(prose)
    open(d + "/lanes/handoff/x.md", "w").write(prose)
    return d


class Live(unittest.TestCase):
    def test_current_keys_kept_history_and_prose_dropped(self):
        cfg = {"dies": {"s81": {"src": R + "kw45/src_cur", "plan": R + "kw45/src_cur/plan.json", "src_prev_d4": R + "kw45/src_old",
                                "superseded_trees": [R + "kw45/src_gone"], "rollback_tree": R + "kw45/src_rb", "note_x": "see " + R + "lane/z/deep/a",
                                "item_inputs": {"a": R + "kw45/inputs_cur/x"}, "item_inputs_prev_kw43": {"a": R + "kw43/old/in/x"}}}}
        d = mk(cfg, prose="quoted " + R + "foo/bar/baz/qux and " + R + "kw45/src_gone")
        got = B.build(d, [d + "/lanes/handoff"])
        self.assertEqual(got, {R + "kw45/src_cur", R + "kw45/src_cur/plan.json", R + "kw45/src_rb", R + "kw45/inputs_cur/x"})

    def test_markers_use_the_same_rule_and_protected_dbs_count(self):
        d = mk({"dies": {}}, markers=[{"tree": R + "kw45/src_new", "superseded_trees": [R + "kw45/src_old"], "prev_tree": R + "kw45/src_older"}])
        open(d + "/PROTECTED-DBS.txt", "w").write(R + "db/keep/me/here # why\n/tmp/nope\n")
        self.assertEqual(B.build(d, [d + "/lanes/handoff"]), {R + "kw45/src_new", R + "db/keep/me/here"})

    def test_unreadable_kit_wave_refuses_an_empty_list(self):
        with self.assertRaises(SystemExit):
            B.build(tempfile.mkdtemp(), [])


class Cutover(unittest.TestCase):
    def test_a_prov_view_sources_current_kept_prev_dropped(self):
        cfg = {"dies": {"s81": {"prov_view_sources": {"v": R + "views/cur/a/b"}, "prov_view_sources_prev_kw43": {"v": R + "views/old/a/b"}}}}
        d = mk(cfg)
        self.assertEqual(B.build(d, []), {R + "views/cur/a/b"})

    def test_b_in_flight_event_json_recent_only(self):
        d = mk({"dies": {}}); os.makedirs(d + "/autopilot/tree_checks")
        json.dump({"bind": R + "events/c4/bind/x", "superseded_trees": [R + "kw45/src_x"]}, open(d + "/autopilot/tree_checks/aa", "w"))
        old = d + "/autopilot/tree_checks/bb"; json.dump({"bind": R + "events/old/bind/y"}, open(old, "w")); os.utime(old, (1, 1))
        out = set(); B.event_paths(d, out, os.path.normpath)
        self.assertEqual(out, {R + "events/c4/bind/x"})

    def test_c_cmdlines_and_units(self):
        p = tempfile.mkdtemp(); os.makedirs(p + "/123"); open(p + "/123/cmdline", "wb").write(("ot-run --dir " + R + "lane/q/run/x --stage " + R + "t/a/b/c").encode().replace(b" ", b"\0"))
        u = tempfile.mkdtemp(); open(u + "/a.service", "w").write("ExecStart=python3 " + R + "svc/tools/a/b.py")
        out = set(); B.live_cmd_paths(out, os.path.normpath, proc=p, unit_dirs=(u,))
        self.assertEqual(out, {R + "lane/q/run/x", R + "t/a/b/c", R + "svc/tools/a/b.py"})

    def test_d_handoff_prose_last_24h_not_queue_not_coord(self):
        d = tempfile.mkdtemp(); new = d + "/lane.md"; old = d + "/old.md"; q = d + "/COORD-REVIEW-QUEUE.md"; cd = d + "/COORD-X.md"
        for f in (new, old, q, cd): open(f, "w").write("see " + R + ("n/e/w/" if f == new else "o/l/d/") + "path")
        os.utime(old, (1, 1))
        out = set(); B.prose_paths([new, old, q, cd], out, os.path.normpath)
        self.assertEqual(out, {R + "n/e/w/path"})


class Superseded(unittest.TestCase):
    def test_superseded_marker_protects_nothing_but_a_live_one_does(self):
        d = mk({"dies": {}}, markers=[{"status": "SUPERSEDED by D16 (COORD)", "tree": R + "kw45/src_dead/a/b"}, {"status": "PENDING CANDIDATE NOT ADOPTED", "tree": R + "kw45/src_live/a/b"}])
        self.assertEqual(B.build(d, [d + "/lanes/handoff"]), {R + "kw45/src_live/a/b"})


class MainIgnoresProse(unittest.TestCase):
    def test_main_does_not_protect_a_path_quoted_only_in_a_handoff_note(self):
        import os, subprocess, sys, tempfile
        R = "/srv/opentallas-scratch2/claude/"
        d = mk({"dies": {}}, prose="BUILD RUNNING kit at " + R + "lane-x/sd9h_gen NEXT export")
        out = tempfile.mkdtemp() + "/list.txt"
        r = subprocess.run([sys.executable, "-I", os.path.join(os.path.dirname(os.path.abspath(__file__)), "build_protected_live.py"), d, out], capture_output=True, text=True, env=dict(os.environ, OT_PROV_PATHS_CACHE="/nonexistent"))
        txt = open(out).read() if os.path.exists(out) else ""
        self.assertNotIn("sd9h_gen", txt, r.stdout + r.stderr)
