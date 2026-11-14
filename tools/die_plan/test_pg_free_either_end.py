import schema as S

LAYERS = {"M5": {"pitch_um": 0.048, "offset_um": 0.0, "dir": "V", "name": "M5"}}


def _plan():
    p = S.Plan.__new__(S.Plan)
    full = {"hard": True, "outline_um": [100.0, 200.0], "clock": {"tap_um": [50.0, 199.0]},
            "contents": [{"inst": "u", "module": "m", "lef": "a.lef", "origin_um": [0, 0], "outline_um": [99.0, 199.0]}]}
    p.types = {"phy": full, "nb": {"outline_um": [300.0, 300.0]}}
    p.parts = {"io_phy": {"type": "phy"}, "coll": {"type": "nb"}}
    return p


def test_port_pg_free_when_either_end_is_full_area_hard_ip():
    p = _plan()
    assert p.port_pg_free({"src": {"part": "coll"}, "dst": {"part": "io_phy"}})     # neighbour-resolved: phy is the dst
    assert p.port_pg_free({"src": {"part": "io_phy"}, "dst": {"part": "coll"}})
    assert not p.port_pg_free({"src": {"part": "coll"}, "dst": {"part": "coll"}})
    assert not p.port_pg_free({"src": {"part": S.DIE_PART}, "dst": {"part": "coll"}})


def test_neighbour_window_is_not_widened_by_pg_bands():
    # 597 pins at 0.048 pitch: with the PG keep-out the window must widen, with pg_free it is the pin span
    L = LAYERS["M5"]
    plain = S.window_for(753.2, 597, ["M5"], LAYERS, per_um=1000.0, track_max=1.0)
    free = S.window_for(753.2, 597, ["M5"], LAYERS, per_um=1000.0, track_max=1.0, pg_free=True)
    assert free < plain
    assert abs((free - 753.2) - 597 * 0.048) < 0.2
    assert S.usable_tracks(L, "M5", 753.2, free, pg_free=True) >= 597 > S.usable_tracks(L, "M5", 753.2, free)
