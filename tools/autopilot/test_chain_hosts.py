"""FLOW-FLEET-R2: a private kit's chain (cts/grt/route/finish) lists spill alternatives after its home host, so ot-run can move a waiter the home host will not admit."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW      # noqa: E402

SP = {"private": {"lane": "L"}, "hosts": ["epyc8", "intel1", "epyc9", "epyc10", "epyc2", "epyc7"], "ot_run": "/x/ot-run"}


def test_private_chain_keeps_home_first_then_alternatives():
    assert KW.chain_hosts(SP, "epyc9", "intel2") == ["epyc9", "epyc8", "intel1", "epyc10", "epyc2", "epyc7"]


def test_draining_hosts_and_the_hub_are_not_alternatives():
    sp = dict(SP, hosts=SP["hosts"] + ["intel2", "localhost"])
    assert KW.chain_hosts(sp, "epyc9", "intel2", avoid={"epyc8", "epyc2"}) == ["epyc9", "intel1", "epyc10", "epyc7"]


def test_pin_opt_outs_and_wave_specs():
    assert KW.chain_hosts(dict(SP, chain_spill=False), "epyc9", "intel2") == ["epyc9"]
    assert KW.chain_hosts({"hosts": SP["hosts"]}, "epyc9", "intel2") == ["epyc9"]                       # not a private spec
    import os
    os.environ["KW_CHAIN_PIN"] = "1"
    try:
        assert KW.chain_hosts(SP, "epyc9", "intel2") == ["epyc9"]
    finally:
        del os.environ["KW_CHAIN_PIN"]
    assert KW.chain_hosts(SP, "intel2", "intel2")[0] == "localhost"                                       # the hub is spelled localhost, first


def test_chain_argv_carries_the_list_and_still_stages_the_kit():
    class AP:
        stage_disk_args = staticmethod(lambda: ["--disk", "60"])
        ADMISSION_BOOTSTRAP = "x"
        stage_admission_tools = staticmethod(lambda: {})
        late_eco_on = staticmethod(lambda: True)
    a = KW.chain_argv(SP, AP, "/srv/k", "/srv/k/run_kit.sh", "grt", 48, 16, "epyc9", "intel2")
    assert a[a.index("--hosts") + 1] == "epyc9,epyc8,intel1,epyc10,epyc2,epyc7" and a[a.index("--dir") + 1] == "/srv/k" and "--stage" in a
