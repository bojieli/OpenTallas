"""FLOW-HEALTH-1 11-15: hourly flow report (no LLM).   python3 -m pytest -q tools/autopilot/test_flow_health.py"""
import hashlib
import json
import tempfile
import time
import unittest
from pathlib import Path

import flow_guard as FG
import flow_health as FH
from test_flow_guard import local_rpy

NOW = time.mktime(time.strptime("2026-11-15 07:30:00", "%Y-%m-%d %H:%M:%S"))
LOG = """\
2026-11-15 06:05:55 PST AUTOPILOT: KIT-WAVE LAUNCH qwen_kvsys/a (type, 2 replicas) event-key k
2026-11-15 06:06:41 PST AUTOPILOT: KIT-WAVE LAUNCH qwen_compute/b (type, 24 replicas) event-key k
2026-11-15 06:33:50 PST AUTOPILOT: KIT-WAVE FAIL qwen_kvsys/a INFRA: infra (python exception) @gen: AttributeError: module 'schema' has no attribute 'full_area_hard_ip'
2026-11-15 06:33:51 PST AUTOPILOT: KIT-WAVE FAIL qwen_kvsys/c INFRA: infra (python exception) @gen: AttributeError: module 'schema' has no attribute 'full_area_hard_ip'
2026-11-15 06:44:09 PST AUTOPILOT: KIT-WAVE FAIL s81/t24 FLOW: unclassified failure @place (see log): KW_PLACE_RC=0
2026-11-15 06:54:00 PST AUTOPILOT: KIT-WAVE FAIL s81/t26 PLAN: plan geometry / site @place: GRTM mode
2026-11-15 06:44:04 PST AUTOPILOT: KIT-WAVE ENQUEUE s81/x epyc7:/srv/a geom AP_AUTO_GEOM
2026-11-15 07:01:00 PST AUTOPILOT: KIT-WAVE LAUNCH qwen_kvsys/d (type, 2 replicas) event-key k
2026-11-15 07:02:00 PST AUTOPILOT: KIT-WAVE FAIL qwen_compute/e FLOW: kit-RTL bind of record names HDL sources that are gone @kit_rtl: bind: ERROR preferred HDL source missing: /srv/x/y.sv
2026-11-10 07:02:00 PST AUTOPILOT: KIT-WAVE LAUNCH old/old (type) too old
2026-11-15 07:03:00 PST AUTOPILOT: KIT-WAVE RETRY-IGNORED not a counted line
"""


class Hourly(unittest.TestCase):
    def test_counts_per_hour(self):
        h = FH.hourly(LOG.splitlines(), 48, now=NOW)
        self.assertEqual(sorted(h), ["2026-11-15 06", "2026-11-15 07"])
        a, b = h["2026-11-15 06"], h["2026-11-15 07"]
        self.assertEqual((a["launch"], a["pass"]), (2, 1))
        self.assertEqual(sum(a["pre"].values()), 2)
        self.assertEqual(dict(a["pr"]), {"place": 2})
        self.assertEqual((b["launch"], sum(b["pre"].values()), sum(b["pr"].values())), (1, 1, 0))

    def test_render_has_class_and_stage_columns(self):
        h = FH.hourly(LOG.splitlines(), 48, now=NOW)
        rows = FH.render(h, {"2026-11-15 07": 3}, ["CLASS-X"], now=NOW)
        self.assertEqual(rows[0].split("\t"), FH.HEAD)
        r6 = rows[1].split("\t")
        self.assertIn("2x INFRA", r6[3])
        self.assertIn("2x place", r6[5].replace("place=2", "2x place"))
        r7 = rows[2].split("\t")
        self.assertEqual((r7[7], r7[8]), ("3", "CLASS-X"))

    def test_state_info(self):
        st = {"flow_guard": {"refused": [[NOW, "k", "d/i"], [NOW, "k", "d/j"]], "open": {"cls": {}}}}
        ref, op = FH.state_info(st)
        self.assertEqual((ref["2026-11-15 07"], op), (2, ["cls"]))


class Hostnames(unittest.TestCase):
    def test_link_local_only_is_not_ok(self):
        self.assertFalse(FH.resolve_ok(["fe80::1"]))
        self.assertFalse(FH.resolve_ok([]))
        self.assertTrue(FH.resolve_ok(["127.0.1.1", "fe80::1"]))

    def test_section_flags_bad_host(self):
        fake = lambda h, code, args, timeout=0: {"host": h, "ips": ["fe80::2"]} if h == "bad" else {"host": h, "ips": ["127.0.1.1"]}  # noqa: E731
        rows = FH.hostname_section(fake, ("good", "bad"))
        self.assertIn("good\tgood\t127.0.1.1\tyes", rows)
        self.assertIn("bad\tbad\tfe80::2\tNO", rows)
        self.assertEqual(FH.RESOLVE_PY.count("AP_JSON"), 1)


class Skew(unittest.TestCase):
    def test_section_lists_differing_modules(self):
        files = {"tools/die_plan/gen.py": b"import gen_phys\n", "tools/die_plan/gen_phys.py": b"import schema\n", "tools/die_plan/schema.py": b"X=1\n",
                 "tools/die_plan/bind.py": b"import json\n"}
        tree = Path(tempfile.mkdtemp()) / "src"
        for rel, b in files.items():
            (tree / rel).parent.mkdir(parents=True, exist_ok=True)
            (tree / rel).write_bytes(b)
        (tree / "tools/die_plan/schema.py").write_bytes(b"X=0\n")
        cfg = {"dies": {"kv": {"enabled": True, "gen_host": "h1", "gen_hosts": ["h1"], "src": str(tree), "item_inputs": {}}}}
        out = FH.skew_section(cfg, rpy=local_rpy, blob=lambda rel: files.get(rel), compare_mod=None, now=NOW)
        txt = "\n".join(out)
        self.assertIn("# SKEW 2026-11-15 07:30", txt)
        self.assertIn("kv\th1\t" + str(tree) + "\t1\ttools/die_plan/schema.py", txt)
        (tree / "tools/die_plan/schema.py").write_bytes(b"X=1\n")
        out = FH.skew_section(cfg, rpy=local_rpy, blob=lambda rel: files.get(rel), compare_mod=None, now=NOW)
        self.assertIn("matches main", "\n".join(out))

    def test_compare_module_used_for_cross_host_diffs(self):
        class Mod:
            @staticmethod
            def compare(hosts, src):
                return [], {"tools/die_plan/gen_phys.py": {}, "physical/x.json": {}}
        files = {"tools/die_plan/gen.py": b"import gen_phys\n", "tools/die_plan/gen_phys.py": b"\n"}
        cfg = {"dies": {"kv": {"enabled": True, "gen_host": "h1", "gen_hosts": ["h1", "h2"], "src": "/nonexistent/tree", "item_inputs": {}}}}
        out = FH.skew_section(cfg, rpy=lambda *a, **k: {"error": "x"}, blob=lambda rel: files.get(rel), compare_mod=Mod, now=NOW)
        self.assertTrue(any(l.startswith("kv\t/nonexistent/tree\tok\t1\ttools/die_plan/gen_phys.py") for l in out), out)

    def test_main_writes_file_without_commit(self):
        d = Path(tempfile.mkdtemp())
        (d / "log.txt").write_text(LOG)
        FH.LOG = d / "log.txt"
        FH.STATE = d / "none.json"
        out = d / "out.tsv"
        FH.main(["--out", str(out), "--no-skew", "--hours", "100000"])
        self.assertTrue(out.read_text().startswith("hour\tlaunches"))


if __name__ == "__main__":
    unittest.main()


class OtRunDrift(unittest.TestCase):
    def test_states(self):
        self.assertEqual(FH.ot_run_drift("a\nb\n", "a\nb\n"), ("SAME", 0))
        self.assertEqual(FH.ot_run_drift("a\nb\n", "a\nc\n"), ("DIFFERS", 2))
        self.assertEqual(FH.ot_run_drift(None, "a")[0], "NO-INSTALLED")
        self.assertEqual(FH.ot_run_drift("a", None)[0], "NO-MAIN")

    def test_wrapper_backend_and_section(self):
        d = Path(tempfile.mkdtemp())
        be = d / "be/ot-run"
        be.parent.mkdir()
        be.write_text("x = 1\n")
        w = d / "ot-run"
        w.write_text("#!/bin/sh\n/usr/bin/python3 -I /x/lane-declare \"$@\" || exit $?\nexec /usr/bin/python3 %s \"$@\"\n" % be)
        self.assertEqual(FH.installed_backend(str(w)), str(be))
        rows = FH.ot_run_drift_section(blob=lambda rel: b"x = 1\n", wrapper=str(w), host="h")
        self.assertEqual(rows[-1].split("\t"), ["h", str(be), "SAME", "0"])
        rows = FH.ot_run_drift_section(blob=lambda rel: b"x = 2\n", wrapper=str(w), host="h")
        self.assertEqual(rows[-1].split("\t")[2:], ["DIFFERS", "2"])
        self.assertEqual(FH.installed_backend(str(d / "nope")), "")


class NoprogDrift(unittest.TestCase):
    def test_states(self):
        import hashlib
        h = lambda b: hashlib.sha1(b).hexdigest()
        main = {"tools/autopilot/noprog_watchdog.py": b"a\n", "tools/autopilot/noprog_stage.py": b"b\n"}
        got = {"good": {"noprog_watchdog.py": h(b"a\n"), "noprog_stage.py": h(b"b\n")},
               "old": {"noprog_watchdog.py": h(b"a\n"), "noprog_stage.py": h(b"OLD")},
               "none": {"noprog_watchdog.py": None, "noprog_stage.py": None}}
        rpy = lambda host, code, args, timeout=0: got[host] if host in got else {"error": "ssh"}
        rows = FH.noprog_drift_section(blob=lambda rel: main.get(rel), rpy=rpy, hosts=("good", "old", "none", "down"))
        st = {tuple(r.split("\t")[:2]): r.split("\t")[2] for r in rows[2:]}
        self.assertEqual(st[("good", "noprog_watchdog.py")], "SAME")
        self.assertEqual(st[("old", "noprog_stage.py")], "DIFFERS")
        self.assertEqual(st[("old", "noprog_watchdog.py")], "SAME")
        self.assertEqual(st[("none", "noprog_stage.py")], "MISSING")
        self.assertEqual(st[("down", "noprog_stage.py")], "UNREACHABLE")

    def test_remote_script_hashes_files(self):
        import json, subprocess, sys
        d = Path(tempfile.mkdtemp())
        (d / "noprog_watchdog.py").write_text("x")
        r = subprocess.run([sys.executable, "-I", "-c", FH.SHA_PY, json.dumps({"files": list(FH.NOPROG_FILES), "dir": str(d)})], capture_output=True, text=True)
        out = json.loads([l for l in r.stdout.splitlines() if l.startswith("AP_JSON ")][-1][8:])
        self.assertEqual(out["noprog_stage.py"], None)
        self.assertEqual(len(out["noprog_watchdog.py"]), 40)


class CountGap(unittest.TestCase):
    def test_uncredited_archived_rows_are_listed(self):
        tsv = ("qwen_compute\tcore_a\tcore\t\t/a\t/b\t1\tsha\tvp\tso\tARCHIVED-BOTH\tnote a\\n"
               "qwen_compute\tcore_b\tcore\t\t/a\t/b\t1\tsha\tvp\tso\tARCHIVED-BOTH\\n"
               "qwen_compute\tcore_c\tcore\t\t/a\t/b\t1\tsha\tvp\tso\tARCHIVED-RTX\\n"
               "hbm\ttype_x\ttype\t\t/a\t/b\t1\tsha\tvp\tso\tARCHIVED-BOTH\\n")
        listing = {"agidock_index_tsv": tsv.replace("\\\\n", "\\n")}
        cache = {"plans": {"p1": {"die": "qwen_compute", "signed_cores": {"core_b": ["r"]}}, "p2": {"die": "hbm", "signed_types": {"type_x": ["r"]}}}}
        rows = FH.count_gap_rows(listing, cache)
        self.assertEqual([(r[0], r[1]) for r in rows], [("qwen_compute", "core_a")])

    def test_unreadable_inputs_are_not_a_crash(self):
        self.assertTrue(FH.count_gap_section("/nonexistent", "/nonexistent")[0].startswith("# COUNT-GAP not computed"))


class LocalHost(unittest.TestCase):
    def test_is_local_host_by_hostname_and_fleet_table(self):
        d = Path(tempfile.mkdtemp())
        tab = d / "fleet_hosts.tsv"
        tab.write_text("# c\nintel2\ttolerant-swine\t1.2.3.4\tno\nepyc9\trenewed-glider\t1.2.3.5\tyes\n")
        self.assertTrue(FH.is_local_host("intel2", str(tab), "tolerant-swine"))
        self.assertTrue(FH.is_local_host("tolerant-swine", str(tab), "tolerant-swine.example"))
        self.assertTrue(FH.is_local_host("localhost", str(tab), "x"))
        self.assertFalse(FH.is_local_host("epyc9", str(tab), "tolerant-swine"))
        self.assertFalse(FH.is_local_host("epyc9", str(d / "none"), "tolerant-swine"))

    def test_ssh_rpy_runs_the_script_here_for_this_host(self):
        import unittest.mock as mock
        code = 'import json,sys\nprint("AP_JSON " + json.dumps({"args": json.loads(sys.argv[1])}))\n'
        with mock.patch.object(FH, "is_local_host", lambda h, *a, **k: h == "me"):
            self.assertEqual(FH.ssh_rpy("me", code, {"x": 1}), {"args": {"x": 1}})
            r = FH.ssh_rpy("other-host-that-does-not-exist.invalid", code, {"x": 1}, timeout=20)
        self.assertIn("error", r)                      # a remote host still goes through ssh
