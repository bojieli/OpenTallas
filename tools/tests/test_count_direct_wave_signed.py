"""FLOW-HEALTH-1 11-15 (FABLE-CENSUS-1815): a wave row that signed off (queue status SIGNED + q_signoff) is read directly by the count"""
import importlib.util
import json
import pathlib

spec = importlib.util.spec_from_file_location("rtp", str(pathlib.Path(__file__).resolve().parents[1] / "release_tree_plan.py"))
rtp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rtp)


def mk(tmp_path, items):
    (tmp_path / "autopilot").mkdir()
    (tmp_path / "lanes").mkdir()
    (tmp_path / "autopilot/kit_wave_state.json").write_text(json.dumps({"items": items}))
    rtp.COORD_DIR = tmp_path


def test_signed_wave_row_is_a_direct_read(tmp_path):
    mk(tmp_path, {"a": {"q_status": "SIGNED", "q_signoff": "/srv/x/signoff.json", "kit": "epyc7:/srv/x/kit"},
                  "b": {"status": "FAIL", "q_status": "FAIL", "q_signoff": "/srv/y/signoff.json", "kit": "epyc7:/srv/y/kit"},
                  "c": {"q_status": "SIGNED", "q_signoff": "/srv/z/signoff.json", "kit": "no-host-path"}})
    assert rtp.direct_paths() == {"epyc7": ["/srv/x/signoff.json"]}


def test_no_kit_wave_state_is_fine(tmp_path):
    (tmp_path / "lanes").mkdir()
    rtp.COORD_DIR = tmp_path
    assert rtp.direct_paths() == {}
