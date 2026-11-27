"""P-LAUNCH-SETUP-FAIL: deep preflight (interpreter, syntax, imports) and the dry --check mode."""
import json
import subprocess
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

M = SourceFileLoader("ot_run_deep_pf", str(Path(__file__).with_name("ot-run"))).load_module()


def run_local(tmp, cmd, d=None):
    """the remote snippet, run here instead of over ssh"""
    r = subprocess.run([sys.executable, "-I", "-c", M.DEEP_PREFLIGHT_PY], input=json.dumps({"d": d, "cmd": cmd}), capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return M.deep_rows(r.stdout)


def test_clean_script_passes(tmp_path):
    (tmp_path / "a.py").write_text("import os, json\nprint(1)\n")
    assert run_local(tmp_path, ["python3", "-I", "a.py"], str(tmp_path)) == []


def test_syntax_error_and_missing_script_refuse(tmp_path):
    (tmp_path / "bad.py").write_text("def f(:\n")
    r = run_local(tmp_path, ["python3", "bad.py"], str(tmp_path))
    assert r and r[0][0] == "refuse" and "syntax error" in r[0][1]
    r = run_local(tmp_path, ["python3", "nope.py"], str(tmp_path))
    assert r and r[0][0] == "refuse" and "missing" in r[0][1]


def test_missing_interpreter_refuses(tmp_path):
    r = run_local(tmp_path, ["no-such-interp-xyz", "a.sh"], str(tmp_path))
    assert r[0][0] == "refuse" and "127" in r[0][1]


def test_unresolved_import_warns_sibling_import_does_not(tmp_path):
    (tmp_path / "sib.py").write_text("X = 1\n")
    (tmp_path / "m.py").write_text("import sib\nimport l0r_not_a_module_zz\n")
    r = run_local(tmp_path, ["python3", "m.py"], str(tmp_path))
    assert len(r) == 1 and r[0][0] == "warn" and "l0r_not_a_module_zz" in r[0][1] and "sib" not in r[0][1]


def test_missing_dir_skips_script_checks(tmp_path):
    assert run_local(tmp_path, ["python3", "a.py"], str(tmp_path / "later")) == []


def test_report_splits_refusals_and_warnings():
    fake = lambda host, d, cmd: [("refuse", "script x missing"), ("warn", "imports q")]
    M_setup = M.setup_preflight
    M.setup_preflight = lambda *a, **k: None
    try:
        ref, warn = M.preflight_report(["h1", "h2"], "/d", [], ["python3", "x.py"], deep=fake)
    finally:
        M.setup_preflight = M_setup
    assert ref == ["h1: script x missing"] and warn == ["h1: imports q"]


def test_unreachable_host_proves_nothing():
    def boom(*a, **k):
        raise OSError("ssh down")
    assert M.deep_preflight("h", "/d", ["python3", "x.py"], run=boom) == []
    assert M.deep_rows("garbage") == []


def test_abs_missing_shell_script_refuses(tmp_path):
    r = run_local(tmp_path, ["bash", str(tmp_path / "nope.sh")], str(tmp_path))
    assert r and r[0][0] == "refuse" and "NOT-RUN SETUP missing script" in r[0][1]
    r = run_local(tmp_path, ["bash", "-lc", "cd /x; bash /srv/zz_no_such/run.sh a"], str(tmp_path))
    assert r and "missing script /srv/zz_no_such/run.sh" in r[0][1]
    r = run_local(tmp_path, ["python3", str(tmp_path / "nope.txt")], str(tmp_path))
    assert r and "missing script" in r[0][1]


def test_abs_script_false_positives_stay_quiet(tmp_path):
    (tmp_path / "ok.sh").write_text("true\n")
    assert run_local(tmp_path, ["bash", str(tmp_path / "ok.sh")], str(tmp_path)) == []
    assert run_local(tmp_path, ["bash", "/etc/zz_not_under_dir.sh"], str(tmp_path)) == []
    assert run_local(tmp_path, ["bash", "rel.sh"], str(tmp_path)) == []
    f = str(tmp_path / "gen.sh")
    assert run_local(tmp_path, ["bash", "-c", "echo hi > %s; bash %s" % (f, f)], str(tmp_path)) == []
    assert run_local(tmp_path, ["bash", "-c", "cp /a/b.sh %s && bash %s" % (f, f)], str(tmp_path)) == []


R2 = "/srv/opentallas-scratch2/claude"
needs_r2 = __import__("pytest").mark.skipif(not Path(R2).is_dir(), reason="no scratch2 on this host")


def run_skip(tmp, cmd, d=None, skip=()):
    r = subprocess.run([sys.executable, "-I", "-c", M.DEEP_PREFLIGHT_PY], input=json.dumps({"d": d, "cmd": cmd, "skip": list(skip)}), capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return M.deep_rows(r.stdout)


@needs_r2
def test_missing_input_arg_and_flag_value_refuse(tmp_path):
    miss = R2 + "/zz_pf_x/input.json"
    r = run_local(tmp_path, ["python3", "-c", "pass", "--in", miss], str(tmp_path))
    assert r and r[0][0] == "refuse" and r[0][1] == "NOT-RUN SETUP missing input " + miss
    r = run_local(tmp_path, ["python3", "-c", "pass", "--cfg=" + miss], str(tmp_path))
    assert r and "missing input " + miss in r[0][1]
    r = run_local(tmp_path, ["bash", "-c", "cd /tmp && python3 x.py --in %s --n 3" % miss], str(tmp_path))
    assert r and "missing input " + miss in r[0][1]
    r = run_local(tmp_path, ["python3", "-c", "pass", R2 + "/zz_pf_missing_file.json"], str(tmp_path))
    assert r and "missing input" in r[0][1]          # parent exists, file does not


@needs_r2
def test_inputs_false_positives_stay_quiet(tmp_path):
    miss = R2 + "/zz_pf_x/input.json"
    here = str(tmp_path)
    q = lambda cmd: run_local(tmp_path, cmd, here)
    assert q(["python3", "-c", "pass", "--out", miss]) == []
    assert q(["python3", "-c", "pass", "--output=" + miss]) == []
    assert q(["python3", "-c", "pass", "--log", miss, "-o", miss]) == []
    assert q(["python3", "-c", "pass", "--out-dir", miss]) == []
    assert q(["bash", "-c", "echo hi > %s" % miss]) == []
    assert q(["bash", "-c", "echo hi >> %s; cat >> %s" % (miss, miss)]) == []
    assert q(["bash", "-c", "mkdir -p %s && cp a %s/f && python3 x.py --in %s/f" % (R2 + "/zz_pf_x", R2 + "/zz_pf_x", R2 + "/zz_pf_x")]) == []
    assert q(["bash", "-c", "tee %s < /dev/null; python3 x.py --in %s" % (miss, miss)]) == []
    assert q(["python3", "-c", "pass", R2 + "/zz_*/glob.json", "$HOME/x", "~/x", "https://h/srv/opentallas-scratch2/a"]) == []
    assert q(["python3", "-c", "pass", "/tmp/not_scratch/x.json"]) == []
    assert q(["python3", "-c", "pass", R2]) == []


@needs_r2
def test_missing_parent_under_dir_or_stage_skipped(tmp_path):
    under = str(tmp_path / "zz" / "in.json")
    # a path under --dir whose parent is missing (the job creates it) is quiet, and --dir absent here means spill / autostage copies it
    d2 = R2 + "/zz_pf_lane"
    assert run_local(tmp_path, ["python3", "-c", "pass", d2 + "/a/b.json"], d2) == []
    assert run_skip(tmp_path, ["python3", "-c", "pass", "--in", R2 + "/zz_pf_stage/in.json"], str(tmp_path), skip=[R2 + "/zz_pf_stage"]) == []
    r = run_skip(tmp_path, ["python3", "-c", "pass", "--in", R2 + "/zz_pf_stage/in.json"], str(tmp_path))
    assert r and "missing input" in r[0][1]            # parent missing and outside --dir: reported


def test_helpers_hint_and_skip_paths():
    assert M.abs_input_hint(["python3", "x.py", "--in", "/srv/opentallas-scratch2/a"])
    assert M.abs_input_hint(["bash", "-c", "cat /srv/opentallas-scratch/a"])
    assert not M.abs_input_hint(["python3", "x.py", "/tmp/a"])
    assert M.stage_skip_paths(["/srv/a", "h:/srv/b"], ["/srv/c"]) == ["/srv/a", "/srv/b", "/srv/c"]
