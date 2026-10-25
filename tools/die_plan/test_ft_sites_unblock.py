"""ft_sites_unblock.layered (PATH-KV-REBASE 10-25): macro-free per-bit station chains at a fixed station count."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ft_sites_unblock as U  # noqa: E402


def _man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def test_layered_routes_around_a_macro():
    U.FRAME[:] = [1200.0, 900.0]
    ia, ib = (20.0, 450.0), (1180.0, 450.0)          # 1160 um, k = 3 hops: interpolated stations at x 407 / 793
    k, budget = 3, 403.0
    ps = [(20.0 + 1160.0 * j / k, 450.0) for j in range(1, k)]
    grow = [(395.0, 440.0, 418.0, 460.0)]             # macro over the first interpolated station (406.7, 450)
    out = U.layered(ia, ib, ps, k, grow, budget, "t", "ft0", 0)
    chain = [ia] + out + [ib]
    assert len(out) == k - 1
    assert all(not (x0 < p[0] < x1 and y0 < p[1] < y1) for p in out for x0, y0, x1, y1 in grow)
    assert max(_man(a, b) for a, b in zip(chain, chain[1:])) <= budget - U.LAYER_SLACK + 1e-6


def test_layered_fails_closed_without_a_chain():
    U.FRAME[:] = [1300.0, 900.0]
    ia, ib = (20.0, 450.0), (1280.0, 450.0)          # 1260 um > 3 x 403: no chain at k = 3 even without macros
    try:
        U.layered(ia, ib, [(440.0, 450.0), (860.0, 450.0)], 3, [], 403.0, "t", "ft0", 0)
    except SystemExit as e:
        assert "no macro-free chain" in str(e)
    else:
        raise AssertionError("an impossible chain must fail closed")
