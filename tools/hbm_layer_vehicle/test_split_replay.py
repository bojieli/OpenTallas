import unittest

from hbm_layer_vehicle.split_replay import split


class SplitScopeTest(unittest.TestCase):
    def fixture(self):
        rep = {"events": []}
        for p in range(2):
            rep["events"] += [dict(k="D", dom="serial", cyc=p * 10, prog=p, port="command", val="1"),
                              dict(k="C", dom="serial", cyc=p * 10 + 1, rec=p, port=f"vm:{p*8:x}", val="1")]
        man = {"su_programmes": [dict(programme=p, records=[p]) for p in range(2)]}
        return rep, man

    def test_expected_carry_is_explicit_component_only(self):
        rep, man = self.fixture()
        parts = split(rep, man, 3)
        self.assertEqual(len(parts), 2)
        carry = next(e for e in parts[1]["events"] if e["k"] == "M")
        self.assertEqual(carry["state_seed_provenance"], "expected_reference")
        self.assertIn("expected_reference", parts[1]["state_seed_provenance"])
        for p in parts:
            self.assertEqual(p["scope"], "component_probe")
            self.assertFalse(p["qualifies_native_layer"])
            self.assertFalse(p["qualifies_native_chain"])

    def test_native_requests_fail_closed(self):
        rep, man = self.fixture()
        for scope in ["native_layer", "native_chain"]:
            with self.assertRaisesRegex(ValueError, "not measured RTL state"):
                split(rep, man, 3, scope=scope)

    def test_native_input_metadata_cannot_be_relabelled(self):
        rep, man = self.fixture()
        rep["scope"] = "native_chain"
        with self.assertRaises(ValueError):
            split(rep, man, 3)


if __name__ == "__main__":
    unittest.main()
