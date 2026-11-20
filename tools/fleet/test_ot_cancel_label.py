"""CANCEL-LABEL-1120 (FLEET-WATCH-1015): a container is found and stopped by its ot.unit / ot.tag label, with no ot-run client; re-checked gone."""
import importlib.machinery, importlib.util, os, pathlib, subprocess, types
H = pathlib.Path(__file__).parent


def load(name, fn):
    l = importlib.machinery.SourceFileLoader(name, str(H / fn))
    m = importlib.util.module_from_spec(importlib.util.spec_from_loader(name, l)); l.exec_module(m); return m


RUN = load("ot_run_cl", "ot-run")
STOP = load("ot_heavy_stop_cl", "ot-heavy-stop")
ROWS = ["dpkit-a-1|oth-ubuntu-1-9|otrun-hub-111-5", "otc-2-3|oth-ubuntu-2-9|otrun-hub-1112-5", "plain|||", "dpkit-b-4|oth-ubuntu-1-9|otrun-hub-111-6"]


def test_labelled_selects_exact_unit_and_tag_prefix_only():
    assert STOP.labelled(ROWS, unit="oth-ubuntu-1-9") == ["dpkit-a-1", "dpkit-b-4"]
    assert STOP.labelled(ROWS, tag="otrun-hub-111-") == ["dpkit-a-1", "dpkit-b-4"]       # pid 1112 is not pid 111
    assert STOP.labelled(ROWS, unit="oth-ubuntu-1") == []                                   # a unit prefix is not the unit
    assert STOP.labelled(ROWS) == [] and STOP.labelled(ROWS, unit="", tag="") == []        # an empty selector selects nothing


def test_stop_labelled_stops_rechecks_and_kills_the_leftover(monkeypatch):
    calls, live = [], {"dpkit-a-1", "dpkit-b-4", "plain"}
    def sh(*a, timeout=120):
        return "\n".join(ROWS) if "--format" in a and STOP.LABEL_FMT in a else "\n".join(sorted(live))
    def run(argv, **k):
        calls.append(argv)
        if argv[1] == "stop" and argv[-1] == "dpkit-a-1": live.discard("dpkit-a-1")       # dpkit-b-4 ignores the stop
        if argv[1] == "kill": live.discard(argv[-1])
        return types.SimpleNamespace(stdout="", stderr="")
    monkeypatch.setattr(STOP, "sh", sh); monkeypatch.setattr(STOP.subprocess, "run", run)
    found, left = STOP.stop_labelled(unit="oth-ubuntu-1-9")
    assert found == ["dpkit-a-1", "dpkit-b-4"] and left == []
    assert ["docker", "kill", "dpkit-b-4"] in calls and ["docker", "kill", "dpkit-a-1"] not in calls
    assert "plain" in live and not any(c[-1] == "plain" for c in calls)


def test_dry_run_and_empty_selector_stop_nothing(monkeypatch):
    monkeypatch.setattr(STOP, "sh", lambda *a, **k: "\n".join(ROWS))
    monkeypatch.setattr(STOP.subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(AssertionError("stopped")))
    assert STOP.stop_labelled(unit="oth-ubuntu-1-9", dry=True)[0] == ["dpkit-a-1", "dpkit-b-4"]
    assert STOP.stop_labelled() == ([], [])


def test_container_stop_cmd_finds_a_labelled_container_with_no_matching_process(tmp_path):
    fake = tmp_path / "bin"; fake.mkdir(); log = tmp_path / "log"
    (fake / "ps").write_text("#!/bin/bash\necho '/usr/bin/other'\n")
    (fake / "docker").write_text("#!/bin/bash\necho \"$@\" >> " + str(log) + "\n"
        "case \"$1\" in ps) if [ \"$2\" = --format ]; then printf 'otc-2-3|otrun-hub-111-7\\nplain|\\nother|otrun-hub-1112-1\\n'; fi;; esac\n")
    for f in fake.iterdir(): f.chmod(0o755)
    out = subprocess.run(["bash", "-c", RUN.container_stop_cmd("otrun-hub-111-")], capture_output=True, text=True, env=dict(os.environ, PATH=str(fake) + ":" + os.environ["PATH"])).stdout
    lines = log.read_text().splitlines()
    assert "stop -t 30 otc-2-3" in lines and not any(l.endswith(" plain") or l.endswith(" other") for l in lines if l.startswith(("stop", "kill")))
    assert "containers stopped: otc-2-3" in out


def test_clientless_cancel_by_exact_unit_runs_ot_heavy_stop_on_every_host(monkeypatch, capsys):
    calls = []
    def run(cmd, **k):
        calls.append(cmd[-1]); h = cmd[-2]
        return types.SimpleNamespace(stdout="ot-heavy-stop: labelled containers stopped: dpkit-a-1\n" if h == "epyc9" else "ot-heavy-stop: labelled containers stopped: none\n", stderr="")
    monkeypatch.setattr(RUN, "clients", lambda: {}); monkeypatch.setattr(RUN, "log_signal", lambda m: None); monkeypatch.setattr(RUN, "HOSTS", ["epyc9", "epyc2"])
    monkeypatch.setattr(RUN.subprocess, "run", run)
    assert RUN.cancel("oth-ubuntu-1-9", False) == 0
    assert calls == ["ot-heavy-stop --unit oth-ubuntu-1-9"] * 2


def test_clientless_cancel_refuses_a_non_exact_selector_and_reports_a_survivor(monkeypatch):
    monkeypatch.setattr(RUN, "clients", lambda: {})
    assert RUN.cancel("dpkit", False) == 1 and RUN.cancel("oth-", False) == 1
    monkeypatch.setattr(RUN, "HOSTS", ["epyc9"]); monkeypatch.setattr(RUN, "log_signal", lambda m: None)
    monkeypatch.setattr(RUN.subprocess, "run", lambda cmd, **k: types.SimpleNamespace(stdout="ot-heavy-stop: STILL RUNNING after docker stop and kill: x\n", stderr=""))
    assert RUN.cancel("otrun-hub-111-", False) == 3
    monkeypatch.setattr(RUN.subprocess, "run", lambda cmd, **k: types.SimpleNamespace(stdout="ot-heavy-stop: labelled containers stopped: none\n", stderr=""))
    assert RUN.cancel("otrun-hub-111-", False) == 1


def test_docker_shim_and_ot_heavy_export_the_labels():
    shim = (H / "ot-heavy-docker").read_text(); heavy = (H / "ot-heavy").read_text()
    assert '--label=ot.unit=$OT_HEAVY_UNIT' in shim and '--label=ot.tag=$OT_HEAVY_TAG' in shim
    assert 'export OT_HEAVY_UNIT="$UNIT"; [ -n "$TAG" ] && export OT_HEAVY_TAG="$TAG"' in heavy
