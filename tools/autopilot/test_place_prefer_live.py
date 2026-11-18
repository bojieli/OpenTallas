import kit_wave as KW


def test_place_prefer_is_computed_from_live_admission():
    stt = {"intel1": {"admit": 300, "scratch_gb": 21}, "epyc10": {"admit": 700, "scratch_gb": 44}, "epyc8": {"admit": 300, "scratch_gb": 110},
           "epyc2": {"admit": 5, "scratch_gb": 200}, "localhost": {"admit": 300, "scratch_gb": 120}, "epyc7": {"admit": 300}}
    pref = ["intel1", "epyc10", "epyc8", "epyc2", "intel2", "epyc7"]
    assert KW.place_prefer_live(pref, stt, 32, hub="intel2") == ["epyc8", "epyc7"]       # intel1/epyc10 refused (<50), epyc2 cannot admit 32 GB, intel2 = localhost refused (<150), epyc7 unknown scratch kept


def test_a_recovered_host_returns_without_any_config_change():
    pref = ["intel1", "epyc8"]
    assert KW.place_prefer_live(pref, {"intel1": {"admit": 300, "scratch_gb": 30}, "epyc8": {"admit": 300, "scratch_gb": 90}}, 16) == ["epyc8"]
    assert KW.place_prefer_live(pref, {"intel1": {"admit": 300, "scratch_gb": 80}, "epyc8": {"admit": 300, "scratch_gb": 90}}, 16) == ["intel1", "epyc8"]
