"""KV-BIND-REGEN-1 11-12: pre-submit KIT_TOPOLOGY_BIND_STALE check (same kit_topology.bind_matches as prepare-stations)."""
import json
import subprocess
import sys

import kit_wave as KW


def cfg(**die):
    d = {"event": "e", "gen_host": "h", "src": "/s", "plan": "/p/vF.json",
         "kit_rtl": {"mode": "bind", "bind_out": "/b/vF2", "asbuilt": "/a.json"},
         "item_inputs": {"t_old": {"kit_rtl": {"bind_out": "/b/vD"}}}}
    d.update(die)
    return {"dies": {"kv": d}}


class Probe:
    def __init__(self, stale=(), error=None):
        self.calls, self.stale, self.error = [], set(stale), error

    def __call__(self, host, code, args, timeout=600):
        self.calls.append(args)
        if self.error:
            return {"error": self.error}
        return {"stale": [t for t in args["types"] if (args["bind_out"], t) in self.stale]}


ROWS = [{"item": "t_old"}, {"item": "t_new"}, {"item": "c", "kind": "core"}]


def test_item_override_on_old_bind_is_held_and_the_rest_launch():
    p, st = Probe(stale={("/b/vD", "t_old")}), {}
    out = KW.bind_preflight(None, cfg(), st, "kv", ROWS, now=100.0, rpy=p)
    assert list(out) == ["t_old"] and "KIT_TOPOLOGY_BIND_STALE" in out["t_old"] and "/b/vD" in out["t_old"]
    assert sorted(c["bind_out"] for c in p.calls) == ["/b/vD", "/b/vF2"]          # one probe per bind, core skipped
    assert all(c["plan"] == "/p/vF.json" and c["asbuilt"] == "/a.json" for c in p.calls)


def test_cached_until_ttl():
    p, st = Probe(stale={("/b/vD", "t_old")}), {}
    KW.bind_preflight(None, cfg(), st, "kv", ROWS, now=100.0, rpy=p)
    KW.bind_preflight(None, cfg(), st, "kv", ROWS, now=200.0, rpy=p)
    assert len(p.calls) == 2
    KW.bind_preflight(None, cfg(), st, "kv", ROWS, now=100.0 + KW.BIND_PREFLIGHT_TTL_S + 1, rpy=p)
    assert len(p.calls) == 4


def test_probe_error_fails_open_and_opt_out():
    assert KW.bind_preflight(None, cfg(), {}, "kv", ROWS, now=1.0, rpy=Probe(error="boom")) == {}
    p = Probe(stale={("/b/vD", "t_old")})
    assert KW.bind_preflight(None, cfg(bind_preflight=False), {}, "kv", ROWS, now=1.0, rpy=p) == {} and not p.calls
    assert KW.bind_preflight(None, cfg(canonical_topology_prepare=False), {}, "kv", ROWS, now=1.0, rpy=p) == {}
    c = cfg(); c["dies"]["kv"]["kit_rtl"]["mode"] = "script"; c["dies"]["kv"]["item_inputs"] = {}
    assert KW.bind_preflight(None, c, {}, "kv", ROWS, now=1.0, rpy=p) == {} and not p.calls


def test_reset_scope_is_forwarded():
    c = cfg(item_env={"t_new": {"OT_NATIVE_RESET_SCOPE": "selected"}})
    p = Probe()
    KW.bind_preflight(None, c, {}, "kv", [{"item": "t_new"}], now=1.0, rpy=p)
    assert p.calls[0]["scope"] == "selected"


def test_probe_code_runs_the_source_kit_topology(tmp_path):
    dp = tmp_path / "src" / "tools" / "die_plan"
    dp.mkdir(parents=True)
    (dp / "kit_topology.py").write_text(
        "import os\n"
        "def has_topology(raw, tn, ab=None):\n    return tn != 'flat'\n"
        "def bind_matches(raw, tn, out, ab=None, plan_path=None):\n"
        "    return tn == 'ok' or os.environ.get('OT_NATIVE_RESET_SCOPE') == 'selected'\n")
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({"partition_types": {"ok": {}, "bad": {}, "flat": {}}}))
    args = {"src": str(tmp_path / "src"), "plan": str(plan), "bind_out": "/b", "asbuilt": "",
            "types": ["ok", "bad", "flat", "absent"]}
    def run(a):
        r = subprocess.run([sys.executable, "-I", "-", json.dumps(a)], input=KW.PROBE_BIND, capture_output=True, text=True)
        return json.loads([ln for ln in r.stdout.splitlines() if ln.startswith("AP_JSON ")][-1][8:])
    assert run(args) == {"stale": ["bad"]}
    assert run(dict(args, scope="selected")) == {"stale": []}
    assert "error" in run(dict(args, plan=str(tmp_path / "missing.json")))
