"""R-CLOCK-7: the kit SDC of a type with plan clock.tap_offset rows (per-port set_clock_latency -source -early o-u / -late o+u)
must pass sdc_lint (QC slw_fe_v2 S3M2 write_type_kit raised SdcLintError, 67 errors: the lint only knew the -W/0 window)."""
import copy
import json
from pathlib import Path

import gen_phys as G
import schema as S
import sdc_lint

HERE = Path(__file__).resolve().parent
TINY = json.loads((HERE / "examples" / "tiny_plan.json").read_text())


def _plan(rows=True, win=80.0):
    raw = copy.deepcopy(TINY)
    P0 = S.Plan(raw)
    tn = next(t for t in P0.types if not P0.types[t].get("hard") and any(p["type"] == t for p in P0.parts.values()))
    raw["clock"]["tap_window"] = dict(window_ps=win, related_pair_ps=win)
    raw["clock"].setdefault("seam_hold", dict(sender_ps=25, seam_ps=80))
    P1 = S.Plan(raw)
    ports = [n for _ck, ps in G.tap_window_ports(P1, tn) for n in ps]
    if rows:
        raw["clock"]["tap_offset"] = {"per_port_ps": {tn: {n: dict(TT=float(7 * i + 3), FF=float(5 * i + 2), tol=float(10 + i))
                                                           for i, n in enumerate(ports)}}}
    return raw, tn, ports


def test_offset_sdc_passes_lint_and_wrong_value_fails():
    raw, tn, ports = _plan()
    P = S.Plan(raw)
    assert ports and G.tap_offset_table(P, tn)
    s = G.sdc(P, tn, G.type_pins(P, tn))
    assert "set_clock_latency -source -early" in s
    ctx = sdc_lint.kit_context(P, tn)
    assert "tap_offset_ps" in ctx
    assert sdc_lint.lint(s, **ctx) == []
    # the same SDC against a lint context without the offset rows is the old failure (window form expected)
    bare = {k: v for k, v in ctx.items() if k != "tap_offset_ps"}
    assert sdc_lint.lint(s, **bare) != []
    # a changed late value fails closed
    bad = s.replace("-late -clock clk", "-late -clock clk 99.0 [get_ports {zz}]\nset_clock_latency -source -late -clock clk", 1)
    assert sdc_lint.lint(bad, **ctx) != []


def test_window_only_type_unchanged():
    raw, tn, ports = _plan(rows=False)
    P = S.Plan(raw)
    s = G.sdc(P, tn, G.type_pins(P, tn))
    ctx = sdc_lint.kit_context(P, tn)
    assert "tap_offset_ps" not in ctx
    assert sdc_lint.lint(s, **ctx) == []
