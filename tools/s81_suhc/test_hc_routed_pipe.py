"""A new default cannot silently qualify against the old routed cseq view."""
import unittest
import hc_gate as gate

class RoutedPipeTest(unittest.TestCase):
    def probe(self, pipe, rf=4):
        mod = "ot_s81_hc_cseq"
        text = (gate.ROOT / gate.TILES[mod]["src"]).read_text()
        params = gate.tile_params(text, mod)
        params.update(HALF=1, RLY=2, RF=rf, DW=6, PIPE=pipe, PD=40)
        line = "HCTILE " + mod + " dut.seq " + " ".join(f"{k}={v}" for k,v in params.items())
        return gate.tile_check(line, [mod])[mod]

    def test_published_return_ordered_master_matches(self):
        self.assertTrue(self.probe(0)["ok"])

    def test_new_issue_ordered_master_needs_its_own_route(self):
        result = self.probe(1)
        self.assertFalse(result["ok"])
        self.assertEqual(result["routed_params"][0]["PIPE"], 0)
        self.assertEqual(result["foreign"][0]["params"]["PIPE"], 1)

    def test_existing_inert_rf_tolerance_is_preserved(self):
        self.assertTrue(self.probe(0, rf=5)["ok"])

if __name__ == "__main__":
    unittest.main()
