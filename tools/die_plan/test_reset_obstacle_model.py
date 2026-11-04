import reset_tree as RT
import pytest


def _t(**reset):
    return dict(hard_cores=[dict(inst='core', origin_um=[100., 100.], outline_um=[10., 10.],
                                 track_offset_um=[.216, .108])],
                contents=[dict(inst='reuse', origin_um=[20., 20.], outline_um=[10., 10.])], reset=reset)


def test_default_is_canonical_union():
    boxes = RT.blockages(_t())
    assert len(boxes) == 2
    assert not RT._free((25., 25.), boxes, (0., 0., 200., 200.))


def test_lef_origin_reproduces_frozen_model():
    boxes = RT.blockages(_t(obstacle_model="lef_origin"))
    assert boxes == [pytest.approx((95.68, 95.68, 114.32, 114.32))]
    assert RT._free((25., 25.), boxes, (0., 0., 200., 200.))


def test_lef_origin_keeps_keepouts():
    t = _t(obstacle_model="lef_origin"); t["clock"] = dict(keepouts_um=[[60., 60., 80., 80.]])
    assert len(RT.blockages(t)) == 2
