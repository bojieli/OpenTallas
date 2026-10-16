"""layout images + fill + trial route (OWNER RULE 20:45 PT 2026-10-15)"""
import base64
import json
import sys
import tempfile
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import layout_png as LP  # noqa: E402
import pre_route_gate as PG  # noqa: E402
import ref_tile as RT  # noqa: E402

DUMP = {"top": "t", "die": [0, 0, 100, 80], "stats": {"fill": 0.3, "std_area": 1000, "block_area": 1400, "die_area": 8000},
        "clocks": ["clk"], "blocks": [["u0", "SRAM_A", 10, 10, 40, 40], ["u1", "SRAM_A", 52, 10, 82, 40]],
        "pins": [["clk", "M4", 0, 39.9, 0.2, 40.1], ["d[0]", "M5", 20, 0, 20.1, 0.2], ["d[1]", "M5", 21, 0, 21.1, 0.2]],
        "pg": [["VDD", "M5", 0, 5, 100, 5.3]], "density": {"nx": 4, "ny": 4, "grid": [0.1] * 15 + [None]}}


def _png_ok(p):
    b = Path(p).read_bytes()
    return b[:8] == b"\x89PNG\r\n\x1a\n" and len(b) > 100


def test_render_tile_and_die(tmp_path):
    imgs = LP.render_tile(DUMP, tmp_path / "t", title="t")
    assert _png_ok(imgs["floorplan"]) and _png_ok(imgs["density"])
    gaps = LP._gaps([b[2:6] for b in DUMP["blocks"]], DUMP["die"])
    assert (40, 10, 52, 40) in gaps                      # 12 um channel between the macros is flagged
    die = {"die": [0, 0, 1000, 800], "blocks": [["a", 0, 0, 400, 400], ["b", 500, 0, 900, 400]],
           "buses": [["a", "b", 512, 3]]}
    d = LP.render_die(die, tmp_path / "d", "die")
    assert _png_ok(d["floorplan"]) and _png_ok(d["buses"])


def test_gate_layout_fill_and_trial(tmp_path):
    b = base64.b64encode(zlib.compress(json.dumps(DUMP).encode())).decode()
    out = (f"GATE_LAYOUT_B64 floorplan {b}\nGATE_LAYOUT_B64 placed {b}\nGATE_GRT_RC=0\n"
           "GATE_GRT_LAYER M2  100  50  50.00%  0 /  0 /  0\nGATE_GRT_LAYER Total  200  60  30.00%  0 /  0 /  0\nGATE_DONE\n")
    g = PG.Gate()
    PG.gate_layout(g, tmp_path, {"name": "t", "macros": [1, 2, 3, 4]}, out)
    sev = {i["check"]: i["severity"] for i in g.items}
    assert sev == {"layout_images": "INFO", "fill": "FAIL", "trial_route": "INFO"}
    g = PG.Gate()
    PG.gate_layout(g, tmp_path, {"name": "t", "macros": [1, 2, 3, 4], "fill_reason": {"pin_bound": "edges full"}},
                   out.replace("0 /  0 /  0\nGATE_DONE", "1 /  2 /  3\nGATE_DONE"))
    sev = {i["check"]: i["severity"] for i in g.items}
    assert sev["fill"] == "WARN" and sev["trial_route"] == "FAIL"
    g = PG.Gate()
    PG.gate_layout(g, tmp_path, {"name": "leaf", "macros": []}, out)
    assert {i["check"] for i in g.items} == {"layout_images"}       # a leaf tile: images only


def test_gen_fill_check():
    bl = [{"w": 20, "h": 20}] * 4
    assert RT.fill_check({"kind": "tile", "macros": [1] * 4}, 100, 100, bl, 100)[0] == "FAIL"       # 17 %
    assert RT.fill_check({"kind": "tile", "macros": [1] * 4, "fill_reason": {"pin_bound": "x"}}, 100, 100, bl, 100)[0] == "WARN"
    assert RT.fill_check({"kind": "tile", "macros": [1]}, 100, 100, bl[:1], 100) is None            # a leaf tile
    assert RT.fill_check({"kind": "cluster", "macros": [1] * 4}, 100, 100, bl, 2500)[0] == "WARN"   # 41 %
    assert RT.fill_check({"kind": "cluster", "macros": [1] * 4}, 100, 100, bl, 4000) is None        # 56 %


def test_die_render_adapters(tmp_path):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import die_layout_render as DL
    blocks = [["a", 0, 0, 100, 100], ["b", 1100, 0, 1200, 100], ["c", 0, 300, 100, 400]]
    bus = DL._buses(blocks, [("a", "b", 64, None), ("b", "a", 64, None), ("a", "c", 8, 1), ("a", "x", 9, None)], 500)
    assert sorted(bus) == [["a", "b", 128, 1], ["a", "c", 8, 1]]   # merged per pair; 1100 um -> 1 stage; unknown dropped
    assert DL.grt_table("Total   10  5  3.72%   0 /  0 /  2")[0]["overflow"] == 2
    p = tmp_path / "plan.json"
    p.write_text(json.dumps({"die_outline_um": [3000, 2000], "hard_fixed_boxes": [["hub", 100, 100, 500, 500]],
                             "hcp_homes": [{"name": "h", "at_um": [1000, 100], "outline": {"w": 200, "h": 200}}],
                             "columns": [{"x_um": 2000, "y0_um": 20, "y1_um": 1980, "roots": 7}]}))
    assert DL.main(["--s81", str(p), "--out", str(tmp_path / "o")]) == 0
    assert _png_ok(tmp_path / "o" / "die_floorplan.png")
