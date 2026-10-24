"""RETIRED-HOST (HOSTFIX 2026-10-17): retired fleet hosts in a spec's hosts / host_require are dropped with a warning
and the job falls back to admission, instead of INVALID 'unknown host ot-epyc1tb' (qkd_static_ectla_k3-r3-c71c412db)."""
import contextlib
import io
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))
import closure_loop as cl  # noqa: E402
import retired_hosts as R  # noqa: E402
import submit_exact as SE  # noqa: E402


def spec(**kw):
    s = {"name": "t-r1-abcdef123", "block": "t", "owner": "claude:T", "source": {"branch": "b", "commit": "abcdef123"},
         "stages": {"bench": []}}
    s.update(kw)
    return s


class RetiredHosts(unittest.TestCase):
    def test_drop_keeps_live_hosts(self):
        s = spec(hosts=["ot-epyc1tb", "ot-epyc4", "ot-pve1"])
        out, warns = R.drop_retired_hosts(s, {"ot-epyc4", "ot-pve1"})
        self.assertEqual(out["hosts"], ["ot-epyc4", "ot-pve1"])
        self.assertEqual(s["hosts"], ["ot-epyc1tb", "ot-epyc4", "ot-pve1"], "input spec must not be mutated")
        self.assertEqual(len(warns), 1)
        self.assertIn("ot-epyc1tb", warns[0])

    def test_emptied_lists_fall_back_to_admission(self):
        out, warns = R.drop_retired_hosts(spec(hosts=["ot-epyc3"], host_require=["ot-epyc2", "ot-epyc1tb"]), set())
        self.assertNotIn("hosts", out)
        self.assertNotIn("host_require", out)
        self.assertEqual(len(warns), 2)

    def test_unchanged_spec_is_same_object(self):
        s = spec(hosts=["ot-epyc4"])
        out, warns = R.drop_retired_hosts(s, {"ot-epyc4"})
        self.assertIs(out, s)
        self.assertEqual(warns, [])

    def test_reenabled_host_in_table_wins(self):
        out, warns = R.drop_retired_hosts(spec(hosts=["ot-epyc3"]), {"ot-epyc3"})
        self.assertEqual(out["hosts"], ["ot-epyc3"])
        self.assertEqual(warns, [])

    def test_hosts_json_extra_retired(self):
        self.assertIn("ot-old9", R.retired_names({"retired_hosts": ["ot-old9"]}))

    def test_daemon_validate_no_longer_invalid(self):
        s = spec(hosts=["ot-epyc1tb", "epyc3"], host_require=["ot-epyc1tb"])   # FLEET-NEW3: epyc3 is a live host
        self.assertTrue(any("unknown host" in e for e in cl.validate(s)), "precondition: the raw spec is rejected")
        out, warns = cl.drop_retired_hosts(s)
        self.assertFalse(any("unknown host" in e for e in cl.validate(out)), cl.validate(out))
        self.assertEqual(out["hosts"], ["epyc3"])
        self.assertNotIn("host_require", out)
        self.assertEqual(len(warns), 2)

    def test_typo_host_still_invalid(self):
        out, _ = cl.drop_retired_hosts(spec(hosts=["ot-epyc44"]))
        self.assertTrue(any("unknown host ot-epyc44" in e for e in cl.validate(out)))

    def test_submit_exact_strips_and_warns(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            out = SE.drop_retired(spec(hosts=["ot-epyc1tb"]))
        self.assertNotIn("hosts", out)
        self.assertIn("RETIRED-HOST WARN", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
