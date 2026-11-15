"""RC125_1111 (KW-FIX-44, COORD 11-11): docker rc 125 at gen / gen_lint classifies INFRA."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW  # noqa: E402


class RC125(unittest.TestCase):
    def test_gen_lint_yosys_rc125_is_infra(self):
        c, why = KW.classify("gen_lint", "  - GEN_LINT FAIL rtl_check: yosys elaboration failed rc 125 (gen_lint_yosys.log)\n")
        self.assertEqual(c, "INFRA", why)

    def test_gen_docker_daemon_error_is_infra(self):
        c, why = KW.classify("gen", "docker: Error response from daemon: failed to create task for container: x\n")
        self.assertEqual(c, "INFRA", why)

    def test_other_stage_rc125_text_not_reclassified(self):
        c, _ = KW.classify("route", "[ERROR DRT-0073] no access point\nrc 125\n")
        self.assertNotEqual(c, "INFRA")

    def test_real_rtl_lint_stays_rtl(self):
        c, _ = KW.classify("gen_lint", "  - GEN_LINT FAIL rtl_check: ERROR: Module `x' referenced but not found\n")
        self.assertEqual(c, "RTL")


    def test_netnone_network_failure_is_infra(self):
        c, why = KW.classify("place", "pip._vendor.urllib3: Failed to establish a new connection: [Errno -3] Temporary failure in name resolution\n")
        self.assertEqual(c, "INFRA", why)
        self.assertIn("NETNONE", why)


if __name__ == "__main__":
    unittest.main()
