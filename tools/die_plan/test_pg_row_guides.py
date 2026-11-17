"""PG-ROW-GUIDES-1 (FABLE-FIX-S81-SERDES2 11-17): pg_row_guides.tcl PRE_DETAIL_ROUTE hook and its generator lines; serdes rck balance default."""
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

import gen_phys as G

HERE = Path(__file__).resolve().parent
TCLSH = shutil.which("tclsh")


def _legal(grid, a, b, spans, hw, sp):
    script = f"""set ::env(OT_PG_ROW_GUIDES_NO_RUN) 1
source {HERE / "pg_row_guides.tcl"}
puts [pgrg::legal_tracks {{{" ".join(map(str, grid))}}} {a} {b} {{{" ".join("{%d %d}" % s for s in spans)}}} {hw} {sp}]
"""
    return int(subprocess.run([TCLSH], input=script, capture_output=True, text=True, check=True).stdout.strip())


@pytest.mark.skipif(TCLSH is None, reason="tclsh not installed")
def test_legal_tracks_on_the_measured_serdes_pair_row():
    # ASAP7 M6: tracks 32 + 64 k nm, wire 32 (hw 16), spacing 32; die PDN pair VSS 654144-654432, VDD 654528-654816 (serdes__t13)
    grid = list(range(32, 700000, 64)); pair = [(654144, 654432), (654528, 654816)]
    assert _legal(grid, 654360, 654930, pair, 16, 32) == 1     # the H5 failing row: one legal track (654880)
    assert _legal(grid, 653790, 654360, pair, 16, 32) >= 4     # the row below keeps its tracks clear of the pair
    assert _legal(grid, 654360, 654930, [], 16, 32) == 9       # no stripe: every track of the row


def test_hook_only_edits_guides_and_is_guarded():
    t = (HERE / "pg_row_guides.tcl").read_text()
    assert "odb::dbGuide_create" in t and "odb::dbGuide_destroy" in t
    code = "\n".join(line for line in t.splitlines() if not line.lstrip().startswith("#"))
    for banned in ("dbInst_", "dbNet_create", "dbObstruction", "global_route", "detailed_route", "set_global_routing"):
        assert banned not in code, banned
    assert "catch {pgrg::run}" in t and '[pgrg::env OT_PG_ROW_GUIDES 1] eq "0"' in t
    # connectors are made before the old guide is destroyed
    body = t[t.index("proc pgrg::run"):]
    assert body.index("incr conn") < body.index("odb::dbGuide_destroy $g")


def test_generator_stages_the_hook_and_opt_in_line(monkeypatch):
    gp = (HERE / "gen_phys.py").read_text()
    assert '"pg_row_guides.tcl"' in gp
    assert G.pg_row_guides_lines([]) == G.PG_ROW_GUIDES_LINES
    assert G.pg_row_guides_lines(["override export PRE_DETAIL_ROUTE_TCL = /work/eco_drt_pre.tcl"]) == []
    assert G.pg_row_guides_lines(["export PRE_DETAIL_ROUTE_TCL = /work/x.tcl"]) == []


def test_serdes_pipe_kits_get_the_hook_by_default():
    with tempfile.TemporaryDirectory() as d:
        out = G.txl_mid_exports([], d, env={}, defines=["-DOT_S81_SERDES_TXPIPE", "-DOT_S81_SERDES_RXPIPE"])
        assert "export PRE_DETAIL_ROUTE_TCL = /work/pg_row_guides.tcl" in out
        assert "export OT_S81_RCK_BALANCE = 1" not in out                  # not an RCK4 kit: no rck balance
        off = G.txl_mid_exports([], d, env={"OT_PG_ROW_GUIDES": "0"}, defines=["-DOT_S81_SERDES_TXPIPE"])
        assert not any("pg_row_guides" in c for c in off)
        forced = G.txl_mid_exports([], d, env={"OT_S81_RCK_BALANCE": "1"}, defines=["-DOT_S81_SERDES_TXPIPE"])
        assert "export OT_S81_RCK_BALANCE = 1" in forced and "export OT_STB_ROUNDS = 16" in forced
        assert G.txl_mid_exports([], d, env={}, defines=["-DSYNTHESIS"]) == []    # non-serdes kit: still no lines


def test_rck4_kits_get_balance_with_16_rounds_by_default():
    from test_txl_mid_exports import _rck4_capsule
    with tempfile.TemporaryDirectory() as d:
        cfg, defines = _rck4_capsule(d)
        out = G.txl_mid_exports(cfg, d, env={}, defines=defines)
        assert "export OT_S81_RCK_BALANCE = 1" in out and "export OT_STB_ROUNDS = 16" in out
        assert out[-1].startswith("export POST_GLOBAL_PLACE_TCL")
    with tempfile.TemporaryDirectory() as d:
        cfg, defines = _rck4_capsule(d)
        off = G.txl_mid_exports(cfg, d, env={"OT_S81_RCK_BALANCE": "0"}, defines=defines)
        assert "export OT_S81_RCK_BALANCE = 1" not in off and "export OT_STB_ROUNDS = 16" not in off


def test_rck_balance_defaults_to_16_rounds():
    rb = (HERE / "rck_balance.tcl").read_text()
    assert "OT_RCK_BALANCE_ROUNDS [ot_rck_env OT_STB_ROUNDS 16]" in rb
