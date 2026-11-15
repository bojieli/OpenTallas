"""COORD 11-01 18:3x: attempts on a superseded plan block are stopped at the next tick (cancel_superseded)."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import kit_wave as KW


class Superseded(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp())
        self.stops, self.logs, self.remote = [], [], []

        def sh(cmd, timeout=None, input=None):
            if input:                                    # wave_jobs.STOP_KIT on one fleet host
                self.remote.append(json.loads(cmd[-1].strip("'"))["roots"])
                return 0, json.dumps({"containers": ["dpkit-old-1"], "scopes": []}), ""
            self.stops.append(cmd[-1])
            return 0, "", ""
        self.AP = SimpleNamespace(DRY=False, log=self.logs.append, sh=sh, HUB_NAME="intel2")
        cur_blk, old_blk = "a" * 40, "b" * 40
        self.cfg = {"dies": {"d": {"plan": "/p.json", "event": "e", "gen_host": "h"}}}
        wdir = self.t / "w"; wdir.mkdir()
        (wdir / "place_service.json").write_text(json.dumps({"unit": "kw-place-old"}))
        (self.t / "state.json").write_text(json.dumps({"jobs": {"j1": {"status": "RUNNING", "unit": "ap-j1-a1"},
                                                                 "j2": {"status": "WAIT-GEOM", "unit": "ap-j2-a1"}}}))
        self.st = {"plans": {"h:/p.json|e": {"blocks": {"t": cur_blk, "u": cur_blk, "v": cur_blk}}},
                   "items": {
                       KW.item_key("d", "e", "t", cur_blk): dict(die="d", item="t", attempt=2, status="RUNNING", unit="kw-cur"),
                       KW.item_key("d", "e", "t", old_blk): dict(die="d", item="t", attempt=1, status="RUNNING",
                                                                 unit="kw-old", dir=str(wdir), stage="place"),
                       KW.item_key("d", "e", "u", old_blk): dict(die="d", item="u", attempt=1, status="ENQUEUED", q_id="j1"),
                       KW.item_key("d", "e", "v", old_blk): dict(die="d", item="v", attempt=1, status="ENQUEUED", q_id="j2"),
                       KW.item_key("d", "e", "w", old_blk): dict(die="d", item="w", attempt=1, status="FAIL"),
                   }}

    def test_stops_only_superseded_active(self):
        notices = {}
        n = KW.cancel_superseded(self.AP, self.cfg, self.st, notices, self.t)
        self.assertEqual(n, 2)
        self.assertEqual(sorted(self.stops), ["ap-j1-a1", "kw-old", "kw-place-old"])
        it = self.st["items"]
        self.assertEqual(it[KW.item_key("d", "e", "t", "a" * 40)]["status"], "RUNNING")      # current block untouched
        self.assertEqual(it[KW.item_key("d", "e", "t", "b" * 40)]["class"], "SUPERSEDED")
        self.assertEqual(it[KW.item_key("d", "e", "v", "b" * 40)]["status"], "ENQUEUED")     # waiting job: no compute
        self.assertEqual(it[KW.item_key("d", "e", "w", "b" * 40)]["status"], "FAIL")
        self.assertEqual(len(notices["d"]), 2)

    def test_no_probe_or_opt_out_is_noop(self):
        st = dict(self.st, plans={})
        self.assertEqual(KW.cancel_superseded(self.AP, self.cfg, st, {}, self.t), 0)
        self.cfg["dies"]["d"]["cancel_superseded"] = False
        self.assertEqual(KW.cancel_superseded(self.AP, self.cfg, self.st, {}, self.t), 0)
        self.assertEqual(self.stops, [])

    def test_cap_per_tick(self):
        self.cfg["supersede_max_per_tick"] = 1
        self.assertEqual(KW.cancel_superseded(self.AP, self.cfg, self.st, {}, self.t), 1)
        self.assertEqual(KW.cancel_superseded(self.AP, self.cfg, self.st, {}, self.t), 1)   # the rest next tick


if __name__ == "__main__":
    unittest.main()
