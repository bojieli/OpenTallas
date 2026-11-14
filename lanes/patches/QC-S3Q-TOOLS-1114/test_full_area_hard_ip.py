import schema as S


def _t(**kw):
    t = {"hard": True, "outline_um": [100.0, 200.0], "clock": {"tap_um": [50.0, 199.0]},
         "contents": [{"inst": "u", "module": "m", "lef": "a.lef", "origin_um": [0, 0], "outline_um": [99.0, 199.0]}]}
    t.update(kw)
    return t


def test_full_area_macro_detected():
    assert S.full_area_hard_ip(_t())


def test_small_macro_not_full_area():
    t = _t()
    t["contents"][0]["outline_um"] = [50.0, 50.0]
    assert not S.full_area_hard_ip(t)


def test_needs_lef_and_single_content_and_no_hard_cores():
    t = _t()
    t["contents"][0].pop("lef")
    assert not S.full_area_hard_ip(t)
    assert not S.full_area_hard_ip(_t(hard_cores=[{"inst": "c"}]))
    t2 = _t()
    t2["contents"].append(dict(t2["contents"][0], inst="v"))
    assert not S.full_area_hard_ip(t2)
