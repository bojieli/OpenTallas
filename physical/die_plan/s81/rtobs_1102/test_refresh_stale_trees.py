"""refresh_stale_trees (S81 plan event step 4, DIE-S81-50/diegrt 11-03): contract guard + overlap helper."""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("rst", Path(__file__).with_name("refresh_stale_trees.py"))
R = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R)


def _tree(**kw):
    t = dict(root=[10.0, 20.0], entry="relayed", sync_stages=2, depth=3, own_depth=3, tap_depth={"0": 1},
             taps=["clk"], n_clock_taps=1, n_reset_consumers=1, local_reset_taps=False, outs=[[1.0, 2.0]],
             core_resets=[dict(inst="u_c", pin="rst_n", pin_um=[50.0, 5.0], xy=[49.0, 5.0], internal_depth=1, tap=0)],
             relays=[dict(name="u_rrl_0", xy=[45.0, 5.0], d="rst_root_n", q="rst_rl_0")])
    t.update(kw)
    return t


def test_geometry_only_change_keeps_contract():
    new = _tree(core_resets=[dict(inst="u_c", pin="rst_n", pin_um=[41.36, 5.0], xy=[40.0, 5.0], internal_depth=1, tap=0)],
                relays=[dict(name="u_rrl_0", xy=[36.36, 5.0], d="rst_root_n", q="rst_rl_0")])
    assert R.contract_kept(_tree(), new) is None


def test_tap_or_depth_change_rejected():
    assert R.contract_kept(_tree(), _tree(depth=4)) == "depth"
    cr = [dict(inst="u_c", pin="rst_n", pin_um=[50.0, 5.0], xy=[49.0, 5.0], internal_depth=1, tap=1)]
    assert R.contract_kept(_tree(), _tree(core_resets=cr)) == "core_resets"


def test_relay_graph_change_rejected():
    new = _tree(relays=[dict(name="u_rrl_0", xy=[45.0, 5.0], d="rst_rl_9", q="rst_rl_0")])
    assert R.contract_kept(_tree(), new) == "relay graph"


def test_overlap_is_strict_interior():
    assert R._over([0, 0, 2, 2], [1, 1, 3, 3])
    assert not R._over([0, 0, 2, 2], [2, 0, 4, 2])
