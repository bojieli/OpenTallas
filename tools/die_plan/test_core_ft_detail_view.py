"""DIE-QC-97 11-11 ISLAND-VIEW (b): a physical FT core accepts the abstract_detail form of its captured LEF (same
signed ODB, refined M6 OBS for DRT-0073 pin access) only through its detail receipt; everything else stays refused.

The real case is the DIE-HBM-97 vmr detail (receipt base 6dd379d21ce4 = captured FT LEF, out 7c36c9cdee22, M6, 81
rects): the fixture keeps the real receipt and its 81 M6 rects and rebuilds the exact detail LEF bytes from the
captured LEF (the test checks the rebuilt sha256 equals the receipt's out_sha256)."""
import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/die_plan"))
import core_ft_physical as CF  # noqa: E402

M = "qfd_dv_s8x_vmr"
FT = ROOT / "physical/die_plan/qwen_compute/ft_physical_1106/vmr"
FIX = ROOT / "tools/die_plan/testdata/qc_vmr_detail_m6"
BLANKET = "    LAYER M6 ;\n     RECT  0 0 246.24 211.811 ;\n  END\n"
OK = "ok; signed_view_ok via detail receipt"


def _pv():
    spec = importlib.util.spec_from_file_location("_pv_dv", ROOT / "tools/autopilot/prov_view.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def entry():
    decl = json.loads((FT / "ft_ports.json").read_text())
    r = json.loads((FT / "proof.json").read_text())
    return {"inst": "u_suvm_u_vm8q_u_va", "module": M, "outline_um": r["outline_um"],
            "pins_file": str(FT / "plan_pins.json"),
            "physical_ft": {"proof": "physical/die_plan/qwen_compute/ft_physical_1106/vmr/proof.json",
                            "proof_sha256": CF.sha(FT / "proof.json"),
                            "unconsumed_outputs": sorted(p["name"] for p in decl["ports"] if p["direction"] == "OUTPUT")},
            "native_port_adapter": {"merge": {}, "cycles": 0,
                                    "tie": {p["name"]: "1'b0" for p in decl["ports"] if p["direction"] == "INPUT"}}}


def detail_text():
    a = (FT / f"{M}.lef").read_text()
    assert a.count(BLANKET) == 1
    return a.replace(BLANKET, "    LAYER M6 ;\n" + (FIX / "m6_obs_rects.txt").read_text() + "  END\n")


def view(tmp_path, text=None, **receipt_edit):
    """cdir with the captured libs, the detail LEF as the selected file, and its receipt (out sha follows the text)"""
    d = tmp_path / "cand"
    d.mkdir()
    for s in ("_tt.lib", "_ff.lib", ".lef"):
        shutil.copyfile(FT / f"{M}{s}", d / f"{M}{s}")
    sel = d / "detail_view.lef"
    sel.write_text(text if text is not None else detail_text())
    rec = json.loads((FIX / "detail_receipt.json").read_text())
    rec["out_sha256"] = CF.sha(sel)
    rec.update(receipt_edit)
    return d, sel, rec


def check(d, sel, rec):
    PV = _pv()
    e = entry()
    return PV.check_routed(str(d), M, e, PV.plan_pins(e, str(FT)), None, str(ROOT), str(sel), rec)


def test_real_receipt_and_detail_lef_ok(tmp_path):
    d, sel, rec = view(tmp_path)
    real = json.loads((FIX / "detail_receipt.json").read_text())
    assert CF.sha(sel) == real["out_sha256"] and real["base_sha256"] == CF.sha(FT / f"{M}.lef")
    assert check(d, sel, real) == (True, OK)
    c = CF.load(entry(), M, sel, d / f"{M}_tt.lib", d / f"{M}_ff.lib", root=ROOT, plan_dir=FT, detail_receipt=real)
    assert c["signed_view_ok"] == "via detail receipt" and c["detail_view"]["rects"] == {"M6": 81}


def test_exact_captured_lef_still_plain_ok(tmp_path):
    d, _, rec = view(tmp_path)
    assert check(d, d / f"{M}.lef", None) == (True, "ok")


def test_missing_receipt_refused(tmp_path):
    d, sel, _ = view(tmp_path)
    ok, why = check(d, sel, None)
    assert not ok and "differs from captured" in why


@pytest.mark.parametrize("edit,match", [
    (dict(base_sha256="0" * 64), "receipt base is not the captured"),
    (dict(out_sha256="0" * 64), "receipt output is not the selected"),
    (dict(check_ok=False), "lacks its pin/geometry check"),
    (dict(detail_pins_equal_base=False), "lacks its pin/geometry check"),
    (dict(pin_clear_um=0.1), "pin-clear"),
    (dict(layers_detailed=[]), "no detailed layers"),
    (dict(layers_detailed=["M5"]), "unlisted layer M6"),
])
def test_receipt_mutants_refused(tmp_path, edit, match):
    d, sel, rec = view(tmp_path, **edit)
    ok, why = check(d, sel, rec)
    assert not ok and match in why, why


@pytest.mark.parametrize("mutate,match", [
    (lambda t: t.replace("RECT  127.872 105.648 127.896 106.032 ;", "RECT  127.872 105.600 127.896 106.032 ;", 1),
     "pins differ"),
    (lambda t: t.replace("END UNITS", "END UNITS\n# edited", 1), "change outside OBS"),
    (lambda t: t.replace("    LAYER M5 ;\n     RECT  0 0 246.24 211.811 ;\n    LAYER M6 ;",
                         "    LAYER M5 ;\n     RECT  0 0 246.24 200 ;\n    LAYER M6 ;", 1), "unlisted layer M5"),
    (lambda t: t.replace("    LAYER M6 ;\n", "    LAYER M6 ;\n     RECT  0 0 250 211.811 ;\n", 1), "outside the captured"),
    (lambda t: t.replace("    LAYER M6 ;\n", "    LAYER M6 ;\n     SPACING 0.1 ;\n", 1), "non-RECT"),
    (lambda t: t.replace("    LAYER M6 ;\n", "    LAYER M7 ;\n", 1), "layer order"),
])
def test_lef_mutants_refused(tmp_path, mutate, match):
    t = mutate(detail_text())
    assert t != detail_text()
    d, sel, rec = view(tmp_path, text=t)
    ok, why = check(d, sel, rec)
    assert not ok and match in why, why


def test_gen_contracts_take_the_receipt_beside_the_kit_lef(tmp_path):
    d, sel, rec = view(tmp_path)
    kit = tmp_path / "views" / M
    kit.mkdir(parents=True)
    for s in ("_tt.lib", "_ff.lib"):
        shutil.copyfile(d / f"{M}{s}", kit / f"{M}{s}")
    shutil.copyfile(sel, kit / f"{M}.lef")
    e = entry()
    staged = f"module p(input clk);\n  {M} u_{e['inst']} (\n    .clk(clk),\n    .ft_ck_i(1'b0),\n    .ft_rst_i(1'b0)\n  );\nendmodule\n"
    macros = [(None, M, kit / f"{M}.lef", kit / f"{M}_tt.lib")]
    with pytest.raises(ValueError, match="differs from captured"):
        CF.contracts([e], macros, staged, ROOT, FT)
    (kit / f"{M}.detail_receipt.json").write_text(json.dumps(rec))
    out = CF.contracts([e], macros, staged, ROOT, FT)
    assert out[M]["signed_view_ok"] == "via detail receipt"
