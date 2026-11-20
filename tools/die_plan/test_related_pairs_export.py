"""DIE-LEVEL-CHECK-1119: sign-off exports the kit related tap pairs (TT session), signoff_ports publishes them append-only,
real_views rekeys them to the plan type and passes --related-pairs."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import real_views as RV  # noqa: E402
import signoff as SO  # noqa: E402
import signoff_ports as SP  # noqa: E402


def test_tt_session_gets_export(tmp_path):
    (tmp_path / "session.tcl").write_text("puts hi\n")
    assert SO.export_related_pairs_tcl(tmp_path)
    s = (tmp_path / "session.tcl").read_text()
    assert "kit_tap_related_pairs.tcl" in s and "/out/related_pairs.json" in s and "catch" in s
    assert (tmp_path / "kit_tap_related_pairs.tcl").is_file()


def test_collect_and_publish_append_only(tmp_path):
    out = tmp_path / "out"
    (out / "tt").mkdir(parents=True)
    (out / "tt" / "related_pairs.json").write_text(json.dumps({"related_pairs": {"blk": [["clk", "clk_t1"]]}}))
    assert SO.collect_related_pairs(out)
    (out / "signoff_ports.json").write_text("{}")
    rec = tmp_path / "rec"
    rec.mkdir()
    (rec / "related_pairs.json").write_text("KEEP")
    assert SP.publish_sidecar(out / "signoff_ports.json", rec)
    assert (rec / "related_pairs.json").read_text() == "KEEP"          # never overwritten
    rec2 = tmp_path / "rec2"
    rec2.mkdir()
    SP.publish_sidecar(out / "signoff_ports.json", rec2)
    assert json.loads((rec2 / "related_pairs.json").read_text())["related_pairs"]["blk"] == [["clk", "clk_t1"]]


def test_real_views_rekeys_to_type(tmp_path):
    r = tmp_path / "r"
    r.mkdir()
    (r / "signoff.json").write_text("{}")
    (r / "related_pairs.json").write_text(json.dumps({"related_pairs": {"blk_eco": [["clk", "clk_t1"], ["clk_t1", "clk_t2"]]}}))
    out = tmp_path / "o"
    out.mkdir()
    assert RV.related_pairs_for(str(r / "signoff.json"), "kv3_pv", out, False) == 2
    d = json.loads((out / "related_pairs" / "kv3_pv.json").read_text())
    assert list(d["related_pairs"]) == ["kv3_pv"]
    assert RV.related_pairs_for(str(tmp_path / "none" / "signoff.json"), "x", out, False) is None
