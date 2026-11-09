#!/usr/bin/env python3
"""Tests for tools/die_plan/transport_table.py: toy bind, each exposure class, and a mutant check (the class must vanish
when the toy no longer has that shape)."""
import json, tempfile, pathlib, unittest, sys, importlib.util, copy
HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("transport_table", HERE / "transport_table.py")
tt = importlib.util.module_from_spec(spec); spec.loader.exec_module(tt)


def member(sink_port, source, asb, landed, lane):
    return dict(sink_port=sink_port, sink_bits=[[0, 0]], source=source, source_bits=[[0, 0]], asbuilt_stages=asb, bound_stages=landed,
                landed_stages=landed, lane=lane)


def bus(lane, src, dst, asb, bound, width=8, leaves=None):
    return dict(lane=lane, src=src, dst=dst, bus_out=lane + "_o", bus_in=lane + "_i", width=width, planned_width=width, param="P", leaves=leaves or [f"{src}.u.o[{width}]"],
                source_bit_order="lsb_first", source_bits=[], forwarded=0, asbuilt_stages=[asb], bound_stages=bound, plan_cycles=bound, delta=bound - asb)


BASE_LAT = dict(buses=[bus("a1", "a", "b", 2, 2), bus("a2", "a", "c", 2, 6, leaves=["a.v.o[8]"]), bus("x_torn", "x", "y", 3, 7)])
BASE_GROUPS = dict(
    landing=[
        # ZERO + ABS: single-source, intact
        dict(sink="leaf_b", sink_part="b", src_part="a", aligned_by_lanes=True, aligned_landed=True, asbuilt_stage_set=[2], members=[member("p", "a.o", 2, 2, "a1")]),
        dict(sink="leaf_c", sink_part="c", src_part="a", aligned_by_lanes=True, aligned_landed=True, asbuilt_stage_set=[2], members=[member("p", "a.o", 2, 6, "a2")]),
        # TORN: same sink/source, same as-built stage, unequal landed
        dict(sink="leaf_y", sink_part="y", src_part="x", aligned_by_lanes=False, aligned_landed=False, asbuilt_stage_set=[3],
             members=[member("p", "x.o", 3, 7, "x_torn"), member("q", "x.o", 3, 9, "x_torn")]),
        # JOIN: one sink, two source partitions with different deltas
        dict(sink="leaf_j", sink_part="j", src_part="a", aligned_by_lanes=True, aligned_landed=True, asbuilt_stage_set=[2], members=[member("p", "a.o", 2, 4, "a2")]),
        dict(sink="leaf_j", sink_part="j", src_part="x", aligned_by_lanes=True, aligned_landed=True, asbuilt_stage_set=[3], members=[member("q", "x.o", 3, 9, "x_torn")]),
    ],
    replica=[dict(source="a.v.o", asbuilt_stages=2, sink_parts=["b", "c"], bound_depths={"b": [2], "c": [6]}, equal=False)],
    summary={})


class T(unittest.TestCase):
    def setUp(self):
        self.d = pathlib.Path(tempfile.mkdtemp())

    def run_tool(self, lat, groups):
        (self.d / "bind_latency.json").write_text(json.dumps(lat))
        (self.d / "bus_groups.json").write_text(json.dumps(groups))
        (self.d / "param_regen.json").write_text(json.dumps(dict(changed=[dict(inst="x.u", param="RT", asbuilt="1", bound=5)])))
        out = self.d / "out"
        tt.main([str(self.d), "--die", "toy", "--out", str(out)])
        return json.loads((out / "toy_summary.json").read_text()), out

    def test_classes(self):
        s, out = self.run_tool(BASE_LAT, BASE_GROUPS)
        self.assertEqual(s["buses"], 3)
        # a1 has delta 0, not torn/join/replica
        t = {l.split("\t")[0]: l.rstrip("\n").split("\t")[-1] for l in (out / "toy_buses.tsv").read_text().splitlines()[1:]}
        self.assertIn("ZERO", t["a1"]); self.assertIn("TORN", t["x_torn"]); self.assertIn("JOIN", t["a2"])
        self.assertEqual(s["torn_groups"], 1); self.assertEqual(s["join_sinks"], 1); self.assertEqual(s["replica_unequal"], 1)

    def test_mutants(self):
        lat = copy.deepcopy(BASE_LAT); g = copy.deepcopy(BASE_GROUPS)
        # no tear
        g["landing"][2]["members"][1]["landed_stages"] = 7
        g["landing"][2]["aligned_landed"] = True
        s, _ = self.run_tool(lat, g)
        self.assertEqual(s["torn_groups"], 0)
        # no join: only one source on leaf_j
        g = copy.deepcopy(BASE_GROUPS); g["landing"].pop()
        s, _ = self.run_tool(lat, g)
        self.assertEqual(s["join_sinks"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=1)
