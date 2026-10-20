"""BENCH-TOOL-RACE (ROOT-INF2 2026-10-18): a Verilator hier PCH race is a tool crash, never an RTL verdict."""
import os
import subprocess
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import closure_loop as cl  # noqa: E402


class BenchToolRace(unittest.TestCase):
    def test_pch_invalid_in_tail(self):
        tail = "Vtb.cpp:1:10: note: one or more PCH files were found, but they were invalid\nmake: *** Error 1\n"
        self.assertIn("PCH files were found", cl.bench_tool_race({}, tail))

    def test_pch_missing_in_tail(self):
        tail = ("Vot_hgi_coll_tkm_tile_e86.cpp:3:10: fatal error: Vot_hgi_coll_tkm_tile_e86__pch.h.fast: "
                "No such file or directory\n")
        self.assertTrue(cl.bench_tool_race({}, tail))

    def test_rtl_failure_is_not_a_race(self):
        self.assertEqual(cl.bench_tool_race({}, "MISMATCH R word 7\nTKM_STATIC FAIL\n"), "")
        self.assertEqual(cl.bench_tool_race({}, "%Error: tb.sv:213:17: $readmemh loading non-variable\n"), "")

    def test_remote_logs_are_searched(self):
        v = dict(stage_tag="bench_x.a1b1", run="/srv/r", host="ot-epyc4")
        out = "one or more PCH files were found, but they were invalid\n"
        with mock.patch.object(cl, "ssh", return_value=subprocess.CompletedProcess([], 0, out, "")) as s:
            self.assertIn("PCH", cl.bench_tool_race(v, "make: *** [x.mk:38: y.mk] Error 2\n"))
            cmd = s.call_args[0][1]
            self.assertIn("/srv/r/bench", cmd)
            self.assertIn("-newer /srv/r/cl/bench_x.a1b1.start", cmd)
            self.assertIn("[^[:space:]]*__pch", cmd)

    def test_remote_unreachable_is_no_race(self):
        v = dict(stage_tag="t", run="/srv/r", host="h")
        with mock.patch.object(cl, "ssh", return_value=subprocess.CompletedProcess([], 255, "", "")):
            self.assertEqual(cl.bench_tool_race(v, ""), "")

    def test_grep_pattern_matches_real_lines(self):
        pat = cl.TOOL_RACE_RE.pattern.replace("\\S", "[^[:space:]]").replace("(?:", "(")
        for line in ("x.cpp:1:10: fatal error: Vtb__pch.h.fast: No such file or directory",
                     "note: one or more PCH files were found, but they were invalid"):
            r = subprocess.run(["grep", "-qE", pat], input=line, text=True)
            self.assertEqual(r.returncode, 0, line)


if __name__ == "__main__":
    unittest.main()
