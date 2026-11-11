"""WAVE-OPS-1 11-10 (COORD, HBM-CORES-B q_hub_ne/epyc8): item_inputs probes the item plan's dir + a sampled pins_file;
prov_stage names prov_view's last traceback line."""
import json, os, subprocess, tempfile, unittest
import kit_wave as KW


def cfg(plan):
    return {"dies": {"hbm": {"item_inputs": {"q_hub_ne": {"plan": plan, "note": "x /srv/ignored/path"}}}}}


class PlanPins(unittest.TestCase):
    def test_plan_dir_is_an_input(self):
        ins = KW.item_inputs(cfg("/srv/x/claude/l/plan_p9/die_plan.json"), "hbm")
        self.assertIn("/srv/x/claude/l/plan_p9/die_plan.json", ins["q_hub_ne"])
        self.assertIn("/srv/x/claude/l/plan_p9", ins["q_hub_ne"])

    def probe(self, d, make_core):
        os.makedirs(os.path.join(d, "cores"))
        if make_core:
            open(os.path.join(d, "cores", "a_pins.json"), "w").write("{}")
        plan = os.path.join(d, "die_plan.json")
        json.dump({"partition_types": {"t": {"hard_cores": [{"pins_file": "cores/a_pins.json"},
                                                            {"pins_file": "cores/b_pins.json"}]}}}, open(plan, "w"))
        o = subprocess.run(["bash", "-c", KW._deep_probe_cmd([plan])], capture_output=True, text=True).stdout
        return plan, o

    def test_missing_pins_file_is_a_D_line(self):
        with tempfile.TemporaryDirectory() as d:
            plan, o = self.probe(d, False)
            self.assertIn("D %s %s/cores/a_pins.json" % (plan, d), o)

    def test_present_pins_file_is_silent(self):
        with tempfile.TemporaryDirectory() as d:
            plan, o = self.probe(d, True)
            self.assertEqual(o.strip(), "")

    def test_json_without_pins_is_silent(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "a.json"); json.dump({"base": "rel"}, open(p, "w"))
            o = subprocess.run(["bash", "-c", KW._deep_probe_cmd([p])], capture_output=True, text=True).stdout
            self.assertEqual(o.strip(), "")

    def test_prov_tb_last(self):
        t = ("log\nTraceback (most recent call last):\n  File \"prov_view.py\", line 3, in <module>\n    x()\n"
             "KeyError: 'ot_hbm_core'\n")
        self.assertEqual(KW.prov_tb_last(t), "KeyError: 'ot_hbm_core'")
        self.assertEqual(KW.prov_tb_last("no crash\nPROV_JSON {}"), "")

    def test_prov_stage_message_names_the_crash(self):
        calls = []
        def run(name, cmd, idempotent=False):
            if name == "prov_views":
                return 1, "Traceback (most recent call last):\n  File \"p\", line 1\nValueError: bad pins q_hub_ne\n"
            return 0, ""
        def fail(stage, txt, *a):
            calls.append(txt); return 7
        with tempfile.TemporaryDirectory() as d:
            sp = {"gen_host": "localhost", "hub": "localhost", "work": d, "item": "q_hub_ne", "prov_views": {},
                  "plan": "/p.json", "src": "/s"}
            r = KW.prov_stage(sp, run, lambda c: c, fail, {})
        self.assertEqual(r, (None, 7))
        self.assertTrue(calls[0].startswith("PROVISIONAL view FAIL (KW-PROV-1): prov_view.py crashed on q_hub_ne: "
                                            "ValueError: bad pins q_hub_ne"), calls[0][:200])


if __name__ == "__main__":
    unittest.main()
