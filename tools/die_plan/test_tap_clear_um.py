"""S81-PHYT1 11-15 (FABLE-PD-S81-0850 lever 3): per-type clock.tap_clear_um; ring bands avoid clock.tap_reserved_um."""
import pytest
import schema as S


def _t(clear=None):
    ck = dict(keepouts_um=[[0, 0, 40, 80], [50.8, 0, 100, 80]])
    if clear is not None:
        ck['tap_clear_um'] = clear
    return dict(module='ch', outline_um=[100, 80], clock=ck)


def test_default_clear_fits_no_tap_in_a_10p8_channel():
    with pytest.raises(ValueError, match='no legal clock tap site'):
        S.tap_clear(_t(), 45, 40)


def test_tap_clear_um_4p32_fits_the_channel_centre():
    t = _t(4.32)
    assert S.type_tap_clear(t) == 4.32 and S.type_tap_clear(_t()) == S.TAP_CLEAR_UM
    x, y = S.tap_clear(t, 45, 40)
    assert 44.32 - 1e-9 <= x <= 46.48 + 1e-9 and 4.32 <= y <= 80 - 4.32


def test_default_unchanged_without_key():
    t = dict(module='p', outline_um=[100, 80], clock=dict(keepouts_um=[[0, 0, 40, 80]]))
    x, y = S.tap_clear(t, 20, 40)
    assert x >= 40 + S.TAP_CLEAR_UM - 1e-9


def test_ring_band_obstacles_include_tap_reserved():
    import clock_landing_plan as C
    t = dict(module='ch', outline_um=[100, 80], clock=dict(tap_reserved_um=[[44.0, 10.0, 48.0, 14.0]]))
    assert [44.0, 10.0, 48.0, 14.0] in [list(o) for o in C._band_obstacles(t, [])]
