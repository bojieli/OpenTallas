"""D1 (FABLE-FLOW-0800): a DIED post of a kit_wave stage (X.live.log) waits for the stdout log X.log, which the caller writes after
ot-run exits; read too early it gave class=NO-PATTERN 'rc 1 after N s, no log' for 42 AUTO-GEOM FAIL deaths on 11-22."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ot_status as S  # noqa: E402


def _rec(tmp_path, rc=1):
    return {"kind": "run", "lane": "T", "rc": rc, "t_start": int(time.time()) - 100, "t_end": int(time.time()), "unit": "u", "name": "n",
            "host": "h", "cmd": "--mem 4 -- bash geom_check.sh", "log": str(tmp_path / "geom.live.log")}


def test_died_stage_post_is_deferred_and_waits_for_the_stdout_log(tmp_path, monkeypatch):
    rec = _rec(tmp_path)
    monkeypatch.setenv("OT_LANE", "T")
    monkeypatch.setattr(S, "enabled", lambda: True)
    started = []
    monkeypatch.setattr(S.subprocess, "Popen", lambda argv, **k: started.append(argv))
    argv = S.post(rec)
    assert argv[-2] == "deferred-post" and json.loads(argv[-1])["log"] == rec["log"]
    assert started == [argv]
    monkeypatch.setenv("OT_STATUS_DEFER", "0")
    assert S.deferred_post_argv(rec) is None
    monkeypatch.delenv("OT_STATUS_DEFER")
    assert S.deferred_post_argv(dict(rec, rc=0)) is None
    assert S.deferred_post_argv(dict(rec, log=str(tmp_path / "x.log"))) is None


def test_wait_returns_once_the_stdout_log_is_written(tmp_path):
    rec = _rec(tmp_path)
    (tmp_path / "geom.live.log").write_text("ot-run: RAN on epyc7 (unit u): exit 1\n")
    clock = [0.0]
    so = tmp_path / "geom.log"

    def sleep(dt):
        clock[0] += dt
        if clock[0] >= 3 and not so.exists():
            so.write_text("AP_AUTO_GEOM AUTO-GEOM FAIL t KIT-WAVE e 3_place fill=FAIL(0.01)\n")
    assert S.wait_stdout_log(rec, wait_s=30, sleep=sleep, now=lambda: clock[0]) is True
    assert 3 <= clock[0] < 30
    import ot_deathclass as D
    assert D.label(1, rec["cmd"], rec["log"], 100).startswith(" | class=GEOM-FAIL")


def test_wait_gives_up_after_the_bound(tmp_path):
    clock = [0.0]
    assert S.wait_stdout_log(_rec(tmp_path), wait_s=5, sleep=lambda dt: clock.__setitem__(0, clock[0] + dt), now=lambda: clock[0]) is False
    assert clock[0] >= 5


def test_deferred_post_cli_posts_the_classified_text(tmp_path):
    rec = _rec(tmp_path)
    (tmp_path / "geom.log").write_text("AP_AUTO_GEOM AUTO-GEOM FAIL t KIT-WAVE e 3_place fill=FAIL(0.01)\n")
    os.utime(tmp_path / "geom.log", (rec["t_end"] + 1, rec["t_end"] + 1))
    out = tmp_path / "posted.txt"
    post_sh = tmp_path / "post.sh"
    post_sh.write_text(f'printf "%s\\n" "$2" > {out}\n')
    env = dict(os.environ, OT_POST_SH=str(post_sh), OT_LANE="T", OT_STATUS_STDOUT_WAIT_S="5", OT_STATUS_POST="1", OT_STATUS_DIR=str(tmp_path / "st"))
    env.pop("OT_UNDER_TEST", None)
    r = subprocess.run([sys.executable, "-I", S.__file__, "deferred-post", json.dumps(rec)], env=env, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    deadline = time.time() + 20
    while not out.exists() and time.time() < deadline:
        time.sleep(0.2)
    assert "class=GEOM-FAIL" in out.read_text()
