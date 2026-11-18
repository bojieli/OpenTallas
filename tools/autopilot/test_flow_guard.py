"""FLOW-HEALTH-1 11-15: flow_guard preflight (paths, tree skew, count frames), class circuit-breaker, skew report, kit_wave gate.
    python3 -m pytest -q tools/autopilot/test_flow_guard.py"""
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import flow_guard as FG
import kit_wave as KW


def local_rpy(host, code, args, timeout=600, roots=None):
    """runs the remote script locally; host 'b' sees tree /A as /B (a second copy), so two 'hosts' can differ"""
    txt = json.dumps(args)
    if roots and host in roots:
        txt = txt.replace(roots["from"], roots[host])
    r = subprocess.run([sys.executable, "-I", "-c", code, txt], capture_output=True, text=True)
    line = [ln for ln in r.stdout.splitlines() if ln.startswith("AP_JSON ")]
    if not line:
        return {"error": r.stderr[-300:]}
    out = line[-1][8:]
    if roots and host in roots:
        out = out.replace(roots[host], roots["from"])
    return json.loads(out)


def two_hosts(a):
    return lambda host, code, args, timeout=600: local_rpy(host, code, args, timeout, roots={"from": str(a), "b": str(a) + "_b"})


def mk(tmp):
    """a kit input set: bind dir with bind.f, an as-built json with base + relative prefer + abs HDL, a recipe .sh"""
    a = Path(tmp) / "A"
    (a / "rtl").mkdir(parents=True)
    (a / "rtl/ok.sv").write_text("module ok; endmodule\n")
    (a / "rtl/ok2.sv").write_text("module ok2; endmodule\n")
    (a / "bind").mkdir()
    (a / "bind/bind.f").write_text(f"{a}/rtl/ok.sv\n")
    (a / "asbuilt.json").write_text(json.dumps({"base": str(a), "prefer": ["rtl/ok2.sv"], "files": ["rtl/ok.sv"], "x": {"y": str(a / "rtl/ok.sv")}}))
    (a / "recipe.sh").write_text(f"export S81_ASBUILT={a}/asbuilt.json\n")
    return a


def mirror(a):
    """host b's copy"""
    import shutil
    b = Path(str(a) + "_b")
    shutil.copytree(a, b)
    for f in b.rglob("*"):
        if f.is_file() and f.suffix in (".json", ".f", ".sh"):
            f.write_text(f.read_text().replace(str(a), str(b)))
    return b


class Keys(unittest.TestCase):
    def test_norm_class_masks_paths_hashes_numbers(self):
        k1 = FG.norm_class("FLOW", "bind: ERROR preferred HDL source missing: /srv/opentallas-scratch2/claude/die-qc-103/treeA/a.sv, /srv/x/b.sv; restore")
        k2 = FG.norm_class("FLOW", "bind: ERROR preferred HDL source missing: /srv/opentallas-scratch3/claude/die-qc-9/treeB/c.sv; restore")
        self.assertEqual(k1, k2)
        self.assertEqual(FG.pf_kind(k1), "paths")
        self.assertEqual(FG.pf_kind(FG.norm_class("INFRA", "@gen: AttributeError: module 'schema' has no attribute 'full_area_hard_ip'")), "skew")
        self.assertEqual(FG.pf_kind(FG.norm_class("FLOW", "tool / Tcl error @place: ModuleNotFoundError: No module named 'ot_store'")), "skew")
        self.assertEqual(FG.pf_kind("FLOW: hold after CTS"), "")
        self.assertEqual(FG.fail_stage("x @kit_rtl: y"), "kit_rtl")


class Paths(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.a = mk(self.tmp)

    def check(self, paths):
        return local_rpy("a", FG.PATHS_PY, {"paths": paths})

    def test_whole_inputs_pass(self):
        r = self.check([str(self.a / "bind"), str(self.a / "asbuilt.json"), str(self.a / "recipe.sh")])
        self.assertTrue(all(not v["hard"] and not v["soft"] for v in r.values()), r)

    def test_bind_f_source_gone(self):
        (self.a / "rtl/ok.sv").unlink()
        r = self.check([str(self.a / "bind")])
        self.assertIn("ok.sv", r[str(self.a / "bind")]["hard"][0])

    def test_asbuilt_relative_prefer_resolved_against_base(self):
        (self.a / "rtl/ok2.sv").unlink()
        r = self.check([str(self.a / "asbuilt.json")])
        self.assertIn("ok2.sv", r[str(self.a / "asbuilt.json")]["hard"][0])

    def test_recipe_script_followed_into_json_into_hdl(self):
        code = FG.PATHS_PY.replace("(?:srv|home)", "(?:srv|home|tmp)")        # test trees live in /tmp
        (self.a / "rtl/ok.sv").unlink()
        r = local_rpy("a", code, {"paths": [str(self.a / "recipe.sh")]})
        v = r[str(self.a / "recipe.sh")]
        self.assertTrue(v["hard"] or v["soft"], v)
        self.assertIn("ok.sv", (v["hard"] + v["soft"])[0])

    def test_missing_top_path(self):
        self.assertEqual(self.check([str(self.a / "nope")])[str(self.a / "nope")]["hard"], [str(self.a / "nope")])

    def test_broken_link_below_lane_dir(self):
        lane = Path(self.tmp) / "srv" / "x" / "claude" / "lane" / "tree"      # LANE regex: /srv/<d>/claude/<l>/<t>
        # emulate the regex with a replaced pattern for /tmp
        orig = r'LANE = re.compile(r"^/srv/[^/]+/claude/[^/]+/[^/]+")'
        self.assertIn(orig, FG.PATHS_PY)
        code = FG.PATHS_PY.replace(orig, 'LANE = re.compile(r"^' + re.escape(str(self.a)) + '")')      # wherever TMPDIR is
        (self.a / "d").mkdir()
        (self.a / "d/l").symlink_to(self.a / "gone")
        r = local_rpy("a", code, {"paths": [str(self.a / "d")]})
        self.assertIn("broken link", r[str(self.a / "d")]["hard"][0])

    def test_incidental_hdl_strings_are_soft(self):
        (self.a / "prov.json").write_text(json.dumps({"note": {"old": "/srv/zzz/old.sv"}}))
        v = self.check([str(self.a / "prov.json")])[str(self.a / "prov.json")]
        self.assertEqual(v["hard"], [])
        self.assertTrue(v["soft"])


class Tree(unittest.TestCase):
    def tree(self, schema_body, gen_phys_body, extra=None):
        t = Path(tempfile.mkdtemp()) / "src"
        d = t / "tools/die_plan"
        d.mkdir(parents=True)
        (t / "physical/common_flow").mkdir(parents=True)
        (d / "gen.py").write_text("import gen_phys\n")
        (d / "bind.py").write_text("import json\n")
        (d / "gen_phys.py").write_text(gen_phys_body)
        (d / "schema.py").write_text(schema_body)
        for n, b in (extra or {}).items():
            (d / n).write_text(b)
        return t

    def probe(self, t, known=""):
        return local_rpy("a", FG.tree_code(["core_view_sha", "ot_store", "schema", "gen_phys"]), {"tree": str(t), "known": known,
                         "entry": list(FG.ENTRY_FILES), "search": list(FG.SEARCH_DIRS)})

    def test_healthy_tree(self):
        t = self.tree("def full_area_hard_ip(): pass\nX = 1\n", "import schema\nfrom schema import X\nprint(schema.full_area_hard_ip, schema.X)\n")
        r = self.probe(t)
        self.assertEqual(r["bad"], [], r)

    def test_gen_phys_newer_than_schema(self):
        t = self.tree("X = 1\n", "import schema\ndef f():\n    return schema.full_area_hard_ip()\n")
        r = self.probe(t)
        self.assertTrue(any("full_area_hard_ip" in b for b in r["bad"]), r)

    def test_from_import_name_absent(self):
        t = self.tree("X = 1\n", "from schema import tap_offset_table\n")
        self.assertTrue(any("tap_offset_table" in b for b in self.probe(t)["bad"]))

    def test_lazy_import_of_module_missing_from_tree(self):
        t = self.tree("X = 1\n", "def f():\n    import core_view_sha as c\n    return c\n")
        self.assertTrue(any("core_view_sha" in b for b in self.probe(t)["bad"]))
        (t / "tools/die_plan/core_view_sha.py").write_text("Y = 1\n")
        self.assertEqual(self.probe(t)["bad"], [])

    def test_third_party_and_shadowed_names_are_not_skew(self):
        t = self.tree("X = 1\n", "import matplotlib\nimport schema\ndef f(schema):\n    return schema.whatever\n")
        self.assertEqual(self.probe(t)["bad"], [])
        t = self.tree("X = 1\n", "import schema\nschema = {}\nschema.update(a=1)\n")
        self.assertEqual(self.probe(t)["bad"], [])

    def test_no_local_names_turns_the_missing_module_check_off(self):
        t = self.tree("X = 1\n", "def f():\n    import core_view_sha\n")
        r = local_rpy("a", FG.tree_code(None), {"tree": str(t), "known": "", "entry": list(FG.ENTRY_FILES), "search": list(FG.SEARCH_DIRS)})
        self.assertEqual(r["bad"], [])

    def test_optional_import_in_try_is_fine(self):
        t = self.tree("X = 1\n", "try:\n    import ot_store\nexcept ImportError:\n    ot_store = None\n")
        self.assertEqual(self.probe(t)["bad"], [])

    def test_module_with_getattr_or_star_is_not_judged(self):
        t = self.tree("def __getattr__(n): return 1\n", "import schema\nschema.anything\n")
        self.assertEqual(self.probe(t)["bad"], [])

    def test_digest_same_answer_and_cache(self):
        t = self.tree("X = 1\n", "import schema\n")
        g = FG.fg_state({})
        calls = []

        def rpy(h, code, args, timeout=0):
            calls.append(args.get("known"))
            return local_rpy(h, code, args)
        self.assertEqual(FG.probe_tree({"trees": {}}, "a", str(t), rpy, 1000), [])   # code=None: attribute skew only
        g = {"trees": {}}
        FG.probe_tree(g, "a", str(t), rpy, 1000)
        FG.probe_tree(g, "a", str(t), rpy, 1100)                 # inside TTL: no call
        self.assertEqual(len(calls), 2)
        FG.probe_tree(g, "a", str(t), rpy, 1000 + FG.TREE_TTL_S + 1)   # TTL over: asks with the digest, remote answers same
        self.assertEqual(calls[-1], g["trees"]["a"][str(t)]["digest"])
        self.assertEqual(g["trees"]["a"][str(t)]["bad"], [])
        (t / "tools/die_plan/schema.py").write_text("X = 2  # changed\n")
        FG.probe_tree(g, "a", str(t), rpy, 5000)
        self.assertNotEqual(calls[-1], "")


class Preflight(unittest.TestCase):
    def test_host_lacking_a_source_is_dropped_item_launches_elsewhere_then_nowhere(self):
        tmp = tempfile.mkdtemp()
        a = mk(tmp)
        b = mirror(a)
        (b / "rtl/ok2.sv").unlink()                     # host b lacks a preferred source
        rpy = two_hosts(a)
        g = FG.fg_state({})
        items = {"t1": {"paths": [str(a / "asbuilt.json"), str(a / "bind")], "trees": [], "plans": []}}
        r = FG.preflight_items(g, items, {"t1": ["a", "b"]}, rpy, now=1000)["t1"]
        self.assertEqual(r["ok"], ["a"])
        self.assertIn("b", r["bad"])
        self.assertIn("ok2.sv", r["bad"]["b"])
        (a / "rtl/ok2.sv").unlink()
        g = FG.fg_state({})
        r = FG.preflight_items(g, items, {"t1": ["a", "b"]}, rpy, now=1000)["t1"]
        self.assertEqual(r["ok"], [])
        self.assertEqual(r["kind"], "paths")

    def test_unreachable_host_is_unknown_not_bad(self):
        a = mk(tempfile.mkdtemp())
        g = FG.fg_state({})
        r = FG.preflight_items(g, {"t": {"paths": [str(a / "nope")], "trees": [], "plans": []}}, {"t": ["h"]},
                               lambda *x, **k: {"error": "ssh"}, now=1)["t"]
        self.assertEqual((r["ok"], r["bad"]), (["h"], {}))

    def test_missing_path_everywhere_soft_names_do_not_refuse(self):
        a = mk(tempfile.mkdtemp())
        b = mirror(a)
        (a / "prov.json").write_text(json.dumps({"old": "/srv/zzz/old.sv"}))
        (b / "prov.json").write_text(json.dumps({"old": "/srv/zzz/old.sv"}))
        g = FG.fg_state({})
        r = FG.preflight_items(g, {"t": {"paths": [str(a / "prov.json")], "trees": [], "plans": []}}, {"t": ["a", "b"]}, two_hosts(a), now=1)["t"]
        self.assertEqual(r["bad"], {})

    def test_count_frame_files_beside_plan_must_exist_on_every_host(self):
        tmp = tempfile.mkdtemp()
        a = Path(tmp) / "A"
        (a / "plan_of_record").mkdir(parents=True)
        d = a / "plan_of_record"
        (d / "plan.json").write_text("{}")
        for n in ("feed_s1.json", "regions_s1.json"):
            (d / n).write_text("{}")
        b = Path(str(a) + "_b")
        import shutil
        shutil.copytree(a, b)
        (b / "plan_of_record/regions_s1.json").unlink()
        it = {"t": {"paths": [], "trees": [], "plans": [str(d / "plan.json")]}}
        r = FG.preflight_items(FG.fg_state({}), it, {"t": ["a", "b"]}, two_hosts(a), now=1)["t"]
        self.assertEqual(r["ok"], ["a"])
        self.assertIn("regions_s1.json", r["bad"]["b"])
        # a host with no frame at all while another has them
        for f in list((b / "plan_of_record").glob("*_s1.json")):
            f.unlink()
        r = FG.preflight_items(FG.fg_state({}), it, {"t": ["a", "b"]}, two_hosts(a), now=1)["t"]
        self.assertIn("count-frame", r["bad"]["b"])
        self.assertEqual(r["ok"], ["a"])


class Breaker(unittest.TestCase):
    def setUp(self):
        self._cn = FG.CLASS_N
        FG.CLASS_N = 10               # these tests exercise the legacy per-class breaker; the class-level breaker (CLASS_N = 3) is tested in test_flow_breaker_deadlock

    def tearDown(self):
        FG.CLASS_N = self._cn

    WHY = "kit-RTL bind of record names HDL sources that are gone @kit_rtl: bind: ERROR preferred HDL source missing: /srv/a/b%d.sv"

    def fails(self, st, n, t0=1000.0, why=None):
        for i in range(n):
            FG.record_fail(st, "qc", f"it{i}", "FLOW", (why or self.WHY) % i if "%d" in (why or self.WHY) else why, evidence=f"/log/{i}.log", now=t0 + i)

    def test_four_fails_stay_closed_fifth_opens_and_holds_last_fail_items(self):
        st = {}
        self.fails(st, 4)
        self.assertEqual(FG.held_key(st, "qc", "it0"), "")
        self.fails(st, 5)
        self.assertTrue(FG.held_key(st, "qc", "it0"))
        self.assertEqual(FG.held_key(st, "qc", "other"), "")
        lines = FG.alert_lines(st, "2026-11-15 07:00 PST")
        self.assertEqual(len(lines), 1)
        self.assertIn("ALERT", lines[0][1])
        self.assertIn("/log/0.log", lines[0][1])
        self.assertEqual(FG.alert_lines(st, "x"), [])                                  # once

    def test_window_30_min(self):
        st = {}
        for i in range(5):
            FG.record_fail(st, "qc", f"i{i}", "FLOW", self.WHY % 1, now=1000 + i * 500)   # 2000 s span > 1800: never 5 in the window
        self.assertEqual(FG.held_key(st, "qc", "i4"), "")

    def test_item_that_failed_another_class_since_is_not_held(self):
        st = {}
        self.fails(st, 5)
        FG.record_fail(st, "qc", "it0", "PLAN", "plan geometry @place: x", now=1100)
        self.assertEqual(FG.held_key(st, "qc", "it0"), "")

    def test_preflight_release_when_all_held_pass(self):
        st = {}
        self.fails(st, 5)
        key = FG.held_key(st, "qc", "it1")
        self.assertEqual(FG.release_by_preflight(st, {key: [True, False]}), [])
        self.assertEqual(len(FG.release_by_preflight(st, {key: [True, True]}, now=2000)), 1)     # WAVE-PILOT-FIX: opens the PROBE window, closes nothing
        self.assertIn(key, st["flow_guard"]["open"])
        self.assertEqual(FG.held_key(st, "qc", "it1", claim=True), "")                          # the probe launches
        FG.probe_result(st, "qc", "it1", "place", passed=True)                                   # only a probe passing the stage closes the class
        self.assertEqual(FG.held_key(st, "qc", "it1"), "")
        # probation: the same class reopens after 2 fails
        FG.record_fail(st, "qc", "z1", "FLOW", self.WHY % 1, now=2100)
        FG.record_fail(st, "qc", "z2", "FLOW", self.WHY % 2, now=2101)
        self.assertTrue(FG.held_key(st, "qc", "z2"))

    def test_unjudgeable_class_half_opens_after_cooldown(self):
        st = {}
        why = "hold after CTS @cts: setup -3 ps"
        for i in range(5):
            FG.record_fail(st, "qc", f"i{i}", "FLOW", why, now=1000 + i)
        self.assertTrue(FG.held_key(st, "qc", "i0"))           # stage cts: record_fail itself counts any class; kit_wave filters
        self.assertEqual(FG.breaker_tick(st, now=1000 + 100), [])
        self.assertGreaterEqual(len(FG.breaker_tick(st, now=1004 + FG.BREAKER_COOLDOWN_S + 1)), 1)
        self.assertEqual(FG.held_key(st, "qc", "i0"), "")


class SkewReport(unittest.TestCase):
    def test_closure_and_diff(self):
        files = {"tools/die_plan/gen.py": "import gen_phys\n", "tools/die_plan/gen_phys.py": "import schema, ot_store\n",
                 "tools/die_plan/schema.py": "X=1\n", "tools/fleet/ot_store.py": "Z=1\n"}
        rd = lambda rel: files.get(rel)      # noqa: E731
        cl = FG.closure_files(rd, search=("tools/die_plan", "tools", "tools/fleet"))
        self.assertEqual(cl, ["tools/die_plan/gen.py", "tools/die_plan/gen_phys.py", "tools/die_plan/schema.py", "tools/fleet/ot_store.py"])
        tree = Path(tempfile.mkdtemp())
        for rel, txt in files.items():
            (tree / rel).parent.mkdir(parents=True, exist_ok=True)
            (tree / rel).write_text(txt)
        (tree / "tools/die_plan/schema.py").write_text("X=2\n")           # differs
        (tree / "tools/fleet/ot_store.py").unlink()                         # missing counts
        import hashlib
        sha = lambda rel: hashlib.sha1(files[rel].encode()).hexdigest() if rel in files else None   # noqa: E731
        orig = FG.closure_files
        FG.closure_files = lambda read, **k: orig(read, search=("tools/die_plan", "tools", "tools/fleet"))
        try:
            rows = FG.skew_report([("qc", str(tree))], sha, rd, local_rpy, {"qc": ["h"]})
        finally:
            FG.closure_files = orig
        self.assertEqual(len(rows), 1)
        self.assertEqual(sorted(rows[0][3]), ["tools/die_plan/schema.py", "tools/fleet/ot_store.py"])


class KitWaveGate(unittest.TestCase):
    class AP:
        def __init__(self):
            self.logs, self.q = [], []
            self.rpy = local_rpy

        def log(self, m):
            self.logs.append(m)

        def coord_append(self, rel, line):
            self.q.append((rel, line))

    def setUp(self):
        self._cn = FG.CLASS_N
        FG.CLASS_N = 10                                     # legacy per-class breaker under test; CLASS_N = 3 is tested in test_flow_breaker_deadlock
        self.addCleanup(lambda: setattr(FG, "CLASS_N", self._cn))
        self.tmp = tempfile.mkdtemp()
        self.a = mk(self.tmp)
        self.cfg = {"dies": {"qc": {"gen_host": "a", "gen_hosts": ["a"], "src": "", "plan": "",
                                    "kit_rtl": {"script": str(self.a / "recipe.sh"), "bind_out": str(self.a / "bind")}}}}

    def test_missing_path_item_is_refused_one_queue_line_per_class(self):
        (self.a / "rtl/ok.sv").unlink()                    # named by bind.f
        ap, st = self.AP(), {}
        go = [{"item": f"it{i}"} for i in range(3)]
        skip = {}
        out = KW.flow_guard_gate(ap, self.cfg, st, "qc", go, go, skip, now=1000, rpy=local_rpy)
        self.assertEqual(out, [])
        self.assertTrue(any("FLOW-PREFLIGHT" in k for k in skip))
        asks = [l for _, l in ap.q if "PREFLIGHT-REFUSED" in l]
        self.assertEqual(len(asks), 1)
        KW.flow_guard_gate(ap, self.cfg, st, "qc", go, go, {}, now=1100, rpy=local_rpy)       # next tick: no second line
        self.assertEqual(len([l for _, l in ap.q if "PREFLIGHT-REFUSED" in l]), 1)
        (self.a / "rtl").mkdir(exist_ok=True)
        (self.a / "rtl/ok.sv").write_text("module ok; endmodule\n")
        out = KW.flow_guard_gate(ap, self.cfg, st, "qc", go, go, {}, now=1300, rpy=local_rpy)  # inputs back: launches
        self.assertEqual(len(out), 3)

    def test_breaker_holds_then_preflight_release(self):
        ap, st = self.AP(), {}
        for i in range(5):
            FG.record_fail(st, "qc", f"it{i}", "FLOW", "@kit_rtl: preferred HDL source missing: /srv/x/a%d.sv" % i, evidence="/l.log", now=1000 + i)
        go = [{"item": "it0"}, {"item": "fresh"}]
        skip = {}
        # inputs are whole, so the preflight passes for the held row at once: the PROBE window opens (WAVE-PILOT-FIX: a preflight closes nothing)
        out = KW.flow_guard_gate(ap, self.cfg, st, "qc", go, go, skip, now=1010, rpy=local_rpy)
        self.assertEqual([r["item"] for r in out], ["it0", "fresh"])
        self.assertTrue(any("RELEASE" in m for m in ap.logs))
        # a class the preflight cannot judge stays held
        st2 = {}
        for i in range(5):
            FG.record_fail(st2, "qc", f"it{i}", "FLOW", "@place: some other error", evidence="/l.log", now=1000 + i)
        skip = {}
        out = KW.flow_guard_gate(ap, self.cfg, st2, "qc", go, go, skip, now=1010, rpy=local_rpy)
        self.assertEqual([r["item"] for r in out], ["fresh"])
        self.assertTrue(any("FLOW-BREAKER" in k for k in skip))
        self.assertEqual(len([1 for _, l in ap.q if "ALERT" in l]), 2)            # the gate posts each open class once (the first stays open in PROBE state)

    def test_launch_refuses_a_held_item(self):
        st = {}
        for i in range(5):
            FG.record_fail(st, "qc", f"it{i}", "FLOW", "@place: some other error", now=1000 + i)
        ap = self.AP()
        self.assertIsNone(KW.launch(ap, self.cfg, st, "qc", {"item": "it0"}, "hub"))
        self.assertTrue(any("LAUNCH-HELD" in m for m in ap.logs))

    def test_reason_tagged_puts_class_text_first(self):
        r = KW.reason_tagged("kit-RTL bind names HDL sources that are gone @kit_rtl: x", "PROVISIONAL[" + ",".join("m%d:routed" % i for i in range(40)) + "]")
        self.assertTrue(r.startswith("kit-RTL bind names"))
        self.assertLessEqual(len(r), 240)
        self.assertEqual(KW.reason_tagged("", "PROVISIONAL[a:b]"), "PROVISIONAL[a:b]")


if __name__ == "__main__":
    unittest.main()
