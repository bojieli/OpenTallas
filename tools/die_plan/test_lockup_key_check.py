"""FABLE-PLAN-QC-N 11-17: a latch_except / latch_except_hb4 module key must match a BOUND lockup module (bind error otherwise), and
asbuilt_sources.json `lib` paths of another copy of the source tree are rebased onto this tree."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bind  # noqa: E402

PLAN = {"clock": {"core_input_lockup": {"modules": {"qfd_tile_nk_a0c": ["tap"], "qfd_tile_nk_rp2_romleaf_rr": ["tap"]}, "all": True, "pipe": 1,
                                         "latch_except": {"qfd_tile_nk_a0c": ["tap[0]"]},
                                         "latch_except_hb4": {"qfd_tile_nk_a0c": {"tap[0]": 3}}}}}


def test_a_key_on_the_plan_hard_core_name_matches_no_bound_module():
    errs = bind.lockup_key_errors(PLAN, {"qfd_tile_nk_rp2_romleaf_rr"})
    assert len(errs) == 1 and errs[0].startswith("LATCH_EXCEPT_MODULE qfd_tile_nk_a0c") and "rp2_romleaf_rr" in errs[0]


def test_a_key_on_the_bound_leaf_module_is_accepted_and_no_key_is_silent():
    p = {"clock": {"core_input_lockup": dict(PLAN["clock"]["core_input_lockup"], latch_except={"qfd_tile_nk_rp2_romleaf_rr": ["tap[0]"]},
                                              latch_except_hb4={"qfd_tile_nk_rp2_romleaf_rr": {"tap[0]": 3}})}}
    assert bind.lockup_key_errors(p, {"qfd_tile_nk_rp2_romleaf_rr"}) == []
    assert bind.lockup_key_errors({"clock": {"core_input_lockup": {"modules": {"m": ["tap"]}}}}, set()) == []
    assert bind.lockup_key_errors({}, set()) == []


def test_the_emitter_records_the_bound_lockup_modules_and_bind_reports_the_errors():
    src = (HERE / "bind.py").read_text()
    assert 'self.__dict__.setdefault("lockup_seen", set()).add(c.module)' in src
    assert "B.errors.extend(lockup_key_errors(B.plan" in src


def test_lib_paths_of_another_copy_are_rebased_onto_this_tree(tmp_path):
    base = tmp_path / "tree"
    (base / "rtl/q").mkdir(parents=True)
    (base / "physical/m").mkdir(parents=True)
    (base / "rtl/q/a.sv").write_text("module a; endmodule\n")
    (base / "physical/m/b.sv").write_text("module b; endmodule\n")
    real = tmp_path / "other.sv"
    real.write_text("x")
    got = bind.rebase_lib_paths(["/gone/src_x/rtl/q/a.sv", "/gone/src_x/physical/m/b.sv", "/gone/src_x/rtl/q/missing.sv", str(real)], base)
    assert got == [str(base / "rtl/q/a.sv"), str(base / "physical/m/b.sv"), "/gone/src_x/rtl/q/missing.sv", str(real)]
