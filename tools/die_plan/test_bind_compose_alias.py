"""DIE-KV-64 11-03: r8 table names of composed member leaves follow the composite (whole, bit-identical ports only)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind_compose  # noqa: E402
from bind import _compose_rename  # noqa: E402


def _spec():
    t = lambda m, p, b: {"member": m, "port": p, "bit": b}  # noqa: E731
    return {"cores": [{"inst": "nc_pair", "module": "pair", "members": ["a", "b"], "ports": {
        "s0__d": {"dir": "input", "bits": [[t("a", "d", 0)], [t("a", "d", 1)]]},
        "s1__d": {"dir": "input", "bits": [[t("b", "d", 1)], [t("b", "d", 0)]]},          # swapped: no alias
        "s1__clk": {"dir": "input", "bits": [[t("a", "clk", 0), t("b", "clk", 0)]]},
        "s0__q": {"dir": "output", "bits": [[t("a", "q", 0)]]}}}]}


def test_port_alias_whole_identity_only():
    al, cells = bind_compose.port_alias(_spec(), {"a": {"d": 2, "clk": 1, "q": 2}, "b": {"d": 2, "clk": 1}})
    assert al == {("a", "d"): ("nc_pair", "s0__d"), ("a", "clk"): ("nc_pair", "s1__clk"),
                  ("b", "clk"): ("nc_pair", "s1__clk")}          # b.d swapped, a.q partial
    assert cells == {"a": "nc_pair", "b": "nc_pair"}


def test_compose_rename():
    al, cells = {("a", "d"): ("nc", "s0__d"), ("x", "o"): ("nc2", "s1__o")}, {"x": "nc2"}
    m = _compose_rename(dict(id="e1", sink="a", sink_port="d", source="x.o"), al, cells)
    assert (m["sink"], m["sink_port"], m["source"]) == ("nc", "s0__d", "nc2.s1__o")
    m = _compose_rename(dict(id="INNER:p:a.d<-x", sink="a", sink_port="d", source="x"), al, cells)
    assert m["source"] == "nc2"
    keep = dict(id="e2", sink="z", sink_port="d", source="y.o")
    assert _compose_rename(keep, al, cells) == keep
