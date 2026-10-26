"""hc128_export emits plain instance identifiers (COORD ruling 5): deterministic, unique, macros untouched."""
import copy, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import hc128_export as E

leaf = dict(ports={"a": {"direction": "input", "bits": [2]}}, cells={}, netnames={"a": {"bits": [2]}})
mods = {
    "top": dict(ports={}, netnames={"g_lvl_1__g_n_1__u_a": {"bits": [3]}}, cells={
        "g_lvl[1].g_n[0].u_a": {"type": "leaf$top.g_lvl[1].g_n[0].u_a"},
        "g_lvl[1].g_n[1].u_a": {"type": "leaf$top.g_lvl[1].g_n[0].u_a"},   # collides with a net name -> suffix
        "g_lvl.1..g_n.0..u_a": {"type": "leaf$top.g_lvl[1].g_n[0].u_a"},   # same sanitised base: sorts first, takes the base
        "u_c.u_b.g_w[0].u_m": {"type": "sram"},                            # blackbox macro keeps its name
        "u_plain": {"type": "leaf$top.g_lvl[1].g_n[0].u_a"},
        "$and$x.v:1$7": {"type": "$and"}}),
    "leaf$top.g_lvl[1].g_n[0].u_a": leaf,
    "sram": dict(attributes={"blackbox": "1"}, ports={}, cells={}, netnames={}),
}
a, b = copy.deepcopy(mods), copy.deepcopy(mods)
ra = E.plain_instances(a, E.closure_of(a, "top")); rb = E.plain_instances(b, E.closure_of(b, "top"))
assert ra == rb and a == b, "not deterministic"
m = ra["top"]
assert m["g_lvl.1..g_n.0..u_a"] == "g_lvl_1__g_n_0__u_a", m   # sorted original-name order picks the base
assert m["g_lvl[1].g_n[1].u_a"] == "g_lvl_1__g_n_1__u_a_1", m
assert m["g_lvl[1].g_n[0].u_a"] == "g_lvl_1__g_n_0__u_a_1", m
assert "u_c.u_b.g_w[0].u_m" in a["top"]["cells"] and "u_plain" in a["top"]["cells"] and "$and$x.v:1$7" in a["top"]["cells"]
names = list(a["top"]["cells"]) + list(a["top"]["netnames"])
assert len(names) == len(set(names)), "not unique"
assert all(E.PLAIN.match(c) for c, cd in a["top"]["cells"].items() if cd["type"] not in ("sram", "$and"))
assert sorted(cd["type"] for cd in a["top"]["cells"].values()) == sorted(cd["type"] for cd in mods["top"]["cells"].values())
assert E.plain_name("3x[0]") == "i_3x_0_"
print("PASS plain instance identifiers: deterministic, unique vs cells+nets, blackbox/plain/primitive cells untouched")
