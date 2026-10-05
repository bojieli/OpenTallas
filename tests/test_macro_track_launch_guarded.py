"""Refuse incomplete abstracts before starting any physical flow."""
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import run_abi3_physical_aligned_guarded as G


def abstract(name="requested", signal=True):
    pin = "\n PIN x\n USE SIGNAL ;\n PORT\n LAYER M4 ;\n RECT 0.000 0.000 0.024 0.024 ;\n END\n END x\n" if signal else ""
    return f"MACRO {name}\n CLASS BLOCK ;\n SIZE 1.032 BY 1.032 ;\n SYMMETRY X Y ;\n{pin}END {name}\n"


def reject(tmp_path, text, needle):
    (tmp_path / "requested.lef").write_text(text)
    with patch.object(G, "ORIGINAL_GATE", side_effect=AssertionError("must refuse before original gate")):
        _, receipt = G.gate(["--macro-view", "requested=" + str(tmp_path)])
    assert receipt["verdict"] == "REFUSED"
    assert any(needle in reason for reason in receipt["refusals"])


def test_requested_master_absent(tmp_path):
    reject(tmp_path, abstract("other"), "found 0")


def test_duplicate_master_in_file(tmp_path):
    reject(tmp_path, abstract() + abstract(), "found 2")


def test_empty_outline(tmp_path):
    reject(tmp_path, abstract(signal=False), "signal pins required")


def test_truncated_master(tmp_path):
    reject(tmp_path, abstract().replace("END requested", ""), "closing END")


def test_unchecked_layer(tmp_path):
    reject(tmp_path, abstract().replace("M4", "UNQUALIFIED"), "unchecked layer")


def test_outside_geometry(tmp_path):
    reject(tmp_path, abstract().replace("0.024 0.024", "2.000 2.000"), "outside")


def test_signal_without_geometry(tmp_path):
    reject(tmp_path, abstract().replace(" RECT 0.000 0.000 0.024 0.024 ;\n", ""), "no rectangles")


def test_duplicate_requested_view(tmp_path):
    (tmp_path / "requested.lef").write_text(abstract())
    spec = "requested=" + str(tmp_path)
    _, receipt = G.gate(["--macro-view", spec, "--macro-view", spec])
    assert receipt["verdict"] == "REFUSED"
    assert any("duplicate requested master" in r for r in receipt["refusals"])


def test_selected_real_v2_and_assert():
    args, receipt = G.gate(["--macro-view", "ot_rom_4096x274_m8=physical/asap7_memory_macros_v2/ot_rom_4096x274_m8"])
    assert receipt["verdict"] == "PASS"
    assert receipt["required_master_guard"]["masters"][0]["signal_pins_checked"] > 0
    assert args[-2:] == ["--step-tcl", "POST_TAPCELL=physical/common/ot_macro_track_assert_hook.tcl"]


def test_gate_only_refuses_without_launch(tmp_path):
    (tmp_path / "requested.lef").write_text(abstract("other"))
    assert G.main(["--macro-track-gate", "--gate-only", "--macro-view", "requested=" + str(tmp_path)]) == 3


def test_default_off_delegates_original_arguments():
    args = ["--gate-only"]
    with patch.object(G.base, "main", return_value=0) as original:
        assert G.main(args) == 0
        original.assert_called_once_with(args)
