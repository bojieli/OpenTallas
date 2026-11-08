"""Actual frontend failure is infrastructure; payload/HDL syntax errors keep their failures."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import autopilot as AP
import auto_resign as AR

# Exact shell diagnostics from shared-client 7ec9fea73266/a1.log (2026-11-07).
FRONTEND = """AP_START 1794092539 ap-7ec9fea73266-a1
/home/ubuntu/.local/lib/kw10/ot-run: line 43: syntax error near unexpected token `;'
/home/ubuntu/.local/lib/kw10/ot-run: line 43: ` ; pre+=("$a"); done'
AP_RC=2
"""

class ClientFrontendSyntaxTest(unittest.TestCase):
    def test_real_pre_admission_client_is_not_run_infrastructure(self):
        client=AP.parse_client_log(FRONTEND)
        self.assertTrue(client["not_run"])
        self.assertIn("frontend_shell_fail",client)
        self.assertEqual(client["exit"],2)
        self.assertEqual(AR.classify(client,{}, "flow-20261107-dg-s81")[0],"INFRA")

    def test_hdl_syntax_error_remains_failure(self):
        for line in ("ERROR: /work/rtl/core.sv:43: syntax error",
                     "/work/run_kit.sh: line 43: syntax error near unexpected token ;",
                     "ERROR: /home/ubuntu/.local/lib/kw10/ot-run: line 43: syntax error"):
            with self.subTest(line=line):
                client=AP.parse_client_log(line+"\nAP_RC=2\n")
                self.assertNotIn("not_run",client)
                self.assertEqual(AR.classify(client,{}, "flow-20261107-dg-s81")[0],"FAILED")

    def test_after_ran_is_not_frontend_infrastructure(self):
        client=AP.parse_client_log(FRONTEND+"ot-run: RAN on epyc5: exit 2\n")
        self.assertNotIn("not_run",client)
        self.assertNotIn("frontend_shell_fail",client)
        self.assertEqual(AR.classify(client,{}, "flow-20261107-dg-s81")[0],"FAILED")

    def test_after_admission_without_completion_is_not_claimed_never_run(self):
        client=AP.parse_client_log("ot-heavy: admitted on epyc5\n"+FRONTEND)
        self.assertNotIn("not_run",client)
        self.assertNotIn("frontend_shell_fail",client)

if __name__=="__main__":
    unittest.main()

