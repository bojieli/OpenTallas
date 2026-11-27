"""HIFANOUT (HEAD-INT-R2 11-26, C-HIFANOUT-SELECT): source-level driver duplication per sink bank, static guards.
The cycle-exactness is proved formally by rtl/test/meso/write_select_bank/eq.sh and rtl/test/head_host_fw_bank/eq.sh (yosys equiv, mutant caught)."""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CA = (REPO / "rtl/common/ot_dp_clk_landing_ca.sv").read_text()
EP = (REPO / "rtl/dsrom_sys/s81_head/ot_s81hd_host_ep_core.sv").read_text()
CL = Path(__file__).with_name("clock_landings.py").read_text()


def test_write_select_bank_default_keeps_the_legacy_scope_and_names():
    assert CA.count("parameter int WRITE_SELECT_BANK = 0") == 2
    assert "if (WRITE_SELECT_LOCAL && (WRITE_SELECT_BANK == 0 || WRITE_SELECT_BANK >= W)) begin : g_local_slot_write" in CA
    assert "end else if (WRITE_SELECT_LOCAL) begin : g_bank_slot_write" in CA and "begin : g_legacy_slot_write" in CA
    assert ".WRITE_SELECT_BANK(WRITE_SELECT_BANK)) u_ring" in CA


def test_write_select_bank_bank_decodes_are_kept_apart_and_mutant_hook_exists():
    assert re.search(r"\(\* keep_hierarchy \*\)\s*module ot_meso_write_slot_select", CA)
    assert "OT_MESO_CA_MUTANT_WSBANK" in CA and "if (b == 0) s_lap[i] <= tc[AW];" in CA


def test_generator_key_is_validated_and_adds_no_cycles():
    assert 'band.get("write_select_bank", 0)' in CL and "write_select_bank_added_cycles=0" in CL
    assert "write_select_bank needs write_select_local" in CL


def test_host_fw_select_is_per_64_bit_bank_only_for_cs_copies():
    assert re.search(r"\(\* keep_hierarchy \*\)\s*module ot_s81hd_host_fw_bank", EP)
    assert "fw_b[(gi/64)<CS_COPIES?(gi/64):CS_COPIES-1]?forward_frame[gi]" in EP
    assert "assign ctl_rx_d=fw?forward_frame:cfg?host1_d:fault_frame;" in EP          # CS_COPIES = 0 (every other host) unchanged
