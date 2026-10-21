"""ROOT-0615 10-18: dcd8111e5 (CHILD-FLOP basis) is a tightening with requires=child_flop_basis: kept for wires-only
parents and for kits whose macros carry no insertion reference; refused (re-gate) when a macro has one."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "closure_loop"))
import source_binding as SB  # noqa: E402
import helper_overlay as HO  # noqa: E402

C = "dcd8111e54a033d01ffd6e3d58ec91b6f070bb27"


def kit(tmp, macros, lib_text=None, ij=False):
    kd = tmp / "physical" / "ref_tile" / "k"
    kd.mkdir(parents=True)
    (kd / "kit.env").write_text("TOP=x\n" + (f"MACROS=({' '.join(macros)})\n" if macros else ""))
    for m in macros:
        p = tmp / m
        p.parent.mkdir(parents=True, exist_ok=True)
        for c in ("tt", "ff"):
            (p.parent / f"{p.name}_{c}.lib").write_text(lib_text or "cell(x) { pin(CLK) { clock : true; } }")
        if ij:
            (p.parent / "insertion.json").write_text("{}")
    return dict(kit="k")


def test_registered_as_tightening_with_requirement():
    e = HO.RULE_COMMITS[C]
    assert e["kind"] == "tightening" and e["requires"] == "child_flop_basis"


def test_wires_only_parent_kept(tmp_path):
    clock = dict(tt_pin_spread_basis="child_pair", ff_pin_spread_basis="child_pair")
    assert SB.relaxed_rule_requirement(["child_flop_basis"], clock, dict(kit="nokit"), root=tmp_path)[0]


def test_plain_macros_kept_referenced_refused(tmp_path):
    assert SB.relaxed_rule_requirement(["child_flop_basis"], {}, kit(tmp_path / "a", []), root=tmp_path / "a")[0]
    g = kit(tmp_path / "b", ["m/sram/sram"])
    assert SB.relaxed_rule_requirement(["child_flop_basis"], {}, g, root=tmp_path / "b")[0]
    g = kit(tmp_path / "c", ["m/rom/rom"], lib_text="timing_type : max_clock_tree_path ;")
    assert not SB.relaxed_rule_requirement(["child_flop_basis"], {}, g, root=tmp_path / "c")[0]
    g = kit(tmp_path / "d", ["v/etm/etm"], ij=True)
    assert not SB.relaxed_rule_requirement(["child_flop_basis"], {}, g, root=tmp_path / "d")[0]
