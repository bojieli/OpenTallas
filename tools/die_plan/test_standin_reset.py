"""die_trial stand-ins carry the reset wavefront + START ports (PATH-QC 2026-10-25): every die-top connection of every
partition instance resolves to a stand-in port (QC plan 441d had 373 start_i + 1134 rst_o/start_o + 308 shared-module
variant ports dangling -> die STA silently dropped them), and each reset/START pin has its own pin register."""
import re
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import die_trial as T  # noqa: E402
import gen_phys as G  # noqa: E402
import gen_rtl  # noqa: E402
import schema as S  # noqa: E402

PLANS = [HERE.parent.parent / "physical" / "die_plan" / d / "die_plan.json" for d in ("s81_head", "qwen_compute")]


def _ports(v):
    return {x.strip() for x in re.search(r"module \S+ \(([^)]*)\);", v).group(1).split(",")}


@pytest.mark.parametrize("plan", [p for p in PLANS if p.is_file()], ids=lambda p: p.parent.name)
def test_every_die_top_connection_has_a_standin_port(plan):
    P = S.Plan(S.load(plan), plan)
    smod = T.standin_module_names(P)
    mods = {}
    for tn, t in P.types.items():
        v, k = T.standin_netlist(P, tn)
        assert len(re.findall(r"\.CLK\(", v)) == k
        ports = _ports(v)
        for n, _, _ in G.reset_out_pins(P, tn):          # registered outs: one flop drives each
            assert n in ports and len(re.findall(r"\.QN\(" + re.escape(n) + r"\)", v)) == 1
        for n in ("arst_n", "start_i"):
            if any(p[0] == n for p in G.tap_pins(P, tn)):  # registered entries: one hold-contract cell -> flop
                assert n in ports and len(re.findall(r"\.A\(" + re.escape(n) + r"\)", v)) == 1
        mods.setdefault(smod[tn], ports)
        assert mods[smod[tn]] == ports                     # a stand-in module is never shared by different pin sets
    top = T.retarget_shared_modules(P, gen_rtl.die_top(P, gen_rtl.bus_epochs(P), {}), smod)
    cur, n_inst, miss = None, 0, []
    for ln in top.splitlines():
        m = re.match(r"^\s*(\S+)\s+(\w+)\s*\($", ln)
        if m and m.group(1) in mods:
            cur, n_inst = m.group(1), n_inst + 1
            continue
        if cur and ln.strip().startswith(");"):
            cur = None
        elif cur:
            pm = re.match(r"^\s*\.(\w+)\s*\(", ln)
            if pm and pm.group(1) not in mods[cur]:
                miss.append((cur, pm.group(1)))
    assert n_inst == len(P.parts)
    assert not miss, miss[:10]


def test_retarget_refuses_missing_instance():
    class _P:
        types = {"a": {"module": "m"}, "b": {"module": "m"}}
        parts = {"x": {"type": "a"}}
    with pytest.raises(ValueError):
        T.retarget_shared_modules(_P, "module top();\nendmodule\n", T.standin_module_names(_P))
