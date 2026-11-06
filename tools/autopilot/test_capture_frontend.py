import kit_wave as KW


def config():
    return {"dies": {"s81_head": {"event": "test", "plan": "/plan.json", "src": "/source", "gen_host": "epyc5"}}}


def test_spec_captures_explicit_executable(tmp_path, monkeypatch):
    frontend = tmp_path / "immutable-230" / "ot-run"
    frontend.parent.mkdir()
    frontend.write_text("#!/bin/sh\nexit 0\n")
    frontend.chmod(0o755)
    cfg = config()
    cfg["ot_run"] = str(frontend)
    monkeypatch.setattr(KW, "OT_RUN", "/legacy/default")
    spec = KW.spec_for(cfg, "s81_head", "hd_spn", "intel2")
    assert spec["ot_run"] == str(frontend)
    cfg["ot_run"] = "/changed/later"
    assert spec["ot_run"] == str(frontend)


def test_spec_without_override_keeps_module_default(monkeypatch):
    monkeypatch.setattr(KW, "OT_RUN", "/legacy/default")
    assert KW.spec_for(config(), "s81_head", "hd_spn", "intel2")["ot_run"] == "/legacy/default"
