"""KV-KITS-2 (COORD ruling KV-KITS-1 ASK5 + the 25 OUTPUT_OPEN on kv3_hg/hgi/pc): the strict port-bind wrapper passes
the declared parent ID strap file, and the binder declares (never ties) the type-uniform wavefront reset/START outs an
instance leaves open, with the reset_tree.wf_open_outs proof."""
import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind  # noqa: E402
import reset_tree as RT  # noqa: E402
import schema  # noqa: E402
from test_bind_wavefront import emitter, plan  # noqa: E402

INST = re.compile(r"^    (\w+)(?: #\(.*?\))? (\w+) \(\n(.*?)\n    \);", re.S | re.M)


def _open_ports_in_top(top, P):
    """{instance: {open rst_o_/start_o_ port}} read from the emitted top + the type's generated out pins."""
    W = RT.wf_plan(P)
    res = {}
    for m in INST.finditer(top):
        name, body = m.group(2), m.group(3)
        part = next(p for p in W["parts"] if bind.sv_id(p) == name)
        tn = W["parts"][part]["type"]
        if tn not in W["types"]:
            continue
        ports = [n for n, _x, _y in RT.out_pins(P, tn) + RT.start_out_pins(P, tn)]
        o = {n for n in ports if not re.search(rf"\.{n}\(", body)}
        if o:
            res[name] = o
    return res


@pytest.mark.parametrize("start", [False, True])
def test_wavefront_open_outs_declared_exactly(tmp_path, start):
    raw = plan()
    if start:
        raw["reset"]["start"] = "broadcast"
    P = schema.Plan(raw)
    b = emitter(raw)
    b.emit(tmp_path)
    top_f = next((tmp_path / "rtl").glob("*_bound_top.sv"))
    top = top_f.read_text()
    want = _open_ports_in_top(top, P)
    pf = Path(str(top_f) + ".pads.json")
    got = {}
    if pf.exists():
        doc = json.loads(pf.read_text())
        for inst, e in doc["instances"].items():
            assert e["reason"] and set(e["wavefront_open"]) == set(e["ports"])
            assert all(v == [[0, 0]] for v in e["ports"].values())
            got[inst] = set(e["ports"])
    assert got == want
    oo = RT.wf_open_outs(P)
    assert {bind.sv_id(p): set(v) for p, v in oo.items()} == want


def test_open_out_declaration_refuses_a_connected_port(tmp_path):
    raw = plan()
    P = schema.Plan(raw)
    b = emitter(raw)
    b.emit(tmp_path)
    top_f = next((tmp_path / "rtl").glob("*_bound_top.sv"))
    top = top_f.read_text()
    W = RT.wf_plan(P)
    child = next(p for p, r in W["parts"].items() if r["parent"] is not None)
    q, port = W["parts"][child]["source"].split(".")
    fake = dict(RT.wf_open_outs(P))
    fake[q] = {port: "mutant"}
    orig = RT.wf_open_outs
    RT.wf_open_outs = lambda _P: fake
    try:
        with pytest.raises(bind.BindError, match="connected in the top"):
            b.write_wavefront_open_pads(P, tmp_path / "x_bound_top.sv", top)
    finally:
        RT.wf_open_outs = orig


def test_portbind_strap_file_from_declared_manifest(tmp_path):
    top = tmp_path / "rtl" / "d_bound_top.sv"
    top.parent.mkdir()
    top.write_text("module d_bound_top ();\n    m_a #(.P(1)) a_0 (\n        .strap_x(2'b01)\n    );\n"
                   "    m_b b_0 (\n        .strap_y(1'b1)\n    );\nendmodule\n")
    assert bind.declared_strap_file(tmp_path, top) is None
    man = dict(schema="opentallas.parent_id_straps.v1", types={"ta": {"strap_x": {}}, "tb": {"strap_y": {}}},
               instances={"a_0": {"strap_x": {"width": 2, "value": 1}}, "b_0": {"strap_y": {"width": 1, "value": 1}}})
    (tmp_path / "bind_parent_id_straps.json").write_text(json.dumps(man))
    sf = bind.declared_strap_file(tmp_path, top)
    assert json.loads(sf.read_text())["straps"] == [["m_a", "strap_x"], ["m_b", "strap_y"]]
    man["instances"]["c_0"] = {"strap_z": {"width": 1, "value": 0}}
    (tmp_path / "bind_parent_id_straps.json").write_text(json.dumps(man))
    with pytest.raises(bind.BindError, match="c_0"):
        bind.declared_strap_file(tmp_path, top)


def test_cmd_portbind_passes_the_strap_file(tmp_path, monkeypatch):
    """the wrapper's die_port_bind command line carries --strap-file when the manifest exists."""
    seen = {}
    import subprocess

    def fake_run(cmd, **k):
        seen["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0, "DIE_PORT_BIND PASS\n", "")
    monkeypatch.setattr(subprocess, "run", fake_run)
    out = tmp_path / "out"
    (out / "rtl").mkdir(parents=True)
    top = out / "rtl" / "d_bound_top.sv"
    top.write_text("module d_bound_top ();\n    m_a a_0 (\n        .strap_x(1'b1)\n    );\nendmodule\n")
    (out / "bind_report.json").write_text(json.dumps(dict(files=[str(top)])))
    (out / "bind_parent_id_straps.json").write_text(json.dumps(dict(instances={"a_0": {"strap_x": {}}})))
    base = tmp_path / "base"
    (base / "rtl").mkdir(parents=True)
    monkeypatch.setattr(bind, "load_plan", lambda p: dict(asbuilt={}))
    monkeypatch.setattr(bind, "plan_base", lambda p, raw: str(base))
    from types import SimpleNamespace
    assert bind.cmd_portbind(SimpleNamespace(plan="x", out=str(out))) == 0
    i = seen["cmd"].index("--strap-file")
    assert json.loads(Path(seen["cmd"][i + 1]).read_text())["straps"] == [["m_a", "strap_x"]]
