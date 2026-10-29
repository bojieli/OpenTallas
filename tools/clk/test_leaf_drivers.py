"""ot-clk leaf-drivers: trunk legs keep no register sinks; drivers legal, polarity kept, clusters split by span."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
pytest.importorskip("shapely")
import leaf_drivers as L  # noqa: E402

LEF = """MACRO INVA
  SIZE 1.188 BY 0.27 ;
END INVA
MACRO INVB
  SIZE 1.62 BY 0.27 ;
END INVB
"""


def ff(name, bit, stage):
    return dict(inst=name, stage=stage, master="DFF", wh_um=[1.08, .27], area_um2=.29, sequential=True,
                connections={"CLK": [bit], "D": [100], "QN": [101 + len(name)]},
                directions={"CLK": "input", "D": "input", "QN": "output"})


def setup(tmp_path, far_um):
    """trunk net 'ckA' carries two provider clock bits (1, 2): bit 1 FFs at x=10 um, bit 2 FFs at x=10+far_um."""
    cells = [ff("f0", 1, "s1"), ff("f1", 1, "s1"), ff("f2", 2, "s2"), ff("f3", 2, "s2")]
    inv = dict(schema="ot_start_provider_cells/1", counts=dict(cells=4, comb=0), stages=2, cells=cells)
    xs = {"f0": 10.0, "f1": 11.08, "f2": 10.0 + far_um, "f3": 11.08 + far_um}
    pl = dict(dbu=1000, failed=[], summary=dict(all_cells=4, placed=4, comb=0),
              cells=[dict(inst=n, odb_inst="p/" + n, stage="s", master="DFF", sequential=True,
                          bbox_dbu=[round(x * 1000), 5400, round(x * 1000) + 1080, 5670], xy_dbu=[round(x * 1000), 5400])
                     for n, x in xs.items()])
    mapped = dict(modules=dict(top=dict(ports=dict(c1=dict(direction="input", bits=[1]), c2=dict(direction="input", bits=[2])),
                                        cells={c["inst"]: dict(type="DFF", connections=json.loads(json.dumps(c["connections"])),
                                                               port_directions=c["directions"]) for c in cells},
                                        netnames={})))
    rows = [dict(name=f"R{k}", orient="R0" if k % 2 == 0 else "MX", site="s", origin=[0, 270 * k], spacing=54, sites=4000,
                 bbox=[0, 270 * k, 216000, 270 * k + 270]) for k in range(80)]
    blk = [["x", "M1", 13000, 5400, 20000, 5670]]       # an OBS right of the bit-1 FFs on their row
    g = dict(dbu=1000, rows=rows, actual_lower_OBS=blk, hard_forbidden=[["core", 0, 0, 5000, 21600]], existing_cells=[],
             actual_lower_PG=[])
    files = {}
    for k, v in dict(inventory=inv, mapped=mapped, constraints=g, bit_nets={"1": "ckA", "2": "ckA"}).items():
        files[k] = tmp_path / f"{k}.json"
        files[k].write_text(json.dumps(v))
    pl["inventory_sha256"] = L.sha(files["inventory"])
    files["placements"] = tmp_path / "placements.json"
    files["placements"].write_text(json.dumps(pl))
    files["lef"] = tmp_path / "c.lef"
    files["lef"].write_text(LEF)
    lc = {k: str(v) for k, v in files.items()}
    lc.update(top="top", trunk_cell="INVA", leaf_cell="INVB", merge_um=30, search_um=20, sizing="fixed", odb_prefix="p/")
    return lc, g, pl


def test_trunk_has_no_register_sinks_and_polarity_is_even(tmp_path):
    lc, g, pl0 = setup(tmp_path, far_um=100)
    s = L.run(lc, tmp_path / "out")
    assert s["clusters"] == 2 and s["new_cells"] == 4          # 100 um apart > merge_um -> split
    inv = json.loads((tmp_path / "out" / L.FILES[0]).read_text())
    mod = json.loads((tmp_path / "out" / L.FILES[1]).read_text())["modules"]["top"]
    drv = {c["connections"]["Y"][0]: c for c in inv["cells"] if c.get("role") == "clock_leaf"}
    for c in inv["cells"]:
        if c["sequential"]:
            b = c["connections"]["CLK"][0]
            assert b not in (1, 2)                              # no register on the trunk bits
            leaf = drv[b]
            assert leaf["master"] == "INVB"
            trunk = drv[leaf["connections"]["A"][0]]           # two inverters back to the trunk bit
            assert trunk["master"] == "INVA" and trunk["connections"]["A"][0] in (1, 2)
            assert mod["cells"][c["inst"]]["connections"]["CLK"] == [b]
    assert all(n in mod["cells"] for n in (c["inst"] for c in drv.values()))


def test_placement_is_legal(tmp_path):
    lc, g, pl0 = setup(tmp_path, far_um=100)
    L.run(lc, tmp_path / "out")
    pl = json.loads((tmp_path / "out" / L.FILES[2]).read_text())
    assert pl["inventory_sha256"] == L.sha(tmp_path / "out" / L.FILES[0])
    new = [c for c in pl["cells"] if c["inst"].startswith("ot_leaf_ck")]
    block = [r[2:] for r in g["actual_lower_OBS"]] + [r[1:] for r in g["hard_forbidden"]] + [c["bbox_dbu"] for c in pl0["cells"]]
    for i, c in enumerate(new):
        r = c["bbox_dbu"]
        assert r[1] % 540 == 0 and r[0] % 54 == 0             # R0 row, site grid
        assert not any(L.hit(r, q) for q in block)
        assert not any(L.hit(r, d["bbox_dbu"]) for d in new[i + 1:])
        assert c["odb_inst"] == "p/" + c["inst"]


def test_near_bits_on_one_trunk_merge(tmp_path):
    lc, _, _ = setup(tmp_path, far_um=5)
    assert L.run(lc, tmp_path / "out")["clusters"] == 1


def test_stage_model_sizing_and_fail_closed(tmp_path):
    e = dict(key=dict(cell="INVB"), leg=[0, 0, 0, 12.0], tap=[0.15, 0.0005])
    cell, d = L.stage_model_sizing(e)
    assert cell == "INVB" and abs(0.15 * d + 0.0005 * d * d - 12.0) < 1e-2
    lc, _, _ = setup(tmp_path, far_um=50)
    assert L.run(dict(lc), tmp_path / "o1")["clusters"] == 2                      # fixed: 51 um > merge_um 30
    lc["sizing"] = "stage_model"
    s = L.run(lc, tmp_path / "o2", {"m": e}, "m")
    assert s["trunk_cell"] == s["leaf_cell"] == "INVB" and s["clusters"] == 1    # 51 um < modelled span 65.6 um
    with pytest.raises(ValueError, match="preserve existing"):
        L.run(lc, tmp_path / "o2", {"m": e}, "m")
    with pytest.raises(ValueError, match="tap model"):
        L.run(lc, tmp_path / "o3", {}, "missing")
