import json, os, tempfile, unittest
import wave_prepare_refresh as W


class Refresh(unittest.TestCase):
    def prep(self, edit_plan):
        d = tempfile.mkdtemp()
        open(os.path.join(d, "source_plan.json"), "w").write("{}")
        open(os.path.join(d, "source_sidecar.json"), "w").write("{}")
        json.dump({"prepared_plan_sha256": W.digest(os.path.join(d, "source_plan.json")),
                   "sidecar_sha256": W.digest(os.path.join(d, "source_sidecar.json"))}, open(os.path.join(d, "wave_prepare.json"), "w"))
        if edit_plan:
            open(os.path.join(d, "source_plan.json"), "w").write('{"edited": 1}')
        return d

    def test_current_receipt_untouched(self):
        d = self.prep(False)
        rc, msg = W.refresh(d)
        self.assertEqual(rc, 0); self.assertIn("current", msg)

    def test_edited_plan_republished(self):
        d = self.prep(True)
        rc, msg = W.refresh(d)
        self.assertEqual(rc, 0); self.assertIn("refreshed", msg)
        w = json.load(open(os.path.join(d, "wave_prepare.json")))
        self.assertEqual(w["prepared_plan_sha256"], W.digest(os.path.join(d, "source_plan.json")))
        self.assertEqual(W.refresh(d)[0], 0); self.assertIn("current", W.refresh(d)[1])

    def test_missing_receipt(self):
        self.assertEqual(W.refresh(tempfile.mkdtemp())[0], 1)


if __name__ == "__main__":
    unittest.main()
