"""S81-DIE-R3 11-19 (D8i SEQHOST-REACH-1): extract_bound_endpoints.trace_lob follows binder out-bus station chains."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_bound_endpoints as X  # noqa: E402

SRC = """
    wire [33:0] w_u_seqhost_mu_c_0s;
    wire [0:0] lob_unit_o6__u_seqhost__mu_c_0s_5_0;
    wire [0:0] lob_unit_o6__u_seqhost__mu_c_0s_5_1;
    ot_dp_dly_keep #(.W(1), .D(1)) u_lob_unit_o6__u_seqhost__mu_c_0s_5_0 (.clk(clk), .d(w_u_seqhost_mu_c_0s[5]), .q(lob_unit_o6__u_seqhost__mu_c_0s_5_0));  // st 0
    ot_dp_dly_keep #(.W(1), .D(1)) u_lob_unit_o6__u_seqhost__mu_c_0s_5_1 (.clk(clk), .d(lob_unit_o6__u_seqhost__mu_c_0s_5_0[0]), .q(lob_unit_o6__u_seqhost__mu_c_0s_5_1));  // st 1
    ot_dp_st #(.W(2)) u_bout_unit_o6 (.clk(clk), .rst_n(rst_n), .d({lob_unit_o6__u_seqhost__mu_c_0s_5_1[0], w_u_seqhost_mu_c_0s[4]}), .ea(rst_n), .q(unit_o6[1:0]), .eq(unit_o6[2]));
"""


def emitted():
    return X.bits(SRC, X.instance(SRC, 'u_bout_unit_o6')['ports']['d'])


def test_direct_wire_resolves_with_zero_stations():
    assert X.trace_lob(SRC, emitted()[0]) == (('w_u_seqhost_mu_c_0s', 4), 0)


def test_two_station_chain_resolves_to_leaf_bit():
    assert X.trace_lob(SRC, emitted()[1]) == (('w_u_seqhost_mu_c_0s', 5), 2)


def test_foreign_primitive_fails_closed():
    bad = SRC.replace('ot_dp_dly_keep #(.W(1), .D(1)) u_lob_unit_o6__u_seqhost__mu_c_0s_5_0',
                      'ot_dp_st #(.W(1)) u_lob_unit_o6__u_seqhost__mu_c_0s_5_0')
    with pytest.raises(ValueError):
        X.trace_lob(bad, emitted()[1])
