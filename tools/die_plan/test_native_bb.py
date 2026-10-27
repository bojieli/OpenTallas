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


def test_pdn_macro_patterns_match_exact_odb_names_not_prefixed_std_cells():
    import subprocess
    import gen_phys
    patterns = gen_phys._pdn_inst_patterns(["u.phy", "u.g[0].mem"])
    script = "set ps {" + patterns + "}\n"
    names = [r"u.phy", r"u.phy_123", r"uXphy", r"u.g\[0\].mem", r"u.g0.mem"]
    for name in names:
        script += "set hit 0; foreach p $ps {if {[regexp -- $p {" + name + "}]} {incr hit}}; puts $hit\n"
    r = subprocess.run(["tclsh"], input=script, text=True, capture_output=True, check=True)
    assert r.stdout.split() == ["1", "0", "0", "1", "0"]


def test_phy_macro_pg_landing_uses_actual_pin_layer_and_rejects_ambiguity(tmp_path):
    import gen_phys
    lef = tmp_path / "phy.lef"
    for layer, expected in (("M5", "M5 M6"), ("M6", "M6 M7")):
        lef.write_text("\n".join(f"PIN {p}\n PORT\n LAYER {layer} ;\n END\nEND {p}" for p in ("VDD", "VSS")))
        assert gen_phys._macro_pg_layers(lef) == expected
    lef.write_text(lef.read_text().replace("END VSS", "LAYER M5 ;\nEND VSS"))
    with pytest.raises(ValueError, match="ambiguous"):
        gen_phys._macro_pg_layers(lef)


def test_die_driver_islands_create_real_blockages_and_measure_rows():
    import subprocess
    import gen_phys
    class P:
        types = {"t": {"outline_um": [100, 100], "clock": {"die_islands_um": [[10, 10, 20, 20]]}}}
    mock = r'''
namespace eval ord {}
namespace eval odb {}
proc ord::get_db_block {} {return block}
proc ord::get_db_tech {} {return tech}
proc tech {m} {return 1000}
proc block {m} {return {row0 row1}}
proc row0 {m} {return box0}
proc row1 {m} {return box1}
proc box0 {m} {return [dict get {xMin 0 xMax 100000 yMin 15000 yMax 15270} $m]}
proc box1 {m} {return [dict get {xMin 0 xMax 100000 yMin 25000 yMax 25270} $m]}
proc odb::dbBlockage_create {b x0 y0 x1 y1} {puts "BLOCK $x0 $y0 $x1 $y1"}
'''
    result = subprocess.run(["tclsh"], input=mock + gen_phys.die_islands_tcl(P(), "t"),
                            text=True, capture_output=True, check=True)
    assert "BLOCK 10000 10000 20000 20000" in result.stdout
    assert "blockages=1 rectangle_area_sum_um2=100.0 row_intersections=1" in result.stdout
    P.types["t"]["clock"]["die_islands_um"] = [[90, 10, 110, 20]]
    with pytest.raises(ValueError, match="outside outline"):
        gen_phys.die_islands_tcl(P(), "t")
