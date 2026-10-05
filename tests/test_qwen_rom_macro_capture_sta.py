import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from qwen_rom_macro_capture_sta import parse_slack,netlist


def test_report_parser_requires_actual_ps_path_and_unique_slack():
    assert parse_slack('time 1ps\n 7.895628 slack (MET)')==pytest.approx(7.895628)
    assert parse_slack('time 1ps\n -61.0 slack (VIOLATED)')==-61
    for raw in ['time 1ns\n1 slack (MET)','time 1ps\n','time 1ps\nWarning: bad pin\n1 slack (MET)']:
        with pytest.raises(ValueError):parse_slack(raw)


def test_fixed_fixture_never_claims_enabled_capture_or_engine():
    raw=netlist('ot_rom_4096x266_m8')
    assert 'DFFHQNx1_ASAP7_75t_R capture' in raw
    assert 'ot_qwen_rom_tile' not in raw


def test_RF_repair_pins_use_physical_rows_not_logical_address_width():
    raw=netlist('ot_sram_1r1w_512x128_m4_r2c2')
    assert '.rr_addr(14\'b0)' in raw and '.cr_sel(14\'b0)' in raw
