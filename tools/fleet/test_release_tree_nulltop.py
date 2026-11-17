"""A record with no face_guard top is matched by its kit run name k<x>_<module>_synth<N> (EXPLORER-FABLE-1 11-14)."""
import importlib.util, pathlib
spec = importlib.util.spec_from_file_location("rtp", str(pathlib.Path(__file__).with_name("release_tree_plan.py"))); rtp = importlib.util.module_from_spec(spec); spec.loader.exec_module(rtp)


def test_null_top_run_name_maps_to_module():
    assert "sta_region_nb0" in rtp.rec_keys(dict(top=None, name="kq_sta_region_nb0_synth0"))
    assert "qfd_dv_s8_station_tail1" in rtp.rec_keys(dict(top=None, name="kq_qfd_dv_s8_station_tail1_synth0"))


def test_named_top_is_not_overridden():
    ks = rtp.rec_keys(dict(top="other_top", name="kq_some_mod_synth0"))
    assert "other_top" in ks and "some_mod" not in ks


def test_other_names_unchanged():
    assert rtp.rec_keys(dict(top=None, name="dp_kv3_phy")) == frozenset({"dp_kv3_phy", "kv3_phy"})
    assert "plain" in rtp.rec_keys(dict(top=None, name="plain")) and len(rtp.rec_keys(dict(top=None, name="plain"))) == 1
