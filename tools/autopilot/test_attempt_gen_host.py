import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as K


def test_attempt_gen_host_prefers_the_record_then_spec_then_kit_then_die(tmp_path):
    cfg = {"dies": {"d": {"gen_host": "epyc9"}}}
    assert K.attempt_gen_host(cfg, "d", {"gen_host": "epyc10"}) == "epyc10"
    (tmp_path / "spec.json").write_text(json.dumps({"gen_host": "epyc8"}))
    assert K.attempt_gen_host(cfg, "d", {"dir": str(tmp_path)}) == "epyc8"
    assert K.attempt_gen_host(cfg, "d", {"dir": str(tmp_path / "none"), "kit": "epyc7:/srv/x"}) == "epyc7"
    assert K.attempt_gen_host(cfg, "d", {}) == "epyc9"
