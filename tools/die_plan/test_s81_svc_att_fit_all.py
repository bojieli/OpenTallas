"""s81_svc_att_fit_all: witness derivation is fail-closed (FAM-S81-SVC-OWN 11-22)."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s81_svc_att_fit_all as A

PM = A.PM


def test_types_map_to_bound_modules():
    assert set(A.TYPES.values()) == {'s81p_' + t + '_bound' for t in A.TYPES}


def test_names_needs_exactly_one_pmem():
    with pytest.raises(AssertionError):
        A.names('module m;\nendmodule\n')
    one = f'    {PM} g_u_rsv_06_u_u_att_pmem (.RD_ADDR(a));\n'
    assert A.names(one)[0] == 'g_u_rsv_06_u_u_att_'
    assert A.names(one.replace('06_u_u_att', '05_u_u_u_att'))[0] == 'g_u_rsv_05_u_u_u_att_'
    with pytest.raises(AssertionError):
        A.names(one + one)


def test_stage_requires_both_instances():
    G = 'g_u_rsv_06_u_u_att_'
    row = A.STAGE + 'u_u_rsv_06_u_u_att_u_eng_g_stage2_u_stage%d ('
    both = '\n'.join(row % i for i in range(2))
    assert A.replace_stage(both, G).count("attn_staging_fit #(.D(32), .NL(4), .SRAM_MACRO(1'b1)") == 2
    with pytest.raises(AssertionError):
        A.replace_stage(row % 0, G)


def test_pmem_witness_fails_closed_without_cone():
    src = f"    {PM} g_u_rsv_06_u_u_att_pmem (.RD_ADDR({{w_u_rsv_06_u_u_att_driver_pr_Q[8:0], w_u_rsv_06_u_u_att_src_aa_Y[8:0]}}), .RD_DATA(w_u_rsv_06_u_u_att_pmem_RD_DATA), .WR_ADDR(w_u_rsv_06_u_u_att_driver_pw_Q[8:0]), .WR_CLK(clk), .WR_DATA(w_u_rsv_06_u_src_bb_Q[511:0]), .WR_EN(w_u_rsv_06_u_u_att_src_cc_Y[511:0]));\n"
    with pytest.raises(AssertionError):
        A.replace_pmem(src)
