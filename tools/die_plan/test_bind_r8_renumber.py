"""align_r8 source identity under Yosys renumbering (FLOW-9 10-30, QC-KITS-X $procdff$60311-13 -> 60305-07)."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind  # noqa: E402


def canon(x):   # the align_r8 canonical form of located Yosys names
    return re.sub(r"\$(\w+)\$[\w.]+:\d+\$\d+", r"$\1$#", x)


P = "dvs_E0.u_core.u_sub.u_suvm"


def matcher(cells):
    return bind.r8_source_matcher({c: i for i, c in enumerate(cells)}, canon)


def test_consistent_renumbering_matches_and_is_recorded():
    same, renum = matcher([f"{P}.$procdff$60305", f"{P}.$procdff$60307"])
    for _ in range(3):      # every bit of a 256-bit source asks again
        assert same(f"{P}.$procdff$60307.Q", f"{P}.$procdff$60313.Q")
    assert same(f"{P}.$procdff$60305.Q", f"{P}.$procdff$60311.Q")
    assert renum == {f"{P}.$procdff$60313": f"{P}.$procdff$60307", f"{P}.$procdff$60311": f"{P}.$procdff$60305"}


def test_exact_and_located_names_unchanged():
    same, renum = matcher([f"{P}.u_x"])
    assert same(f"{P}.u_x.q", f"{P}.u_x.q")
    assert same(f"{P}.$or$a.sv:12$901.Y", f"{P}.$or$a.sv:12$77.Y")
    assert not same(f"{P}.u_x.q", f"{P}.u_y.q") and renum == {}


def test_existing_table_cell_is_a_different_flop():
    same, _ = matcher([f"{P}.$procdff$60307", f"{P}.$procdff$60313"])
    assert not same(f"{P}.$procdff$60307.Q", f"{P}.$procdff$60313.Q")


def test_other_parent_type_or_pin_refused():
    same, _ = matcher([f"{P}.$procdff$7"])
    assert not same(f"{P}.$procdff$7.Q", f"dvs_E1.u_core.u_sub.u_suvm.$procdff$9.Q")
    assert not same(f"{P}.$procdff$7.Q", f"{P}.$dff$9.Q")
    assert not same(f"{P}.$procdff$7.Q", f"{P}.$procdff$9.D")
    assert not same(f"{P}.u_named.Q", f"{P}.$procdff$9.Q")


def test_renumbering_must_be_one_to_one():
    same, _ = matcher([f"{P}.$procdff$1", f"{P}.$procdff$2"])
    assert same(f"{P}.$procdff$1.Q", f"{P}.$procdff$11.Q")
    assert not same(f"{P}.$procdff$1.Q", f"{P}.$procdff$12.Q")    # two old flops onto one new flop
    assert not same(f"{P}.$procdff$2.Q", f"{P}.$procdff$11.Q")    # one old flop onto two new flops
