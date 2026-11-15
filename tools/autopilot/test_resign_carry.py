#!/usr/bin/env python3
"""KW-FIX-4/HBMRS 11-03: a SIGNED-UNVERSIONED autopilot job is carried by a valid RE-SIGN of its same routed DB
(autopilot.resign_carry); a superseded-block FAIL reads SUPERSEDED in kit_wave_stages.tsv (no ssh, hosts faked)"""
import importlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

DB = "/srv/opentallas-scratch2/claude/kit-wave/hbm/d44o/items/x/gen/x_1/eco/i1/run/results/asap7/hbc_x/base/6_final.odb"
COPY = "/home/ubuntu/scratch-root/claude/ss24/x_kit/run/results/asap7/hbc_x/base/6_final.odb"


def rec(**kw):
    r = dict(name="hbc_x", path="/r/signoff/signoff.json", host="dear-crayfish", versioned=True, resign=True,
             flow_tag="flow-20261102-r-hbm", src_commit="b" * 40, prov_file="/r/PROVENANCE.json", routed_db=COPY,
             resign_error=None)
    r.update(kw)
    return r


class ResignCarry(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["AP_DIR"] = self.tmp.name
        os.environ["AP_RELEASE_CACHE"] = str(Path(self.tmp.name) / "release_cache.json")
        os.environ["AP_OT_RUN_SIGNALS"] = str(Path(self.tmp.name) / "no_signals.log")
        import autopilot
        self.ap = importlib.reload(autopilot)
        self.ap.DRY = False
        self.ap._all_flow_tags = lambda: [("flow-20261103-v-hbm", 3), ("flow-20261102-r-hbm", 2), ("flow-20261102-r-kv", 1)]
        self.sha = {("intel2", DB): "s1", ("dear-crayfish", "/r/PROVENANCE.json"): "s1"}
        self.calls = []

    def tearDown(self):
        self.tmp.cleanup()
        for k in ("AP_DIR", "AP_RELEASE_CACHE", "AP_OT_RUN_SIGNALS"):
            os.environ.pop(k, None)

    def probe(self, host, code, args, timeout=0):
        self.calls.append((host, args))
        if code is self.ap.PROBE_PROVENANCE:
            return {"ok": True}
        k = (host, args.get("prov") or args["db"])
        return {"sha": self.sha[k]} if k in self.sha else {"error": "no such file"}

    def job(self, **kw):
        j = dict(id="j1", die="hbm", type="x", status="SIGNED-UNVERSIONED", host="intel2", src="b@e96f241822a",
                 archive="localhost:/srv/opentallas-scratch2/claude/autopilot/closed/hbm/x", mirror="", kit="intel2:/k",
                 signoff={"odb": DB, "tt_wns": 1.0, "ff_wns": 2.0}, history=[], started=2e9)
        j.update(kw)
        return j

    def carry(self, j, recs, budget=None):
        return self.ap.resign_carry(j, {"signed_records": recs}, probe=self.probe, budget=budget or [10])

    def test_byte_copy_resign_carries(self):
        got = self.carry(self.job(), [rec()])
        self.assertEqual((got["flow_tag"], got["record"], got["routed_db_sha256"]),
                         ("flow-20261102-r-hbm", "/r/PROVENANCE.json", "s1"))

    def test_different_db_or_bad_record_does_not_carry(self):
        self.sha[("dear-crayfish", "/r/PROVENANCE.json")] = "s2"
        self.assertIsNone(self.carry(self.job(), [rec()]))                       # other routed DB bytes
        self.sha[("dear-crayfish", "/r/PROVENANCE.json")] = "s1"
        self.assertIsNone(self.carry(self.job(), [rec(flow_tag="flow-20261102-r-kv")]))   # tag of another die
        self.assertIsNone(self.carry(self.job(), [rec(flow_tag="flow-20261009-z-hbm")]))  # not a tag on origin
        self.assertIsNone(self.carry(self.job(), [rec(resign_error="re-sign LEC verdict None")]))
        self.assertIsNone(self.carry(self.job(), [rec(resign=None)]))            # a plain record is not a RE-SIGN
        self.assertIsNone(self.carry(self.job(), [rec(routed_db=COPY.replace("hbc_x", "hbc_y"))]))  # other design
        self.assertIsNone(self.carry(self.job(signoff={}), [rec()]))

    def test_db_read_where_the_run_ran(self):
        self.sha[("epyc2", DB)] = self.sha.pop(("intel2", DB))
        self.assertIsNone(self.carry(self.job(), [rec()]))
        self.assertIsNotNone(self.carry(self.job(ran_on="epyc2"), [rec()]))

    def test_budget_and_memo(self):
        self.assertIsNone(self.carry(self.job(), [rec()], budget=[0]))
        self.assertEqual(self.calls, [])
        j = self.job()
        self.assertIsNotNone(self.carry(j, [rec()]))
        n = len(self.calls)
        self.assertIsNotNone(self.carry(j, [rec()], budget=[0]))                # hashes kept on the job
        self.assertEqual(len(self.calls), n)

    def test_retry_unversioned_promotes_through_resign(self):
        Path(os.environ["AP_RELEASE_CACHE"]).write_text(json.dumps({"signed_records": [rec()]}))
        self.ap.rpy = self.probe
        self.ap.resolve_provenance = lambda src, flow="", die=None: {
            "src_commit": "e" * 40, "flow_tag": "", "error": "no flow release tag carries this commit's flow"}
        self.ap.first_flow_tag_ts = lambda die=None: 1.0                       # started after the first tag: no legacy
        j = self.job()
        st = {"jobs": {"j1": j}}
        self.ap.retry_unversioned(st)
        self.assertEqual((j["status"], j["flow_tag"], j["src_commit"]), ("ARCHIVED", "flow-20261102-r-hbm", "e" * 40))
        (prov,) = [a["prov"] for h, a in self.calls if "prov" in a and isinstance(a["prov"], dict)]
        self.assertEqual((prov["kind"], prov["verdict"], prov["resign_carry"]["record"]),
                         ("resign-carry", "SIGNED", "/r/PROVENANCE.json"))
        self.assertIn("flow-20261102-r-hbm", (Path(self.tmp.name) / "signed.tsv").read_text())

    def test_retry_unversioned_without_resign_stays(self):
        Path(os.environ["AP_RELEASE_CACHE"]).write_text(json.dumps({"signed_records": []}))
        self.ap.rpy = self.probe
        self.ap.resolve_provenance = lambda src, flow="", die=None: {"src_commit": "e" * 40, "flow_tag": "", "error": "none"}
        self.ap.first_flow_tag_ts = lambda die=None: 1.0
        j = self.job()
        self.ap.retry_unversioned({"jobs": {"j1": j}})
        self.assertEqual((j["status"], j.get("flow_tag")), ("SIGNED-UNVERSIONED", None))


class SupersededStages(unittest.TestCase):
    def test_superseded_fail_reads_superseded(self):
        import kit_wave as KW
        cfg = {"dies": {"hbm": {"gen_host": "h", "plan": "/p.json", "event": "d44v"}}}
        cur_b, old_b = "a" * 64, "b" * 64
        st = {"plans": {"h:/p.json|d44v": {"blocks": {"t1": cur_b}}},
              "items": {KW.item_key("hbm", "d44v", "t1", cur_b): dict(die="hbm", item="t1", event="d44v", block_sha=cur_b,
                                                                        status="FAIL", **{"class": "PLAN"}, reason="r1", updated=0),
                        KW.item_key("hbm", "d44g", "t0", old_b): dict(die="hbm", item="t0", event="d44g", block_sha=old_b,
                                                                        status="FAIL", **{"class": "PLAN"}, reason="no recipe", updated=0),
                        KW.item_key("hbm", "d44g", "t2", old_b): dict(die="hbm", item="t2", event="d44g", block_sha=old_b,
                                                                        status="CANCELLED", **{"class": "SUPERSEDED"}, updated=0)}}
        with tempfile.TemporaryDirectory() as d:
            KW.write_stages(st, d, cfg)
            rows = [ln.split("\t") for ln in open(os.path.join(d, KW.STAGES_FILE)).read().splitlines()]
            got = {r[1]: dict(zip(rows[0], r)) for r in rows[1:]}
        self.assertEqual((got["t1"]["status"], got["t1"]["class"], got["t1"]["plan_current"]), ("FAIL", "PLAN", "yes"))
        self.assertEqual((got["t0"]["status"], got["t0"]["class"], got["t0"]["plan_current"]), ("SUPERSEDED", "SUPERSEDED", "no"))
        self.assertIn("was FAIL PLAN: no recipe", got["t0"]["reason"])
        self.assertEqual(got["t2"]["status"], "CANCELLED")
        self.assertEqual(st["items"][KW.item_key("hbm", "d44g", "t0", old_b)]["status"], "FAIL")   # record unchanged


if __name__ == "__main__":
    unittest.main()
