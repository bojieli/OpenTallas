"""DIE-S81-85 11-09: a collector window whose runtime grow law (x2..x32) cannot reach any row is moved at gen, clear
of every hard core; a window that can reach rows is byte-identical; no room fails at gen with a clear error."""
from types import SimpleNamespace

import pytest

import landing_place as LP

# S81 ot_s81sl_leaf__t10 geometry: u_lf.u_vsw 224.64 um square at (77.76, 708.48); rst_rl_148 at (194.32, 859.32)
VSW = {'inst': 'u_lf.u_vsw', 'origin_um': [77.76, 708.48], 'outline_um': [224.64, 224.64]}
OUTLINE = [1442.88, 1226.88]
RELAY = [194.32, 859.32]


def _plan(cores, relay_xy=RELAY, outline=OUTLINE):
    tree = {'root': [300.0, 1200.0], 'relays': [
        {'q': 'rst_rl_1', 'd': 'rst_root_n', 'xy': [300.0, 1100.0]},
        {'q': 'rst_rl_148', 'd': 'rst_rl_1', 'xy': list(relay_xy)},
        {'q': 'rst_n_t40', 'd': 'rst_rl_148', 'xy': [112.32, 1123.2]}]}
    c = {'collector_tree': tree, 'collector_root_node': 'rst_root_n',
         'collector_local_sources': [{'name': 'ft0_i', 'tap': 40, 'xy_um': [112.32, 1123.2]}]}
    t = {'outline_um': outline, 'hard_cores': cores, 'clock': {'landing_contract': c}}
    return SimpleNamespace(types={'t': t})


def _group(text, prefix):
    line = next(ln for ln in text.splitlines() if ln.strip().startswith('{' + prefix + ' '))
    return [float(v) for v in line.split('{')[2].split('}')[0].split()]


def test_t10_relay_deep_in_macro_moves_out_at_gen():
    out = LP.tcl(_plan([VSW]), 't')
    x0, y0, x1, y1 = _group(out, 'u_cland_collect_rst_rl_148')
    assert (x1 - x0, y1 - y0) == (pytest.approx(4.32), pytest.approx(4.32))
    top = 708.48 + 224.64
    assert y0 >= top + 4.32 - 1e-6 and y0 == pytest.approx(top + 4.32)   # nearest edge (73.8 um) first
    assert _group(out, 'u_cland_reset_rst_rl_148') == [x0, y0, x1, y1]  # the raw copy shares the window


def test_runtime_grow_law_reaches_rows_so_output_is_identical():
    # same relay, smaller macro: the x32 window (+-69.12 um) reaches rows beside it, so the runtime law places it
    small = dict(VSW, origin_um=[150.0, 820.0], outline_um=[90.0, 90.0])
    out = LP.tcl(_plan([small]), 't')
    assert _group(out, 'u_cland_collect_rst_rl_148') == pytest.approx([192.16, 857.16, 196.48, 861.48])
    assert out == LP.tcl(_plan([]), 't')  # the same text as a type without the core


def test_no_core_identical_to_plain_window():
    out = LP.tcl(_plan([]), 't')
    assert _group(out, 'u_cland_collect_rst_rl_148') == pytest.approx([192.16, 857.16, 196.48, 861.48])


def test_mutant_without_gen_move_keeps_window_inside_macro():
    # negative control: the old law (plain +-2.16 window) leaves the t10 window inside u_vsw with no reachable row
    t = _plan([VSW]).types['t']
    g = 2.16 * LP.COLLECTOR_GROW_MAX
    assert not LP._rows_reachable(t, [RELAY[0] - g, RELAY[1] - g, RELAY[0] + g, RELAY[1] + g])
    plain = [RELAY[0] - 2.16, RELAY[1] - 2.16, RELAY[0] + 2.16, RELAY[1] + 2.16]
    assert LP._collector_window('t', t, 'rst_rl_148', RELAY) != plain


def test_neighbour_core_blocks_nearest_exit():
    above = {'inst': 'u_n', 'origin_um': [77.76, 933.12 + 2.0], 'outline_um': [224.64, 200.0]}
    x0, y0, x1, y1 = _group(LP.tcl(_plan([VSW, above]), 't'), 'u_cland_collect_rst_rl_148')
    for a, b, c, d in LP._hard_core_rects(_plan([VSW, above]).types['t']):
        assert x1 <= a - 4.32 + 1e-6 or x0 >= c + 4.32 - 1e-6 or y1 <= b - 4.32 + 1e-6 or y0 >= d + 4.32 - 1e-6


def test_macro_moves_use_kit_sites():
    # OT_MACRO_MOVES moved u_vsw 30 um up: the window clears the MOVED macro, not the plan one
    moves = {'u_bound.u_u_vsw': {'inst': 'u_lf.u_vsw', 'from': [77.76, 708.48], 'to': [77.76, 738.48],
                                 'orient': 'MX', 'x': 77.868, 'y': 738.516}}
    y0 = _group(LP.tcl(_plan([VSW]), 't', moves), 'u_cland_collect_rst_rl_148')[1]
    assert y0 == pytest.approx(738.48 + 224.64 + 4.32)
    assert LP.tcl(_plan([VSW]), 't', {}) == LP.tcl(_plan([VSW]), 't')


def test_no_room_fails_at_gen_with_size_error():
    # the macro fills the type: no 4.32 um window clear of it fits the outline
    full = {'inst': 'u_f', 'origin_um': [0.0, 0.0], 'outline_um': [300.0, 300.0]}
    with pytest.raises(ValueError, match=r'landing collector \w+ window .*no row within \+-69\.12 um'):
        LP.tcl(_plan([full], relay_xy=[150.0, 150.0], outline=[300.0, 300.0]), 't')
