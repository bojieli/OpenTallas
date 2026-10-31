"""HEAD-SERDES-2 10-31: an INTERNAL_CORE kit (freeze.json endpoint_contract, METHODOLOGY 9.10 R2) is judged at sign-off by
the same typed endpoint census as its kit preflight (internal_core_guard), not by the partition face-register rule."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import signoff

# input a drives logic before its register (legal inside a partition-timed internal core, a face-guard 'unregistered')
NET_INTERNAL = r"""
module top(clk, rst_n, a, o);
  input clk; input rst_n; input [1:0] a; output [1:0] o;
  wire _0_; wire _1_; wire [1:0] q; wire x;
  AND2x2_ASAP7_75t_R _4_ (.A(a[0]), .B(a[1]), .Y(x));
  DFFHQNx1_ASAP7_75t_R \q[0]$_DFF_P_  (.CLK(clk), .D(x), .QN(q[0]));
  DFFHQNx1_ASAP7_75t_R \q[1]$_DFF_P_  (.CLK(clk), .D(a[1]), .QN(q[1]));
  INVx3_ASAP7_75t_R _2_ (.A(q[0]), .Y(o[0]));
  INVx3_ASAP7_75t_R _3_ (.A(q[1]), .Y(o[1]));
endmodule
"""
CONTRACT = dict(kind="INTERNAL_CORE", partition_rule="R2_INTERNAL_TIMED_IN_PARTITION", parent_partition="p",
                instance="u_x", source="rtl/x.sv")


def kit(tmp_path, contract=CONTRACT):
    (tmp_path / "synth.v").write_text(NET_INTERNAL)
    fz = dict(design="top", clocks=["clk"], resets=["rst_n"], macros=[], face_shell=None,
              source_profile=dict(endpoint_contract=contract) if contract else {})
    (tmp_path / "freeze.json").write_text(json.dumps(fz))
    return dict(kit=str(tmp_path), synth=str(tmp_path / "synth.v"))


def test_partition_rule_without_contract_fails(tmp_path):
    r = signoff.run_face_guard(kit(tmp_path, contract=None))
    assert r["verdict"] == "FAIL" and "unregistered" in r["fail_counts"], r


def test_internal_core_contract_uses_typed_census(tmp_path):
    r = signoff.run_face_guard(kit(tmp_path))
    assert r["mode"].startswith("INTERNAL_CORE") and r["contract"]["kind"] == "INTERNAL_CORE", r
    assert r["verdict"] == "PASS" and r["checked"] and r["ok"] == r["checked"], r
    assert r["guard"].endswith("internal_core_guard.py") and len(r["guard_sha256"]) == 64


def test_internal_core_census_still_fails_closed(tmp_path):
    disc = kit(tmp_path)
    bad = dict(CONTRACT, partition_rule="NONE")      # an undeclared partition timing contract is rejected
    fz = json.loads((tmp_path / "freeze.json").read_text())
    fz["source_profile"]["endpoint_contract"] = bad
    (tmp_path / "freeze.json").write_text(json.dumps(fz))
    r = signoff.run_face_guard(disc)
    assert r["verdict"] == "FAIL" and r["fail_counts"] == {"contract": 1}, r
    # a constant-driven output is still rejected by the census
    fz["source_profile"]["endpoint_contract"] = CONTRACT
    (tmp_path / "freeze.json").write_text(json.dumps(fz))
    Path(disc["synth"]).write_text(NET_INTERNAL.replace("INVx3_ASAP7_75t_R _3_ (.A(q[1]), .Y(o[1]));", "assign o[1] = 1'b0;"))
    assert signoff.run_face_guard(disc)["verdict"] == "FAIL"
