import json
import tempfile
import unittest
from pathlib import Path
import kit_wave as KW


class AP:
    DRY = False
    HUB_NAME = "intel2"

    def __init__(self, rc_out="KW_RECLAIM 900 12"):
        self.logs, self.cmds, self.out = [], [], rc_out

    def log(self, m):
        self.logs.append(m)

    def sh(self, cmd, timeout=0, input=None):
        self.cmds.append(cmd)
        if input:                        # FLEET-WATCH-R4: the reclaim script goes in on stdin (never in a cmdline)
            self.cmds.append(input)
        return 0, self.out, ""


def rec(att=3, status="FAIL"):
    d = Path(tempfile.mkdtemp())
    (d / "spec.json").write_text(json.dumps({"work": f"/srv/opentallas-scratch2/claude/w/items/t1/attempt_{att}"}))
    return {"die": "s81", "item": "t1", "attempt": att, "status": status, "dir": str(d), "kit": "epyc10:/x/gen/t1"}


CFG = {"dies": {"s81": {"gen_host": "epyc10"}}}


class Reclaim(unittest.TestCase):
    def test_fail_result_deletes_run_dbs_keeps_reports(self):
        a, r = AP(), rec()
        note = KW.reclaim_at_result(a, CFG, r, "FLOW")
        self.assertIn("900->12 MB", note)
        cmd = " ".join(" ".join(c) if isinstance(c, list) else c for c in a.cmds)
        for g in ("*.odb", "*.def", "*.spef"):
            self.assertIn(g, cmd)
        self.assertNotIn("reports", cmd)                              # reports / logs / bind inputs are not in the delete list
        self.assertIn("signoff.json", cmd)                            # fail-closed on a signed dir
        self.assertEqual(r["reclaim"], note)

    def test_infra_signed_optout_dry_and_attempt1_are_left_alone(self):
        for args in ((CFG, rec(), "INFRA"), ({"dies": {"s81": {"reclaim_failed": False}}}, rec(), "FLOW"),
                     (CFG, rec(status="SIGNED"), "FLOW")):
            a = AP()
            self.assertEqual(KW.reclaim_at_result(a, *args), "")
            self.assertEqual(a.cmds, [])
        a = AP()
        self.assertIn("not reclaimed", KW.reclaim_at_result(a, CFG, rec(att=1), "FLOW"))   # attempt 1's dir holds the later attempts
        self.assertEqual(a.cmds, [])


class ReclaimGuard(unittest.TestCase):
    def test_delete_goes_through_the_delete_guard_and_fails_closed(self):
        a = AP()
        KW.reclaim_at_result(a, CFG, rec(), "FLOW")
        cmd = " ".join(" ".join(c) if isinstance(c, list) else c for c in a.cmds)
        self.assertIn("ot_delete_guard.py", cmd)
        self.assertIn("protected.txt", cmd)
        self.assertIn(" check ", cmd)
        self.assertIn("delete guard missing", cmd)
        # the guard check precedes the delete
        self.assertLess(cmd.index(" check "), cmd.index(") -delete"))
        # missing module/list: skip branch exits before any delete
        self.assertLess(cmd.index("delete guard missing"), cmd.index(") -delete"))
