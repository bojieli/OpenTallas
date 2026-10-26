"""Conservative source naming controls: no source/shape ambiguity is erased."""
import sys
from pathlib import Path
from types import SimpleNamespace as NS
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind


def mk(specs):
    cells = [NS(module="$mux", ytype="$mux", yparams=params, src=src,
                ports={"A": list(range(width)), "Y": list(range(width))}, path=name)
             for name, src, width, params in specs]
    b = NS(F=NS(cells=cells), G=NS(kind=["glue"] * len(cells),
           dirs=[{"A": "input", "Y": "output"}] * len(cells)),
           members={"P": list(range(len(cells)))}, local={}, warns=[])
    b.rel_of = lambda ci: b.local.get(ci, cells[ci].path)
    bind.Binder._glue_source_names(b)
    return b


def test_same_source_and_shape_stable_across_auto_numbers():
    a = mk([("u_lf.$mux$1", "same.sv:3.1-3.10", 8, {"A_SIGNED": 0})])
    b = mk([("u_lf.$mux$999", "same.sv:3.1-3.10", 8, {"A_SIGNED": 0})])
    assert a.local[0] == b.local[0]


def test_width_signedness_and_source_remain_distinct():
    cases = [("s.sv:1", 8, {"SIGNED": 0}), ("s.sv:1", 9, {"SIGNED": 0}),
             ("s.sv:1", 8, {"SIGNED": 1}), ("s.sv:2", 8, {"SIGNED": 0})]
    names = [mk([("u.$a$9", src, width, params)]).local[0] for src, width, params in cases]
    assert len(set(names)) == 4


def test_ambiguous_siblings_missing_source_and_named_cells_keep_original_names():
    b = mk([("u.$a$1", "s:1", 8, {}), ("u.$a$2", "s:1", 8, {}),
            ("u.$a$3", None, 8, {}), ("u.named", "s:4", 8, {})])
    assert b.local == {} and any("AMBIGUOUS" in x for x in b.warns)
