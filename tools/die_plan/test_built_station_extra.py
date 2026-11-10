"""built_station_extra: lane_natural counts stations a kit step already built; the map is outside partition_types."""
import pathlib
import sys
import types
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import schema as S


def stub(extra):
    raw = {"built_station_extra": extra} if extra is not None else {}
    p = types.SimpleNamespace(raw=raw, _lane_clock_landing_cycles={},
                              lanes={"l": {"ports": ["a", "b"]}},
                              ports={"a": {"src": {"part": "x"}}, "b": {"dst": {"part": "y"}}},
                              parts={"m": {"type": "T"}})
    p.lane_crossings = lambda _lid: [("m", "ft5", None, None)]
    p.slot = lambda _part, _slot: {"stations": 6}
    return p


class BuiltStations(unittest.TestCase):
    def test_absent_map_is_plan_stations(self):
        d = S.Plan.lane_natural(stub(None), "l")
        self.assertEqual((d["stations"], d["cycles"]), (6, 8))

    def test_extra_counts_as_stations(self):
        d = S.Plan.lane_natural(stub({"T": {"ft5": 1}}), "l")
        self.assertEqual((d["stations"], d["cycles"]), (7, 9))

    def test_other_slot_unaffected(self):
        self.assertEqual(S.Plan.lane_natural(stub({"T": {"ft6": 2}}), "l")["stations"], 6)
        self.assertEqual(S.Plan.lane_natural(stub({"U": {"ft5": 2}}), "l")["stations"], 6)

    def test_helper_defaults(self):
        self.assertEqual(S.built_station_extra({}, "T", "ft5"), 0)
        self.assertEqual(S.built_station_extra({"built_station_extra": {"T": {"ft5": 3}}}, "T", "ft5"), 3)


if __name__ == "__main__":
    unittest.main()
