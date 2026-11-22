"""host_caps: hand-set admission caps carry an owner and an expiry (FLOW-FLEET-R1, FABLE-FLOW-2200 H2)."""
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import host_caps as H

NOW = dt.datetime(2026, 11, 22, 6, 0, tzinfo=dt.timezone.utc)


def verdicts(text):
    return [(v, k, val) for v, k, val, *_ in H.scan(text, NOW)]


def test_off_caps_and_rails_are_not_flagged():
    t = "THREAD_CAP_FACTOR=0   # off\nLOAD_GATE_FACTOR=0\nINV_HEADROOM_GB=48\nSMALL_FLOOR_GB=36\n"
    assert verdicts(t) == []


def test_unowned_cap_is_flagged():
    t = "THREAD_CAP_FACTOR=1.0   # FLEET-EPYC7-R1 hand set\n"
    assert verdicts(t) == [("CAP-UNOWNED", "THREAD_CAP_FACTOR", "1.0")]


def test_owned_cap_ok_until_expiry_then_expired():
    t = ("#@cap LOAD_CAP_FACTOR owner=FLOW-FLEET-R1 expires=2026-11-23T06:00Z why=revert to 0\n"
         "LOAD_CAP_FACTOR=1.2   # note\n")
    assert verdicts(t) == [("CAP-OK", "LOAD_CAP_FACTOR", "1.2")]
    late = H.scan(t, NOW + dt.timedelta(days=2))
    assert late[0][0] == "CAP-EXPIRED" and late[0][3] == "FLOW-FLEET-R1"


def test_tag_must_sit_directly_above_its_key():
    t = ("#@cap LOAD_CAP_FACTOR owner=X expires=2026-11-23T06:00Z\n"
         "SMALL_JOB_GB=8\nLOAD_CAP_FACTOR=1.2\n")
    assert verdicts(t) == [("CAP-UNOWNED", "LOAD_CAP_FACTOR", "1.2")]


def test_tag_for_other_key_or_missing_expiry():
    assert verdicts("#@cap LOAD_CAP_FACTOR owner=X expires=2026-11-23T06:00Z\nTHREAD_CAP_FACTOR=1\n")[0][0] == "CAP-UNOWNED"
    assert verdicts("#@cap THREAD_CAP_FACTOR owner=X\nTHREAD_CAP_FACTOR=1\n")[0][0] == "CAP-BADTAG"
    assert verdicts("#@cap THREAD_CAP_FACTOR owner=X expires=2026-11-23T06:00\nTHREAD_CAP_FACTOR=1\n")[0][0] == "CAP-BADTAG"


def test_main_file_mode(tmp_path, capsys):
    f = tmp_path / "c"
    f.write_text("THREAD_CAP_FACTOR=1.0\n")
    assert H.main(["--file", str(f), "--now", "2026-11-22T06:00Z"]) == 0
    assert H.main(["--file", str(f), "--now", "2026-11-22T06:00Z", "--strict"]) == 1
    assert "HOST-CAPS 1 flagged" in capsys.readouterr().out.splitlines()[-1]
