"""LEAFPARAM (P-PLAN-AHEAD-OF-RTL, S81 cut-2100 v3/v4 WREG row): a plan row's leaf_params must name parameters the elaborated RTL
master declares; the live c085 plan (no leaf_params) passes, the WREG row on a master without WREG fails with a class tag."""
import bind_rowcheck as RC

WREG_ROW = [{"module": "ot_s81sl_vpw", "params": {"WREG": 1}, "note": "S81-VPW-WREG per instance"}]


def yjs(master_params):
    """elab with ot_s81sl_vpw declaring `master_params` (the c085 as-built declares REP / XR / SLR only)."""
    return {"modules": {
        "top": {"cells": {"u_lf": dict(type="ot_s81sl_vpw", connections={}, parameters={"REP": 8})}},
        "ot_s81sl_vpw": {"attributes": {"hdlname": "ot_s81sl_vpw"}, "cells": {},
                         "parameter_default_values": {k: "0" for k in master_params}}}}


def plan(rows):
    return {"partition_types": {"ot_s81sl_leaf__t1": {"leaf_params": rows} if rows else {}, "other": {}}}


def test_c085_without_leaf_params_passes():
    assert RC.check_leafparams(plan(None), {}, yjs(["REP", "XR", "SLR"])) == []


def test_wreg_row_on_rtl_without_wreg_fails_with_class_tag():
    out = RC.check_leafparams(plan(WREG_ROW), {}, yjs(["REP", "XR", "SLR"]))
    assert len(out) == 1 and out[0].startswith("FAIL LEAFPARAM ot_s81sl_leaf__t1[0] ot_s81sl_vpw.WREG")
    assert "P-PLAN-AHEAD-OF-RTL" in out[0]


def test_wreg_row_passes_once_the_rtl_declares_wreg():
    assert RC.check_leafparams(plan(WREG_ROW), {}, yjs(["REP", "XR", "SLR", "WREG"])) == []


def test_param_regen_declare_counts_as_declared():
    ab = {"param_regen": {"declare": {"ot_s81sl_vpw": {"WREG": 0}}}}
    assert RC.check_leafparams(plan(WREG_ROW), ab, yjs(["REP"])) == []


def test_unknown_master_fails_but_substitute_target_only_warns():
    row = [{"module": "ot_nope", "params": {"A": 1}}]
    assert RC.check_leafparams(plan(row), {}, yjs(["REP"]))[0].startswith("FAIL LEAFPARAM")
    ab = {"substitute_inst": [{"inst": "x", "module": "ot_nope"}]}
    assert RC.check_leafparams(plan(row), ab, yjs(["REP"]))[0].startswith("WARN LEAFPARAM")


def test_cell_instance_parameter_counts_when_module_defaults_are_empty():
    y = yjs([])
    y["modules"]["top"]["cells"]["u_lf"]["parameters"]["WREG"] = 0
    assert RC.check_leafparams(plan(WREG_ROW), {}, y) == []
