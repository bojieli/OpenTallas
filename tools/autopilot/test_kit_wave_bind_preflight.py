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
    def __init__(self, stale=(), error=None, sig="s1"):
        self.calls, self.stale, self.error, self.sig, self.sig_calls = [], set(stale), error, sig, 0

    def __call__(self, host, code, args, timeout=600):
        if code is KW.PROBE_BIND_SIG:                    # WAVE-TICK-1119: the cheap input signature, counted apart from the full probes
            self.sig_calls += 1
            return {"sig": self.sig}
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


def test_probe_error_fails_closed_and_opt_out():
    r = KW.bind_preflight(None, cfg(), {}, "kv", ROWS, now=1.0, rpy=Probe(error="boom"))
    assert r and all("BIND_PREFLIGHT_UNKNOWN" in v for v in r.values())
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


def test_probe_code_runs_the_source_kit_topology(tmp_path, monkeypatch):
    monkeypatch.setenv("OT_BIND_PROBE_RT", str(tmp_path / "no_rt"))      # no rt copy on this host: the die src tree is used
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


def test_verdict_stands_while_inputs_are_unchanged_and_is_reprobed_when_they_change():
    # WAVE-TICK-1119 (COORD 2): no 30-min re-probe; a 5-min signature check; a changed signature runs the full probe again
    p, st = Probe(stale={("/b/vD", "t_old")}), {}
    KW.bind_preflight(None, cfg(), st, "kv", ROWS, now=100.0, rpy=p)
    assert len(p.calls) == 2
    t = 100.0 + KW.BIND_PREFLIGHT_TTL_S - 10
    for i in range(1, 4):                                # 3 later ticks, hours later, same inputs
        KW.bind_preflight(None, cfg(), st, "kv", ROWS, now=100.0 + i * 3600, rpy=p)
    assert len(p.calls) == 2 and p.sig_calls >= 2 + 2 * 3     # 2 signatures at fill, one per group per later check
    n = p.sig_calls
    KW.bind_preflight(None, cfg(), st, "kv", ROWS, now=100.0 + 3600 + 10, rpy=p)           # inside the 5-min recheck window: not even a signature
    assert p.sig_calls == n and len(p.calls) == 2
    p.sig = "s2"                                                                          # the plan / bind / kit_topology.py changed
    out = KW.bind_preflight(None, cfg(), st, "kv", ROWS, now=100.0 + 5 * 3600, rpy=p)
    assert len(p.calls) == 4 and list(out) == ["t_old"]


def test_unreadable_signature_probe_forces_the_full_probe():
    p, st = Probe(), {}
    KW.bind_preflight(None, cfg(), st, "kv", ROWS, now=100.0, rpy=p)
    p2 = lambda host, code, args, timeout=600: {"error": "x"} if code is KW.PROBE_BIND_SIG else Probe()(host, code, args, timeout)
    KW.bind_preflight(None, cfg(), st, "kv", ROWS, now=100.0 + 1000, rpy=p2)
    assert len(p.calls) == 2                                                               # p itself not asked again; the fallback probe ran through p2


def test_detached_probe_pends_then_reads_the_result(tmp_path):
    """PROBE-DETACH-1122: with KW_DETACH_PROBES the tick never waits on the bind probe; a unit writes the result, the next tick reads it"""
    import json as _j
    import kit_wave as K

    class AP:
        KW_DETACH_PROBES, DRY, AP_DIR = True, False, tmp_path
        units, logs = [], []

        def launch_unit(self, unit, logf, argv):
            self.units.append((unit, argv))
            return True

        def unit_active(self, unit):
            return True

        def log(self, m):
            self.logs.append(m)
    ap = AP()
    assert K.bind_probe_detached(ap, "epyc10", {"types": ["t"]}, 1000.0) is None and len(ap.units) == 1
    assert K.bind_probe_detached(ap, "epyc10", {"types": ["t"]}, 1001.0) is None and len(ap.units) == 1   # running: not started twice
    req = ap.units[0][1][-1]
    rq = _j.loads(open(req).read())
    open(rq["out"], "w").write(_j.dumps({"stale": [], "relay": {}}))
    assert K.bind_probe_detached(ap, "epyc10", {"types": ["t"]}, 1002.0) == {"stale": [], "relay": {}}
