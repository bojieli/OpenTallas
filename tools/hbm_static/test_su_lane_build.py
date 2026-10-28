"""su_lane_build: the as-built constants are the numbers the compilers hard-coded before REBAL-9 and the RTL headers."""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import su_lane_build as B  # noqa: E402

ROOT = HERE.parents[1]


def test_as_built_matches_old_constants():
    d = B.depths(4, 3)
    assert {k: d[k] for k in (1, 2, 3, 4, 5, 6, 7)} == {1: 56, 2: 46, 3: 31, 4: 78, 5: 78, 6: 180, 7: 111}
    assert B.lin(4, 3, 1) == 28
    assert {fn: B.side_ii(fn, 4, 3) for fn in (2, 3, 6, 7)} == {2: 10, 3: 1, 6: 19, 7: 8}
    assert B.side_ii(1, 4, 3) == 1 and B.commit_extra(0) == 0


def test_mlat5_deltas():
    d4, d5 = B.depths(4, 3), B.depths(5, 3)
    assert {k: d5[k] - d4[k] for k in d4} == {0: 0, 1: 7, 2: 9, 3: 0, 4: 7, 5: 7, 6: 18, 7: 7}
    assert B.lin(5, 3, 1) - B.lin(4, 3, 1) == 4
    assert {fn: B.side_ii(fn, 5, 3) for fn in (2, 3, 6, 7)} == {2: 19, 3: 1, 6: 37, 7: 15}


def test_rtl_localparams_are_the_formulas():
    t = (ROOT / "rtl/hbm_accel/generic/adapters/static_su/arithmetic/ot_hbm_su_static_lane.sv").read_text()
    for pat in (r"D_EXP = 7 \* MLAT \+ 8 \* ALAT \+ 4", r"D_SIG = D_EXP \+ ALAT \+ D_DIV",
                r"D_RSQ = 1 \+ 9 \* MLAT \+ 3 \* ALAT", r"D_SQRT = 31", r"D_SP = D_EXP \+ 11 \* MLAT \+ 10 \* ALAT \+ 50",
                r"D_EG = 1 \+ 31 \+ 1 \+ D_SIG", r"D_DIV = 19"):
        assert re.search(pat, t), pat
    s = (ROOT / "rtl/hbm_accel/generic/adapters/static_su/arithmetic/ot_hbm_su_static_side.sv").read_text()
    assert re.search(r"localparam integer MLAT=3, ALAT=3;", s)


def test_refuses_non_builds():
    for bad in ((4, 5), (2, 3), (3, 4)):
        try:
            B.depths(*bad)
        except ValueError:
            continue
        raise AssertionError(bad)
