"""DEATHCLASS-1122 (FLOW-DEATHCLASS-R1 via COORD): SSH-DROP host naming, RAIL-KILL pin fallback, SETUP preflight; FABLE-FLOW-0000 F2 cancel reason."""
import importlib.machinery, importlib.util, pathlib, subprocess
H = pathlib.Path(__file__).parent
l = importlib.machinery.SourceFileLoader("ot_run_dc", str(H / "ot-run"))
RUN = importlib.util.module_from_spec(importlib.util.spec_from_loader("ot_run_dc", l)); l.exec_module(RUN)

IPS = {"intel2": "185.8.106.226", "epyc8": "84.0.0.8", "epyc10": "84.0.0.10", "epyc2": "84.0.0.2"}


def test_self_alias_by_ssh_config_address(monkeypatch):
    monkeypatch.delenv("OT_RUN_SELF_ALIAS", raising=False)
    assert RUN.self_alias(["epyc2", "localhost", "epyc8"], ip_of=IPS.get, addrs={"84.0.0.8", "127.0.0.1"}) == "epyc8"
    assert RUN.self_alias(["epyc2", "localhost", "epyc8"], ip_of=IPS.get, addrs={"185.8.106.226"}) == "intel2"   # the hub alias is always a candidate
    assert RUN.self_alias(["epyc2", "localhost"], ip_of=IPS.get, addrs={"10.0.0.1"}) == ""                        # rtx-pro: no fleet alias


def test_canon_hosts_off_hub_and_on_hub():
    # epyc8: 'localhost' (which meant the hub only on the hub) is this machine; its alias is not listed twice
    assert RUN.canon_hosts(["epyc2", "localhost", "epyc8"], me="epyc8") == ["epyc2", "epyc8"]
    assert RUN.canon_hosts(["localhost"], me="epyc8") == ["epyc8"]
    # the hub: its alias is 'localhost' (HUB_SELF, HOST_RESERVE key)
    assert RUN.canon_hosts(["intel2", "epyc2"], me="intel2") == ["localhost", "epyc2"]
    assert RUN.canon_hosts(["localhost", "intel2"], me="intel2") == ["localhost"]
    # not a fleet machine: unchanged (drop_no_heavy refuses localhost there)
    assert RUN.canon_hosts(["localhost", "epyc2"], me="") == ["localhost", "epyc2"]


def test_probe_retries_transient_resolve(monkeypatch):
    calls = []

    def fake_run(argv, **kw):
        calls.append(argv)
        if len(calls) < 3:
            return subprocess.CompletedProcess(argv, 255, "", "ssh: Could not resolve hostname intel2: Temporary failure in name resolution")
        return subprocess.CompletedProcess(argv, 0, "NODIR\n", "")
    monkeypatch.setattr(RUN.subprocess, "run", fake_run)
    monkeypatch.setattr(RUN.time, "sleep", lambda s: None)
    assert RUN.probe("intel2", "/srv/x") == ("intel2", None)        # third try answered (NODIR)
    assert len(calls) == 3


def test_probe_does_not_retry_a_real_refusal(monkeypatch):
    calls = []

    def fake_run(argv, **kw):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 255, "", "Host key verification failed.")
    monkeypatch.setattr(RUN.subprocess, "run", fake_run)
    h, r = RUN.probe("epyc8", "/srv/x")
    assert len(calls) == 1 and "Host key verification failed" in r["error"]


def test_pin_fallback_once_and_strict(monkeypatch):
    monkeypatch.delenv("OT_RUN_STRICT_HOST", raising=False)
    monkeypatch.delenv("OT_RUN_HARD_PIN", raising=False)
    monkeypatch.setattr(RUN, "PIN_FALLBACK", [False])
    pool = ["epyc2", "intel1", "localhost", "epyc7", "epyc10"]
    monkeypatch.setenv("OT_RUN_SELF_ALIAS", "")
    fb = RUN.pin_fallback_pool(["epyc10"], {"epyc7": "held"}, ["true"], pool=pool)
    assert fb[0] == "epyc10" and "epyc7" not in fb and "epyc2" in fb
    assert RUN.pin_fallback_pool(["epyc10"], {}, ["true"], pool=pool) is None          # only once per client
    monkeypatch.setattr(RUN, "PIN_FALLBACK", [False])
    monkeypatch.setenv("OT_RUN_STRICT_HOST", "1")
    assert RUN.pin_fallback_pool(["epyc10"], {}, ["true"], pool=pool) is None          # --strict-host keeps the hard pin


def test_pin_fallback_skips_gate_hosts(monkeypatch):
    monkeypatch.delenv("OT_RUN_STRICT_HOST", raising=False)
    monkeypatch.setenv("OT_RUN_SELF_ALIAS", "")
    monkeypatch.setattr(RUN, "PIN_FALLBACK", [False])
    fb = RUN.pin_fallback_pool(["epyc10"], {}, ["ot-gate-remote", "x"], pool=["localhost", "intel2", "epyc2"])
    assert fb == ["epyc10", "epyc2"]


def test_strict_host_option_parses():
    src = (H / "ot-run").read_text()
    assert 'elif o == "--strict-host": os.environ["OT_RUN_STRICT_HOST"] = "1"' in src


def test_rel_script():
    assert RUN.rel_script(["python3", "-I", "colcap.py", "plan.json"]) == "colcap.py"
    assert RUN.rel_script(["python3", "-I", "-B", "tools/die_plan/gen.py", "x"]) == "tools/die_plan/gen.py"
    assert RUN.rel_script(["bash", "-c", "x.sh"]) is None
    assert RUN.rel_script(["python3", "-m", "pytest"]) is None
    assert RUN.rel_script(["python3", "/srv/a/b.py"]) is None          # absolute paths are the NEEDS check's
    assert RUN.rel_script(["make", "x.py"]) is None


def _probe(table):
    return lambda h, paths: {p: (p in table.get(h, set())) or (p == "/" and h in table) for p in paths}


def test_setup_preflight_refuses_missing_dir_and_script():
    tab = {"epyc8": {"/srv/s/claude/l/run"}, "epyc9": set()}
    why = RUN.setup_preflight(["epyc8", "epyc9"], "/srv/s/claude/l/run", [], ["python3", "-I", "solve.py"], probe=_probe(tab), local_exists=lambda p: False)
    assert why.startswith("SETUP: script /srv/s/claude/l/run/solve.py exists on none")
    why = RUN.setup_preflight(["epyc8"], "/srv/s/claude/l/gone", [], ["true"], probe=_probe(tab), local_exists=lambda p: False)
    assert "--dir /srv/s/claude/l/gone" in why
    assert RUN.setup_preflight(["epyc8"], "/srv/s/claude/l/gone", [], ["true"], probe=_probe(tab), check_dir=False) is None
    tab["epyc9"] = {"/srv/s/claude/l/run", "/srv/s/claude/l/run/solve.py"}
    assert RUN.setup_preflight(["epyc8", "epyc9"], "/srv/s/claude/l/run", [], ["python3", "solve.py"], probe=_probe(tab)) is None


def test_setup_preflight_stage_and_unreachable():
    tab = {"epyc8": {"/srv/s/claude/l/run"}}
    why = RUN.setup_preflight(["epyc8"], "/srv/s/claude/l/run", ["/srv/s/claude/l/in"], ["true"], probe=_probe(tab), local_exists=lambda p: False)
    assert "--stage path /srv/s/claude/l/in" in why
    assert RUN.setup_preflight(["epyc8"], "/srv/s/claude/l/run", ["/srv/s/claude/l/in"], ["true"], probe=_probe(tab),
                               local_exists=lambda p: p == "/srv/s/claude/l/in") is None       # staged from this machine
    assert RUN.setup_preflight(["epyc8"], "/x", [], ["true"], probe=lambda h, p: {x: False for x in p}) is None   # no host answered: no refusal


def test_cancel_reason_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(RUN, "CANCEL_REASON_DIR", str(tmp_path))
    RUN.note_cancel_reason([4242], "design", "pid 1")
    assert RUN.take_cancel_reason(4242) == "design"
    assert RUN.take_cancel_reason(4242) is None                 # consumed
    src = (H / "ot-run").read_text()
    assert "OT-RUN-CANCEL reason=" in src and 'reason={reason} by pid' in src


def test_main_wiring():
    src = (H / "ot-run").read_text()
    assert "_pf = setup_preflight(_have, d, STAGE, cmd, check_dir=False)" in src
    assert '_nod = [h for h in hosts if PLACE_NOTES.get(h) == "no " + str(d)]' in src


def test_pin_fallback_pool_names_this_machine_once(monkeypatch):
    monkeypatch.delenv("OT_RUN_STRICT_HOST", raising=False)
    monkeypatch.setenv("OT_RUN_SELF_ALIAS", "epyc9")
    monkeypatch.setattr(RUN, "PIN_FALLBACK", [False])
    assert RUN.pin_fallback_pool(["epyc10"], {}, ["true"], pool=["localhost", "epyc9", "epyc2"]) == ["epyc10", "epyc9", "epyc2"]
