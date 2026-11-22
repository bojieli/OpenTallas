"""KEEP-THROUGH (COORD 11-22, FAM-S81-LEPE-4): a (* keep *) register of a dissolved parent (xf_driver g_cp_{0..3} g_dlv_e_*_r_q) is re-emitted
by the binder as a plain glue reg, so yosys opt_merge folded the per-core copies into one.  The keep now survives: flatten marks the glue FF,
_glue writes (* keep *), and gen_phys names the reg in OT_KEEP_WIRES (replica_keep.keep_glue_regs)."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind  # noqa: E402
import bind_elab as E  # noqa: E402
import replica_keep as RK  # noqa: E402

FF = {"CLK_POLARITY": "1", "WIDTH": "00000000000000000000000000000001"}


def _ff(q, attrs=None):
    return {"hide_name": 1, "type": "$dff", "parameters": dict(FF), "attributes": dict(attrs or {}, src="xf_driver.sv:40"),
            "port_directions": {"CLK": "input", "D": "input", "Q": "output"}, "connections": {"CLK": [2], "D": [3], "Q": [q]}}


def yjs():
    return {"modules": {"top": {
        "attributes": {}, "ports": {"clk": {"direction": "input", "bits": [2]}, "d": {"direction": "input", "bits": [3]}},
        "cells": {"$procdff$1": _ff(5), "$procdff$2": _ff(6), "$procdff$3": _ff(7, {"keep": "true"})},
        "netnames": {"g_cp[0].r_q": {"bits": [5], "attributes": {"keep": "00000000000000000000000000000001"}},
                     "plain_q": {"bits": [6], "attributes": {}},
                     "c_q": {"bits": [7], "attributes": {}}}}}}


def test_flatten_marks_glue_ffs_of_keep_registers():
    F = E.flatten(yjs(), "top")
    keep = {c.path: c.keep for c in F.cells}
    assert keep == {"$procdff$1": True, "$procdff$2": False, "$procdff$3": True}


def test_glue_emits_keep_and_gen_names_it(tmp_path, monkeypatch):
    F = E.flatten(yjs(), "top")
    conns = {"CLK": "clk", "D": "d", "Q": "q0"}
    by = {c.path: c for c in F.cells}
    kept = bind._glue(by["$procdff$1"], dict(conns), "u_xf_driver_g_cp_0_g_dlv_e_d_r")
    plain = bind._glue(by["$procdff$2"], dict(conns), "u_plain_r")
    assert "(* keep *) reg [0:0] g_u_xf_driver_g_cp_0_g_dlv_e_d_r_q;" in kept
    assert "(* keep *)" not in plain
    (tmp_path / "t.sv").write_text("module slice_bound(input clk, input d, output q0, output q1);\n" + kept + "\n"
                                   + plain.replace("q0", "q1") + "\nendmodule\n")
    assert RK.keep_glue_regs(tmp_path) == ["slice_bound:g_u_xf_driver_g_cp_0_g_dlv_e_d_r_q"]
    monkeypatch.setenv("OT_BIND_KEEP_THROUGH", "0")
    assert "(* keep *)" not in bind._glue(by["$procdff$1"], dict(conns), "u_xf_driver_g_cp_0_g_dlv_e_d_r")


def test_gen_keep_wires_include_keep_glue_regs(tmp_path, monkeypatch):
    import gen_phys as G
    (tmp_path / "t.sv").write_text("module slice_bound(input clk, input d, output q0);\n"
                                   "    (* keep *) reg [0:0] g_u_xf_g_cp_1_r_q;\n    assign q0 = g_u_xf_g_cp_1_r_q;\n"
                                   "    always @(posedge clk) g_u_xf_g_cp_1_r_q <= d;\nendmodule\n")
    assert "slice_bound:g_u_xf_g_cp_1_r_q" in G.replica_keep_wires(tmp_path)
    monkeypatch.setenv("OT_KEEP_THROUGH", "0")
    assert "slice_bound:g_u_xf_g_cp_1_r_q" not in G.replica_keep_wires(tmp_path)
