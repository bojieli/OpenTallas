"""KV-HOST-REGEN-1 10-27: core_pins_hr.leaf_module finds the bound u_host module (plain obsx or a bound variant)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import core_pins_hr as CH  # noqa: E402

PLAIN = ("module kv3_hub_Wi_part_bound(input wire clk);\n"
         "    qkd_host_root_admission_obsx #(.ENABLE_TOKEN(1), .NL(2)) u_host (\n        .ck_host(clk));\nendmodule\n")
C45 = ("module kv3_hub_Wi_part_bound(input wire clk);\n"
       "    qkd_host_root_admission_obsx_bo1_c45 #(.D2D_BOOT_ORDER(1), .ENABLE_TOKEN(1), .NL(2), .REQUIRE_MISSION_START(1)) u_host (\n"
       "        .ck_host(clk));\nendmodule\n")


def test_plain(tmp_path):
    p = tmp_path / 'p.sv'
    p.write_text(PLAIN)
    assert CH.leaf_module(p)[0] == 'qkd_host_root_admission_obsx'
    assert CH.leaf_params(p) == [('ENABLE_TOKEN', '1'), ('NL', '2')]


def test_bound_variant(tmp_path):
    p = tmp_path / 'c.sv'
    p.write_text(C45)
    assert CH.leaf_module(p)[0] == 'qkd_host_root_admission_obsx_bo1_c45'
    assert dict(CH.leaf_params(p)) == {'D2D_BOOT_ORDER': '1', 'ENABLE_TOKEN': '1', 'NL': '2', 'REQUIRE_MISSION_START': '1'}


def test_absent(tmp_path):
    p = tmp_path / 'n.sv'
    p.write_text('module x; endmodule\n')
    assert CH.leaf_module(p) == (CH.TOP, '') and CH.leaf_params(p) == []
