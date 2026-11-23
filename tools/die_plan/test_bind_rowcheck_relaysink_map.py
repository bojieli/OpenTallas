"""RELAYSINK-MAP-1123 (KV-D29 K3): RELAYSINK resolves relay_depth rows through the asbuilt map rel names, as bind.rel_of does."""
import json
import bind_rowcheck as RC


def yjs():
    leaf = lambda m: dict(type=m, connections={"d": [1], "q": [2]})
    return {"modules": {
        "top": {"cells": {"head_EN_7_u_x": leaf("rlys"), "pvw_0_u_T0Q0_3_r0": leaf("rlys")}},
        "rlys": {"attributes": {"blackbox": 1}}}}


def plan(tn, rows):
    return {"partition_types": {tn: {"relay_depth": rows}}}


def test_map_rel_name_passes(tmp_path):
    (tmp_path / "map.json").write_text(json.dumps({"parts": {"head_EN_7_u_x": ["hgi_EN_2", "hst3_g"]}}))
    ab = {"top": "top", "map_file": "map.json"}
    rows = [dict(inst="hst3_g", port="d", side="sink", D=2)]
    assert RC.check_relaysink(plan("kv3_hgi_v3", rows), ab, yjs(), str(tmp_path / "asbuilt_vN.json")) == []
    ab2 = {"top": "top", "map": {"parts": {"pvw_0_u_T0Q0_3_r0": ["pv_EN_0", "pv__u_T0Q0_3_r0"]}}}
    assert RC.check_relaysink(plan("kv3_pv", [dict(inst="pv__u_T0Q0_3_r0", port="q", side="src", D=1)]), ab2, yjs()) == []


def test_unmapped_or_bad_port_still_fails(tmp_path):
    (tmp_path / "map.json").write_text(json.dumps({"parts": {"head_EN_7_u_x": ["hgi_EN_2", "hst3_g"]}}))
    ab = {"top": "top", "map_file": "map.json"}
    ap = str(tmp_path / "asbuilt_vN.json")
    out = RC.check_relaysink(plan("kv3_hgi_v3", [dict(inst="hst9_g", port="d", side="sink", D=2)]), ab, yjs(), ap)
    assert out and out[0].startswith("FAIL RELAYSINK") and "no leaf" in out[0]
    out = RC.check_relaysink(plan("kv3_hgi_v3", [dict(inst="hst3_g", port="ti_a", side="sink", D=2)]), ab, yjs(), ap)
    assert out and out[0].startswith("FAIL RELAYSINK") and "has no port" in out[0]
    # no map at all: old behaviour (raw as-built path)
    assert RC.check_relaysink(plan("kv3_hgi_v3", [dict(inst="hst3_g", port="d", side="sink", D=2)]), {"top": "top"}, yjs())[0].startswith("FAIL")
