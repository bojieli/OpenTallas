import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW


def test_frozen_hosts_outside_the_current_gen_hosts_are_replaced(tmp_path):
    cfg = tmp_path / "kit_wave.json"
    cfg.write_text(json.dumps({"dies": {"kv": {"gen_hosts": ["epyc7", "epyc9"]}}}))
    sp = {"die": "kv", "hub": "intel2", "hosts": ["intel1", "intel2", "epyc7"], "place_prefer": ["intel1", "epyc7"], "roam_hosts": ["intel1", "epyc7"]}
    out = KW.repick_stage_hosts(sp, cfg)
    assert out["hosts"] == ["epyc7", "epyc9"] and out["place_prefer"] == ["epyc7"] and out["roam_hosts"] == ["epyc7"]
    assert sp["hosts"] == ["intel1", "intel2", "epyc7"]                       # the input is not mutated
    ok = {"die": "kv", "hub": "intel2", "hosts": ["epyc7"], "place_prefer": []}
    assert KW.repick_stage_hosts(ok, cfg) is ok
    assert KW.repick_stage_hosts(sp, tmp_path / "missing.json") is sp
