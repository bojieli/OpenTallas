"""PLATEAU-ACT 11-25 (S81-ALLFIX-INT): an explicit `ot-run --cancel` of a stage client is final for EVERY stage (place was already); an admission refusal / ssh drop still retries."""
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
import autopilot as AP
import kit_wave as KW

OT = "/home/ubuntu/.local/bin/ot-run"
KIT = "/srv/x/lane/kit/gen/t1"
ARGV = [OT, "--dir", KIT, "--hosts", "epyc7", "--", "bash", "route.sh"]
T0 = 1_700_000_000


def signal_line(path, ts=T0 + 5, sender="ot-run --cancel"):
    t = datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S%z")
    return f"{t} signal 15 from pid 1 ({sender} 'x'): ot-run pid 9 dir {path}: x\n"


def with_signals(tmp_path, monkeypatch, text):
    f = tmp_path / "signals.log"
    f.write_text(text)
    monkeypatch.setattr(AP, "OT_RUN_SIGNALS", f)


def test_cancelled_client_is_final_even_though_it_never_printed_ran_on(tmp_path, monkeypatch):
    with_signals(tmp_path, monkeypatch, signal_line(KIT))
    txt = "ot-run: NOT RUN: no host qualifies (epyc7: terminated)"                 # what a cancelled waiter looks like: matches SSH_DROP
    act, cx = KW.stage_retry_decision(143, txt, ARGV, T0, OT, False, 0, 3)
    assert act == "cancel" and "ot-run --cancel" in cx


def test_the_clients_own_cancel_line_is_final_except_reason_infra(tmp_path, monkeypatch):
    with_signals(tmp_path, monkeypatch, "")
    assert KW.stage_retry_decision(143, "OT-RUN-CANCEL reason=design\nNOT RUN", ARGV, T0, OT, False, 0, 3)[0] == "cancel"
    assert KW.stage_retry_decision(143, "OT-RUN-CANCEL reason=hang", ARGV, T0, OT, False, 0, 3)[0] == "cancel"
    assert KW.stage_retry_decision(143, "OT-RUN-CANCEL reason=infra\not-run: NOT RUN: x", ARGV, T0, OT, False, 0, 3)[0] == "retry"


def test_admission_refusal_and_ssh_drop_still_retry_until_the_last_try(tmp_path, monkeypatch):
    with_signals(tmp_path, monkeypatch, "")
    for txt in ("ot-run: NOT RUN: no host qualifies (epyc7 load)", "kex_exchange_identification: Connection closed by remote host"):
        assert KW.stage_retry_decision(255, txt, ARGV, T0, OT, False, 0, 3)[0] == "retry"
        assert KW.stage_retry_decision(255, txt, ARGV, T0, OT, False, 3, 3)[0] == "done"            # no tries left
    assert KW.stage_retry_decision(0, "ot-run: NOT RUN", ARGV, T0, OT, False, 0, 3)[0] == "done"     # rc 0 is a result, not a drop


def test_other_kits_old_cancels_and_other_senders_do_not_stop_a_retry(tmp_path, monkeypatch):
    with_signals(tmp_path, monkeypatch, signal_line(KIT + "x") + signal_line(KIT, sender="other-tool") + signal_line(KIT, ts=T0 - 7200))
    assert KW.stage_retry_decision(255, "ot-run: NOT RUN: no host qualifies", ARGV, T0, OT, False, 0, 3)[0] == "retry"


def test_argv_without_dir_and_a_ran_stage_are_unchanged(tmp_path, monkeypatch):
    with_signals(tmp_path, monkeypatch, signal_line(KIT))
    assert KW.stage_cancelled(["bash", "-c", "x"], T0) is None
    with_signals(tmp_path, monkeypatch, "")
    assert KW.stage_retry_decision(1, "ot-run: RAN on epyc7\nNOT RUN", ARGV, T0, OT, False, 0, 3)[0] == "done"
