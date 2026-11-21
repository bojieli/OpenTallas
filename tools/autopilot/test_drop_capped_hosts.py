"""FLEET-WATCH-R5: a launch spec's frozen host list is re-filtered against the admit caps (gen_host_min_free_gb) at place time."""
import kit_wave as K

STT = {"epyc8": {"scratch_gb": 400}, "intel1": {"scratch_gb": 120}, "epyc9": {"scratch_gb": 169}, "intel2": {"scratch_gb": 90}}


def test_capped_hosts_are_dropped_while_another_stays():
    assert K.drop_capped_hosts(["epyc8", "intel1", "epyc9"], {"intel1": 250, "epyc9": 250}, STT) == ["epyc8"]


def test_host_over_its_cap_stays_and_unknown_status_is_kept():
    assert K.drop_capped_hosts(["epyc8", "intel1"], {"intel1": 100}, STT) == ["epyc8", "intel1"]
    assert K.drop_capped_hosts(["epyc8", "epyc10"], {"epyc10": 250}, STT) == ["epyc8", "epyc10"]


def test_never_an_empty_list():
    assert K.drop_capped_hosts(["intel1", "epyc9"], {"intel1": 250, "epyc9": 250}, STT) == ["intel1", "epyc9"]


def test_hub_is_read_as_localhost():
    assert K.drop_capped_hosts(["epyc8", "intel2"], {"intel2": 250}, dict(STT, localhost={"scratch_gb": 90}), "intel2") == ["epyc8"]
