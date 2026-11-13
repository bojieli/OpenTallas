"""KW-FIX-46 11-12 (STA2204-1): a re-sign replays the signed record's bound-ff reference when the kit has none."""
import json, os, sys, tempfile, unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import resign  # noqa: E402

# ot_s81_su_smc record epyc8:/srv/opentallas-scratch2/claude/s81-svcrs-3/resign/smc_kd/signoff/signoff.json (policy as signed)
SMC_POLICY = {"ff_vclk": "bound-ff", "ff_vclk_bound_ps": 202.5, "insertion_bound": None,
              "ff_vclk_contract": "S81 native core view modes: FF hold vclk bound-ff 202.5 (COORD ruling 11-10: same S81 "
                                  "core-view IO reference as every S81 core)"}


class FfReplayTest(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.kit = os.path.join(self.td.name, "orfs")
        os.makedirs(self.kit)
        open(os.path.join(self.kit, "config.mk"), "w").close()
        self.rec = os.path.join(self.td.name, "signoff.json")
        json.dump({"verdict": "SIGNED", "policy": SMC_POLICY}, open(self.rec, "w"))

    def tearDown(self):
        self.td.cleanup()

    def so(self, rec):
        os.makedirs(os.path.join(self.td.name, "run", "results", "asap7", "x", "base"), exist_ok=True)
        open(os.path.join(self.td.name, "run", "results", "asap7", "x", "base", "6_final.v"), "w").close()
        kit_run = os.path.join(self.kit, "run")
        os.makedirs(os.path.join(kit_run, "results", "asap7", "x", "base"), exist_ok=True)
        open(os.path.join(kit_run, "results", "asap7", "x", "base", "6_final.v"), "w").close()
        so, _ = resign.run_cmds(self.kit, kit_run, self.td.name, os.path.join(self.td.name, "out"), "img", "n",
                                source_record=rec)
        return so

    def test_smc_record_replays_bound_ff(self):
        so = self.so(self.rec)
        i = so.index("--ff-vclk")
        self.assertEqual(so[i + 1], "bound-ff")
        self.assertEqual(so[so.index("--ff-bound-ps") + 1], "202.5")
        self.assertIn("COORD ruling 11-10", so[so.index("--ff-vclk-contract") + 1])
        self.assertIn(self.rec, so[so.index("--ff-vclk-contract") + 1])

    def test_kit_with_own_reference_keeps_auto(self):
        json.dump({"insertion_ps": 250, "insertion_ff_ps": 202.5}, open(os.path.join(self.kit, "sdc_lint.json"), "w"))
        so = self.so(self.rec)
        self.assertEqual(so[so.index("--ff-vclk") + 1], "auto")
        self.assertNotIn("--ff-bound-ps", so)

    def test_no_record_or_other_policy_keeps_auto(self):
        self.assertEqual(self.so(None)[self.so(None).index("--ff-vclk") + 1], "auto")
        json.dump({"policy": {"ff_vclk": "sdc"}}, open(self.rec, "w"))
        self.assertEqual(self.so(self.rec)[self.so(self.rec).index("--ff-vclk") + 1], "auto")
        self.assertEqual(self.so("/nonexistent/signoff.json")[2:4], self.so(None)[2:4])

    def test_cli_accepts_source_record(self):
        self.assertIn("--source-record", open(resign.__file__).read())


if __name__ == "__main__":
    unittest.main()
