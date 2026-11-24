"""HEADSTOP-1124: ot-run --cancel runs the head's ot-heavy-stop on the host (inline), so a stale host rt cannot weaken a cancel."""
import importlib.machinery, importlib.util, pathlib, subprocess, types
H = pathlib.Path(__file__).parent
l = importlib.machinery.SourceFileLoader("ot_run_head_stop", str(H / "ot-run"))
RUN = importlib.util.module_from_spec(importlib.util.spec_from_loader("ot_run_head_stop", l)); l.exec_module(RUN)


def test_cancel_command_carries_the_head_copy(tmp_path):
    f = tmp_path / "ot-heavy-stop"
    f.write_text("import sys\nprint('ot-heavy-stop: HEAD', ' '.join(sys.argv[1:]))\n")
    c = RUN.head_stop_cmd("ot-heavy-stop --unit oth-a; ot-heavy-stop --tag t- >/dev/null 2>&1; echo x", path=str(f))
    assert "ot-heavy-stop --" not in c and c.count("ot_heavy_stop_head --") == 2
    out = subprocess.run(["bash", "-c", c], capture_output=True, text=True).stdout
    assert out.splitlines()[0] == "ot-heavy-stop: HEAD --unit oth-a" and out.splitlines()[-1] == "x"


def test_unrelated_or_unreadable_left_alone(tmp_path):
    assert RUN.head_stop_cmd("docker ps") == "docker ps"
    assert RUN.head_stop_cmd("ot-heavy-stop --unit u", path=str(tmp_path / "missing")) == "ot-heavy-stop --unit u"


def test_host_run_ships_the_real_head_copy(monkeypatch):
    seen = []
    RUN._host_run(lambda a, **k: (seen.append(a), types.SimpleNamespace(stdout="", stderr=""))[1], "epyc11", "ot-heavy-stop --unit oth-x")
    cmd = seen[0][-1]
    assert seen[0][0] == "ssh" and "ot_heavy_stop_head --unit oth-x" in cmd and "base64 -d" in cmd
    import base64, re
    b = re.search(r"printf %s (\S+) \| base64 -d", cmd).group(1)
    assert base64.b64decode(b) == pathlib.Path(RUN.HEAD_STOP).read_bytes()
