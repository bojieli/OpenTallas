"""CLOCK-KV-R21 (RULING CLOCK-KV-R20 (a)): clock.hold_demand source "die_sta" (per-port-bit demand from the shared die
gate, provenance gate JSON sha + tool sha, type-hardened), gen_phys per-bit SDC tightening (receiver inputs, sender
outputs for macro receivers), sdc_lint per-bit rule; default (no die_sta demand) output unchanged."""
import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys  # noqa: E402
import hold_demand_die_sta as HD  # noqa: E402
import schema  # noqa: E402
import sdc_lint  # noqa: E402

PAIR = json.loads((HERE / "examples" / "s81_pair" / "s81_pair_plan.json").read_text())
G, T = "a" * 64, "b" * 64


def _write(tmp_path, inputs, outputs, gate=G, tool=T):
    rec = dict(schema=HD.SCHEMA, provenance=dict(gate_json_sha256=gate, tool_sha256=tool), inputs=inputs,
               outputs=outputs, unplaced={})
    body = json.dumps(rec)
    f = tmp_path / "hold_demand_die_sta.json"
    f.write_text(body)
    return f, hashlib.sha256(body.encode()).hexdigest()


def _plan(tmp_path, inputs=None, outputs=None, **over):
    gen_phys._DIE_STA_CACHE.clear()
    f, h = _write(tmp_path, inputs or {}, outputs or {})
    raw = copy.deepcopy(PAIR)
    hd = dict(source="die_sta", file=str(f), sha256=h, gate_json_sha256=G, tool_sha256=T)
    hd.update(over)
    raw.setdefault("clock", {})["hold_demand"] = hd
    return schema.Plan(raw)


def test_default_unchanged(monkeypatch):
    monkeypatch.delenv("OT_IO_HOLD", raising=False)
    P = schema.Plan(copy.deepcopy(PAIR))
    assert gen_phys.die_sta_hold_demand(P, "fb") is None
    s = gen_phys.sdc(P, "fb", gen_phys.type_pins(P, "fb"))
    assert "HOLD-DEMAND die_sta" not in s


def test_schema_accepts_die_sta(tmp_path):
    P = _plan(tmp_path, {"fb": {"x_i": {"3": [2, 60.0]}}})
    schema.validate(P.raw)


def test_receiver_per_bit_tightening_and_lint(tmp_path, monkeypatch):
    monkeypatch.delenv("OT_IO_HOLD", raising=False)
    P = _plan(tmp_path, {"fb": {"x_i": {"3": [2, 60.0], "4": [1, 30.0], "5": [0, 0.0]}}},
              {"fa": {"x_o": {"7": [1, 20.0]}}})
    s = gen_phys.sdc(P, "fb", gen_phys.type_pins(P, "fb"))
    base = gen_phys.hold_in_min_ps(P)
    assert f"set_input_delay -min {gen_phys.t_lib(base - 60.0):.4f} -clock vclk [get_ports {{x_i[3]}}]" in s
    assert f"set_input_delay -min {gen_phys.t_lib(base - 30.0):.4f} -clock vclk [get_ports {{x_i[4]}}]" in s
    assert "x_i[5]" not in s                                     # k 0: no line
    # per-bit lines come after the bus-level -min, lint accepts tightening
    assert s.index("HOLD-DEMAND die_sta") > s.index("set_input_delay -min")
    ctx = sdc_lint.kit_context(P, "fb")
    assert sdc_lint.lint(s, **ctx) == []
    sa = gen_phys.sdc(P, "fa", gen_phys.type_pins(P, "fa"))      # sender side: output -min tightened after all_outputs
    ob = gen_phys.hold_out_min_sdc_ps(P)
    line = f"set_output_delay -min {gen_phys.t_lib(ob - 20.0):.4f} -clock vclk [get_ports {{x_o[7]}}]"
    assert line in sa and sa.index(line) > sa.index("[all_outputs]")
    assert sdc_lint.lint(sa, **sdc_lint.kit_context(P, "fa")) == []


def test_lint_rejects_relaxing_bit(tmp_path, monkeypatch):
    monkeypatch.delenv("OT_IO_HOLD", raising=False)
    P = _plan(tmp_path, {"fb": {"x_i": {"3": [2, 60.0]}}})
    s = gen_phys.sdc(P, "fb", gen_phys.type_pins(P, "fb"))
    bad = s + "set_input_delay -min 500.0000 -clock vclk [get_ports {x_i[9]}]\n"
    if gen_phys.t_lib(1.0) != 1.0:
        bad = s + f"set_input_delay -min {gen_phys.t_lib(500.0):.4f} -clock vclk [get_ports {{x_i[9]}}]\n"
    err = sdc_lint.lint(bad, **sdc_lint.kit_context(P, "fb"))
    assert any("per-bit" in e for e in err)


def test_provenance_checked(tmp_path):
    P = _plan(tmp_path, {"fb": {}}, sha256="0" * 64)
    with pytest.raises(ValueError, match="sha256 differs"):
        gen_phys.die_sta_hold_demand(P, "fb")
    P = _plan(tmp_path, {"fb": {}}, tool_sha256="c" * 64)
    with pytest.raises(ValueError, match="tool sha256 differ"):
        gen_phys.die_sta_hold_demand(P, "fb")
    P = _plan(tmp_path, {"fb": {}}, gate_json_sha256=None)
    with pytest.raises(ValueError, match="needs 'gate_json_sha256'"):
        gen_phys.die_sta_hold_demand(P, "fb")


def test_plan_source_still_required_for_plan_demand(tmp_path):
    P = _plan(tmp_path, {"fb": {}})
    with pytest.raises(ValueError, match="must be 'plan'"):
        gen_phys.hold_demand_ps(P, "pfa", "pfb")


def test_harden_worst_instance_and_sender_side():
    rows = [dict(k=1, demand_ps=30.0, dst_type="R", dst_bus="a_i", dst_part="r1", src_type="S", src_bus="a_o",
                 src_part="s1", bit=0),
            dict(k=2, demand_ps=70.0, dst_type="R", dst_bus="a_i", dst_part="r2", src_type="S", src_bus="a_o",
                 src_part="s2", bit=0),
            dict(k=3, demand_ps=100.0, dst_type="PHY", dst_bus="p_i", dst_part="p1", src_type="S", src_bus="b_o",
                 src_part="s1", bit=5),
            dict(k=1, demand_ps=40.0, dst_type="PHY", dst_bus="ft_i", dst_part="p2", src_type="PHY", src_bus="ft_o",
                 src_part="p1", bit=0),
            dict(k=0, demand_ps=0.0, dst_type="R", dst_bus="a_i", dst_part="r1", src_type="S", src_bus="a_o",
                 src_part="s1", bit=1)]
    dem, ninst = HD.harden(rows, {"PHY"})
    assert dem["inputs"] == {"R": {"a_i": {"0": [2, 70.0]}}}
    assert dem["outputs"] == {"S": {"b_o": {"5": [3, 100.0]}}}
    assert dem["unplaced"] == {"PHY": {"ft_o": {"0": [1, 40.0]}}}
    assert ninst["inputs"] == {"R": 2} and ninst["outputs"] == {"S": 1}
