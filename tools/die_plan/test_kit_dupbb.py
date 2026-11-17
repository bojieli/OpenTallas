"""S81-KIT-DUPBB 11-17: a rewritten existing blackbox must not be listed twice in the kit source list (kit_contract duplicate_modules)."""
import ast
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = (HERE / "gen_phys.py").read_text()


def _helper():
    tree = ast.parse(SRC)
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "append_new_src")
    ns = {}
    exec(compile(ast.Module([fn], []), "gen_phys_helper", "exec"), ns)
    return ns["append_new_src"]


def test_existing_blackbox_is_not_listed_twice():
    f = _helper()
    srcs = ["/work/rtl/a.sv", "/work/rtl/ot_s81sl_egn_bb.v", "/work/rtl/ot_s81sl_egg_bb.v"]
    f(srcs, "/work/rtl/ot_s81sl_egn_bb.v")           # rewritten in place by macro_param_blackboxes: already listed
    f(srcs, "/work/rtl/ot_s81sl_egg_bb.v")
    assert srcs == ["/work/rtl/a.sv", "/work/rtl/ot_s81sl_egn_bb.v", "/work/rtl/ot_s81sl_egg_bb.v"]


def test_a_new_blackbox_is_appended_once():
    f = _helper()
    srcs = ["/work/rtl/a.sv"]
    f(srcs, "/work/rtl/m_bb.v")
    f(srcs, "/work/rtl/m_bb.v")
    assert srcs == ["/work/rtl/a.sv", "/work/rtl/m_bb.v"]


def test_gen_phys_uses_the_helper_for_the_param_blackboxes():
    assert "append_new_src(srcs, f\"/work/rtl/{f.name}\")" in SRC
    assert "srcs.append(f\"/work/rtl/{f.name}\")" not in SRC
