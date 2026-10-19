"""TOK-S81-GAPS/G8R2: frame x-chain read epochs resolve source-first (a delayed source delays its receivers)."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent))
from dv_bind import frame_release_epochs


def test_source_first_propagation():
    # a -> b -> c along an x chain; b and c released by the tree BEFORE their sources
    base = dict(a=40, b=30, c=20)
    deps = dict(b=[('a', 1)], c=[('b', 0)])
    ep = frame_release_epochs(base, deps, sync_edges=2)
    assert ep['a'] == 40
    assert ep['b'] == 40 + 1 - 2          # R0 = rst+2 >= G + N mod 2
    assert ep['c'] == ep['b'] + 0 - 2     # uses b's DELAYED epoch, not its tree release


def test_no_delay_when_receiver_late():
    ep = frame_release_epochs(dict(a=10, b=50), dict(b=[('a', 1)]), sync_edges=2)
    assert ep == dict(a=10, b=50)


def test_cycle_rejected():
    with pytest.raises(ValueError):
        frame_release_epochs(dict(a=1, b=2), dict(a=[('b', 0)], b=[('a', 0)]))
