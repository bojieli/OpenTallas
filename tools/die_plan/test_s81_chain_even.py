"""S81-RCK-4 11-07: chain_even type key (equal hops on register chains after GPL) + serdes rate matcher / relay source forms."""
from pathlib import Path

import gen_phys as G
import gen_rtl as R

HERE = Path(__file__).parent


def test_cfg_keeps_regex_and_groups():
    c = G.chain_even_cfg({"chains": [[r"u_a\\.q", r"u_b|u_c\\.pv\\$"]],
                          "groups": [["am", "f", ["s0", "s1"], "c", "z"]]})
    assert r"set ::ot_chain_res {{{u_a\\.q} {u_b|u_c\\.pv\\$}}}" in c
    assert "set ::ot_chain_groups {{{am} {f} {{s0} {s1}} {c} {z}}}" in c


def test_no_groups_no_group_var():
    assert "ot_chain_groups" not in G.chain_even_cfg({"chains": [["a", "b"]]})


def test_tool_shipped_and_reads_cfg_vars():
    t = (HERE / "chain_even.tcl").read_text()
    assert "$::ot_chain_res" in t and "$::ot_chain_groups" in t and "::env(OT_CHAIN" not in t


def test_relay_full_form_is_opt_in():
    c = R.LOCKUP_CELLS
    assert "`ifdef OT_DP_RRELAY_FULL" in c and "always @(negedge clk) q <= state;" in c


def test_rate_match_forms_are_opt_in():
    s = (HERE.parents[1] / "rtl/dsrom_sys/s81_link/ot_pdie_serdes.sv").read_text()
    assert "`ifdef OT_S81_RM_STAGED" in s and "`ifdef OT_S81_SERDES_RST_COPIES" in s
