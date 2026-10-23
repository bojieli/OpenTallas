"""layout review picture + stats + gate rule (TILE-REVIEW 2026-10-23)"""
import base64
import json
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import layout_review as LR  # noqa: E402
import pre_route_gate as PG  # noqa: E402


def _dump(cells_um2=0.0, pin_reg_um=5.0, placed=True, n_cells=200):
    """100 x 100 um tile, one 20 x 20 um macro (free area 9600 um2), 4 pins on W/E, cells of equal size"""
    side = (cells_um2 / n_cells) ** 0.5 if cells_um2 else 0.0
    cells = []
    for k in range(n_cells if cells_um2 else 0):
        x, y = 30 + (k % 20) * 3.0, 30 + (k // 20) * 3.0
        m = "DFFHQNx1_ASAP7_75t_R" if k % 4 == 0 else ("BUFx2_ASAP7_75t_R" if k % 4 == 1 else "NAND2xp5_ASAP7_75t_R")
        cells.append([f"c{k}", m, "PLACED" if placed else "NONE", x, y, x + side, y + side])
    cells.append(["fill0", "FILLERxp5_ASAP7_75t_R", "PLACED", 0, 0, 50, 50])     # fillers never count
    pins = [["a[0]", "M4", 0, 10, 0.1, 10.1], ["a[1]", "M4", 0, 20, 0.1, 20.1],
            ["b[0]", "M4", 99.9, 10, 100, 10.1], ["clk", "M4", 0, 50, 0.1, 50.1]]
    regs = [["a[0]", "R", 0.05, 10.05, 0.05 + pin_reg_um, 10.05, 0], ["a[1]", "R", 0.05, 20.05, 0.05 + pin_reg_um, 20.05, 1],
            ["b[0]", "M", 99.95, 10.05, 80, 10, 0]]
    return {"top": "t", "die": [0, 0, 100, 100], "blocks": [["u_m", "SRAM", 70, 70, 90, 90]], "pins": pins,
            "std_cells": cells, "pin_regs": regs, "clock_roots": [["ck0", "BUFx24_ASAP7_75t_R", 1, 49, 3, 51, 1]],
            "macro_faces": [["u_m", 80, 80, 89, 80, 50, 50]], "macro_obs": {"SRAM": ["M1", "M2", "M3", "M4"]},
            "stats": {"fill": 0.1}}


def _png_ok(p):
    b = Path(p).read_bytes()
    return b[:8] == b"\x89PNG\r\n\x1a\n" and len(b) > 100


def test_stats_fill_pins_and_regs(tmp_path):
    st = LR.review_stats(_dump(cells_um2=960.0))
    assert st["placed"] and st["macros"] == 1 and abs(st["macro_area_pct"] - 4.0) < 1e-6
    assert abs(st["std_fill_of_free"] - 0.1) < 1e-3                 # 960 / 9600, the filler is ignored
    assert st["ff"] == 50 and st["buf_inv"] == 50 and abs(st["buf_share"] - 0.25) < 1e-9
    assert st["pins_per_face"] == {"W": 3, "E": 1} and st["pins_per_um"] == {"E": 0.01, "W": 0.03}
    assert st["pins_registered"] == 2 and st["pins_to_macro"] == 1
    assert st["pin_to_reg_median_um"] == 5.0 and st["pin_to_reg_p90_um"] == 5.0
    assert 0.5 < st["empty_area"] < 1.0                              # cells sit in one 60 x 30 um corner
    assert st["macros_pins_facing_away"] == ["u_m"]                  # pins east, logic south-west
    assert st["clock_roots"] == 1
    assert any("low fill" in f for f in st["flags"]) and any("face away" in f for f in st["flags"])


def test_judge_fill_fail_and_reason():
    st = LR.review_stats(_dump(cells_um2=960.0))
    sev = [x[0] for x in LR.judge(st, {})]
    assert "FAIL" in sev
    sev = [x[0] for x in LR.judge(st, {"low_fill_reason": "pin-bound: 1,024 pins on a 100 um face"})]
    assert "FAIL" not in sev and "WARN" in sev
    st = LR.review_stats(_dump(cells_um2=3000.0))                   # 31 % of free: passes
    assert [x[0] for x in LR.judge(st, {})] == ["INFO"]


def test_judge_pin_register_distance():
    st = LR.review_stats(_dump(cells_um2=3000.0, pin_reg_um=160.0))
    items = LR.judge(st, {})
    assert items[0][0] == "FAIL" and "p90 160 um" in items[0][2]
    st = LR.review_stats(_dump(cells_um2=3000.0, pin_reg_um=120.0))  # flagged (> 100) but not failed (<= 150)
    assert "FAIL" not in [x[0] for x in LR.judge(st, {})] and any("pin->register" in f for f in st["flags"])


def test_floorplan_only_not_judged(tmp_path):
    d = _dump(cells_um2=960.0, placed=False)
    st, png, items = LR.review(d, tmp_path / "gl", "t", {})
    assert not st["placed"] and [x[0] for x in items] == ["INFO"] and _png_ok(png)
    assert json.loads((tmp_path / "gl" / "review_stats.json").read_text())["placed"] is False


def test_review_writes_png_and_stats(tmp_path):
    st, png, items = LR.review(_dump(cells_um2=960.0), tmp_path / "gl", "tile t", {})
    assert _png_ok(png) and Path(png).name == "review.png"
    js = json.loads((tmp_path / "gl" / "review_stats.json").read_text())
    assert js["schema"] == "opentallas.ref_tile.layout_review.v1" and js["png"] == png


def test_old_dump_without_review_fields(tmp_path):
    d = _dump(cells_um2=3000.0)
    for k in ("pin_regs", "clock_roots", "macro_faces", "macro_obs"):
        d.pop(k)
    st, png, items = LR.review(d, tmp_path / "gl", "t", {})
    assert st["pin_to_reg_p90_um"] is None and [x[0] for x in items] == ["INFO"] and _png_ok(png)


def test_gate_layout_hook_fails_low_fill(tmp_path):
    def b64(d):
        return base64.b64encode(zlib.compress(json.dumps(d).encode())).decode()
    out = (f"GATE_LAYOUT_B64 floorplan {b64(_dump(cells_um2=960.0, placed=False))}\n"
           f"GATE_LAYOUT_B64 placed {b64(_dump(cells_um2=960.0))}\nGATE_DONE\n")
    g = PG.Gate()
    kd = tmp_path / "kit"
    kd.mkdir()
    PG.gate_layout(g, kd, {"name": "kit", "kind": "tile"}, out)
    rv = [i for i in g.items if i["check"] == "layout_review"]
    assert any(i["severity"] == "FAIL" for i in rv) and g.verdict == "FAIL"
    assert (kd / "gate_layout" / "review.png").exists() and (kd / "gate_layout" / "review_stats.json").exists()
    assert g.layout_images["review"].endswith("review.png") and g.layout_review["std_fill_of_free"] < 0.2
    g = PG.Gate()
    PG.gate_layout(g, kd, {"name": "kit", "kind": "tile", "low_fill_reason": "pin-bound perimeter"}, out)
    assert not any(i["severity"] == "FAIL" and i["check"] == "layout_review" for i in g.items)


def test_parent_not_judged_on_std_fill():
    st = LR.review_stats(_dump(cells_um2=960.0))
    assert "FAIL" not in [x[0] for x in LR.judge(st, {}, parent=True)]
    st = LR.review_stats(_dump(cells_um2=960.0, pin_reg_um=200.0))
    assert LR.judge(st, {}, parent=True)[0][0] == "FAIL"           # pin-register rule still applies


def test_geom_review_verdict_excuses_fill_and_pin_regs():
    st = LR.review_stats(_dump(cells_um2=960.0, pin_reg_um=200.0))          # low fill AND far pin registers
    pas = {"verdict": "PASS-CONDITIONAL", "hash": "ab" * 32, "kit": "physical/ref_tile/k@c"}
    items = LR.judge(st, {}, review=pas)
    assert "FAIL" not in [x[0] for x in items] and "GEOM-REVIEW PASS-CONDITIONAL" in items[0][2]
    items = LR.judge(st, {}, review=dict(pas, verdict="FAIL"))               # a FAIL verdict excuses nothing
    assert items[0][0] == "FAIL" and any("no exemption" in x[2] for x in items)


def test_fill_reason_and_band_never_excuse_far_pin_regs():
    st = LR.review_stats(_dump(cells_um2=960.0, pin_reg_um=200.0))
    items = LR.judge(st, {"low_fill_reason": "pin-bound"})
    assert [x[0] for x in items][:2] == ["WARN", "FAIL"] and "p90 200" in items[1][2]
    # BAD parent with a measured lattice/channel band: the band no longer waives the pin-register rule
    items = LR.judge(st, {}, parent=True, band_reason="measured lattice/channel band 100 um2 at density 60%")
    assert items[0][0] == "FAIL" and "p90 200" in items[0][2]
    assert "FAIL" not in [x[0] for x in LR.judge(st, {"pin_reg_reason": "pins land on a hard child edge"}, parent=True)]
    st = LR.review_stats(_dump(cells_um2=960.0))
    assert "FAIL" not in [x[0] for x in LR.judge(st, {}, band_reason="measured band")]   # band excuses fill


def test_gate_layout_hook_honours_geom_review(tmp_path, monkeypatch):
    def b64(d):
        return base64.b64encode(zlib.compress(json.dumps(d).encode())).decode()
    out = (f"GATE_LAYOUT_B64 floorplan {b64(_dump(cells_um2=960.0, placed=False))}\n"
           f"GATE_LAYOUT_B64 placed {b64(_dump(cells_um2=960.0))}\nGATE_DONE\n")
    kd = tmp_path / "kit"
    kd.mkdir()
    seen = []
    monkeypatch.setattr(PG, "geom_review_verdict", lambda k: seen.append(k) or {"verdict": "PASS", "hash": "cd" * 32,
                                                                                "kit": "physical/ref_tile/kit@x"})
    g = PG.Gate()
    PG.gate_layout(g, kd, {"name": "kit", "kind": "tile"}, out)
    assert seen == [kd] and not any(i["severity"] == "FAIL" and i["check"] == "layout_review" for i in g.items)
    assert g.layout_review["geom_review"]["verdict"] == "PASS"
    monkeypatch.setattr(PG, "geom_review_verdict", lambda k: None)
    g = PG.Gate()
    PG.gate_layout(g, kd, {"name": "kit", "kind": "tile"}, out)
    assert any(i["severity"] == "FAIL" and i["check"] == "layout_review" for i in g.items)


def test_geom_review_verdict_lookup_by_content_hash(tmp_path, monkeypatch):
    import importlib
    kd = tmp_path / "physical" / "ref_tile" / "kk"
    kd.mkdir(parents=True)
    (kd / "spec.json").write_text("{}\n")
    (kd / "gate_layout").mkdir()
    (kd / "gate_layout" / "review.png").write_bytes(b"x")                    # excluded from the content hash
    vd = tmp_path / "verdicts"
    vd.mkdir()
    monkeypatch.setenv("GEOM_REVIEW_DIR", str(vd))
    monkeypatch.setenv("GEOM_REVIEW_LANE", str(tmp_path / "lane.md"))
    sys.path.insert(0, str(Path(PG.__file__).resolve().parent.parent / "closure_loop"))
    try:
        GR = importlib.import_module("geom_review_gate")
    except ImportError:
        import pytest
        pytest.skip("geom_review_gate not on this branch yet (merged on main)")
    monkeypatch.setattr(GR, "VERDICT_DIR", vd)
    monkeypatch.setattr(GR, "LANE", tmp_path / "lane.md")
    assert PG.geom_review_verdict(kd) is None
    h = GR.kit_hash_fs(str(kd))
    (vd / "e__kk.json").write_text(json.dumps({"element": "e", "kit": "physical/ref_tile/kk@c", "verdict": "PASS",
                                               "hash": h, "at": "2026-10-23T03:00:00-07:00"}))
    assert PG.geom_review_verdict(kd)["verdict"] == "PASS"
    (kd / "spec.json").write_text('{"changed": 1}\n')                           # content changed -> verdict no longer applies
    assert PG.geom_review_verdict(kd) is None


def test_parent_fill_reason_revoked_by_geom_review_fail(tmp_path, monkeypatch):
    def b64(d):
        return base64.b64encode(zlib.compress(json.dumps(d).encode())).decode()
    fp = _dump(cells_um2=960.0, placed=False)
    fp["stats"] = {"fill": 0.10, "block_area": 400, "std_area": 960, "die_area": 10000}
    out = f"GATE_LAYOUT_B64 floorplan {b64(fp)}\nGATE_LAYOUT_B64 placed {b64(_dump(cells_um2=960.0))}\nGATE_DONE\n"
    kd = tmp_path / "kit"
    kd.mkdir()
    spec = {"name": "kit", "kind": "cluster", "children": [{"view": "v"}], "fill_reason": {"pin_bound": "edges full"}}
    monkeypatch.setattr(PG, "is_parent_kit", lambda s: True)
    monkeypatch.setattr(PG, "geom_review_verdict", lambda k: None)
    g = PG.Gate()
    PG.gate_layout(g, kd, spec, out)
    assert not any(i["severity"] == "FAIL" and i["check"] == "fill" for i in g.items)        # pin-bound text: WARN
    monkeypatch.setattr(PG, "geom_review_verdict", lambda k: {"verdict": "FAIL", "hash": "ef" * 32, "kit": "kit@x"})
    g = PG.Gate()
    PG.gate_layout(g, kd, spec, out)
    assert any(i["severity"] == "FAIL" and i["check"] == "fill" and "revoked" in i["message"] for i in g.items)
