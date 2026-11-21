"""FLOW-NOADV-R4 (COORD, S81-DIE-R5): an `ot-run --cancel` of a wave place stage is final: no 'ot-run never started' retry, no restart from scratch."""
import json
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

_TMP = tempfile.TemporaryDirectory()
os.environ["AP_OT_RUN_SIGNALS"] = str(Path(_TMP.name) / "signals.log")
import autopilot as AP            # noqa: E402
import kit_wave as KW             # noqa: E402

KIT = "/srv/x/kit-wave/items/t1/a3/gen/t1"


class PlaceCancel(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.rec = {"dir": self.d.name}
        (Path(self.d.name) / "place_service.json").write_text(json.dumps({"kit": KIT, "started": time.time() - 600}))
        Path(os.environ["AP_OT_RUN_SIGNALS"]).write_text("")

    def tearDown(self):
        self.d.cleanup()

    def sig(self, kit, off=0, sender="ot-run --cancel"):
        ts = time.strftime("%Y-%m-%dT%H:%M:%S%z", time.gmtime(time.time() - off))
        with open(os.environ["AP_OT_RUN_SIGNALS"], "a") as f:
            f.write(f"{ts} signal 15 from pid 1 ({sender} 'kwp'): ot-run pid 9 dir {kit}: x\n")

    def test_cancel_in_signals_log_is_found(self):
        self.assertIsNone(KW.place_cancelled(AP, self.rec))
        self.sig(KIT)
        self.assertIn("ot-run --cancel", KW.place_cancelled(AP, self.rec))

    def test_other_kit_or_other_sender_or_old_cancel_is_not_this_one(self):
        self.sig(KIT + "x")
        self.sig(KIT, sender="other-tool")
        self.sig(KIT, off=7200)                       # before this attempt's service started
        self.assertIsNone(KW.place_cancelled(AP, self.rec))

    def test_no_service_file_is_no_cancel(self):
        os.remove(Path(self.d.name) / "place_service.json")
        self.sig(KIT)
        self.assertIsNone(KW.place_cancelled(AP, self.rec))

    def run_sh(self, inner):
        log = Path(self.d.name) / "p.log"
        sh = f"exec >> {log} 2>&1; " + KW.place_retry_sh(inner, str(log)) + "; echo KW_PLACE_RC=$rc"
        subprocess.run(["bash", "-c", sh], timeout=120)
        return log.read_text()

    def test_signalled_client_is_not_retried_even_with_not_run_text(self):
        t = self.run_sh("echo 'ot-run: NOT RUN: cancelled'; (exit 143)")
        self.assertEqual(t.count("KW_PLACE_TRY"), 1)
        self.assertIn("KW_PLACE_RC=143", t)

    def test_a_real_not_run_still_retries(self):
        old, KW.SSH_RETRIES = KW.SSH_RETRIES, 1
        try:
            t = self.run_sh("echo 'ot-run: NOT RUN: no host qualifies'; (exit 1)")
        finally:
            KW.SSH_RETRIES = old
        self.assertEqual(t.count("KW_PLACE_TRY"), 2)
