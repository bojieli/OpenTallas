"""FLOW-FLEET-R2 C2: submit ledger; --cancel resolves a job with no live client by dir, tag, pid or lane."""
import importlib.machinery, importlib.util, json, pathlib, subprocess
H = pathlib.Path(__file__).parent
l = importlib.machinery.SourceFileLoader("ot_run_led", str(H / "ot-run"))
RUN = importlib.util.module_from_spec(importlib.util.spec_from_loader("ot_run_led", l)); l.exec_module(RUN)


def test_ledger_write_and_find(tmp_path, monkeypatch):
    led = str(tmp_path / "l.jsonl")
    monkeypatch.setenv("OT_LANE", "FAM-X")
    r = RUN.ledger_write("/srv/opentallas-scratch2/claude/FAM-X/kit/", ["epyc8"], ["bash", "run.sh"], ledger=led, now=1000, pid=42, node="intel2")
    assert r["tag"] == "otrun-intel2-42-" and r["dir"] == "/srv/opentallas-scratch2/claude/FAM-X/kit"
    f = lambda s: RUN.ledger_find(s, ledger=led, now=2000)
    assert f("/srv/opentallas-scratch2/claude/FAM-X/kit") and f("otrun-intel2-42-") and f("42") and f("lane:FAM-X")
    assert not f("lane:OTHER") and not f("/srv/opentallas-scratch2/claude/FAM-X") and not f("otrun-intel2-4-")
    assert not RUN.ledger_find("42", ledger=led, now=1000 + 97 * 3600)          # older than the ledger window


def test_cancel_ledger_stops_the_tag_and_the_dir(tmp_path):
    led = str(tmp_path / "l.jsonl")
    RUN.ledger_write("/srv/opentallas-scratch2/claude/A/k", [], ["x"], ledger=led, pid=7, node="intel2")
    calls = []

    def run(argv, **kw):
        calls.append(argv[-1] if isinstance(argv, list) else argv)
        return subprocess.CompletedProcess(argv, 0, "ot-heavy-stop: containers stopped: 1\n", "")
    rc = RUN.cancel_ledger("/srv/opentallas-scratch2/claude/A/k", ledger=led, run=run, fleet=["epyc8"])
    assert rc == 0 and any("--tag otrun-intel2-7-" in c for c in calls)
    assert RUN.cancel_ledger("/srv/nothing", ledger=led, run=run, fleet=["epyc8"]) is None


def test_lane_selector_over_several_dirs_needs_all_dirs(tmp_path, capsys):
    led = str(tmp_path / "l.jsonl")
    RUN.ledger_write("/srv/opentallas-scratch2/claude/A/k1", [], ["x"], ledger=led, pid=1, node="n")
    RUN.ledger_write("/srv/opentallas-scratch2/claude/A/k2", [], ["x"], ledger=led, pid=2, node="n")
    import os
    os.environ["OT_LANE"] = "LA"
    RUN.ledger_write("/srv/opentallas-scratch2/claude/A/k3", [], ["x"], ledger=led, pid=3, node="n")
    RUN.ledger_write("/srv/opentallas-scratch2/claude/A/k4", [], ["x"], ledger=led, pid=4, node="n")
    os.environ.pop("OT_LANE")
    assert RUN.cancel_ledger("lane:LA", ledger=led, run=lambda *a, **k: subprocess.CompletedProcess(a, 0, "", ""), fleet=["h"]) == 2
    assert "REFUSED" in capsys.readouterr().out


def test_rotation_keeps_recent_lines(tmp_path, monkeypatch):
    led = tmp_path / "l.jsonl"
    led.write_text("\n".join(json.dumps({"ts": i, "tag": "t%d" % i, "pid": i, "dir": "", "lane": ""}) for i in range(30000)) + "\n" + "x" * (8 << 20))
    RUN.ledger_write("/srv/x", [], ["x"], ledger=str(led), pid=5, node="n")
    assert len(led.read_text().splitlines()) <= RUN.LEDGER_KEEP_LINES + 1
