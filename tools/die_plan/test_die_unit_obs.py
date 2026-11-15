#!/usr/bin/env python3
"""DIE-ROUTE-ABS-1: python3 -m pytest tools/die_plan/test_die_unit_obs.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import die_unit_obs as U  # noqa: E402

TCL = """create_obstruction -region {0.000 1.920 17712.000 2.400} -layer M8
create_obstruction -region {8718.640 10.000 8719.040 20.000} -layer M9
# comment
set x 1
"""


class _L:
    def __init__(self, n): self.n = n
    def getName(self): return self.n


class _B:
    def __init__(self, l, r): self.l, self.r = l, r
    def getTechLayer(self): return _L(self.l)
    def xMin(self): return self.r[0]
    def yMin(self): return self.r[1]
    def xMax(self): return self.r[2]
    def yMax(self): return self.r[3]


class _O:
    def __init__(self, l, r): self.b = _B(l, r)
    def getBBox(self): return self.b


class _Blk:
    def __init__(self, obs): self.obs = obs
    def getObstructions(self): return list(self.obs)


def test_parse_obs_tcl():
    r = U.parse_obs_tcl(TCL, 1000)
    assert r == {("M8", 0, 1920, 17712000, 2400), ("M9", 8718640, 10000, 8719040, 20000)}


def test_drop_only_exact_matches():
    r = U.parse_obs_tcl(TCL, 1000)
    a, b = _O("M8", (0, 1920, 17712000, 2400)), _O("M9", (8718640, 10000, 8719040, 20000))
    macro = _O("M8", (0, 1920, 17712000, 2401))     # same place, different size: a real obstruction, kept
    other = _O("M7", (0, 1920, 17712000, 2400))     # other layer: kept
    blk, gone = _Blk([a, b, macro, other]), []
    st = U.drop_grt_obstructions(blk, r, gone.append)
    assert st == dict(total=4, dropped=2, kept=2) and gone == [a, b]


def test_unit_prep_wires_the_drop():
    txt = (Path(__file__).resolve().parent / "unit_prep.py").read_text()
    assert "DROP_GRT_OBS" in txt and "die_unit_obs.drop_grt_obstructions" in txt
    assert txt.index("DROP_GRT_OBS") < txt.index("odb.write_db(db,os.environ")      # before the unit database is written


def test_unit_prep_env_names_are_strings_not_bare_names():
    """HEAD-100: unit_prep.py shipped os.environ.get(SNAP_TAP_PINS) / print(TAP_PIN_SNAP, ...) / DROP_GRT_OBS / GRT_OBS_DROP as bare
    names -> NameError at the first unit prep with either opt-in set (11-15).  unit_prep needs openroad odb, so check the module AST:
    no Name load of the four identifiers, and the env keys are read as string constants."""
    import ast
    from pathlib import Path
    src = (Path(__file__).parent / "unit_prep.py").read_text()
    tree = ast.parse(src)
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
    for ident in ("SNAP_TAP_PINS", "TAP_PIN_SNAP", "DROP_GRT_OBS", "GRT_OBS_DROP"):
        assert ident not in names, ident + " used as a bare name"
    consts = {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    assert {"SNAP_TAP_PINS", "DROP_GRT_OBS", "TAP_PIN_SNAP", "GRT_OBS_DROP"} <= consts
