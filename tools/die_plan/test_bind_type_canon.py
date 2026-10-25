"""asbuilt.type_canon: name-only type splits merge; any structural difference still splits (PATH-S81/SPLITS 10-25)."""
import sys
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace as NS
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind


def part(cells, sinks, p, root):
    """cells: [(path, module, kind, ports{pn: (dir, width)})]; sinks: {(cell idx, port, bit): descriptor}"""
    return dict(cells=cells, sinks=sinks, p=p, root=root)


def binder(*parts):
    b = object.__new__(bind.Binder)
    F_cells, kinds, dirs = [], [], []
    b.members, b.cpart, b.root, b.sinks, b.local = defaultdict(list), {}, {}, {}, {}
    for P in parts:
        off = len(F_cells)
        for path, module, kind, ports in P["cells"]:
            ci = len(F_cells)
            F_cells.append(NS(path=path, module=module, params={"WIDTH": 1} if kind == "glue" else {},
                              ytype=module if kind == "glue" else None,
                              ports={pn: list(range(w)) for pn, (_d, w) in ports.items()}))
            kinds.append(kind)
            dirs.append({pn: d for pn, (d, _w) in ports.items()})
            b.members[P["p"]].append(ci)
            b.cpart[ci] = P["p"]
        b.root[P["p"]] = P["root"]
        def shift(d, off=off):
            if d[0] == "int":
                return ("int", d[1] + off) + tuple(d[2:])
            if d[0] in ("or", "and"):
                return (d[0], tuple(shift(u) for u in d[1]))
            return d
        for (i, pn, bit), d in P["sinks"].items():
            b.sinks[(i + off, pn, bit)] = shift(d)
    b.F = NS(cells=F_cells)
    b.G = NS(kind=kinds, dirs=dirs)
    b.out_bus, b.in_bus, b.ft_bus = defaultdict(list), defaultdict(list), defaultdict(list)
    b.clk_dom = defaultdict(set)
    b.ab = {"type_canon": True}
    b.warns = []
    return b


LEAF = {"D": ("input", 1), "Q": ("output", 1)}
NOT = {"A": ("input", 1), "Y": ("output", 1)}
AND = {"A": ("input", 1), "B": ("input", 1), "Y": ("output", 1)}


def leaf_part(p, lf, n_not, n_and, and_b=("top", "pin_a", 0), d_from=2, extra_buf=None):
    """a leaf u_lfK.u_x whose D = AND(NOT(Q), pin) through two auto-named glue cells (replace_const_cells numbers
    differ between instances); a slice-level $buf glue (moved by glue_follows_sinks) feeds the pin path."""
    cells = [(f"u_s.u_lp.{lf}.u_x", "m_leaf", "leaf", LEAF),
             (f"u_s.u_lp.{lf}.u_vp.$auto$opt_expr.cc:768:replace_const_cells${n_not}", "$not", "glue", NOT),
             (f"u_s.u_lp.{lf}.u_vp.$auto$opt_expr.cc:768:replace_const_cells${n_and}", "$and", "glue", AND),
             (extra_buf or "u_s.u_lp.$28", "$buf", "glue", NOT)]
    sinks = {(0, "D", 0): ("int", d_from, "Y", 0, 0), (1, "A", 0): ("int", 0, "Q", 0, 0),
             (2, "A", 0): ("int", 1, "Y", 0, 0), (2, "B", 0): ("int", 3, "Y", 0, 0), (3, "A", 0): and_b}
    return part(cells, sinks, p, "u_s.u_lp")


def merge(b, ps):
    sigs = {p: b.type_signature(p) for p in ps}
    b._canon_merge("t", ps, sigs)
    return sigs


def test_auto_names_and_leaf_index_merge():
    b = binder(leaf_part("A", "u_lf4", 109243, 109245), leaf_part("B", "u_lf3", 107983, 107985, extra_buf="u_s.u_lp.$25"))
    assert b.type_signature("A")[0] != b.type_signature("B")[0]          # raw: names differ
    sigs = merge(b, ["A", "B"])
    assert sigs["A"][0] == sigs["B"][0]
    assert b.type_signature("B")[0] == b.type_signature("A")[0]
    # B's cells now carry A's relative names (emission + bind_names use them)
    assert sorted(b.rel_of(ci) for ci in b.members["B"]) == sorted(b.rel_of(ci) for ci in b.members["A"])
    assert b.type_canon_merged == [dict(type="t", inst="B", ref="A", renamed=4)]


def test_structural_mutants_still_split():
    mutants = [dict(and_b=("top", "pin_a", 1)),          # glue input from another die pin bit
               dict(d_from=1),                            # leaf D from the NOT instead of the AND
               dict(n_not=109245, n_and=109243)]          # names swapped vs roles: still the same structure -> merges
    for k, mut in enumerate(mutants):
        kw = dict(n_not=107983, n_and=107985)
        kw.update(mut)
        b = binder(leaf_part("A", "u_lf4", 109243, 109245), leaf_part("B", "u_lf3", **kw))
        before = {ci: b.rel_of(ci) for ci in b.members["B"]}
        sigs = merge(b, ["A", "B"])
        if k < 2:
            assert sigs["A"][0] != sigs["B"][0], mut
            assert {ci: b.rel_of(ci) for ci in b.members["B"]} == before    # renaming undone / never applied
            assert not getattr(b, "type_canon_merged", [])
        else:
            assert sigs["A"][0] == sigs["B"][0]


def test_symmetric_glue_tie_broken_then_confirmed():
    """two auto $not cells with identical fan-in and fan-out (an OR of both) cannot be told apart by refinement;
    they are individualised by the order of their original numbers and the merge is confirmed by the signature.
    The same pair with one input moved to another pin must still split."""
    def p(name, a, b2, pin2=0):
        cells = [("u_s.u_lp.u_lf4.u_x", "m_leaf", "leaf", {"D": ("input", 2), "Q": ("output", 1)}),
                 (f"u_s.u_lp.u_lf4.$procmux${a}", "$not", "glue", NOT),
                 (f"u_s.u_lp.u_lf4.$procmux${b2}", "$not", "glue", NOT)]
        sinks = {(0, "D", 0): ("or", (("int", 1, "Y", 0, 0), ("int", 2, "Y", 0, 0))), (0, "D", 1): ("top", "pin_a", 0),
                 (1, "A", 0): ("int", 0, "Q", 0, 0), (2, "A", 0): ("top", "pin_b", 0) if pin2 else ("int", 0, "Q", 0, 0)}
        return part(cells, sinks, name, "u_s.u_lp")
    b = binder(p("A", 46183, 46186), p("B", 22108, 22111))
    names = b.canon_names("A")
    assert names[1] != names[2] and "|$wl_" in names[1]
    sigs = merge(b, ["A", "B"])
    assert sigs["A"][0] == sigs["B"][0]
    b = binder(p("A", 46183, 46186), p("B", 22108, 22111, pin2=1))
    sigs = merge(b, ["A", "B"])
    assert sigs["A"][0] != sigs["B"][0] and not getattr(b, "type_canon_merged", [])
