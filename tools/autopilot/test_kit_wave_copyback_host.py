"""KW-FIX-46 11-11: place_probe takes the kit host from the sealed run record (ot_hbm_sm_i8w_front a8: copy-back intel2 -> epyc7,
gen host epyc8; the probe looked on epyc8 and failed a placed kit)."""
import re, sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as K

I8W_TAIL = """ot-job: command exit 0
ot-job: published 1 artifact(s); job dir deleted /srv/opentallas-scratch2/claude/ot-jobs/x
ot-run: RAN on localhost (unit oth-ubuntu-1107185-1794401845): exit 0
ot-run-sealed: SEALED on intel2: /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/hbm/kit-wave/hbm/d44v/items/ot_hbm_sm_i8w_front/attempt_8/gen/k (inputs fetched from epyc7)
ot-run-sealed: copy-back intel2 -> epyc7 rc 0
"""


class CopyBackHost(unittest.TestCase):
    def test_i8w_case_probes_epyc7_not_the_gen_host(self):
        self.assertEqual(K.copy_back_host(I8W_TAIL, "epyc8"), "epyc7")

    def test_unsealed_run_keeps_gen_host(self):
        self.assertEqual(K.copy_back_host("ot-run: RAN on epyc8 (unit u): exit 0\n", "epyc8"), "epyc8")
        self.assertEqual(K.copy_back_host("", "epyc8"), "epyc8")
        self.assertEqual(K.copy_back_host(None, "epyc8"), "epyc8")

    def test_failed_copy_back_is_ignored(self):
        self.assertEqual(K.copy_back_host("ot-run-sealed: copy-back intel2 -> epyc7 rc 23\n", "epyc8"), "epyc8")

    def test_last_copy_back_wins(self):
        t = "ot-run-sealed: copy-back intel2 -> epyc7 rc 0\not-run-sealed: copy-back intel2 -> epyc4 rc 0\n"
        self.assertEqual(K.copy_back_host(t, "epyc8"), "epyc4")

    def test_remote_argv_local_and_remote(self):
        self.assertEqual(K.remote_argv("intel2", "intel2", "ls x"), ["bash", "-c", "ls x"])
        self.assertEqual(K.remote_argv("localhost", "intel2", "ls x"), ["bash", "-c", "ls x"])
        a = K.remote_argv("epyc7", "intel2", "ls 'x y'")
        self.assertEqual(a[:5], ["ssh", "-o", "BatchMode=yes", "-o", "ControlPath=none"])
        self.assertEqual(a[5], "epyc7")
        self.assertTrue(a[6].startswith("bash -c "))

    def test_after_place_never_uses_the_gen_host_remote(self):
        src = Path(K.__file__).read_text()
        a = src.index("    def after_place(K, rc, txt):"); b = src.index('    svc_file = out / "place_service.json"')
        body = src[a:b]
        self.assertNotIn("remote(", body.replace("remote_argv(", ""))
        self.assertIn("copy_back_host(txt, G)", body)
        self.assertEqual(re.findall(r"\{G\}:", body), [])


if __name__ == "__main__":
    unittest.main()
