"""FABLE-FLOW-2200: releasing a hold that covers more than 3 items launches THREE pilots first (WAVE-PILOT-FIX 11-17); the rest stay held until the first passes GEN."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hold_records as HR  # noqa: E402
import kit_wave as KW  # noqa: E402

PLAN = "p" * 64
ITEMS = [f"t{i:02d}" for i in range(34)]


def cfg(items=ITEMS, store=True, **extra):
    c = {"dies": {"s81": {"event": "B6gG3", "plan": "/x/B6gG3.json", "plan_sha256": PLAN, "hold_event_items": {PLAN: list(items)}}}}
    if store:
        c["_release_pilot"] = {}
    c.update(extra)
    HR.add_record(c, "s81", {"id": "svc", "plan_sha": PLAN, "reason": "tree fix", "release": ["event_adopt:B6gG3"], "patterns": ["t*"], "owner": "TEST", "cause": "shared test cause"})
    return c


def compile_(c, rows=()):
    c["_item_rows"] = list(rows)
    c["_item_active"] = {}
    for r in rows:
        if r.get("status") in ("RUNNING", "ENQUEUED", "PASS", "ROUTE-HELD", "SIGNED"):
            c["_item_active"].setdefault(r["die"], []).append(r["item"])
    return HR.compile_holds(c, KW.hold_ctx(c))


class ReleasePilot(unittest.TestCase):
    def test_bulk_release_launches_one_pilot(self):
        c = cfg()
        c["_now"] = 1000.0
        rel = compile_(c)
        self.assertEqual(len(rel), 3)                                          # THREE released
        pilots = [r[1] for r in rel]
        held = c["dies"]["s81"]["hold_items"]
        self.assertEqual(len(held), 31)
        self.assertTrue(all(p not in held for p in pilots))
        self.assertTrue(all("RELEASE PILOT" in v and all(p in v for p in pilots) for v in held.values()))
        self.assertEqual(sorted(c["_release_pilot"]["s81|svc"]["pilots"]), sorted(pilots))

    def test_pilot_is_the_die_choice_then_the_smallest_item(self):
        c = cfg()
        c["dies"]["s81"]["pilot_item"] = "t17"
        compile_(c)
        self.assertEqual(c["_release_pilot"]["s81|svc"]["pilot"], "t17")
        c = cfg()
        c["_item_cells"] = {("s81", i): 5000 - n for n, i in enumerate(ITEMS)}   # t33 is the smallest, then t32, t31
        compile_(c)
        self.assertEqual(c["_release_pilot"]["s81|svc"]["pilots"], ["t33", "t32", "t31"])

    def test_rest_stay_held_while_the_pilot_runs_or_fails(self):
        c = cfg()
        c["_now"] = 1000.0
        pilots = [r[1] for r in compile_(c)]
        for status in ("RUNNING", "FAIL"):
            c2 = cfg()
            c2["_release_pilot"] = c["_release_pilot"]
            rel = compile_(c2, [{"die": "s81", "item": pilots[0], "status": status, "started": 1001}])
            self.assertEqual([k for _, k, _ in rel], pilots, status)
            self.assertEqual(len(c2["dies"]["s81"]["hold_items"]), 31, status)

    def test_a_pilot_that_passes_gen_releases_the_rest(self):
        c = cfg()
        c["_now"] = 1000.0
        pilot = [r[1] for r in compile_(c)][1]                                  # the first pilot of the three that passes releases the rest
        c2 = cfg()
        c2["_release_pilot"] = c["_release_pilot"]
        rel = compile_(c2, [{"die": "s81", "item": pilot, "status": "PASS", "started": 1500}])
        self.assertEqual(len(rel), 34)
        self.assertEqual(c2["dies"]["s81"]["hold_items"], {})
        self.assertTrue(c2["_release_pilot"]["s81|svc"]["passed"])
        c3 = cfg()                                                              # and stays released after the pilot row ages out
        c3["_release_pilot"] = c2["_release_pilot"]
        self.assertEqual(len(compile_(c3)), 34)

    def test_an_old_pass_before_the_release_is_no_pilot_pass(self):
        c = cfg()
        c["_now"] = 5000.0
        pilot = [r[1] for r in compile_(c)][0]
        c2 = cfg()
        c2["_release_pilot"] = c["_release_pilot"]
        rel = compile_(c2, [{"die": "s81", "item": pilot, "status": "PASS", "started": 100}])
        self.assertEqual(len(rel), 3)

    def test_small_releases_and_already_launched_releases_are_untouched(self):
        c = cfg(items=ITEMS[:3])
        self.assertEqual(len(compile_(c)), 3)                                   # 3 items: all at once
        self.assertEqual(c["_release_pilot"], {})
        c = cfg()
        rel = compile_(c, [{"die": "s81", "item": "t05", "status": "RUNNING", "started": 1}])
        self.assertEqual(len(rel), 34)                                          # already launched before the gate existed: no re-hold
        self.assertTrue(c["_release_pilot"]["s81|svc"]["passed"])
        c = cfg()
        rel = compile_(c, [{"die": "s81", "item": "t05", "status": "FAIL", "started": 1}])
        self.assertEqual(len(rel), 3)                                           # an old FAIL row is not a launch

    def test_fails_open(self):
        self.assertEqual(len(compile_(cfg(store=False))), 34)                   # no state store: old behaviour
        c = cfg()
        c["dies"]["s81"]["hold_records"][0]["pilot_release"] = False             # a record may opt out
        self.assertEqual(len(compile_(c)), 34)

    def test_live_gen_receipt_releases_before_place_and_only_after_release(self):
        import hashlib, json, tempfile
        path = Path(tempfile.mkdtemp())
        spec = {"die":"s81", "item":"t00", "src":"/tree", "src_manifest_hash":"a"*64,
                "plan":"/x/B6gG3.json", "gen_args":[], "gen_env":{}}
        file = path/"spec.json"; file.write_text(json.dumps(spec))
        stages = {stage:0 for stage in KW.GEN_PILOT_STAGES}
        self.assertTrue(KW.publish_gen_pilot_receipt(file,hashlib.sha256(file.read_bytes()).hexdigest(),stages))
        c = cfg(); c["_now"]=1000.0
        c["dies"]["s81"].update(src="/tree",src_manifest_hash="a"*64)
        self.assertIn("t00",[r[1] for r in compile_(c)])
        c["dies"]["s81"]["hold_records"].append({"id":"physical","plan_sha":PLAN,"items":["t33"],
            "reason":"physical proof still required","release":["result:PHYS:ready"]})
        row={"die":"s81","item":"t00","status":"RUNNING","started":1000.0,"dir":str(path)}
        self.assertFalse(KW.release_pilot_passed([dict(row,started=999.99)],"s81","t00",1000,c))
        self.assertFalse(KW.release_pilot_passed([dict(row,item="t01")],"s81","t00",1000,c))
        import os
        receipt=path/"gen_pilot.json"
        os.utime(receipt,(999.99,999.99))
        self.assertFalse(KW.release_pilot_passed([row],"s81","t00",1000,c))
        os.utime(receipt,(1001,1001))
        self.assertTrue(KW.release_pilot_passed([row],"s81","t00",1000,c))
        self.assertEqual(len(compile_(c,[row])),34)
        self.assertEqual(c["dies"]["s81"]["hold_items"],{"t33":"physical proof still required"})
        self.assertFalse((path/"result.json").exists())           # no whole-job/physical PASS was manufactured

    def test_live_gen_receipt_rejects_wrong_source_spec_or_incomplete_stage(self):
        import copy, hashlib, json, tempfile
        path=Path(tempfile.mkdtemp())
        spec={"die":"s81","item":"t00","src":"/tree","src_manifest_hash":"a"*64,
              "plan":"/x/B6gG3.json","gen_args":[],"gen_env":{}}
        file=path/"spec.json"; file.write_text(json.dumps(spec))
        stages={stage:0 for stage in KW.GEN_PILOT_STAGES}
        KW.publish_gen_pilot_receipt(file,hashlib.sha256(file.read_bytes()).hexdigest(),stages)
        c=cfg(); c["dies"]["s81"].update(src="/tree",src_manifest_hash="a"*64)
        row={"die":"s81","item":"t00","status":"RUNNING","started":1001,"dir":str(path)}
        for field,value in (("src","/other"),("src_manifest_hash","b"*64),("plan","/other.json")):
            changed=copy.deepcopy(c);changed["dies"]["s81"][field]=value
            self.assertFalse(KW.release_pilot_passed([row],"s81","t00",1000,changed),field)
        file.write_text(json.dumps(dict(spec,dry_gen=True)))
        self.assertFalse(KW.release_pilot_passed([row],"s81","t00",1000,c))
        file.write_text(json.dumps(spec))
        receipt=path/"gen_pilot.json"; rec=json.loads(receipt.read_text());rec["stages"]["preflight"]=2
        receipt.write_text(json.dumps(rec))
        self.assertFalse(KW.release_pilot_passed([row],"s81","t00",1000,c))

    def test_kit_wave_wires_state_and_the_pass_test(self):
        src = (Path(__file__).resolve().parent / "kit_wave.py").read_text()
        self.assertIn('st.setdefault("hold_release_pilot", {})', src)
        self.assertIn("release_pilot_fn=lambda die, item, t0: release_pilot_passed(", src)
        self.assertTrue(KW.release_pilot_passed([{"die": "d", "item": "i", "status": "SIGNED", "started": 10}], "d", "i", 5))
        self.assertFalse(KW.release_pilot_passed([{"die": "d", "item": "i", "status": "FAIL", "started": 10}], "d", "i", 5))


if __name__ == "__main__":
    unittest.main()
