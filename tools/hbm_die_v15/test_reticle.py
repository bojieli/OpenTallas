import pytest
import reticle


def test_landscape_and_portrait_ok():
    assert reticle.check_die(32428.16, 25434.684)['ok']
    assert reticle.check_die(25434.684, 32428.16)['ok']


def test_width_over_fails_even_when_area_fits():
    r = reticle.check_die(33197, 24000)        # the 10-16 area-only d4c grant
    assert not r['ok'] and r['long_margin_um'] < 0
    with pytest.raises(SystemExit):
        reticle.require_die(33197, 24000)


def test_short_side_margin():
    assert not reticle.check_die(32000, 25600)['ok']
    assert reticle.check_die(32000, 25500)['ok']
