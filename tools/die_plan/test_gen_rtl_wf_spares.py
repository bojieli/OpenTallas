"""DIE-HEAD-4b (36 OUTPUT_OPEN on the generated HEAD top): gen_rtl declares the type-uniform wavefront relay outs
(rst_o_<k> / start_o_<k>) an instance leaves open as spare outputs in <top>.sv.pads.json, with the same writer and
reset_tree.wf_open_outs proof as the as-built binder; a connected port is refused."""
import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_rtl  # noqa: E402
import reset_tree as RT  # noqa: E402
import schema  # noqa: E402

HERE = Path(__file__).resolve().parent


def plan():
    raw = json.loads((HERE / 'examples/tiny_plan.json').read_text())
    raw.setdefault('reset', {})['release'] = 'wavefront'
    return raw


def _empty_wf_ports(top):
    """{instance: {rst_o_/start_o_ ports connected as empty .p()}} read from the generated top."""
    res = {}
    for m in RT._WF_INST.finditer(top):
        o = set(re.findall(r"\.((?:rst|start)_o_\d+)\(\s*\)", m.group(3)))
        if o:
            res[m.group(2)] = o
    return res


@pytest.mark.parametrize("start", [False, True])
def test_gen_rtl_declares_wavefront_open_outs(tmp_path, start):
    raw = plan()
    if start:
        raw["reset"]["start"] = "broadcast"
    files = gen_rtl.write_rtl(raw, tmp_path)
    top = next(f for f in files if f.name.endswith("_top.sv"))
    want = _empty_wf_ports(top.read_text())
    pf = Path(str(top) + ".pads.json")
    assert want, "fixture must leave a wavefront out open"
    got = {}
    if want:
        assert pf.exists() and pf not in files   # files = RTL sources (callers compile them)
        for inst, e in json.loads(pf.read_text())["instances"].items():
            assert e["reason"] and set(e["wavefront_open"]) == set(e["ports"])
            assert all(v == [[0, 0]] for v in e["ports"].values())
            got[inst] = set(e["ports"])
    assert got == want
    oo = RT.wf_open_outs(schema.Plan(raw))
    assert {gen_rtl.sv_id(p): set(v) for p, v in oo.items()} == want
    # rerun into the same dir: the pad file is rewritten, never merged with a stale one
    pf.exists() and pf.write_text(json.dumps({"instances": {"stale_x": {"master": "m", "reason": "r", "ports": {}}}}))
    gen_rtl.write_rtl(raw, tmp_path)
    assert not pf.exists() or "stale_x" not in json.loads(pf.read_text())["instances"]


def test_writer_refuses_a_connected_port(tmp_path):
    raw = plan()
    P = schema.Plan(raw)
    top = next(f for f in gen_rtl.write_rtl(raw, tmp_path) if f.name.endswith("_top.sv")).read_text()
    W = RT.wf_plan(P)
    child = next(p for p, r in W["parts"].items() if r["parent"] is not None)
    q, port = W["parts"][child]["source"].split(".")
    fake = dict(RT.wf_open_outs(P))
    fake[q] = {port: "mutant"}
    orig = RT.wf_open_outs
    RT.wf_open_outs = lambda _P: fake
    try:
        with pytest.raises(ValueError, match="connected in the top"):
            RT.write_wf_open_pads(P, tmp_path / "x_top.sv", top, gen_rtl.sv_id)
    finally:
        RT.wf_open_outs = orig
