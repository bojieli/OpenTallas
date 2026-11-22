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


def test_host_scoped_otrun_paths_and_plan_refs_clean_aggr_r3(tmp_path, monkeypatch):
    """CLEAN-AGGR-R3: a hub ot-run --hosts epyc8 path protects only on epyc8 + the hub; paths inside a live die plan file are protected"""
    import importlib.util as iu
    H = os.path.dirname(os.path.abspath(__file__))
    sp = iu.spec_from_file_location("bpl_r3", os.path.join(H, "build_protected_live.py")); B = iu.module_from_spec(sp); sp.loader.exec_module(B)
    sg = iu.spec_from_file_location("g_r3", os.path.join(H, "ot_delete_guard.py")); G = iu.module_from_spec(sg); sg.loader.exec_module(G)
    proc = tmp_path / "proc"
    (proc / "11").mkdir(parents=True)
    (proc / "11" / "cmdline").write_bytes(b"python3\0/x/ot-run\0--hosts\0epyc8\0--dir\0/srv/opentallas-scratch2/claude/lane-a/r5\0--\0bash\0/srv/opentallas-scratch2/claude/lane-a/r5/go.sh")
    (proc / "13").mkdir()
    (proc / "13" / "cmdline").write_bytes(b"ssh\0-o\0ServerAliveInterval=30\0epyc8\0cd /srv/opentallas-scratch2/claude/lane-c/r5 && go")
    (proc / "12").mkdir()
    (proc / "12" / "cmdline").write_bytes(b"bash\0/srv/opentallas-scratch2/claude/lane-b/job/run.sh")
    out = set()
    B.live_cmd_paths(out, G.canon, proc=str(proc), unit_dirs=())
    assert "@epyc8,intel2 /srv/opentallas-scratch2/claude/lane-a/r5" in out
    assert "/srv/opentallas-scratch2/claude/lane-b/job/run.sh" in out
    assert "@epyc8,intel2 /srv/opentallas-scratch2/claude/lane-c/r5" in out
    assert B.ssh_host(["ssh", "-i", "k", "ubuntu@epyc7", "x"]) == "epyc7" and B.ssh_host(["ssh", "rtx-pro", "x"]) is None
    lst = tmp_path / "p.txt"
    G.write_list(out, str(lst))
    for host, want in (("loved-redfish", False), ("outgoing-giraffe", True), ("tolerant-swine", True), ("unknown-box", True)):
        monkeypatch.setenv("OT_HOST_ALIAS", host)
        s, err = G.load_list(str(lst))
        assert err is None
        assert ("/srv/opentallas-scratch2/claude/lane-a/r5" in s) == want, host
        assert "/srv/opentallas-scratch2/claude/lane-b/job/run.sh" in s
    plan = tmp_path / "source_plan.json"
    plan.write_text('{"sink_bins_file": "/srv/opentallas-scratch2/claude/kw45/snap_s81_head/s81_head_r4_s0/physical/x/sink_bins_8.json"}')
    cfg = {"dies": {"s81_head": {"enabled": True, "plan": str(plan), "gen_args": []}, "off": {"enabled": False, "plan": str(plan)}}}
    out2 = set()
    n = B.plan_ref_paths(cfg, out2, G.canon, prefix=str(tmp_path))
    assert n == 1 and "/srv/opentallas-scratch2/claude/kw45/snap_s81_head/s81_head_r4_s0/physical/x/sink_bins_8.json" in out2
    g_prot = {G.canon(x) for x in out2}
    assert G.refuse("/srv/opentallas-scratch2/claude/kw45/snap_s81_head/s81_head_r4_s0", protected=g_prot, ptext="", current={}, allow=set())




def test_plan_refs_follow_specs_nested_plans_and_home_clean_aggr_r3(tmp_path):
    import json as _j, os as _o, importlib.util as iu
    H = _o.path.dirname(_o.path.abspath(__file__))
    sg = iu.spec_from_file_location("g_r3b", _o.path.join(H, "ot_delete_guard.py")); G = iu.module_from_spec(sg); sg.loader.exec_module(G)
    nested = tmp_path / "die_plan" / "source_plan.json"
    nested.parent.mkdir()
    nested.write_text('{"sink_bins": "/srv/opentallas-scratch2/claude/kw45/snap_s81_head/s81_head_r4_s0/physical/a/sink_bins_8.json", "h": "/home/ubuntu/scratch/plan-qc/r56/x.json"}')
    top = tmp_path / "plan.json"
    top.write_text(_j.dumps({"src": str(nested)}))
    spec = tmp_path / "coord" / "autopilot" / "private_specs" / "LANE-X" / "k1"
    spec.mkdir(parents=True)
    (spec / "spec.json").write_text(_j.dumps({"plan": "/srv/opentallas-scratch2/claude/qc-plan-r13/v3p6/tree/physical/die_plan/qwen_compute/p.json"}))
    old = spec.parent / "k0"; old.mkdir(); (old / "spec.json").write_text('{"plan": "/srv/opentallas-scratch2/claude/old-lane/t/physical/die_plan/x.json"}')
    _o.utime(old / "spec.json", (1, 1))
    cfg = {"dies": {"s81_head": {"enabled": True, "plan": str(top), "type_args": ["--x", str(top)]}}}
    out = set()
    B.plan_ref_paths(cfg, out, G.canon, prefix=str(tmp_path), coord=str(tmp_path / "coord"))
    assert "/srv/opentallas-scratch2/claude/kw45/snap_s81_head/s81_head_r4_s0/physical/a/sink_bins_8.json" in out      # followed into the nested die_plan json
    assert "/home/ubuntu/scratch/plan-qc/r56/x.json" in out
    assert "/srv/opentallas-scratch2/claude/qc-plan-r13/v3p6/tree/physical/die_plan/qwen_compute/p.json" in out        # live private spec
    assert not any("old-lane" in x for x in out)                                                                    # spec older than 48 h


def test_running_ot_delete_names_no_live_path_clean_aggr_r3(tmp_path):
    import importlib.util as iu
    H = os.path.dirname(os.path.abspath(__file__))
    sp = iu.spec_from_file_location("bpl_r3d", os.path.join(H, "build_protected_live.py")); BB = iu.module_from_spec(sp); sp.loader.exec_module(BB)
    proc = tmp_path / "proc"
    for pid, argv in (("21", b"timeout\x001800\x00python3\x00-I\x00otd/ot-delete\x00/srv/opentallas-scratch2/claude/autopilot/admission_tools/aaaa"),
                      ("22", b"python3\x00-I\x00/home/u/.local/bin/ot-delete\x00/srv/opentallas-scratch2/claude/lane-x/old/tree"),
                      ("23", b"bash\x00/srv/opentallas-scratch2/claude/lane-y/job/run.sh")):
        (proc / pid).mkdir(parents=True)
        (proc / pid / "cmdline").write_bytes(argv)
    out = set()
    BB.live_cmd_paths(out, os.path.normpath, proc=str(proc), unit_dirs=())
    assert out == {"/srv/opentallas-scratch2/claude/lane-y/job/run.sh"}
