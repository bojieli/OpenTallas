import hashlib, json, os, tempfile, unittest
import export_restore as E
from test_export_restore import mk_export


class Queue(unittest.TestCase):
    def setUp(self):
        self.root, self.rid = mk_export(); self.t = tempfile.mkdtemp(); self.q = self.t + "/restore_needed.jsonl"
        self.prov = {"kit": {"module": "elemA"}, "export": {"signoff_sha256": self.rid, "odb": "/x/xbase/6_final.odb", "signoff": "/x/signoff/signoff.json", "base": "/x/xbase"}}

    def rows(self, paths, host="epyc10"):
        return E.restore_rows([(p, "by.json") for p in paths], lambda b: self.prov, host, now=1.0)

    def test_rows_carry_module_record_path_host_and_a_non_export_path_is_an_original_kit_row(self):
        rows = self.rows(["/x/xbase/6_final.odb", "/not/an/export/path"])
        self.assertEqual([(r["module"], r["key"], r["host"], r["status"]) for r in rows], [("elemA", "odb", "epyc10", "NEEDED"), ("elemA", "original-kit", "epyc10", "NEEDED")])

    def test_queue_append_dedups_per_host_and_path_and_skips_done(self):
        r = self.rows(["/x/xbase/6_final.odb"])
        self.assertEqual(E.queue_append(self.q, r), 1); self.assertEqual(E.queue_append(self.q, r), 0)
        self.assertEqual(E.queue_append(self.q, self.rows(["/x/xbase/6_final.odb"], "epyc8")), 1)           # another host is another request
        self.assertEqual(E.queue_append(self.q, self.rows(["/x/signoff/signoff.json"]), done=[dict(r[0], status="DONE")]), 1)
        self.assertEqual(len(E.read_jsonl(self.q)), 3)

    def test_worker_pushes_verified_files_marks_done_and_is_idempotent(self):
        rows = self.rows(["/x/xbase/6_final.odb", "/x/signoff/signoff.json", "/x/xbase"]); pushed = []
        done = E.work(rows, [], E.load_index(self.root), self.root, lambda h, s, d: pushed.append((h, s and os.path.basename(s), d)))
        self.assertEqual(sorted(r["status"] for r in done), ["DONE"] * 3)
        self.assertIn(("epyc10", "6_final.odb", "/x/xbase/6_final.odb"), pushed); self.assertIn(("epyc10", None, "/x/xbase"), pushed)
        self.assertEqual(E.work(rows, done, E.load_index(self.root), self.root, lambda *a: pushed.append(a)), [])        # nothing pending twice

    def test_a_corrupt_export_file_is_never_pushed_and_an_unknown_record_is_unrestorable(self):
        rows = self.rows(["/x/xbase/6_final.odb"]); pushed = []
        open(self.root + "/s81/elemA/6_final.odb", "wb").write(b"CORRUPT")
        done = E.work(rows, [], E.load_index(self.root), self.root, lambda *a: pushed.append(a))
        self.assertEqual((pushed, done[0]["status"]), ([], "UNRESTORABLE")); self.assertIn("does not match", done[0]["why"])
        rows[0]["record"] = "f" * 64
        self.assertIn("no signed export row", E.work(rows, [], E.load_index(self.root), self.root, lambda *a: 0)[0]["why"])

    def test_a_down_host_stays_pending(self):
        rows = self.rows(["/x/xbase/6_final.odb"])
        def push(h, s, d): raise OSError("host down")
        self.assertEqual(E.work(rows, [], E.load_index(self.root), self.root, push), [])


class OriginalKit(unittest.TestCase):
    def setUp(self):
        self.root, self.rid = mk_export(); os.makedirs(self.root + "/s81/elemA/view"); open(self.root + "/s81/elemA/view/face_guard.json", "w").write("FG")
        self.sha = hashlib.sha256(b"FG").hexdigest()

    def prov(self, by):
        return {"kit": {"module": "elemA"}, "export": {"signoff_sha256": self.rid, "odb": "/x/6_final.odb"}}

    def test_every_missing_path_is_queued_original_kit_rows_carry_the_store_sha_and_skips_are_reasoned(self):
        rows, skips = E.restore_rows_ex([("/orig/kit/face_guard.json", "by1"), ("/x/6_final.odb", "by2"), ("/orig/y", "by3")], lambda b: None if b == "by3" else self.prov(b), "epyc10",
                                       sha_of=lambda rid, p: self.sha)
        self.assertEqual([(r["key"], r["module"]) for r in rows], [("original-kit", "elemA"), ("odb", "elemA")])
        self.assertEqual(rows[0]["sha256"], self.sha); self.assertEqual(len(skips), 1); self.assertIn("unreadable", skips[0][1])

    def test_a_row_without_a_record_id_is_skipped_with_the_reason(self):
        rows, skips = E.restore_rows_ex([("/orig/z", "by")], lambda b: {"kit": {}, "export": {}}, "h")
        self.assertEqual(rows, []); self.assertIn("no export.signoff_sha256", skips[0][1])

    def test_worker_restores_an_original_kit_file_by_name_and_expected_hash_only(self):
        row = E.restore_rows([("/orig/kit/face_guard.json", "by")], self.prov, "epyc10", sha_of=lambda r, p: self.sha)[0]
        pushed = []
        done = E.work([row], [], E.load_index(self.root), self.root, lambda h, s, d: pushed.append((s and os.path.basename(s), d)))
        self.assertEqual((done[0]["status"], pushed), ("DONE", [("face_guard.json", "/orig/kit/face_guard.json")]))
        bad = dict(row, sha256="0" * 64, path="/orig/kit/other_fg.json"); bad["path"] = "/orig/kit/face_guard.json"
        d2 = E.work([bad], [], E.load_index(self.root), self.root, lambda *a: pushed.append(a))
        self.assertEqual(d2[0]["status"], "UNRESTORABLE"); self.assertIn("recorded sha256", d2[0]["why"])

    def test_unknown_hash_is_accepted_only_for_a_unique_name(self):
        row = E.restore_rows([("/orig/kit/face_guard.json", "by")], self.prov, "h", sha_of=lambda r, p: "")[0]
        self.assertIn("expected hash unknown", row["note"])
        self.assertEqual(E.work([row], [], E.load_index(self.root), self.root, lambda *a: 0)[0]["status"], "DONE")
        open(self.root + "/s81/elemA/face_guard.json", "w").write("OTHER")                   # a second candidate: ambiguous, never guessed
        self.assertEqual(E.work([row], [], E.load_index(self.root), self.root, lambda *a: 0)[0]["status"], "UNRESTORABLE")
