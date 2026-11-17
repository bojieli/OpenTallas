"""FT-CHANNEL-TRACKS-1: ft bit sites in a vertical channel beside a hard core vs its tracks (check.ft_channels)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import check as C  # noqa: E402


def _type(core_x, bits_in_seam, bits_east=0):
    """outline 400 x 400, one core at x core_x..core_x+100, y 100..300; an N->S slot with sites in its west seam."""
    sites = [[2.0 + (i % 10), 150.0 + i * 0.01] for i in range(bits_in_seam)] + [[core_x + 150.0, 200.0]] * bits_east
    return {"outline_um": [400.0, 400.0],
            "hard_cores": [{"inst": "u_m", "module": "m", "origin_um": [core_x, 100.0], "outline_um": [100.0, 200.0], "orient": "R0"}],
            "ft_slots": [{"name": "ft0", "in_face": "N", "out_face": "S", "width": len(sites) - 1, "stations": 2,
                          "bit_site_cell_um": [1.404, 0.27], "bit_sites_um": [sites]}]}


def test_west_seam_util():
    ch = {round(r[0], 2): (b, u) for r, b, u in C.ft_channels(_type(30.0, 1000))}
    bits, util = ch[0.0]
    assert bits == 1000 and abs(util - 1000 / (45.6 * 30.0)) < 1e-9


def test_wider_seam_drops_util():
    narrow = max(u for _, _, u in C.ft_channels(_type(30.0, 1000)))
    wide = max(u for _, _, u in C.ft_channels(_type(64.56, 1000)))
    assert narrow > C.FT_CHANNEL_TRACK_MAX > wide


def test_east_channel_counted_once_and_abutted_skipped():
    t = _type(30.0, 0, bits_east=5)
    t["hard_cores"].append({"inst": "u_n", "module": "n", "origin_um": [130.0, 100.0], "outline_um": [50.0, 200.0], "orient": "R0"})
    ch = C.ft_channels(t)
    assert all(r[2] - r[0] > 0 for r, _, _ in ch)
    assert sum(b for _, b, _ in ch) == 5                 # the site east of u_n is in one channel only
