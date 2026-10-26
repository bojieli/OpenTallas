#!/usr/bin/env python3
"""Tests for ot_orphan_reaper.plan() on synthetic process tables (no real process is touched)."""
import os, sys, tempfile, unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ot_orphan_reaper as R  # noqa: E402

H = 3600.0
WRAP = ["/bin/bash", "-c", "source /home/ubuntu/.claude/shell-snapshots/snapshot-bash-1-x.sh && eval 'x'"]
NOPEND = (set(), set())


def table(*procs):
    t = {1: R.Proc(1, 0, ["/sbin/init"], "systemd"), 1537: R.Proc(1537, 1, ["/lib/systemd/systemd", "--user"], "systemd")}
    for p in procs:
        t[p.pid] = p
    return t


def killed(t, pending=NOPEND):
    k, _ = R.plan(t, pending)
    return sorted(p.pid for p, _ in k)


class T(unittest.TestCase):
    def test_orphan_git_grep_origin_main_killed(self):
        t = table(R.Proc(10, 1, WRAP), R.Proc(11, 10, ["git", "grep", "-n", "foo", "origin/main"], elapsed=2.7 * H))
        self.assertEqual(killed(t), [11])

    def test_git_C_grep_rev_after_pattern_killed_under_systemd_user(self):
        t = table(R.Proc(10, 1537, WRAP),
                  R.Proc(11, 10, ["git", "-C", "/home/ubuntu/OpenTallas", "grep", "-e", "x", "d5813f144", "--", "rtl"],
                         elapsed=0.5 * H))
        self.assertEqual(killed(t), [11])

    def test_git_grep_worktree_no_rev_kept(self):
        t = table(R.Proc(10, 1, WRAP), R.Proc(11, 10, ["git", "-C", "/w", "grep", "-n", "foo", "--", "tools/x"],
                                              elapsed=5 * H))
        self.assertEqual(killed(t), [])

    def test_young_git_kept(self):
        t = table(R.Proc(10, 1, WRAP), R.Proc(11, 10, ["git", "ls-tree", "-r", "origin/main"], elapsed=19 * 60))
        self.assertEqual(killed(t), [])

    def test_live_claude_session_kept(self):
        t = table(R.Proc(5, 1, ["claude", "--dangerously-skip-permissions"], "claude"),
                  R.Proc(10, 5, WRAP), R.Proc(11, 10, ["git", "grep", "x", "origin/main"], elapsed=4 * H))
        self.assertEqual(killed(t), [])

    def test_live_claude_detected_by_exe(self):
        t = table(R.Proc(5, 1, ["/x/2.1.303", "bg-spare"], "2.1.303", exe="/home/u/.local/share/claude/versions/2.1.303"),
                  R.Proc(10, 5, WRAP), R.Proc(11, 10, ["iverilog", "-o", "a", "b.v"], elapsed=35 * H))
        self.assertEqual(killed(t), [])

    def test_orphan_iverilog_35h_killed_ivl_too(self):
        t = table(R.Proc(10, 1, WRAP), R.Proc(11, 10, ["iverilog", "-o", "a", "b.v"], elapsed=35 * H),
                  R.Proc(12, 11, ["/usr/lib/ivl/ivl", "-C/tmp/x"], elapsed=35 * H))
        self.assertEqual(killed(t), [11, 12])

    def test_eda_under_2h_kept(self):
        t = table(R.Proc(10, 1, WRAP), R.Proc(11, 10, ["yosys", "-s", "x.ys"], elapsed=1.9 * H))
        self.assertEqual(killed(t), [])

    def test_not_under_wrapper_kept(self):
        t = table(R.Proc(20, 1537, ["/usr/bin/python3", "/w/tools/closure_loop/closure_loop.py", "daemon"]),
                  R.Proc(21, 20, ["openroad", "-exit", "x.tcl"], elapsed=10 * H),
                  R.Proc(30, 1, ["git", "log", "origin/main"], elapsed=10 * H))
        self.assertEqual(killed(t), [])

    def test_protected_ancestor_ot_run_kept(self):
        t = table(R.Proc(10, 1, WRAP), R.Proc(11, 10, ["python3", "/home/ubuntu/bin/ot-run", "--remote", "auto"]),
                  R.Proc(12, 11, ["verilator", "--cc", "x.v"], elapsed=5 * H))
        self.assertEqual(killed(t), [])

    def test_pending_results_path_and_pid_kept(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
            f.write("/home/ubuntu/scratch/lane-x/sim_out/run.log | collect | LANE-X\npid 12 | keep | LANE-Y\n")
        pend = R.load_pending(f.name)
        os.unlink(f.name)
        t = table(R.Proc(10, 1, WRAP),
                  R.Proc(11, 10, ["vvp", "/home/ubuntu/scratch/lane-x/sim_out/a.vvp"], elapsed=5 * H),
                  R.Proc(12, 10, ["yosys", "-s", "y.ys"], elapsed=5 * H),
                  R.Proc(13, 10, ["yosys", "-s", "z.ys"], elapsed=5 * H))
        self.assertEqual(killed(t, pend), [13])

    def test_grep_filter_of_ot_run_kept(self):
        t = table(R.Proc(10, 1, WRAP),
                  R.Proc(11, 10, ["python3", "/home/ubuntu/bin/ot-run", "x"], pipe_w={777}),
                  R.Proc(12, 10, ["grep", "-v", "^ot-run:"], elapsed=3 * H, fd0_pipe=777))
        self.assertEqual(killed(t), [])

    def test_tail_grep_monitor_both_killed(self):
        t = table(R.Proc(10, 1, WRAP),
                  R.Proc(11, 10, ["tail", "-F", "/x/done.txt"], elapsed=2 * H, pipe_w={555}),
                  R.Proc(12, 10, ["ugrep", "--line-buffered", "-E", "rc="], "2.1.302", elapsed=2 * H, fd0_pipe=555,
                         exe="/home/u/.local/share/claude/versions/2.1.302"))
        self.assertEqual(killed(t), [11, 12])

    def test_embedded_ugrep_under_live_claude_kept(self):
        t = table(R.Proc(5, 1, ["claude"], "claude"), R.Proc(10, 5, WRAP),
                  R.Proc(12, 10, ["ugrep", "-r", "x", "/"], "2.1.303", elapsed=3 * H,
                         exe="/home/u/.local/share/claude/versions/2.1.303"))
        self.assertEqual(killed(t), [])

    def test_rg_over_30min_orphan_killed(self):
        t = table(R.Proc(10, 1, WRAP), R.Proc(11, 10, ["rg", "-n", "foo", "/home/ubuntu"], elapsed=31 * 60))
        self.assertEqual(killed(t), [11])

    def test_git_class_parser(self):
        self.assertEqual(R.git_class(["git", "log", "--format=", "--raw", "05e11cc8e", "--", "a"]), "log")
        self.assertEqual(R.git_class(["git", "-c", "a=b", "grep", "--all", "x"]), "grep-rev")
        self.assertIsNone(R.git_class(["git", "status"]))
        self.assertIsNone(R.git_class(["git", "grep", "HEAD"]))           # HEAD is the pattern here
        self.assertEqual(R.git_class(["git", "grep", "x", "HEAD~3"]), "grep-rev")


if __name__ == "__main__":
    unittest.main()
