"""GC-LOCK (KW-FIX-44 11-10, COORD): daily store gc with one lock shared by staging/publish and held exclusive by gc."""
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ot_store as S  # noqa: E402

OLD = time.time() - 3 * 86400


class Gc(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.mkdtemp(prefix="otgc-")
        self.addCleanup(shutil.rmtree, self.t, True)
        self.store = os.path.join(self.t, "store")

    def put(self, name, text, old=True):
        p = os.path.join(self.t, name)
        with open(p, "w") as fh:
            fh.write(text)
        sha = S.put_file(self.store, p)
        if old:
            os.utime(S.obj_path(self.store, sha), (OLD, OLD))
        return sha

    def test_keep_set_is_the_applied_rule(self):
        ref = self.put("r", "ref")
        dead = self.put("d", "dead")
        young = self.put("y", "young", old=False)
        linked = self.put("l", "linked")
        os.link(S.obj_path(self.store, linked), os.path.join(self.t, "staged"))     # still staged in a job dir
        out = os.path.join(self.t, "out")
        os.makedirs(out)
        with open(os.path.join(out, "f"), "w") as fh:
            fh.write("published long ago")
        rec = S.publish(self.store, out, "route")
        for o in S.closure(self.store, rec["sha"]):
            os.utime(S.obj_path(self.store, o), (OLD, OLD))
        S.ref(self.store, "job-a", [ref])
        r = S.gc(self.store, apply=True)
        self.assertEqual(r["delete"], [dead])
        self.assertEqual([S.have(self.store, x) for x in (ref, young, linked, rec["sha"])], [True] * 4)
        self.assertFalse(S.have(self.store, dead))
        self.assertEqual(open(r["log"]).read().split("\t")[0], dead)              # manifest of what went

    def test_gc_waits_for_staging_and_spares_a_dedup_put(self):
        """the 0.3 s race: a job dedups onto an OLD unreferenced object, then writes its ref"""
        old = self.put("o", "kit input")
        stage_in, gc_done, order = threading.Event(), threading.Event(), []

        def job():
            with S.lock(self.store):                               # what ot-job holds from first put to its ref
                p = os.path.join(self.t, "again")
                with open(p, "w") as fh:
                    fh.write("kit input")
                self.assertEqual(S.put_file(self.store, p), old)    # dedup: the object keeps its old mtime
                stage_in.set()
                time.sleep(0.5)                                    # gc starts here and must wait
                S.ref(self.store, "job-b", [old])
                order.append("ref")

        def collector():
            stage_in.wait()
            S.gc(self.store, apply=True)
            order.append("gc")
            gc_done.set()
        ts = [threading.Thread(target=job), threading.Thread(target=collector)]
        [t.start() for t in ts]
        [t.join(20) for t in ts]
        self.assertEqual(order, ["ref", "gc"])
        self.assertTrue(S.have(self.store, old))

    def test_staging_waits_while_gc_runs(self):
        self.put("x", "x")
        got = []
        with S.lock(self.store, exclusive=True):
            t = threading.Thread(target=lambda: (S.lock(self.store).__enter__(), got.append(time.time())))
            t0 = time.time()
            t.start()
            time.sleep(0.4)
            self.assertEqual(got, [])                                 # blocked while gc holds it
        t.join(5)
        self.assertGreaterEqual(got[0] - t0, 0.35)

    def test_ot_job_stages_under_the_lock(self):
        src = (HERE / "ot-job").read_text()
        a = src.index("with S.lock(store):")
        self.assertLess(a, src.index("shas, staged = stage_all(spec, store, J, maps)"))
        self.assertLess(src.index("shas, staged = stage_all(spec, store, J, maps)"), src.index('S.ref(store, "job-" + tag'))
        self.assertGreater(src.index('S.ref(store, "job-" + tag'), a)

    def test_gc_all_cli_runs_only_existing_stores(self):
        r = subprocess.run([sys.executable, "-I", str(HERE / "ot_store.py"), "gc-all"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)


if __name__ == "__main__":
    unittest.main()
