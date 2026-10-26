"""tests for bind.Binder._glue_follow_sinks (asbuilt.glue_follows_sinks, PATH-S81/COLL 10-25): no Yosys needed.

The S81 lep slice top 'assign lrx0 = {rx0[512], rx0[513], rx0[511:0], n0rxv}' is a bit-preserving glue cell that the
map puts with the slice top (C) while all its loads are u_ln0 in LP; with the option it follows its loads."""
import sys
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind  # noqa: E402


def mk(cells, loads, cpart, exact=(), top=None):
    """cells: [(path, kind, ytype, {port: (dir, [nets])})]; loads: net -> [(ci, port, bit)]"""
    F = NS(cells=[NS(path=p, ytype=y, ports={k: v[1] for k, v in ports.items()}) for p, _, y, ports in cells],
           top_ports=top or {})
    G = NS(kind=[k for _, k, _, _ in cells], dirs=[{k: v[0] for k, v in ports.items()} for _, _, _, ports in cells],
           loads=defaultdict(list, loads))
    drv = {n: ci for ci, (_, _, _, ports) in enumerate(cells) for d, nets in ports.values() if d == "output" for n in nets}
    G.source = lambda n: ("pin", drv[n], None, None, 0) if n in drv else ("top", n)
    b = NS(F=F, G=G, cpart=dict(cpart), local={}, warns=[], R=NS(parts=set(exact)))
    return b, bind.Binder._glue_follow_sinks(b)


def test_wire_glue_follows_single_sink_partition():
    cells = [("u_lk.u_phy", "leaf", None, {"rx": ("output", [1, 2])}),
             ("u_s.$4", "glue", "$buf", {"A": ("input", [1, 2]), "Y": ("output", [3, 4])}),
             ("u_s.u_ln0", "leaf", None, {"rx": ("input", [3, 4])})]
    loads = {1: [(1, "A", 0)], 2: [(1, "A", 1)], 3: [(2, "rx", 0)], 4: [(2, "rx", 1)]}
    b, moved = mk(cells, loads, {0: "lk", 1: "C", 2: "LP"})
    assert b.cpart[1] == "LP" and moved == {("C", "LP"): 1}


def test_chain_reaches_fixpoint_and_split_or_unknown_loads_stay():
    cells = [("u_s.$1", "glue", "$pos", {"A": ("input", [1]), "Y": ("output", [2])}),
             ("u_s.$2", "glue", "$not", {"A": ("input", [2]), "Y": ("output", [3])}),
             ("u_s.u_ln0", "leaf", None, {"a": ("input", [3])}),
             ("u_s.$3", "glue", "$buf", {"A": ("input", [1]), "Y": ("output", [4, 5])}),   # split loads
             ("u_s.u_c", "leaf", None, {"a": ("input", [4])}),
             ("u_s.$5", "glue", "$and", {"A": ("input", [1]), "B": ("input", [1]), "Y": ("output", [6])}),  # not 1:1
             ("u_s.$6", "glue", "$buf", {"A": ("input", [1]), "Y": ("output", [7])}),        # load = transport
             ("u_rly", "transport", None, {"i": ("input", [7])})]
    loads = {2: [(1, "A", 0)], 3: [(2, "a", 0)], 4: [(4, "a", 0)], 5: [(2, "a", 0)], 6: [(2, "a", 0)], 7: [(7, "i", 0)]}
    b, moved = mk(cells, loads, {0: "C", 1: "C", 2: "LP", 3: "C", 4: "C", 5: "C", 6: "C"})
    assert b.cpart[0] == "LP" and b.cpart[1] == "LP"          # $2 moves first, then $1 follows it
    assert b.cpart[3] == "C" and b.cpart[5] == "C" and b.cpart[6] == "C"
    assert moved == {("C", "LP"): 2}


def test_exact_map_key_and_die_output_stay():
    cells = [("u_s.$4", "glue", "$buf", {"A": ("input", [1]), "Y": ("output", [2])}),
             ("u_s.u_ln0", "leaf", None, {"a": ("input", [2])}),
             ("u_s.$7", "glue", "$buf", {"A": ("input", [1]), "Y": ("output", [3])})]
    loads = {2: [(1, "a", 0)], 3: [(1, "a", 0)]}
    b, moved = mk(cells, loads, {0: "C", 1: "LP", 2: "C"}, exact={"u_s.$4"}, top={"o": ("output", [3])})
    assert b.cpart == {0: "C", 1: "LP", 2: "C"} and moved == {}


def test_glue_fed_from_own_partition_stays():
    """only a pure pass-through moves: a C-driven bit through C glue into LP keeps the glue in C (no gain, and an
    anonymous glue name in a replicated type would split it)"""
    cells = [("u_s.u_c", "leaf", None, {"q": ("output", [1])}),
             ("u_s.$9", "glue", "$buf", {"A": ("input", [1]), "Y": ("output", [2])}),
             ("u_s.u_lep", "leaf", None, {"a": ("input", [2])})]
    b, moved = mk(cells, {1: [(1, "A", 0)], 2: [(2, "a", 0)]}, {0: "C", 1: "C", 2: "LP"})
    assert b.cpart[1] == "C" and moved == {}
