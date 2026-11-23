"""ASTK-MERGE-1122: RELAYSINK accepts relay_depth rows on native pins of a dissolved hard core."""
import bind_rowcheck as RC


def yjs():
    leaf = lambda m: dict(type=m, connections={"rst_n": [1], "ck": [2], "q": [3]})
    return {"modules": {
        "top": {"cells": {"u_p": dict(type="part", connections={})}},
        "part": {"cells": {"astk_WN__g_phys_fault_u_fault": leaf("qkd_astk_fault_join"),
                           "astk_WN__u_strip_u_strip_u_ctl": leaf("qkd_astk_ctl")}},
        "qkd_astk_fault_join": {"attributes": {"blackbox": 1}}, "qkd_astk_ctl": {"attributes": {"blackbox": 1}}}}


def plan(rows):
    return {"partition_types": {"kv3_hub_Wo": {"relay_depth": rows}}}


def test_native_core_pins_pass():
    rows = [dict(inst="astk_WN", port=p, side="sink", D=9) for p in ("g_phys_fault_u_fault__rst_n", "u_strip_u_strip_u_ctl__rst_n")]
    assert RC.check_relaysink(plan(rows), {"top": "top"}, yjs()) == []


def test_missing_native_pin_still_fails():
    for port in ("u_nope__rst_n", "g_phys_fault_u_fault__nope"):
        out = RC.check_relaysink(plan([dict(inst="astk_WN", port=port, side="sink", D=9)]), {"top": "top"}, yjs())
        assert out and out[0].startswith("FAIL RELAYSINK")
