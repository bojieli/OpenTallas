"""WAVE-CONFIG 11-16: kit_wave_edit (JSON patch + commit in one step), the wave reading the committed HEAD blob, the lock owner in the skip line."""
import fcntl, json, os, subprocess, sys, tempfile, unittest, unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW  # noqa: E402
import kit_wave_edit as KE  # noqa: E402

CFG = {"enabled": True, "max_inflight": 5, "hosts": ["a", "b"], "dies": {"kv": {"owner_lane": "KV-R"}}}


def repo(cfg=CFG):
    d = tempfile.mkdtemp()
    g = lambda *a: subprocess.run(["git", "-C", d, "-c", "user.name=t", "-c", "user.email=t@t", *a], check=True, capture_output=True, text=True)
    g("init", "-q")
    (Path(d) / "autopilot").mkdir()
    (Path(d) / "autopilot/kit_wave.json").write_text(KE.dump(cfg))
    g("add", "-A"); g("commit", "-q", "-m", "init")
    return d, g


class Patch(unittest.TestCase):
    def test_ops(self):
        r = KE.apply_patch(CFG, [{"op": "replace", "path": "/max_inflight", "value": 9}, {"op": "add", "path": "/hosts/-", "value": "c"},
                                 {"op": "add", "path": "/dies/kv/x", "value": {"a": 1}}, {"op": "remove", "path": "/enabled"},
                                 {"op": "test", "path": "/hosts/0", "value": "a"}])
        self.assertEqual((r["max_inflight"], r["hosts"], r["dies"]["kv"]["x"], "enabled" in r), (9, ["a", "b", "c"], {"a": 1}, False))
        self.assertEqual(CFG["max_inflight"], 5)                       # input untouched

    def test_bad_ops_refuse_whole_patch(self):
        for ops in ([{"op": "replace", "path": "/nope", "value": 1}], [{"op": "test", "path": "/enabled", "value": False}],
                    [{"op": "remove", "path": "/hosts/9"}], [{"op": "move", "path": "/a"}], {"op": "add"}, [{"op": "add", "path": "/x"}]):
            with self.assertRaises(KE.PatchError):
                KE.apply_patch(CFG, ops)

    def test_pointer_escapes(self):
        r = KE.apply_patch({"a/b": {"c~d": 1}}, [{"op": "replace", "path": "/a~1b/c~0d", "value": 2}])
        self.assertEqual(r, {"a/b": {"c~d": 2}})


class Edit(unittest.TestCase):
    def test_patch_and_commit_in_one_step(self):
        d, g = repo()
        calls = []

        def commit(msg, rel):
            calls.append((msg, rel)); g("add", "--", rel); g("commit", "-q", "-m", msg)
        KE.edit(d, [{"op": "replace", "path": "/max_inflight", "value": 7}], "KW: test", commit_cmd=commit)
        self.assertEqual(calls, [("KW: test", "autopilot/kit_wave.json")])
        self.assertEqual(json.loads(g("show", "HEAD:autopilot/kit_wave.json").stdout)["max_inflight"], 7)
        self.assertEqual(g("status", "--short").stdout.strip(), "")

    def test_append_only_followup_does_not_trigger_cas_repair(self):
        d, g = repo()
        messages = []

        def commit(msg, rel):
            messages.append(msg)
            g("add", "--", rel)
            g("commit", "-q", "-m", msg)
            own = g("rev-parse", "HEAD").stdout.strip()
            (Path(d) / "journal").write_text("a concurrent append\n")
            g("add", "journal")
            g("commit", "-q", "-m", "journal append")
            return own

        ops = [{"op": "test", "path": "/max_inflight", "value": 5},
               {"op": "replace", "path": "/max_inflight", "value": 7}]
        self.assertEqual(json.loads(KE.edit(d, ops, "own edit", commit_cmd=commit))["max_inflight"], 7)
        self.assertEqual(messages, ["own edit"])
        self.assertEqual(g("log", "-2", "--format=%s").stdout.splitlines(), ["journal append", "own edit"])

    def test_real_intervening_config_commit_still_gets_repaired(self):
        d, g = repo()
        work = Path(d) / KE.REL
        messages = []

        def commit(msg, rel):
            if not messages:
                patched = work.read_text()
                work.write_text(KE.dump(dict(CFG, unmatched_key=42)))
                g("add", "--", rel)
                g("commit", "-q", "-m", "intervening config")
                work.write_text(patched)
            messages.append(msg)
            g("add", "--", rel)
            g("commit", "-q", "-m", msg)
            own = g("rev-parse", "HEAD").stdout.strip()
            (Path(d) / "journal").write_text(msg + "\n")
            g("add", "journal")
            g("commit", "-q", "-m", "journal append")
            return own

        ops = [{"op": "test", "path": "/max_inflight", "value": 5},
               {"op": "replace", "path": "/max_inflight", "value": 7}]
        result = json.loads(KE.edit(d, ops, "own edit", commit_cmd=commit))
        self.assertEqual((result["max_inflight"], result["unmatched_key"]), (7, 42))
        self.assertEqual(len(messages), 2)
        self.assertIn("CAS repair", messages[-1])
        self.assertEqual(json.loads(work.read_text()), result)

    def test_dirty_working_copy_is_refused(self):
        d, g = repo()
        (Path(d) / "autopilot/kit_wave.json").write_text(KE.dump(dict(CFG, max_inflight=99)))
        with self.assertRaises(SystemExit) as e:
            KE.edit(d, [{"op": "replace", "path": "/max_inflight", "value": 7}], "m", commit_cmd=lambda *a: None)
        self.assertIn("differs from HEAD", str(e.exception))

    def test_failed_commit_restores_the_file(self):
        d, g = repo()

        def boom(msg, rel):
            raise RuntimeError("push failed")
        with self.assertRaises(RuntimeError):
            KE.edit(d, [{"op": "replace", "path": "/max_inflight", "value": 7}], "m", commit_cmd=boom)
        self.assertEqual(json.loads((Path(d) / "autopilot/kit_wave.json").read_text())["max_inflight"], 5)

    def test_dry_run_and_noop_write_nothing(self):
        d, g = repo()
        KE.edit(d, [{"op": "replace", "path": "/max_inflight", "value": 7}], "m", dry=True, commit_cmd=lambda *a: self.fail("committed"))
        KE.edit(d, [{"op": "replace", "path": "/max_inflight", "value": 5}], "m", commit_cmd=lambda *a: self.fail("committed"))
        self.assertEqual(g("status", "--short").stdout.strip(), "")

    def test_second_editor_is_refused_with_the_holder(self):
        d, g = repo()
        lk = open(Path(d) / ".git/kit_wave_edit.lock", "a+")
        fcntl.flock(lk, fcntl.LOCK_EX); lk.write("pid=1 cmd=other\n"); lk.flush()
        with self.assertRaises(SystemExit) as e:
            KE.edit(d, [{"op": "replace", "path": "/max_inflight", "value": 7}], "m", commit_cmd=lambda *a: None)
        self.assertIn("pid=1 cmd=other", str(e.exception))


class FakeAP:
    def __init__(self, coord, origin_text=""):
        self.COORD, self.COORD_FILES, self.origin = coord, None, origin_text

    def read_coord(self, rel):
        return self.origin


class Committed(unittest.TestCase):
    def test_wave_reads_head_not_the_working_file(self):
        d, g = repo()
        (Path(d) / "autopilot/kit_wave.json").write_text(KE.dump(dict(CFG, max_inflight=999)))      # uncommitted lane edit
        self.assertEqual(json.loads(KW.read_config_text(FakeAP(d)))["max_inflight"], 5)

    def test_no_head_blob_falls_back_to_the_committed_origin_ref(self):
        d = tempfile.mkdtemp()
        subprocess.run(["git", "-C", d, "init", "-q"], check=True)
        self.assertEqual(KW.read_config_text(FakeAP(d, '{"enabled": false}')), '{"enabled": false}')

    def test_config_override(self):
        ap = FakeAP(tempfile.mkdtemp()); ap.CONFIG_OVERRIDE = '{"x": 1}'
        self.assertEqual(KW.read_config_text(ap), '{"x": 1}')


class Lock(unittest.TestCase):
    def test_skip_line_names_the_owner(self):
        d = tempfile.mkdtemp()
        p = Path(d) / "kit_wave.lock"
        holder = KW.lock_take(p)
        self.assertIn(f"pid={os.getpid()} cmd=", p.read_text())
        # a second process cannot take it, and the owner line is intact (the open must not truncate)
        r = subprocess.run([sys.executable, "-I", "-c", "import sys; sys.path.insert(0, sys.argv[1]); import kit_wave as K; "
                            "print(K.lock_take(sys.argv[2])); print(K.lock_owner_text(sys.argv[2]))", str(Path(__file__).resolve().parent), str(p)],
                           capture_output=True, text=True)
        out = r.stdout.splitlines()
        self.assertEqual(out[0], "None", r.stderr)
        self.assertTrue(out[1].startswith(f"pid={os.getpid()} cmd="), out)
        holder.close()
        self.assertIsNotNone(KW.lock_take(p))

    def test_step_skip_logs_owner(self):
        d = tempfile.mkdtemp()
        holder = KW.lock_take(Path(d) / "kit_wave.lock")
        logs = []

        class AP:
            AP_DIR = d
            log = staticmethod(logs.append)
        with unittest.mock.patch.dict(os.environ, {"KW_LOCK_HELD": ""}):
            self.assertIsNone(KW._step_locked(AP, d))
        self.assertTrue(any("skipped" in l and f"owner pid={os.getpid()}" in l for l in logs), logs)
        holder.close()


if __name__ == "__main__":
    import unittest.mock
    unittest.main()


def test_push_receipt_preserves_failure_diagnostics(monkeypatch, capsys):
    def refused(argv, **kwargs):
        return subprocess.CompletedProcess(argv, 1, "precise rejection\n")

    monkeypatch.setattr(KE.subprocess, "run", refused)
    try:
        KE.commit_config(None, "test", None)
    except subprocess.CalledProcessError as exc:
        assert exc.returncode == 1
    else:
        raise AssertionError("a failed push returned success")
    assert capsys.readouterr().out == "precise rejection\n"
