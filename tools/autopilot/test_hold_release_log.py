import tempfile
import unittest
import kit_wave as KW


class AP:
    DRY = False

    def __init__(self):
        self.logs = []

    def log(self, m):
        self.logs.append(m)


class Once(unittest.TestCase):
    def test_one_line_per_key_change(self):
        d, ap = tempfile.mkdtemp(), AP()
        e = [("s81", "k1", "proof ok"), ("s81", "k2", "tree ready")]
        self.assertEqual(KW.log_hold_releases(ap, d, e, "release_on met", reset=True), 2)
        for _ in range(5):                                        # the next ticks: same release, no new line
            self.assertEqual(KW.log_hold_releases(ap, d, e, "release_on met", reset=True), 0)
        self.assertEqual(len(ap.logs), 2)
        self.assertEqual(KW.log_hold_releases(ap, d, [("s81", "k1", "proof ok v2")], "release_on met", reset=True), 1)   # the condition changed
        self.assertEqual(KW.log_hold_releases(ap, d, e, "release_on met", reset=True), 2)       # k2 left and returned: logs again; k1 old cond is new again
        self.assertEqual(KW.log_hold_releases(ap, d, e, "release terms met"), 0)

    def test_second_call_of_a_tick_keeps_the_first_calls_keys(self):
        d, ap = tempfile.mkdtemp(), AP()
        KW.log_hold_releases(ap, d, [("a", "k", "c")], "x", reset=True)
        KW.log_hold_releases(ap, d, [("b", "k", "c")], "y")                      # no reset: a/k/c stays known
        self.assertEqual(KW.log_hold_releases(ap, d, [("a", "k", "c")], "x"), 0)


class LoadTimeSubset(unittest.TestCase):
    """FABLE-FLOW-0300 11-17: 2,867 HOLD-AUTO-RELEASE lines (35 % of log.txt), the same 125 QC items every tick.  The first call of a tick sees
    only what the load-time compile released (gen_pilot / result terms are not met yet); its reset dropped every record key the second call
    then logged again."""

    def tick(self, ap, d, load_time, records):
        KW.log_hold_releases(ap, d, load_time, "release_on met", reset=True)
        return KW.log_hold_releases(ap, d, records, "release terms met", reset=True, summary_total=len(records))

    def test_same_release_every_tick_is_logged_once(self):
        d, ap = tempfile.mkdtemp(), AP()
        recs = [("qwen_compute", f"item{i}", "gen_pilot:qwen_compute:c8e6") for i in range(125)]
        load = [("qwen_compute", "legacy1", "merge:abc")]
        self.assertEqual(self.tick(ap, d, load, recs), 125)
        first = len(ap.logs)
        for _ in range(10):
            self.assertEqual(self.tick(ap, d, load, recs), 0)
        item_lines = [m for m in ap.logs if "HOLD-AUTO-RELEASE qwen_compute/" in m]
        self.assertEqual(len(item_lines), 126)                                   # 125 record keys + 1 legacy key, once
        summaries = [m for m in ap.logs if "summary:" in m]
        self.assertEqual(len(summaries), 11)                                     # one per tick
        self.assertIn("125 keys released by their terms, 0 new", summaries[-1])
        self.assertEqual(len(ap.logs), first + 10)                               # later ticks add the summary line only

    def test_a_key_that_leaves_and_returns_logs_again(self):
        d, ap = tempfile.mkdtemp(), AP()
        e = [("s", "k", "c")]
        self.assertEqual(self.tick(ap, d, [], e), 1)
        self.assertEqual(self.tick(ap, d, [], []), 0)                            # unreleased (a pilot gate re-held it)
        self.assertEqual(self.tick(ap, d, [], e), 1)                             # released again: a state change, logged

    def test_old_unnamespaced_keys_do_not_relog(self):
        import json
        d, ap = tempfile.mkdtemp(), AP()
        (__import__("pathlib").Path(d) / "hold_release_logged.json").write_text(json.dumps(["s/k/c"]))
        self.assertEqual(self.tick(ap, d, [], [("s", "k", "c")]), 0)

    def test_the_other_pass_already_logged_it(self):
        d, ap = tempfile.mkdtemp(), AP()
        KW.log_hold_releases(ap, d, [("s", "k", "c")], "release_on met", reset=True)
        self.assertEqual(KW.log_hold_releases(ap, d, [("s", "k", "c")], "release terms met", reset=True), 0)
