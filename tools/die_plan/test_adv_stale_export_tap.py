"""pytest: ADV-STALE-EXPORT-TAP (C-FWDCLK-WRONG-TAP): v6ne pattern (exports kept on a renumbered far tap) + clean control."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adv_stale_export_tap as A  # noqa: E402

GRID = {"clk": (0.0, 0.0), "clk_t1": (100.0, 100.0), "clk_t82": (1900.0, 1900.0), "clk_t99": (700.0, 1500.0)}


def pin(name, src, xy):
    return {"kind": "clock", "dir": "out", "name": name, "source_clock_port": src, "source_clock_tap": src, "xy_um": xy}


def test_evidence_case_far_renumbered_tap_is_stale():
    # v6ne: exports at the SW corner still sourced from clk_t82 (NE, 1.8 mm); two sourced from the near tap (clean)
    pins = [pin("fclk_out_ft44_o", "clk_t82", [150.0, 120.0]), pin("fclk_out_ft53_o", "clk_t82", [160.0, 120.0]),
            pin("fclk_out_ft10_o", "clk_t1", [150.0, 120.0]), pin("fclk_out_ft11_o", "clk_t99", [660.0, 1518.0])]
    c = A.classify(pins, GRID)
    assert [x[1] for x in c["stale"]] == ["fclk_out_ft44_o", "fclk_out_ft53_o"] or sorted(x[1] for x in c["stale"]) == ["fclk_out_ft44_o", "fclk_out_ft53_o"]
    assert c["stale"][0][3] == "clk_t1" and c["stale"][0][0] > 1500 and not c["dangling"] and not c["nofix"] and c["n"] == 4


def test_clean_control_has_no_hits():
    pins = [pin("a", "clk_t1", [150.0, 120.0]), pin("b", "clk_t99", [700.0, 1400.0]), pin("c", "clk_t82", [1800.0, 1850.0])]
    c = A.classify(pins, GRID)
    assert not c["stale"] and not c["dangling"] and not c["nofix"]


def test_dangling_and_nofix():
    g = {"clk_t1": (0.0, 0.0), "clk_t2": (2000.0, 0.0)}
    c = A.classify([pin("gone", "clk_t77", [50.0, 0.0]), pin("far", "clk_t1", [1000.0, 0.0])], g)
    assert [x[0] for x in c["dangling"]] == ["gone"] and c["dangling"][0][2] == "clk_t1"
    assert [x[1] for x in c["nofix"]] == ["far"]          # clk_t1 and clk_t2 both 1000 um: already nearest (tie -> name), no repoint


def test_limit_boundary_not_flagged():
    c = A.classify([pin("e", "clk_t1", [300.0, 0.0])], {"clk_t1": (0.0, 0.0), "clk_t2": (299.0, 0.0)})
    assert not c["stale"]


def test_findings_end_to_end(monkeypatch, tmp_path):
    import schema as S
    monkeypatch.setattr(S, "Plan", lambda raw, p: object())
    monkeypatch.setattr(S, "tap_grid", lambda P, tn: [(n, x, y) for n, (x, y) in GRID.items()])
    raw = {"partition_types": {
        "bad": {"clock": {"landing_contract": {"pins": [pin("f0", "clk_t82", [150.0, 120.0]), pin("f1", "clk_t1", [150.0, 120.0])]}}},
        "ok": {"clock": {"landing_contract": {"pins": [pin("f0", "clk_t1", [150.0, 120.0])]}}},
        "noexp": {"clock": {}}},
        "partitions": [{"type": "bad"}, {"type": "bad"}, {"type": "ok"}]}
    out = A.findings(raw, str(tmp_path / "p.json"))
    assert out[0].startswith("WARN ADV-STALE-EXPORT-TAP bad: 1 of 2") and "x2 placed" in out[0]
    assert "1 of 2 export types hit; 1 of 3 forwarded-clock export pins" in out[-1] and "2 of 5 per placed instance" in out[-1]
    assert "C-FWDCLK-WRONG-TAP" in out[-1] and all(x.startswith("WARN ") for x in out)


def test_never_raises():
    assert A.findings(None, "p")[0].startswith("WARN ADV-STALE-EXPORT-TAP")
