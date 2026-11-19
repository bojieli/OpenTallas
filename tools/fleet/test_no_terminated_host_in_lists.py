"""EPYC4-OUT-1119: the terminated epyc4 is in no default host list or probe set (74 host-key failures a day)."""
import importlib.machinery, importlib.util, pathlib, re
H = pathlib.Path(__file__).parent


def test_default_host_lists_do_not_name_epyc4():
    for rel in ("ot-run", "../autopilot/orphan_scan.py", "../autopilot/failfast_scan.py", "../autopilot/gp_noconverge.py"):
        src = (H / rel).read_text()
        for m in re.finditer(r'^(HOSTS|DEFAULT_HOSTS) = (.*)$', src, re.M):
            assert "epyc4" not in m.group(2).split("#")[0], (rel, m.group(0)[:100])
