"""FLOW-FLEET-R2: private-spec without --host picks the gen host with the most headroom."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW      # noqa: E402

STT = {
    "epyc9": {"admit": 80, "load": 140.0, "cores": 96, "wait_n": 6, "wait_gb": 168, "scratch_gb": 400},
    "epyc10": {"admit": 160, "load": 60.0, "cores": 96, "wait_n": 1, "wait_gb": 40, "scratch_gb": 300},
    "epyc7": {"admit": 140, "load": 60.0, "cores": 96, "wait_n": 0, "wait_gb": 0, "scratch_gb": 600},
    "epyc8": {"admit": 20, "load": 20.0, "cores": 96, "scratch_gb": 400},
    "intel1": {"admit": 200, "load": 20.0, "cores": 112, "scratch_gb": 30},
    "localhost": {"admit": 300, "load": 5.0, "cores": 112, "scratch_gb": 600},
}


def test_lowest_load_then_fewest_queued_wins():
    h, why = KW.headroom_host(["epyc9", "epyc10", "epyc7", "epyc8", "intel1"], STT)
    assert h == "epyc7" and "load 60/96" in why                       # epyc10 ties on load, epyc7 queues less


def test_skips_draining_low_scratch_no_admit_and_the_hub():
    assert KW.headroom_host(["epyc9", "epyc10", "epyc7", "epyc8", "intel1", "intel2"], STT, hub="intel2", drain={"epyc7"})[0] == "epyc10"
    assert KW.headroom_host(["epyc8", "intel1"], STT)[0] == ""         # epyc8 admits 20 GB < 48, intel1 scratch 30 < 50 floor
    assert KW.headroom_host(["epyc9"], {}, )[0] == "" and KW.headroom_host([], STT)[0] == ""
