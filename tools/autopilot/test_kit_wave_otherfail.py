#!/usr/bin/env python3
"""S81-OTHERFAIL-1 (11-07): host earlyoom SIGTERM kills are INFRA (not FLOW/RTL/PLAN), a REJECTED queue row keeps its
reason, and the async-LEC FAIL_PREFLOOR reject is RTL.  Snippets are the real e9eda32d41c wave logs."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW  # noqa: E402

RAN = "\not-run: RAN on epyc2 (unit oth-ubuntu-3153044-1794087774): exit 2\nKW_PLACE_RC=2\n"


class KilledIsInfra(unittest.TestCase):
    def test_synth_sigterm_make_error_241(self):
        text = ("Elapsed time: 36:57.22[h:]min:sec. CPU time: user 2321.46 sys 308.49 (118%). Peak memory: 14444300KB.\n"
                "make[1]: *** [Makefile:297: do-yosys] Error 241\n"
                "make: *** [Makefile:311: /work/run/results/asap7/dp_svc_hi_dsdv_svc_rs__t6/base/1_2_yosys.v] Error 2"
                + RAN)
        self.assertEqual(KW.classify("place", text)[0], "INFRA")

    def test_selrange_yosys_exit_minus_15(self):
        text = ("make: *** [Makefile:308: /work/run/results/asap7/dp_x/base/1_1_yosys_canonicalize.rtlil] Error 2\n"
                "SELRANGE ERROR top=s81p_x files=60 unwaived=0 waived=0\n"
                "  ERROR yosys exit -15: Warning: Replacing memory \\native_memory with list of registers.\n"
                "FAIL_PREFLOOR selrange (FAIL or NOT RUN)" + RAN)
        self.assertEqual(KW.classify("place", text)[0], "INFRA")

    def test_killed_marker_beats_the_rtl_lint_rule(self):
        text = ("RTL_LINT KILLED errors 0\nRTL_LINT KILLED yosys signal 15 (host memory; not a design result)\n"
                "FAIL_PREFLOOR rtl_lint KILLED (yosys signal, host memory; not a design result)" + RAN)
        self.assertEqual(KW.classify("place", text)[0], "INFRA")

    def test_own_cap_sigkill_247_is_not_made_infra_here(self):
        # memcg OOM at the job's own cap (kv_leaf__t2 50 GB) is a sizing / form problem: a same-cap relaunch repeats it
        text = "make[1]: *** [Makefile:297: do-yosys] Error 247\nmake: *** [Makefile:311: /work/x/1_2_yosys.v] Error 2" + RAN
        self.assertNotEqual(KW.classify("place", text)[0], "INFRA")

    def test_real_rtl_lint_fail_stays_rtl(self):
        text = "ERROR: Found 65 problems in 'check -assert'.\nFAIL_PREFLOOR rtl_lint (FAIL or NOT RUN)" + RAN
        self.assertEqual(KW.classify("place", text)[0], "RTL")

    def test_queue_preflight_killed_is_infra(self):
        j = dict(status="DONE-STRUCTURAL", kind="preflight",
                 reasons="FAIL_PREFLOOR FAIL_PREFLOOR rtl_lint KILLED (yosys signal, host memory; not a design result)")
        self.assertEqual(KW.queue_class(j)[2], "INFRA")


class RejectReason(unittest.TestCase):
    def test_reject_reason_from_history(self):
        j = dict(status="REJECTED", history=[["2026-11-07 11:07:48 PST", "REJECTED",
                                              "kit carries FAIL_PREFLOOR from an earlier run; enqueue a fresh kit"]])
        st, status, cls, why = KW.queue_class(j)
        self.assertEqual((st, status), ("queue", "FAIL"))
        self.assertIn("kit carries FAIL_PREFLOOR", why)

    def test_reject_on_lec_marker_is_rtl(self):
        j = dict(status="REJECTED", history=[["t", "REJECTED", "kit carries FAIL_PREFLOOR from an earlier run; enqueue a "
                                              "fresh kit [FAIL_PREFLOOR LEC NOT EQUIVALENT (lec/lec.json; pre-route LEC "
                                              "ran beside the flow, exit 1: route stopped)]"]])
        self.assertEqual(KW.queue_class(j)[2], "RTL")


if __name__ == "__main__":
    unittest.main()
