import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_clk_land_obs as A  # noqa: E402
import clk_land_clear as C  # noqa: E402


def core(inst, x, y, w, h, obs="M7", halo=2.16):
    return dict(inst=inst, module="m_" + inst, origin_um=[x, y], outline_um=[w, h], orient="R0", obs_max=obs, halo_um=halo,
                lef="physical/none/%s.lef" % inst)


def plan(tap=(400.0, 400.0), relay=None, reserved=None, obs="M7"):
    t = dict(outline_um=[600.0, 600.0], hard_cores=[core("u_cap", 50, 50, 300, 300, obs)],
             clock=dict(taps=[dict(name="u_cap.ck", kind="core", xy=list(tap)), dict(name="clk_t1", xy=[500.0, 500.0])],
                        added_taps=[dict(name="clk_t2", xy=[10.0, 10.0])], reserved_sites_um=reserved or []),
             relay_sites=relay or {})
    return dict(die=dict(name="d", outline_um=[1000, 1000], reach_um=405, layer_budget={"partition_signal_max": "M7"}),
                partition_types={"t": t}, partitions=[], ports=[], lanes=[])


class T(unittest.TestCase):
    def test_flag_absent_apply_not_called_and_types_shared(self):
        import schema
        raw = plan()
        P = schema.Plan(raw)
        self.assertIs(P.types, raw["partition_types"])
        self.assertEqual(P.clk_land_clear_ledger, [])

    def test_hook_moves_tap_out_of_obstructing_core(self):
        import schema
        raw = plan(tap=(100.0, 200.0))
        raw["clk_land_clear"] = {"enable": 1}
        snap = json.dumps(raw, sort_keys=True)
        P = schema.Plan(raw)
        self.assertEqual(json.dumps(raw, sort_keys=True), snap)               # raw untouched
        x, y = P.types["t"]["clock"]["taps"][0]["xy"]
        self.assertFalse(50 < x < 350 and 50 < y < 350)
        self.assertEqual(P.types["t"]["clock"]["taps"][1]["xy"], [500.0, 500.0])   # clear tap unchanged
        self.assertEqual(A.counts(dict(raw, partition_types=P.types)), {})
        self.assertEqual(len(P.clk_land_clear_ledger), 1)

    def test_low_obs_core_is_not_a_hit(self):
        raw = plan(tap=(100.0, 200.0), obs="M4")
        self.assertEqual(A.counts(raw), {})

    def test_edge_pin_not_a_hit(self):
        self.assertEqual(A.counts(plan(tap=(50.2, 200.0))), {})

    def test_relay_body_moves_no_stack(self):
        raw = plan(relay={"a": [100.0, 200.0], "b": [100.0, 200.0], "c": [10, 10]})
        self.assertEqual(A.counts(raw)["t"]["by_cls"]["relay"]["body"], 2)
        types = copy.deepcopy(raw["partition_types"])
        C.apply(types, dict(raw, clk_land_clear={"enable": 1}))
        r = types["t"]["relay_sites"]
        self.assertEqual(r["c"], [10, 10])
        self.assertGreaterEqual(max(abs(r["a"][0] - r["b"][0]), abs(r["a"][1] - r["b"][1])), 0.5)
        self.assertEqual(A.counts(dict(raw, partition_types=types)), {})

    def test_relay_halo_only_is_ignored(self):
        self.assertEqual(A.counts(plan(relay={"a": [351.0, 200.0]})), {})

    def test_reserved_rect_in_halo_moves_with_stack(self):
        rect = [351.0, 200.0, 353.16, 201.35]
        raw = plan(reserved=[dict(rect_um=rect, kind="die_clock_tree", route_layers="M1-M2", stack_layers="M3-M7", stack_um=[rect])])
        self.assertEqual(A.counts(raw)["t"]["by_cls"]["reserved"]["halo"], 1)
        types = copy.deepcopy(raw["partition_types"])
        led = C.apply(types, dict(raw, clk_land_clear={"enable": 1}))
        e = types["t"]["clock"]["reserved_sites_um"][0]
        self.assertEqual(e["stack_um"][0], e["rect_um"])
        self.assertEqual(A.counts(dict(raw, partition_types=types)), {})
        self.assertEqual(len(led), 1)

    def test_apply_noop_keeps_objects(self):
        raw = plan(tap=(400.0, 400.0))
        types = dict(raw["partition_types"])
        before = types["t"]
        self.assertEqual(C.apply(types, dict(raw, clk_land_clear={"enable": 1})), [])
        self.assertIs(types["t"], before)

    def test_types_option_limits_scope(self):
        raw = plan(tap=(100.0, 200.0))
        types = copy.deepcopy(raw["partition_types"])
        self.assertEqual(C.apply(types, dict(raw, clk_land_clear={"enable": 1, "types": ["other"]})), [])
        self.assertEqual(types["t"]["clock"]["taps"][0]["xy"], [100.0, 200.0])

    def test_schema_registers_flag(self):
        import schema
        base = plan()
        e0 = set(schema.validate_structure(base))
        for v in ({"enable": 1}, {"enable": True, "types": ["t"], "classes": ["tap", "relay"], "clear_um": 2.0, "max_move_um": 60}):
            self.assertEqual(set(schema.validate_structure(dict(base, clk_land_clear=v))) - e0, set())
        bad = set(schema.validate_structure(dict(base, clk_land_clear={"enable": 1, "bogus": 1}))) - e0
        self.assertTrue(bad and all("clk_land_clear" in m or "bogus" in m for m in bad), bad)
        self.assertEqual({m for m in e0 if "clk_land_clear" in m}, set())

    def test_unmovable_is_reported(self):
        raw = plan(tap=(100.0, 200.0))
        raw["clk_land_clear"] = {"enable": 1, "max_move_um": 5}
        types = copy.deepcopy(raw["partition_types"])
        led = C.apply(types, raw)
        self.assertIsNone(led[0]["new"])


if __name__ == "__main__":
    unittest.main()
