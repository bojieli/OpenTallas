"""FLOW-OPS-0900 fix 4: one drain-aware host filter (host_drain.py)."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import host_drain as HD

CFG = {"dies": {"s81": {"gen_host_min_free_gb": {"intel1": 250, "epyc9": 250}}, "s81_head": {"gen_host_min_free_gb": {"epyc9": 300}}, "hbm": {}},
       "host_drain": {"epyc8": "bad"}}


def test_caps_are_the_max_over_dies():
    assert HD.caps_from_cfg(CFG) == {"intel1": 250, "epyc9": 300}


def test_draining_and_no_fallback_to_the_full_list():
    dr = HD.draining({"intel1": 250, "epyc9": 250, "intel2": 100}, {"intel1": 100, "epyc9": 146, "epyc10": 391, "localhost": 90, "epyc2": None}, hub="intel2")
    assert dr == {"intel1": (100, 250), "epyc9": (146, 250), "localhost": (90, 100)}
    assert HD.filter_hosts(["intel1"], dr) == ([], ["intel1"])                    # all capped: empty, the caller refuses
    assert HD.filter_hosts(["intel1", "epyc10"], dr) == (["epyc10"], ["intel1"])
    assert HD.filter_hosts(["intel1"], dr, keep=lambda h: True) == (["intel1"], [])  # --dir already holds data there
    assert HD.draining({"intel1": 250}, {"intel1": 260}) == {}                       # restored over the cap


def test_status_rows_and_refusal_text():
    dr = HD.draining_from_status({"intel1": 250}, {"intel1": {"scratch_gb": 100}, "localhost": {"scratch_gb": 1275}}, hub="intel2")
    assert dr == {"intel1": (100, 250)}
    msg = HD.refusal(["intel1"], dr, ["epyc2", "intel1", "epyc10"])
    assert "intel1 DRAINING (100 of 250 GB scratch free)" in msg and "--hosts epyc2,epyc10" in msg


def test_load_caps_hub_file_then_cache(tmp_path, monkeypatch):
    kw = tmp_path / "kit_wave.json"
    kw.write_text(json.dumps(CFG))
    monkeypatch.setattr(HD, "KIT_WAVE_JSON", str(kw))
    assert HD.load_caps() == {"intel1": 250, "epyc9": 300}
    monkeypatch.setattr(HD, "KIT_WAVE_JSON", str(tmp_path / "none.json"))
    monkeypatch.setattr(HD, "CACHE", str(tmp_path / "c/drain.json"))
    calls = []
    fetch = lambda: (calls.append(1), json.dumps(CFG))[1]
    assert HD.load_caps(now=1000, fetch=fetch) == {"intel1": 250, "epyc9": 300}
    assert HD.load_caps(now=1100, fetch=fetch) == {"intel1": 250, "epyc9": 300} and len(calls) == 1      # cached
    assert HD.load_caps(now=5000, fetch=lambda: "") == {"intel1": 250, "epyc9": 300}                    # fetch failed: stale cache
