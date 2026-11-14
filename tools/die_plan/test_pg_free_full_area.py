import schema as S

LAYERS = {"M5": {"pitch_um": 0.048, "offset_um": 0.0, "dir": "V", "name": "M5"}}


def _port(pg_free):
    return dict(id="p", face="N", window_um=[0.0, 3.0], layers=["M5"], width=60, order="lsb_low",
                **({"pg_free": True} if pg_free else {}))


def test_usable_tracks_pg_free_counts_every_track():
    L = LAYERS["M5"]
    assert S.usable_tracks(L, "M5", 0.0, 3.0, pg_free=True) > S.usable_tracks(L, "M5", 0.0, 3.0)


def test_window_pins_pg_free_places_pins_the_pg_keepout_refuses():
    # 60 pins at the macro's 0.048 pitch fill a 3 um window: the PG stripe keep-out leaves only 52 tracks
    try:
        S._window_pins(_port(False), LAYERS, [0.0, 3.0], list(range(60)))
        raise AssertionError("default must refuse (window has fewer PG-free tracks than pins)")
    except ValueError as exc:
        assert "off the PG" in str(exc)
    pins = S._window_pins(_port(True), LAYERS, [0.0, 3.0], list(range(60)))
    assert len({x[2] for x in pins}) == 60
