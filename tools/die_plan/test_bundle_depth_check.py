"""BUNDLE-DEPTH: unequal relay depth inside one valid / data bundle is a strict-bind error (COORD 11-20)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bundle_depth_check as B  # noqa: E402


def plan(rows):
    return {"partition_types": {"dsdv_slice_c1x_C__t9": {"relay_depth": rows}}}


def row(port, D, inst="u_s_6N_u_lp_u_xr", bits=(0, 0)):
    return dict(inst=inst, port=port, side="sink", bits=list(bits), D=D)


def test_split_bundle_is_an_error():
    errs = B.check(plan([row("eg_v", 1), row("eg_c", 1), row("eg_d", 2, bits=(0, 63))]))
    assert len(errs) == 1 and "eg_*" in errs[0] and "eg_d D2" in errs[0] and "eg_v D1" in errs[0]


def test_aligned_bundle_and_unrelated_ports_pass():
    assert B.check(plan([row("eg_v", 2), row("eg_c", 2), row("eg_d", 2), row("cfg_v", 1, inst="u_cap"),
                         row("fi", 3), dict(inst="u_y_rt_1", port="o", D=1)])) == []


def test_bundles_are_per_inst_and_per_stem():
    assert B.check(plan([row("cfg_v", 2, inst="u_a"), row("cfg_d", 1, inst="u_b"), row("eg_v", 1), row("is_d", 2)])) == []


def test_port_depth_is_max_over_bit_runs():
    errs = B.check(plan([row("cfg_v", 2, inst="u_cap"), row("cfg_d", 1, inst="u_cap", bits=(0, 3)),
                         row("cfg_d", 2, inst="u_cap", bits=(4, 7))]))
    assert errs == []


def test_gate_is_blocking():
    errs, summ = B.gate(plan([row("cfg_d", 1, inst="u_cap"), row("cfg_v", 2, inst="u_cap")]))
    assert summ["gate"] == "BLOCKING" and summ["errors"] == 1 and errs
