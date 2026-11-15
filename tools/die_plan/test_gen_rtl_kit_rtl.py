"""KV hg/hgi 11-15: gen.py rtl --kit-rtl TYPE=FILELIST.  A bind-mode plan (KV) has no contents[].bind / bus.leaf, so the plan
wrapper's leaf-binding check fails on every type with buses (kv3_hg_v1 o_ectl_Q_N_eN ...).  A kit-RTL type takes the bound RTL,
and the plan buses are checked against the bound module header (name, direction, width + epoch bit)."""
import copy
import json
import sys
import tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_rtl  # noqa: E402
import schema  # noqa: E402

PAIR = json.loads((HERE / "examples" / "s81_pair" / "s81_pair_plan.json").read_text())
TN = "fb"


def _bound(raw, d, mutate=None):
    P = schema.Plan(raw)
    ep = gen_rtl.bus_epochs(P)
    t = P.types[TN]
    ports = []
    for b in t["buses"]:
        w = b["width"] + (1 if ep.get((TN, b["name"]), b.get("kind", "data") in ("data", "ctl")) else 0)
        ports.append(f"    {'input' if b['dir'] == 'in' else 'output'} wire [{w - 1}:0] {b['name']}")
    if mutate:
        ports = mutate(ports)
    f = Path(d) / "bound.sv"
    f.write_text(f"module {t['module']} (\n    input wire clk,\n" + ",\n".join(ports) + "\n);\nendmodule\n")
    return f


def test_bound_interface_matches_plan_without_leaf_binding():
    raw = copy.deepcopy(PAIR)
    for c in raw["partition_types"][TN]["contents"]:
        c["bind"] = {}                              # bind-mode plan: no leaf bindings
    for b in raw["partition_types"][TN]["buses"]:
        b.pop("leaf", None)
    with tempfile.TemporaryDirectory() as d:
        with pytest.raises(gen_rtl.GenError, match="not bound to any leaf port"):
            gen_rtl.write_rtl(raw, Path(d) / "a", types=[TN], emit_die_top=False)
        f = _bound(raw, d)
        files = gen_rtl.write_rtl(raw, Path(d) / "b", types=[TN], emit_die_top=False, kit_rtl={TN: [f]})
        assert not any(Path(x).name == raw["partition_types"][TN]["module"] + ".sv" for x in files)


@pytest.mark.parametrize("mut,msg", [
    (lambda p: p[1:], "no such port"),
    (lambda p: [p[0].replace("output", "input") if "output" in p[0] else p[0].replace("input", "output")] + p[1:], "kit"),
    (lambda p: [p[0].replace("[", "[1+")] + p[1:], "kit"),
])
def test_bound_interface_mismatch_is_refused(mut, msg):
    raw = copy.deepcopy(PAIR)
    with tempfile.TemporaryDirectory() as d:
        f = _bound(raw, d, mut)
        with pytest.raises(gen_rtl.GenError, match=msg):
            gen_rtl.write_rtl(raw, Path(d) / "c", types=[TN], emit_die_top=False, kit_rtl={TN: [f]})
