"""KV-BIND-REGEN-1 11-12: pre-submit KIT_TOPOLOGY_BIND_STALE check (same kit_topology.bind_matches as prepare-stations)."""
import json
import os
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


# BINDPROBE-FIX 11-24 (FABLE-FLOW-REVIEW-0750 (4): bf30ce94 re-ran 12x on epyc10, rc 0, nothing in its log, 12 QC + 6 KV rows waited)
def _bp_ap(tmp_path, active=True):
    class AP:
        KW_DETACH_PROBES, DRY, AP_DIR = True, False, tmp_path

        def __init__(self):
            self.units, self.logs, self.active = [], [], active

        def launch_unit(self, unit, logf, argv):
            self.units.append((unit, argv))
            return True

        def unit_active(self, unit):
            return self.active

        def log(self, m):
            self.logs.append(m)
    return AP()


def test_bindprobe_fix_consumed_result_is_kept_and_logged_and_a_lost_one_is_loud(tmp_path):
    ap = _bp_ap(tmp_path)
    assert KW.bind_probe_detached(ap, "h", {"types": ["t1", "t2"]}, 1000.0) is None
    rq = json.loads(open(ap.units[0][1][-1]).read())
    open(rq["out"], "w").write(json.dumps({"stale": ["t2"]}))
    assert KW.bind_probe_detached(ap, "h", {"types": ["t1", "t2"]}, 1001.0) == {"stale": ["t2"]}
    key = rq["out"].rsplit("/", 1)[-1][:-5]
    assert (tmp_path / "bind_probe" / f"{key}.done.json").exists()          # delivered, kept: a missing <key>.json is no lost result
    assert any("BIND-PROBE RESULT h" in m and "1 stale of 2" in m for m in ap.logs)
    # the verdict is dropped later and the probe starts again: no NO-RESULT for a delivered request
    ap.active = False
    assert KW.bind_probe_detached(ap, "h", {"types": ["t1", "t2"]}, 1002.0) is None and len(ap.units) == 2
    assert not any("NO-RESULT" in m for m in ap.logs)
    # that unit ends without writing anything: the next tick says so, then starts it again
    (tmp_path / "bind_probe" / f"{key}.log").write_text("AP_START 1 u\nAP_RC=0\n")
    assert KW.bind_probe_detached(ap, "h", {"types": ["t1", "t2"]}, 1003.0) is None and len(ap.units) == 3
    lost = [m for m in ap.logs if "BIND-PROBE NO-RESULT h" in m]
    assert len(lost) == 1 and "ended without writing" in lost[0] and "AP_RC=0" in lost[0]


def test_bindprobe_fix_worker_writes_a_result_or_fails_loudly(tmp_path, monkeypatch, capsys):
    import autopilot
    req = tmp_path / "k.req.json"
    out = tmp_path / "k.json"
    req.write_text(json.dumps({"host": "h", "args": {"types": ["a", "b"]}, "out": str(out)}))
    monkeypatch.setattr(autopilot, "rpy", lambda h, c, a, timeout=0: {"stale": ["b"]})
    assert KW.bind_probe_cmd(str(req)) == 0 and json.loads(out.read_text()) == {"stale": ["b"]}
    assert "BIND-PROBE RESULT h" in capsys.readouterr().out

    def boom(*a, **k):
        raise RuntimeError("ssh died")
    monkeypatch.setattr(autopilot, "rpy", boom)
    assert KW.bind_probe_cmd(str(req)) == 1 and "ssh died" in json.loads(out.read_text())["error"]
    assert "BIND-PROBE ERROR h" in capsys.readouterr().out
    req.write_text(json.dumps({"host": "h", "args": {"types": ["a"]}, "out": str(tmp_path / "no_such_dir" / "k.json")}))
    monkeypatch.setattr(autopilot, "rpy", lambda h, c, a, timeout=0: {"stale": []})
    assert KW.bind_probe_cmd(str(req)) == 3
    assert "BIND-PROBE NO-RESULT h" in capsys.readouterr().out


def test_bindprobe_fix_signature_ignores_a_republished_tool_with_the_same_bytes(tmp_path):
    rt1, rt2 = tmp_path / "rt1", tmp_path / "rt2"
    for r in (rt1, rt2):
        r.mkdir()
        (r / "kit_topology.py").write_text("X = 1\n")
    os.utime(rt2 / "kit_topology.py", (1, 1))
    (tmp_path / "plan.json").write_text("{}")
    (tmp_path / "bind").mkdir()
    a = {"src": str(tmp_path), "plan": str(tmp_path / "plan.json"), "bind_out": str(tmp_path / "bind")}

    def sig(rt):
        r = subprocess.run([sys.executable, "-I", "-", json.dumps(a)], input=KW.PROBE_BIND_SIG, capture_output=True, text=True,
                           env=dict(os.environ, OT_BIND_PROBE_RT=str(rt)))
        return json.loads(r.stdout.strip().splitlines()[-1][8:])["sig"]
    s1 = sig(rt1)
    assert s1 == sig(rt2)
    (rt2 / "kit_topology.py").write_text("X = 2\n")
    assert sig(rt2) != s1


def test_bindprobe_fix_probe_host_avoids_listed_hosts_and_sticks(tmp_path):
    c = cfg(gen_host="epyc10", gen_hosts=["epyc2", "intel1", "epyc10"])
    st = {}
    assert KW.bind_probe_host(c, "kv", st) == "epyc10"                       # no avoid list: unchanged
    c["bind_probe_avoid_hosts"] = ["epyc10"]
    st = {}
    assert KW.bind_probe_host(c, "kv", st) == "epyc2"
    st["bind_probe_host"]["kv"] = "intel1"
    assert KW.bind_probe_host(c, "kv", st) == "intel1"                       # sticky while allowed
    c["dies"]["kv"]["bind_probe_avoid_hosts"] = ["intel1"]
    assert KW.bind_probe_host(c, "kv", st) == "epyc2"
    c["dies"]["kv"]["_bind_probe_pin"] = "epyc10"                            # auto_rebind: the fresh bind's host wins
    assert KW.bind_probe_host(c, "kv", st) == "epyc10"
    # bind_preflight probes (and rechecks the signature) on that host
    c = cfg(gen_host="epyc10", gen_hosts=["epyc2", "epyc10"])
    c["bind_probe_avoid_hosts"] = ["epyc10"]
    hosts = []
    p = Probe()

    def rec(host, code, args, timeout=600):
        hosts.append(host)
        return p(host, code, args, timeout)
    KW.bind_preflight(None, c, {}, "kv", ROWS, now=100.0, rpy=rec)
    assert hosts and set(hosts) == {"epyc2"}
