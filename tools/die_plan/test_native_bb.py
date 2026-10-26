from pathlib import Path
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent))
import native_bb


def test_patch_refuses_changed_frontend(tmp_path):
    target = tmp_path / "preamble.tcl"
    target.write_text("unknown upstream frontend\n")
    with pytest.raises(ValueError, match="unrecognized"):
        native_bb.patch(target)
    assert target.read_text() == "unknown upstream frontend\n"


def test_patch_is_idempotent(tmp_path):
    target = tmp_path / "preamble.tcl"
    target.write_text(native_bb.OLD + "\n")
    native_bb.patch(target)
    first = target.read_bytes()
    native_bb.patch(target)
    assert target.read_bytes() == first


def test_only_generated_rom_stub_accepts_content_metadata():
    import lec
    ports = [("clk", "input", 1, 0), ("q", "output", 1, 0)]
    rom = lec.stub_verilog({"ot_rom_64x32_m2": ports})
    assert 'parameter VIAMAP = "", INSTANCE = "";' in rom
    assert "INSTNCE" not in rom
    assert "parameter" not in lec.stub_verilog({"other_macro": ports})
