import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import counted_view_canary as C  # noqa: E402


CFG = {"dies": {
    "qwen_compute": {"prov_view_sources": {
        "btab": [{"host": "intel2", "dir": "/v/btab", "job": "COUNTED btab x"}],
        "prog": [{"dir": "/v/prog", "counted": True}, {"dir": "/w/prog", "job": "COUNTED"}],
        "prov": [{"dir": "/v/prov", "job": "provisional only"}]}},
    "hbm": {"prov_view_sources": {"h": [{"dir": "/v/h", "job": "COUNTED"}]}}}}


def test_counted_sources_filters_job_and_die():
    s = C.counted_sources(CFG, {"qwen_compute"})
    assert s == {("qwen_compute", "btab"): ["/v/btab"], ("qwen_compute", "prog"): ["/v/prog", "/w/prog"]}
    assert ("hbm", "h") in C.counted_sources(CFG)


def test_missing_needs_one_live_copy_of_any_source():
    s = C.counted_sources(CFG, {"qwen_compute"})
    assert C.missing(s, {}) == [("qwen_compute", "btab"), ("qwen_compute", "prog")]
    assert C.missing(s, {("prog", "/w/prog"): {"epyc9"}}) == [("qwen_compute", "btab")]
    assert C.missing(s, {("prog", "/w/prog"): {"epyc9"}, ("btab", "/v/btab"): {"epyc8"}}) == []


def test_check_script_requires_all_three_files():
    for s in C.SUFFIXES:
        assert s in C.CHECK
