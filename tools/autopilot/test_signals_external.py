"""STOPPED-OUTSIDE-1630: a signal sent to the job's ot-run client by another process makes the row CANCELLED, not an OOM resubmit."""
import datetime
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import autopilot as AP  # noqa: E402

P = "/srv/x/items/t1/attempt_2"
LINE = "2026-11-20T17:41:31-0800 signal 15 from pid 3626508 (/usr/lib/systemd/systemd --user; parent 1 (init)) -> ot-run pid 1819787 host intel1 tag otrun-a-1 WAITING dir %s"
T = datetime.datetime(2026, 11, 20, 17, 41, 31, tzinfo=datetime.timezone(datetime.timedelta(hours=-8))).timestamp()


def run(tmp_path, monkeypatch, lines, started, now, path=P):
    f = tmp_path / "signals.log"
    f.write_text("\n".join(lines) + "\n")
    monkeypatch.setattr(AP, "OT_RUN_SIGNALS", f)
    return AP.signals_external({"path": path, "started": started}, now=now)


def test_outside_signal_to_the_clients_dir_is_found(tmp_path, monkeypatch):
    assert run(tmp_path, monkeypatch, [LINE % P], T - 600, T + 5)
    assert run(tmp_path, monkeypatch, [(LINE % P) + ": reason"], T - 600, T + 5)


def test_other_dir_older_attempt_and_earlyoom_do_not_count(tmp_path, monkeypatch):
    assert run(tmp_path, monkeypatch, [LINE % (P + "0")], T - 600, T + 5) is None
    assert run(tmp_path, monkeypatch, [LINE % P], T + 1000, T + 2000) is None
    assert run(tmp_path, monkeypatch, [(LINE % P).replace("systemd --user", "earlyoom")], T - 600, T + 5) is None
    assert AP.signals_external({"started": 1}) is None
