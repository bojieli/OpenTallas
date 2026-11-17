import os, tempfile, unittest
import signed_store_ingest as I


class FromArchive(unittest.TestCase):
    def mk(self):
        d = tempfile.mkdtemp()
        u = os.path.join(d, "srv/opentallas-scratch2/claude/lane/unit1/signoff")
        os.makedirs(u)
        open(os.path.join(u, "signoff.json"), "w").write("{}")
        open(os.path.join(u, "x.log"), "w").write("abc")
        return d

    def test_paths_are_original_absolute_paths(self):
        d = self.mk()
        self.assertEqual(I.archive_unit_paths(d), ["/srv/opentallas-scratch2/claude/lane/unit1/signoff/signoff.json"])

    def test_unit_files_are_hashed_and_passed_to_ingest_with_original_paths(self):
        d = self.mk(); got = []
        sj = "/srv/opentallas-scratch2/claude/lane/unit1/signoff/signoff.json"
        runner = lambda cmd, inp=None: type("R", (), {"stdout": __import__("json").dumps({"path": sj, "files": [[sj, 2, 0], ["/srv/opentallas-scratch2/claude/lane/unit1/signoff/x.log", 3, 0]]}) + "\n", "returncode": 0})()
        fails = []
        new = I.from_archive(d, "epyc8", "/archive/x/epyc8", fails, runner=runner, ingest=lambda sh: (got.append(sh), ["id1"])[1], tool="/t")
        self.assertEqual(new, ["id1"]); self.assertEqual(fails, [])
        sh = got[0]
        self.assertEqual(sorted(sh), [sj, "/srv/opentallas-scratch2/claude/lane/unit1/signoff/x.log"])
        self.assertEqual(sh[sj][0], 2); self.assertEqual(sh["/srv/opentallas-scratch2/claude/lane/unit1/signoff/x.log"][1], I.sha_file(os.path.join(d, "srv/opentallas-scratch2/claude/lane/unit1/signoff/x.log")))

    def test_missing_archive_file_is_a_failure_not_a_partial_ingest(self):
        d = self.mk(); got = []
        sj = "/srv/opentallas-scratch2/claude/lane/unit1/signoff/signoff.json"
        runner = lambda cmd, inp=None: type("R", (), {"stdout": __import__("json").dumps({"path": sj, "files": [[sj, 2, 0], ["/srv/opentallas-scratch2/claude/lane/unit1/gone.odb", 9, 0]]}) + "\n", "returncode": 0})()
        fails = []
        self.assertEqual(I.from_archive(d, "epyc8", "/archive/x", fails, runner=runner, ingest=lambda sh: got.append(sh) or [], tool="/t"), [])
        self.assertEqual(got, []); self.assertTrue(fails and "lacks 1 unit files" in fails[0][2])


class SweepSkipsDeadHosts(unittest.TestCase):
    def test_ingest_marks_archive_source(self):
        import signed_store as ss, inspect
        self.assertIn('kind="auto-archive"', inspect.getsource(ss.ingest))
        self.assertIn('source="archive"', inspect.getsource(ss.ingest))
