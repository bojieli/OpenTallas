"""pick_gen_host: least loaded host first (load1 / cores, 5 % steps), ties by most free memory (FLEET-OPS-R, COORD 11-16)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as K


def cfg(hosts, st, **d):
    base = {"gen_host": hosts[0], "event": "e1", "plan": "/p", "src": "/s", "gen_hosts": hosts}
    base.update(d)
    return {"dies": {"s81": base}, "_otrun_status": {h: dict(v, run=0) for h, v in st.items()}}


def test_small_idle_host_beats_big_busy_host():
    # old rule (free cores x free admits): big = (256-205)*700 = 35.7k beats small = (32-2)*100 = 3k; least-loaded rule picks small (6 % vs 80 %)
    c = cfg(["big", "small"], {"big": {"admit": 700, "load": 205, "cores": 256}, "small": {"admit": 100, "load": 2, "cores": 32}})
    assert K.pick_gen_host(c, "s81") == "small"


def test_equal_load_ties_go_to_the_host_with_more_free_memory():
    c = cfg(["a", "b"], {"a": {"admit": 200, "load": 20, "cores": 96}, "b": {"admit": 600, "load": 21, "cores": 96}})
    assert K.pick_gen_host(c, "s81") == "b"                                           # 20.8 % vs 21.9 % = same 5 % step; b has more memory
    c = cfg(["a", "b"], {"a": {"admit": 600, "load": 20, "cores": 96}, "b": {"admit": 600, "load": 70, "cores": 96}})
    assert K.pick_gen_host(c, "s81") == "a"                                           # clearly lower load wins even with equal memory


def test_overloaded_host_is_routed_around_never_refused():
    # epyc10 at 190/96 with admits left is still a candidate; with an idle alternative it is simply not first
    c = cfg(["epyc10", "intel1"], {"epyc10": {"admit": 300, "load": 190, "cores": 96}, "intel1": {"admit": 300, "load": 17, "cores": 112}})
    assert K.pick_gen_host(c, "s81") == "intel1"
    c = cfg(["epyc10"], {"epyc10": {"admit": 300, "load": 190, "cores": 96}})
    assert K.pick_gen_host(c, "s81") == "epyc10"                                      # the only gen host is still used: nothing is refused


def test_host_share_weights_the_memory_tiebreak():
    c = cfg(["a", "b"], {"a": {"admit": 300, "load": 10, "cores": 96}, "b": {"admit": 300, "load": 10, "cores": 96}})
    c["host_share"] = {"a": 0.5}
    assert K.pick_gen_host(c, "s81") == "b"


def test_when_no_host_fits_the_burst_goes_to_the_least_loaded_not_the_best_score():
    """LOADRANK-NOFIT-1119: intel1/epyc7/epyc9 admit 0 (nothing fits); the old fallback took the best memory score = the busiest host"""
    c = cfg(["epyc7", "epyc9", "epyc10"], {"epyc7": {"admit": 0, "load": 473, "cores": 96}, "epyc9": {"admit": 0, "load": 200, "cores": 96}, "epyc10": {"admit": 0, "load": 95, "cores": 96}})
    assert K.pick_gen_host(c, "s81") == "epyc10"
    c = cfg(["epyc7", "epyc9"], {"epyc7": {"admit": 0, "load": 473, "cores": 96}, "epyc9": {"admit": 0, "load": 200, "cores": 96}})
    assert K.pick_gen_host(c, "s81", threads=16) == "epyc9"
    assert K.pick_gen_host(c, "s81", threads=16) == "epyc9"                           # the charged 16 threads (200 -> 232 -> 248) do not flip it: still far below epyc7
