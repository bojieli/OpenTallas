"""tools/view_lineage.py: archive re-export receipts bind only while files and the CLOSED job are unchanged."""
import importlib.util, json, shutil, sys, tempfile, unittest
from unittest.mock import patch
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import view_lineage as VL

VIEW = HERE.parent / "physical/s81_die_views/views/dsfd_stnh_566x1"
JOB = "s81-dsfd-stnh-566x1-2e2d7aa3f-arch"


class ViewLineage(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp())
        self.v = self.t / "dsfd_stnh_566x1"
        shutil.copytree(VIEW, self.v)
        (self.v / VL.RECEIPT).unlink(missing_ok=True)
        self.jobs = self.t / "jobs"
        self.jobs.mkdir()
        self.set_job("CLOSED", "CLOSED TT +76.93 / FF +382.33 ps DRC 0")
        self.addCleanup(shutil.rmtree, self.t)
        self.archive = self.t / JOB
        self.archive.mkdir()
        self.commit = json.loads((self.v / "abstract.json").read_text())["verdict"]["commit"]
        (self.archive / "commit.txt").write_text(self.commit)
        self.manifest = dict(job=JOB, commit=self.commit, final_base="route", metrics=dict(tt_ps=76.93, ff_ps=382.33, drc=0), files=[])
        for ext in ("odb", "sdc", "spef"):
            rel = "route/6_final." + ext
            p = self.archive / "run" / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(("fixture " + ext).encode())
            self.manifest["files"].append(dict(path=rel, stored=rel, raw_size=p.stat().st_size, sha256=VL.sha(p)))
        self.save_manifest()

    def save_manifest(self):
        (self.archive / "manifest.json").write_text(json.dumps(self.manifest))

    def receipt(self):
        r = VL.build_archive_reexport(self.v, self.archive, self.jobs)
        self.assertEqual(r["verdict"], "PASS", r["why"])
        (self.v / VL.RECEIPT).write_text(json.dumps(r))
        return r

    def set_job(self, status, reason):
        (self.jobs / f"{JOB}.json").write_text(json.dumps(dict(name=JOB, status=status, reason=reason)))

    def test_archive_reexport_binds_and_drift_unbinds(self):
        r = VL.build_archive_reexport(self.v, self.archive, self.jobs)
        self.assertEqual(r["verdict"], "PASS", r["why"])
        self.assertEqual(r["original_job"], JOB)
        self.assertTrue(r["native_audit"]["pass"])
        (self.v / VL.RECEIPT).write_text(json.dumps(r))
        self.assertTrue(VL.verify(self.v, self.jobs)[0])
        with open(self.v / "dsfd_stnh_566x1.lef", "a") as fh:
            fh.write("# edit\n")
        ok, why, _ = VL.verify(self.v, self.jobs)
        self.assertFalse(ok)
        self.assertIn("changed", why)

    def test_job_not_closed_refused(self):
        self.set_job("NEEDS_RTL", "TT -5 / FF 1 / DRC 0")
        r = VL.build_archive_reexport(self.v, self.archive, self.jobs)
        self.assertEqual(r["verdict"], "FAIL")

    def test_missing_archive_refused(self):
        r = VL.build_archive_reexport(self.v, None, self.jobs)
        self.assertEqual(r["verdict"], "FAIL")

    def test_missing_input_hash_refused(self):
        del self.manifest["files"][0]["sha256"]
        self.save_manifest()
        r = VL.build_archive_reexport(self.v, self.archive, self.jobs)
        self.assertEqual(r["verdict"], "FAIL")
        self.assertIn("missing raw hash", str(r["why"]))

    def test_route_input_drift_unbinds(self):
        self.receipt()
        (self.archive / "run/route/6_final.odb").write_bytes(b"different route")
        ok, why, _ = VL.verify(self.v, self.jobs)
        self.assertFalse(ok)
        self.assertIn("archive bytes changed", why)

    def test_archive_manifest_drift_unbinds(self):
        self.receipt()
        self.manifest["owner"] = "changed"
        self.save_manifest()
        self.assertFalse(VL.verify(self.v, self.jobs)[0])

    def test_same_status_state_drift_unbinds(self):
        self.receipt()
        self.set_job("CLOSED", "CLOSED TT +77 / FF +382.33 ps DRC 0")
        ok, why, _ = VL.verify(self.v, self.jobs)
        self.assertFalse(ok)
        self.assertIn("state changed", why)

    def test_insertion_drift_unbinds(self):
        self.receipt()
        (self.v / "insertion.json").write_text("{}")
        self.assertFalse(VL.verify(self.v, self.jobs)[0])

    def test_binder_checks_receipt_even_with_existing_closed_job(self):
        # The original job can be resolved directly from verdict.job. That must
        # not bypass the receipt's archive and insertion identity checks.
        self.receipt()
        spec = importlib.util.spec_from_file_location("binding_under_test", HERE / "s81/view_binding_closed.py")
        binder = importlib.util.module_from_spec(spec)
        with patch.object(sys, "path", [str(HERE / "s81"), *sys.path]):
            spec.loader.exec_module(binder)
        out = self.t / "bound.json"
        with patch.object(binder, "ROOT", self.t), \
             patch.object(binder, "VIEW_ABSTRACT_GLOBS", ("*/abstract.json",)), \
             patch.object(binder, "export_fix", return_value=(True, "ok")), \
             patch.object(VL, "verify", return_value=(False, "archive bytes changed", {})) as verify, \
             patch.object(sys, "argv", ["binding", "--out", str(out), "--jobs", str(self.jobs)]):
            binder.main()
        verify.assert_called_once()
        result = json.loads(out.read_text())
        self.assertNotIn(self.v.name, result["bound"])
        self.assertIn("archive bytes changed", str(result["not_bound"][self.v.name]))

    def test_wrong_archive_identity_refused(self):
        self.manifest["job"] = "another-job"
        self.save_manifest()
        self.assertEqual(VL.build_archive_reexport(self.v, self.archive, self.jobs)["verdict"], "FAIL")


if __name__ == "__main__":
    unittest.main()
