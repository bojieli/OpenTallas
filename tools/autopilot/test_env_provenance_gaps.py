"""FLOW-OPS-0900 (FABLE-FLOW-0745 g): ENV-PROVENANCE gaps -- a copied wave kit with an edited config.mk is hand-built (FAIL),
and a kit without a checker copy outside the kit wave is judged by the rt copy in run_kit.sh."""
import base64
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import env_provenance as EP      # noqa: E402

REC = {"source": "wave", "die": "s81", "item": "t", "env": {"OT_PGCAP": "1"}, "wave_env": {"OT_PGCAP": "1"}}


def _write(k, rec=REC):
    b = base64.b64encode(json.dumps(rec).encode()).decode()
    assert subprocess.run([sys.executable, "-I", EP.__file__, "write", str(k), "--b64", b], capture_output=True).returncode == 0


def _check(k):
    return subprocess.run([sys.executable, "-I", EP.__file__, "check", str(k)], capture_output=True, text=True)


def test_record_names_its_kit(tmp_path):
    k = tmp_path / "kit-wave" / "k"
    k.mkdir(parents=True)
    (k / "config.mk").write_text("export OT_PGCAP = 1\n")
    _write(k)
    assert json.loads((k / EP.RECORD).read_text())["kit"] == str(k)
    r = _check(k)
    assert r.returncode == 0 and "copied" not in r.stdout


def test_copied_wave_kit_with_config_edit_is_refused(tmp_path):
    src = tmp_path / "kit-wave" / "k"
    src.mkdir(parents=True)
    (src / "config.mk").write_text("export OT_PGCAP = 1\nexport OT_IO_HOLD = 1\n")
    _write(src)
    dst = tmp_path / "lanes" / "proof9"
    dst.mkdir(parents=True)
    (dst / EP.RECORD).write_text((src / EP.RECORD).read_text())
    (dst / "config.mk").write_text("export OT_PGCAP = 1\n")                # hand diff: OT_IO_HOLD dropped
    r = _check(dst)
    assert r.returncode == EP.REFUSE_RC and "copied wave kit" in r.stdout and "OT_IO_HOLD" in r.stdout
    (dst / "config.mk").write_text((src / "config.mk").read_text())       # plain copy: note only
    r = _check(dst)
    assert r.returncode == 0 and "kit copied from" in r.stdout


def test_edit_in_place_on_wave_kit_stays_a_note_and_old_records_unchanged():
    rec = dict(REC, config_ot={"OT_PGCAP": "1"}, kit="/srv/x/kit-wave/k")
    ok, lines = EP.judge(rec, "export OT_PGCAP = 2\n", kit_path="/srv/x/kit-wave/k")
    assert ok and any("NOTE" in ln for ln in lines)
    old = dict(REC, config_ot={"OT_PGCAP": "1"})                          # no "kit": written before FLOW-OPS-0900
    ok, lines = EP.judge(old, "export OT_PGCAP = 2\n", kit_path="/srv/y/lanes/k")
    assert ok
    ok, lines = EP.judge(dict(rec), "export OT_PGCAP = 2\n", kit_path="/srv/y/lanes/k", placed=True)
    assert ok and any("WARN" in ln for ln in lines)                       # a placed kit is never stopped


def test_run_kit_falls_back_to_rt_checker_outside_the_wave():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "die_plan"))
    import gen_phys
    rk = gen_phys.RUN_KIT
    assert 'env_provenance.py" check "$K"' in rk
    assert '"${K#*/kit-wave/}" = "$K"' in rk and "rt/current/tools}/autopilot/env_provenance.py" in rk
