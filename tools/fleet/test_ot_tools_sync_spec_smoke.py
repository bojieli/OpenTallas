"""T1 (FABLE-FLOW-0800): rt/current flips only after a private-spec dry run on the new rt; red only when the previous rt passes it."""
import importlib.machinery
import importlib.util
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load():
    ld = importlib.machinery.SourceFileLoader("ot_tools_sync_ss", str(HERE / "ot-tools-sync"))
    spec = importlib.util.spec_from_loader("ot_tools_sync_ss", ld)
    m = importlib.util.module_from_spec(spec)
    ld.exec_module(m)
    return m


def setup(tmp_path):
    cfg = tmp_path / "kit_wave.json"
    cfg.write_text(json.dumps({"dies": {"qwen_compute": {"kit_rtl": {"bind_out": "/b/bind"}, "item_inputs": {"leaf__t1": {}, "a__t2": {"gen_tools_pin": {}}}}}}))
    for n in ("new", "old"):
        (tmp_path / "rt" / n).mkdir(parents=True)
    return cfg


def fake(results, calls):
    def runner(argv, timeout=None):
        calls.append(argv)
        root = Path(argv[2]).parents[2].name
        ok = results[root]
        if ok:
            out = Path(argv[argv.index("--out") + 1])
            (out / "spec.json").write_text("{}")
        return subprocess.CompletedProcess(argv, 0 if ok else 2, "", "" if ok else "private-spec: boom")
    return runner


def test_new_ok_flips_without_running_prev(tmp_path):
    M = load()
    cfg, calls = setup(tmp_path), []
    v, note = M.spec_smoke(tmp_path / "rt/new", tmp_path / "rt/old", cfg, fake({"new": True, "old": True}, calls))
    assert v == "ok" and len(calls) == 1
    a = calls[0]
    assert a[3:6] == ["private-spec", "qwen_compute", "leaf__t1"] and "--allow-bind-stale" in a and a[a.index("--bind-out") + 1] == "/b/bind"
    assert not list((tmp_path / "rt").glob(".rt-spec-smoke.*"))          # tmp out removed


def test_red_only_when_prev_passes(tmp_path):
    M = load()
    cfg = setup(tmp_path)
    v, note = M.spec_smoke(tmp_path / "rt/new", tmp_path / "rt/old", cfg, fake({"new": False, "old": True}, []))
    assert v == "red" and "boom" in note
    v, _ = M.spec_smoke(tmp_path / "rt/new", tmp_path / "rt/old", cfg, fake({"new": False, "old": False}, []))
    assert v == "infra"
    v, _ = M.spec_smoke(tmp_path / "rt/new", None, cfg, fake({"new": False}, []))
    assert v == "infra"
    v, _ = M.spec_smoke(tmp_path / "rt/new", None, tmp_path / "missing.json", fake({}, []))
    assert v == "infra"


def test_sync_red_spec_smoke_does_not_flip(tmp_path, monkeypatch):
    (tmp_path / "rt").mkdir()
    monkeypatch.setenv("OT_RT_ROOT", str(tmp_path / "rt"))
    M = load()
    M.RT = tmp_path / "rt"
    M.MQ = tmp_path / "mq"
    M.HOSTS, M.GEN_SMOKE_HOSTS = ["h1"], ["g1"]
    M.git = lambda *a, **k: "b" * 40
    M.current = lambda root=None: "aaaaaaaaaaaa"
    M.materialize = lambda full: M.RT / "bbbbbbbbbbbb"
    M.smoke = lambda d, tests=True: []
    M.host_sync = lambda *a, **k: (True, "ok")
    flips = []
    M.flip = lambda root, name: flips.append(name)
    M.spec_smoke = lambda new, prev: ("red", "passes on prev, fails on new")
    assert M.sync("x") == 3 and flips == []
    assert "spec smoke red" in (M.RT / "bbbbbbbbbbbb.smoke-failed").read_text()
