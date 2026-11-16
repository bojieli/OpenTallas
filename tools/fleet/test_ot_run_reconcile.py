"""FLOW-HEALTH-1 11-15 (COORD r196): ot-run reconcile - the hand patches the installed intel2 backend carried (NEEDS_1115, epyc10, host reserve,
60 s probe + retry) are on main with the PSI plan placement, and nothing is defined twice."""
import ast
import importlib.machinery
import importlib.util
import collections
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = (HERE / "ot-run").read_text()


def load():
    loader = importlib.machinery.SourceFileLoader("ot_run_reconcile", str(HERE / "ot-run"))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    m = importlib.util.module_from_spec(spec)
    loader.exec_module(m)
    return m


m = load()


def test_no_function_defined_twice():
    c = collections.Counter(n.name for n in ast.parse(SRC).body if isinstance(n, ast.FunctionDef))
    assert [k for k, v in c.items() if v > 1] == []


def test_needs_replicate_present():
    for name in ("hosts_with_needs", "replicate_dirs", "cmd_input_paths"):
        assert callable(getattr(m, name)), name
    assert "--needs" in SRC and "--replicate" in SRC and "OT_RUN_NO_NEEDS_CHECK" in SRC


def test_epyc10_in_the_host_and_floor_tables():
    assert "epyc10" in m.HOSTS and m.HOST_ROLE.get("epyc10") == "normal"
    assert m.ROOT_SCRATCH_FLOOR_GB_HOSTS.get("epyc10") == 150 and m.ROOTFS_MIN_FREE_GB_HOSTS.get("epyc10") == 150


def test_probe_has_the_timeout_retry_and_psi():
    assert "PROBE_TIMEOUT_1114" in SRC and "for _try in (0, 1)" in SRC
    assert m.psi_of("OT_PSI 3.5\n") == 3.5 and "OT_PSI" in m.PSI_SH


def test_second_roots_per_host_and_inputhold_kept():
    assert "epyc2" in m.ROOT_SCRATCH_ROOTS_HOSTS and callable(m.second_roots)
    assert callable(m.spec_local_inputs) and callable(m.holders_of) and callable(m.soft_pin_ok)
