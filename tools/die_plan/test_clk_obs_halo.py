"""CLK-OBS-HALO 11-18: pure tests of the clock-buffer obstruction halo planner (clk_obs_halo.tcl ::ot_clk_halo::plan)
and of its wiring (tap_balance.tcl hook, kit tool list).  HEAD hd_mesh mesh_w1 clk_t41_tb0_d3 is the reference case."""
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).parent
TOOL = HERE / 'clk_obs_halo.tcl'
TCLSH = shutil.which('tclsh')
needs_tcl = pytest.mark.skipif(TCLSH is None, reason='tclsh not installed')

SITE, ROW = 54, 270


def plan(cells, obs, blocks=(), rows=None, occ=None, hx=10 * SITE, hy=ROW, maxsites=400, maxrows=6):
    rows = rows or {y: (0, 100000, 'R0' if (y // ROW) % 2 == 0 else 'MX') for y in range(0, 20 * ROW, ROW)}
    occ = occ or {}
    lst = lambda rs: ' '.join('{' + ' '.join(str(v) for v in r) + '}' for r in rs)
    rd = ' '.join(f'{y} {{{a} {b} {o}}}' for y, (a, b, o) in rows.items())
    od = ' '.join(f'{y} {{{lst(v)}}}' for y, v in occ.items())
    script = (f'source {{{TOOL}}}\n'
              f'set r [::ot_clk_halo::plan [list {lst(cells)}] [list {lst(obs)}] [list {lst(blocks)}] [dict create {rd}] '
              f'[dict create {od}] {hx} {hy} {SITE} {maxsites} {maxrows}]\n'
              'foreach m [dict get $r moves] {puts "MOVE $m"}\nforeach s [dict get $r stuck] {puts "STUCK $s"}\n')
    out = subprocess.run([TCLSH], input=script, capture_output=True, text=True, check=True).stdout.splitlines()
    moves = {l.split()[1]: (int(l.split()[2]), int(l.split()[3]), l.split()[4]) for l in out if l.startswith('MOVE ')}
    return moves, [l.split()[1] for l in out if l.startswith('STUCK ')]


def clear(x, y, w, obs, hx=10 * SITE, hy=ROW):
    return not any(x < ox1 + hx and ox0 - hx < x + w and y < oy1 + hy and oy0 - hy < y + ROW for ox0, oy0, ox1, oy1 in obs)


@needs_tcl
def test_cell_on_the_padded_edge_moves_out_of_the_halo():
    # mesh_w1: obstruction 278100..280260 x 523260..524340, the buffer 162 dbu east of it (rebased to a small frame)
    obs = [(2160, 1080, 4320, 2160)]
    moves, stuck = plan([('d3', 4482, 1620, 378, ROW)], obs, blocks=[(1998, 1080, 4482, 2160)])
    assert not stuck and set(moves) == {'d3'}
    x, y, _ = moves['d3']
    assert clear(x, y, 378, obs) and (x % SITE, y % ROW) == (0, 0)
    assert abs(x - 4482) + abs(y - 1620) <= 10 * SITE          # nearest free site: 7 sites east, same row
    assert (x, y) == (4860, 1620)


@needs_tcl
def test_cell_under_the_obstruction_leaves_the_row_halo():
    obs = [(2160, 1080, 4320, 2160)]
    moves, stuck = plan([('d3', 3942, 810, 378, ROW)], obs)
    assert not stuck
    x, y, orient = moves['d3']
    assert clear(x, y, 378, obs)
    assert orient == ('R0' if (y // ROW) % 2 == 0 else 'MX')   # the target row's orientation


@needs_tcl
def test_cells_outside_the_halo_do_not_move():
    obs = [(2160, 1080, 4320, 2160)]
    moves, stuck = plan([('far', 4320 + 10 * SITE, 1620, 378, ROW), ('above', 3000, 2160 + ROW, 378, ROW)], obs)
    assert moves == {} and stuck == []


@needs_tcl
def test_occupied_sites_and_blockages_are_skipped():
    obs = [(2160, 1080, 4320, 2160)]
    occ = {1620: [(4860, 5400, 'other'), (4482, 4860, 'a')]}   # the nearest free run is taken by another cell
    moves, stuck = plan([('a', 4482, 1620, 378, ROW)], obs, blocks=[(5400, 1620, 5454, 1890)], occ=occ)
    assert not stuck
    x, y, _ = moves['a']
    assert clear(x, y, 378, obs)
    assert not (y == 1620 and x < 5400 and 4860 < x + 378)     # not on 'other'
    assert not (y == 1620 and x < 5454 and 5400 < x + 378)     # not on the blockage


@needs_tcl
def test_two_halo_cells_never_take_the_same_site():
    obs = [(2160, 1080, 4320, 2160)]
    moves, stuck = plan([('a', 4482, 1620, 378, ROW), ('b', 4536, 1620, 378, ROW)], obs)
    assert not stuck and set(moves) == {'a', 'b'}
    (xa, ya, _), (xb, yb, _) = moves['a'], moves['b']
    assert clear(xa, ya, 378, obs) and clear(xb, yb, 378, obs)
    assert ya != yb or xa + 378 <= xb or xb + 378 <= xa


@needs_tcl
def test_no_free_site_in_reach_is_reported_not_forced():
    obs = [(0, 0, 100000, 20 * ROW)]
    moves, stuck = plan([('d', 5400, 1620, 378, ROW)], obs, maxsites=20, maxrows=2)
    assert moves == {} and stuck == ['d']


def test_tap_balance_calls_the_halo_pass_after_legalisation_and_fails_open():
    text = (HERE / 'tap_balance.tcl').read_text()
    i = text.index('if {$placed} { detailed_placement }')
    j = text.index('::ot_clk_halo::apply')
    assert i < j < text.index('global_route -end_incremental', i)
    assert 'clk_obs_halo.tcl' in text and 'catch {' in text[j - 200:j]


def test_the_tool_is_in_the_kit_tool_list_and_default_on():
    assert '"clk_obs_halo.tcl"' in (HERE / 'gen_phys.py').read_text()
    tool = TOOL.read_text()
    assert '$::env(OT_CLK_OBS_HALO) eq "0"' in tool and 'OT_CLK_OBS_HALO_SITES) : 10' in tool
