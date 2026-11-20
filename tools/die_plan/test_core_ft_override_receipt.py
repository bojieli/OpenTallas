"""QC-SUST-MACRO-1119: a gen LEF override (lef_overrides/) whose corrected LEF is a physical-FT core view is accepted through
the splice receipt kept beside it.  The real case: qfd_dv_s8x_vmr (su_c u_va/u_vb/u_vc), override c6bb9dd3 on base 6dd379d2
= the captured FT LEF; before, every su_c kit stopped in gen with 'selected lef differs from captured qualified FT view'."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/die_plan"))
import core_ft_physical as CF  # noqa: E402
import lef_override as LO  # noqa: E402

M = "qfd_dv_s8x_vmr"
FT = ROOT / "physical/die_plan/qwen_compute/ft_physical_1106/vmr"


def captured_lef():
    r = json.loads((FT / "proof.json").read_text())
    return FT / r["files"]["lef"]["path"]


def test_override_lef_has_its_splice_receipt_beside():
    lef = LO.DIR / (M + ".lef")
    rec = CF.receipt_beside(lef)
    assert rec is not None and rec["out_sha256"] == CF.sha(lef)
    assert rec["base_sha256"] == LO.rows()[M + ".lef"]["base_sha256"]


def test_override_lef_passes_detail_view_against_captured_ft_lef():
    lef = LO.DIR / (M + ".lef")
    cap = captured_lef()
    assert CF.sha(cap) == LO.rows()[M + ".lef"]["base_sha256"]
    v = CF.detail_view(lef, cap, CF.receipt_beside(lef))
    assert v["signed_view_ok"] == "via detail receipt" and v["layers_detailed"] == ["M6"]


def test_no_receipt_for_a_plain_lef(tmp_path):
    f = tmp_path / "x.lef"; f.write_text("VERSION 5.8 ;\n")
    assert CF.receipt_beside(f) is None
    (tmp_path / "x.splice.json").write_text(json.dumps({"base_sha256": "a"}))
    assert CF.receipt_beside(f) == {"base_sha256": "a"}
    (tmp_path / "x.detail_receipt.json").write_text(json.dumps({"base_sha256": "b"}))
    assert CF.receipt_beside(f) == {"base_sha256": "b"}   # prov_view receipt wins
