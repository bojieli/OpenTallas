"""TYPE-SAFE-2-AREA 11-08: slot channel repack map and abutted-lattice growth cost."""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import slot_channel_event as SC  # noqa: E402


def test_axis_map_rigid_cores_and_scaled_gaps():
    fr = [[100.0, 200.0], [300.0, 300.0]]          # one free gap, one zero-length cut
    m = SC.axis_map(fr, [60.0, 40.0])               # gap shrinks by 40, cut opens by 40
    assert m(50.0) == 50.0                          # before: unchanged
    assert abs(m(250.0) - 210.0) < 1e-9             # core between: rigid shift -40
    assert abs(m(350.0) - 350.0) < 1e-9             # after the opened cut: net 0
    assert abs(m(150.0) - 130.0) < 1e-9             # inside the gap: scaled


def test_free_intervals_find_abutment_cut():
    boxes = [(0, 0, 100, 10, {}, "a"), (100, 0, 200, 10, {}, "b")]
    fr = SC.free_intervals(boxes, 0, 300.0)
    assert [100.0, 100.0] in fr and [200.0, 300.0] in fr


def test_transform_keeps_face_points():
    t = dict(outline_um=[300.0, 100.0], hard_cores=[dict(origin_um=[110.0, 20.0], outline_um=[50.0, 50.0])],
             internal_stations=[dict(from_um=[150.0, 0.0], to_um=[150.0, 60.0], regs_um=[[150.0, 30.0]])])
    m = SC.axis_map([[100.0, 100.0], [160.0, 300.0]], [20.0, 120.0])
    SC.transform_type(t, m, lambda y: y, 300.0, 100.0)
    assert t["hard_cores"][0]["origin_um"] == [130.0, 20.0]
    e = t["internal_stations"][0]
    assert e["from_um"] == [150.0, 0.0]             # S-face end stays (abutment)
    assert e["regs_um"][0][0] == 170.0              # interior site moves with the core


def test_lattice_cost(tmp_path):
    plan = dict(partition_types=dict(a=dict(outline_um=[100.0, 100.0]), b=dict(outline_um=[100.0, 100.0])),
                partitions=[dict(name="p0", type="a", origin_um=[0.0, 0.0]), dict(name="p1", type="b", origin_um=[100.0, 0.0]),
                            dict(name="p2", type="b", origin_um=[0.0, 100.0]), dict(name="p3", type="a", origin_um=[100.0, 100.0])])
    gr = dict(types=[dict(type="a", outline=[100, 100], new_outline=[110, 100])])
    pf, gf, of = tmp_path / "p.json", tmp_path / "g.json", tmp_path / "o.json"
    pf.write_text(json.dumps(plan)); gf.write_text(json.dumps(gr))
    subprocess.run([sys.executable, str(HERE / "slot_lattice_cost.py"), str(pf), str(gf), "--cell", "100,100",
                    "--margin", "0", "--out", str(of)], check=True, capture_output=True)
    r = json.loads(of.read_text())["x"]
    assert r["row_sum"] == 10.0                     # each row: one grown partition
    assert r["lattice"]["total"] == 20.0            # a sits in both columns -> both stretch
