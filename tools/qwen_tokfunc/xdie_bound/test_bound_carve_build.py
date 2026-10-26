"""tests for bound_carve_build.py file-list logic: python3 -m pytest tools/qwen_tokfunc/xdie_bound/test_bound_carve_build.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bound_carve_build as B  # noqa: E402

# toy design: two partition types share a leaf; one type reaches a module with no source
GRAPH = {"pA": ["leaf", "sram"], "pB": ["leaf", "hcore"], "pC": ["ghost"], "leaf": [], "sram": [], "hcore": ["leaf"]}
FILE = {"pA": "b/pA.sv", "pB": "b/pB.sv", "pC": "b/pC.sv", "leaf": "r/leaf.sv", "sram": "m/sram.v", "hcore": "r/hc.sv"}


def closure(mods):
    seen, files, miss, todo = set(), [], [], list(mods)
    while todo:
        m = todo.pop(0)
        if m in seen:
            continue
        seen.add(m)
        if m not in FILE:
            miss.append(m)
            continue
        files.append(FILE[m])
        todo += GRAPH[m]
    return files, {}, miss


def test_type_lists_are_per_type_closures():
    lists, amb, miss = B.type_lists(["pB", "pA"], closure)
    assert lists == {"pA": ["b/pA.sv", "r/leaf.sv", "m/sram.v"], "pB": ["b/pB.sv", "r/leaf.sv", "r/hc.sv"]}
    assert "b/pB.sv" not in lists["pA"]          # a type's list never carries another partition's RTL
    assert miss == {} and amb == {}


def test_missing_is_reported_not_stubbed():
    lists, _, miss = B.type_lists(["pC"], closure)
    assert miss == {"pC": ["ghost"]} and lists["pC"] == ["b/pC.sv"]


def test_union_ordered_no_dupes():
    lists, _, _ = B.type_lists(["pA", "pB"], closure)
    u = B.union_files(lists, first=["carve.v"])
    assert u == ["carve.v", "b/pA.sv", "r/leaf.sv", "m/sram.v", "b/pB.sv", "r/hc.sv"]


def test_vlt_and_f_text():
    v = B.vlt_text(["pB", "pA", "pA", "hcore"])
    assert v.splitlines() == ["`verilator_config", 'hier_block -module "hcore"', 'hier_block -module "pA"',
                              'hier_block -module "pB"']
    f = B.ff_text("pA", ["X"], ["src/rtl"], ["b/pA.sv"], ["--lint-only"]).split()
    assert f == ["--lint-only", "--top-module", "pA", "+define+X", "+incdir+src/rtl", "b/pA.sv"]
