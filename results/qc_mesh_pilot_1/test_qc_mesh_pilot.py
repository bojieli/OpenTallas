"""QC-MESH-PILOT-1 builder tests (synthetic A0-quad fixture; no plan/tree from the fleet needed).
run: python3 -m pytest -q results/qc_mesh_pilot_1/test_qc_mesh_pilot.py"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import qc_mesh_pilot as QP   # noqa: E402

W, H = 1235.52, 2617.92
COLS = [68.064, 545.376, 690.144, 1167.456]
ROWS = [186.976, 560.992, 934.752, 1308.96, 1683.168, 2056.928, 2430.944]
MID = [154.46, 463.33, 772.19, 1081.06]


def fixture(tmp):
    cores = [dict(inst=f"u_t{i}", module="qfd_tile_nk_romleaf_rpf", origin_um=o, outline_um=[457.92, 1157.76])
             for i, o in enumerate([[77.76, 69.12], [699.84, 69.12], [77.76, 1382.4], [699.84, 1382.4]])]
    plan = dict(partitions=[dict(name="c_X", type="cq", origin_um=[1000.0, 2000.0], orient="MX")],
                partition_types={"cq": dict(outline_um=[W, H], contents=cores)})
    taps, k = [], 0
    for y in ROWS:
        for x in (MID if y == ROWS[3] else COLS):
            taps.append(dict(port=f"t_c_X__clk_t{k}", part="c_X", tap=f"clk_t{k}", xy=[1000 + x, 2000 + y])); k += 1
    for j, (x, y) in enumerate([(535.2, 1880.7), (700.3, 1880.7), (535.2, 567.5), (700.3, 567.5)]):
        taps.append(dict(port=f"t_c_X__clk_c{j}", part="c_X", tap=f"clk_c{j}", xy=[1000 + x, 2000 + y]))
    (tmp / "plan.json").write_text(json.dumps(plan))
    (tmp / "tree.json").write_text(json.dumps(dict(taps=taps)))
    QP.build(str(tmp / "plan.json"), str(tmp / "tree.json"), "c_X", str(tmp / "o"))
    return json.loads((tmp / "o" / "pilot.json").read_text())


def test_cells_in_glue_and_drivers_on_straps(tmp_path):
    J = fixture(tmp_path)
    g, cells = J["geom"], J["cells"]
    wid = {"BUFx24_ASAP7_75t_R": 1.62, "BUFx4f_ASAP7_75t_R": 0.432}
    for n, c in cells.items():
        for x in (c["x"], c["x"] + wid[c["master"]]):
            assert not QP.in_core(x, c["y"], g["cores"]), n
    assert len(g["drivers"]) == 32 and len(g["mesh_loads"]) == 28
    for d in g["drivers"]:
        c = cells[d]
        assert any(c["x"] <= vx <= c["x"] + 1.62 for vx in g["vx"]), d      # driver under its M9 strap


def test_tree_equal_legs_by_construction(tmp_path):
    J = fixture(tmp_path)
    cells, nets = J["cells"], J["nets"]
    cen = lambda n: (cells[n]["x"] + 0.81, cells[n]["y"])
    legs = {}
    for n, v in nets.items():
        if v["kind"] != "tree" or v["drv"] == "port:root" or v["drv"].startswith(("E", "Q")):
            continue
        d = cen(v["drv"])
        for l in v["loads"]:
            p = cen(l)
            legs.setdefault(v["drv"][0], []).append(abs(p[0] - d[0]) + abs(p[1] - d[1]))
    for lvl, L in legs.items():
        assert max(L) - min(L) < 12.0, (lvl, min(L), max(L))       # equal per level (site snapping + legalization only)
        assert max(L) <= 450.0, (lvl, max(L))                      # repeater rule


def test_mesh_def_one_special_net(tmp_path):
    fixture(tmp_path)
    d = (tmp_path / "o" / "pilot.def").read_text()
    sn = d[d.index("SPECIALNETS"):d.index("END SPECIALNETS")]
    assert sn.count("- ck_mesh") == 1 and sn.count("VIA89") == 28
    assert d.count("( M") > 0 and "USE CLOCK" in sn
