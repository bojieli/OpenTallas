"""HBM-BIND-3 11-05: opt-in asbuilt.sub_core_leaf binds plan sub-cores nested in one as-built leaf."""
import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind
import parent_id_straps
import reset_tree as RT
from test_bind_wavefront import emitter, plan


def sub(name, x, **kw):
    return dict(inst=f"u_a__{name}", module=f"sub_{name}", origin_um=[x, 50], outline_um=[50, 100],
                physical_inst=f"u_a.u_fcore.u_core.u_{name}", physical_master=f"sub_{name}",
                pins=[dict(name="rst_n", layer="M4", xy=[0, 50])], **kw)


def vehicle(table):
    raw = plan()
    raw["partition_types"]["src"]["hard_cores"] = [sub("c", 50), sub("p", 120)]
    b = emitter(raw)
    b.sub_core_leaf = table
    part = next(p for p in b.parts if b.parts[p]["type"] == "src")
    b.F.cells = [SimpleNamespace(path="x.u_a", ports={"rst_n": [1]}, module="parent", params={})]
    b.G.dirs = {0: {"rst_n": "input"}}
    b.G.kind = ["leaf"]
    b.members[part] = [0]
    b.sinks = {(0, "rst_n", 0): ("rst", "low")}
    b.rel_of = lambda ci: "u_a"
    return b, part


def test_subs_drive_one_leaf_port_from_first_tap():
    b, part = vehicle({"u_a": "u_a"})
    text, _ = b.emit_type("src", part)
    targets = RT.for_type(b.wavefront_plan(), "src")["core_resets"]
    assert len(targets) == 2
    assert f".rst_n(rst_n_t{targets[0]['tap']})" in text
    assert len(re.findall(r"\.rst_n\(", text)) == 1


def test_absent_table_keeps_the_gap():
    b, part = vehicle({})
    with pytest.raises(bind.BindError, match="expected one bound leaf, found 0"):
        b.emit_type("src", part)


def test_table_leaf_must_exist():
    b, part = vehicle({"u_a": "u_other"})
    with pytest.raises(bind.BindError, match="sub_core_leaf u_other: expected one bound leaf, found 0"):
        b.emit_type("src", part)


def test_different_release_depth_is_a_gap(monkeypatch):
    b, part = vehicle({"u_a": "u_a"})
    real = RT.for_type

    def skewed(P, tn):
        t = real(P, tn)
        if tn == "src":
            second = t["core_resets"][1]["tap"]
            for r in t["relays"]:
                if r["q"] == f"rst_n_t{second}":
                    r["depth"] += 1
        return t
    monkeypatch.setattr(RT, "for_type", skewed)
    with pytest.raises(bind.BindError, match="differ in release depth"):
        b.emit_type("src", part)


def test_parent_id_declaration_moves_to_the_leaf():
    plan_ = {"asbuilt": {"sub_core_leaf": {"u_a": "u_a"}}, "partition_types": {"t": {"hard_cores": [
        sub("c", 50, parent_id_straps={"map_lane_j": {"width": 4, "value": 3}})]}}}
    b = bind.Binder.__new__(bind.Binder)
    b.sub_core_leaf = plan_["asbuilt"]["sub_core_leaf"]
    h = plan_["partition_types"]["t"]["hard_cores"][0]
    assert b.sub_core_leaf_of(h) == "u_a"
    h["parent_id_leaf"] = b.sub_core_leaf_of(h)
    assert "u_a" in parent_id_straps.type_parent_id_straps(plan_["partition_types"]["t"])
