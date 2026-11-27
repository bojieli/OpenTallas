"""entry_phase_bench.py (reads the plans, simulates the real ot_dp_rrelay_ph) and the wf_plan release consistency check of rebind_nr_serdes."""
import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent / "die_plan"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def part(name, h, strap):
    return {"name": name, "type": "hd_serdes", "reset_entry_phase": h, "id_straps": {"strap_rst_ph": strap}}


def plan(*parts):
    return {"partitions": list(parts), "partition_types": {}}


@pytest.fixture(autouse=True)
def _clean_modules():
    for n in ("pin_entry_phase", "head_native_release", "schema", "reset_tree", "cores"):
        sys.modules.pop(n, None)
    yield
    for n in ("pin_entry_phase", "head_native_release", "schema", "reset_tree", "cores"):
        sys.modules.pop(n, None)


pytestmark_iv = pytest.mark.skipif(shutil.which("iverilog") is None or shutil.which("vvp") is None, reason="iverilog not installed")


@pytestmark_iv
def test_bench_reads_the_plans_and_passes(tmp_path):
    epb = _load("epb", HERE / "entry_phase_bench.py")
    old = tmp_path / "old.json"
    new = tmp_path / "new.json"
    old.write_text(json.dumps(plan(part("a", 4, 0), part("b", 3, 1), part("c", 2, 0))))
    new.write_text(json.dumps(plan(part("a", 3, 1), part("b", 2, 0), part("c", 2, 0))))
    sys.path.insert(0, str(TOOLS))
    try:
        assert epb.main(old, new, tmp_path / "o", TOOLS) == 0
    finally:
        sys.path.remove(str(TOOLS))
    ev = json.loads((tmp_path / "o" / "entry_phase_evidence.json").read_text())
    assert ev["verdict"] == "PASS" and len(ev["rows"]) == 4 and {c["partition"] for c in ev["cases"]} == {"a", "b"}   # unchanged c is not benched
    assert {(c["partition"], c["version"]): c["sim_cycles"] for c in ev["cases"]} == {("a", "old"): 2, ("a", "new"): 1, ("b", "old"): 1, ("b", "new"): 2}
    assert "ENTRY_PHASE_BENCH PASS" in (tmp_path / "o" / "bench.log").read_text()


@pytestmark_iv
def test_bench_refuses_inconsistent_plan_strap(tmp_path):
    epb = _load("epb2", HERE / "entry_phase_bench.py")
    (tmp_path / "old.json").write_text(json.dumps(plan(part("a", 4, 0))))
    (tmp_path / "new.json").write_text(json.dumps(plan(part("a", 3, 0))))      # strap 0 but h=3 is odd: the plan contradicts itself
    sys.path.insert(0, str(TOOLS))
    try:
        with pytest.raises(AssertionError, match="strap != reset_entry_phase mod 2"):
            epb.main(tmp_path / "old.json", tmp_path / "new.json", tmp_path / "o", TOOLS)
    finally:
        sys.path.remove(str(TOOLS))


def test_bench_has_no_hardcoded_partitions():
    src = (HERE / "entry_phase_bench.py").read_text()
    assert "lk_EN0" not in src and "lk_WN1" not in src


# ---- consumer check on reset_tree.wf_plan ---------------------------------------------------------------------------------------------------------
def _rd(h):
    import math
    return -math.ceil(h / 2)


def wf(**rel):
    return {"parts": {k: {"release": v[0], "entry_stages": v[1]} for k, v in rel.items()}}


OLDP = {"lk_EN0": {"reset_entry_phase": 4}, "lk_WN1": {"reset_entry_phase": 3}}
NEWP = {"lk_EN0": {"reset_entry_phase": 3}, "lk_WN1": {"reset_entry_phase": 2}}


def mod():
    return _load("rebind_c", HERE / "rebind_nr_serdes.py")


def test_release_consistency_accepts_the_real_pattern():
    m = mod()
    got = m.check_release_consistency(wf(lk_EN0=(73, 0), lk_WN1=(76, 0), x=(5, 1)), wf(lk_EN0=(73, 0), lk_WN1=(77, 1), x=(5, 1)), OLDP, NEWP, _rd)
    assert got == {"lk_WN1": [76, 77]}


@pytest.mark.parametrize("new_wf,why", [
    (wf(lk_EN0=(73, 0), lk_WN1=(76, 0), x=(5, 1)), "release moved \\+0, release_delta says \\+1"),     # lk_WN1 did not move
    (wf(lk_EN0=(74, 0), lk_WN1=(77, 1), x=(5, 1)), "lk_EN0 release moved \\+1"),                     # lk_EN0 moved though its delta is unchanged
    (wf(lk_EN0=(73, 0), lk_WN1=(77, 1), x=(6, 1)), "x release moved"),                               # unrelated partition moved
    (wf(lk_EN0=(73, 0), lk_WN1=(77, 1), x=(5, 2)), "entry_stages changed"),                          # entry_stages changed with no release change
    (wf(lk_EN0=(73, 0), lk_WN1=(78, 1), x=(5, 1)), "lk_WN1 release moved \\+2"),
    (wf(lk_EN0=(73, 0), lk_WN1=(77, 1)), "missing on one side"),
])
def test_release_consistency_refusals(new_wf, why):
    m = mod()
    with pytest.raises(ValueError, match=why):
        m.check_release_consistency(wf(lk_EN0=(73, 0), lk_WN1=(76, 0), x=(5, 1)), new_wf, OLDP, NEWP, _rd)
