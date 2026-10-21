"""FLEET-NEW2 2026-10-19: new job dirs go to the run root (base or alt_bases) with the most free disk."""
import closure_loop as cl


def test_run_base_picks_freest(monkeypatch):
    cfg = dict(name="hx", base="/srv/a/claude/closure-loop", alt_bases=["/srv/b/claude/closure-loop"])
    monkeypatch.setattr(cl, "host_cfg", lambda n: cfg)

    class F:
        probe_cache = {}
    monkeypatch.setattr(cl, "FLEET_REF", None)
    assert cl.run_base("hx") == cfg["base"]                       # no fleet: the base
    monkeypatch.setattr(cl, "FLEET_REF", F)
    assert cl.run_base("hx") == cfg["base"]                       # no probe yet: the base
    F.probe_cache["hx"] = (0, dict(bases_gb={cfg["base"]: 500, cfg["alt_bases"][0]: 1800}))
    assert cl.run_base("hx") == cfg["alt_bases"][0]
    F.probe_cache["hx"] = (0, dict(bases_gb={cfg["base"]: 900, cfg["alt_bases"][0]: 900}))
    assert cl.run_base("hx") == cfg["base"]                       # tie: the base
    assert cl.host_bases(dict(base="/x")) == ["/x"]
