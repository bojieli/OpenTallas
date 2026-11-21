"""DOCKERTO-1400: the reconcile never waits on a docker call that hangs; one wedged container is skipped, the rest still answer."""
import importlib.machinery, importlib.util, json, os, pathlib, pytest, stat, tempfile, time

P = str(pathlib.Path(__file__).with_name("ot-heavy-reconcile"))
loader = importlib.machinery.SourceFileLoader("recon_dockerto", P)
M = importlib.util.module_from_spec(importlib.util.spec_from_loader("recon_dockerto", loader))
loader.exec_module(M)


@pytest.fixture(autouse=True)
def _own_breaker(tmp_path, monkeypatch):
    monkeypatch.setattr(M, "BREAKER", str(tmp_path / "docker.broken"))      # DOCKERBREAKER-1630: never the host's real breaker file


def fake_docker(d, hang_id):
    p = os.path.join(d, "docker")
    open(p, "w").write("""#!/bin/sh
case "$1" in
  ps) echo aaa; echo %s; echo ccc ;;
  inspect) shift; for i in "$@"; do [ "$i" = "%s" ] && sleep 60; done; for i in "$@"; do echo "[{\\"Id\\": \\"$i\\"}]"; done ;;
esac
""" % (hang_id, hang_id))
    os.chmod(p, 0o755)


def test_hung_container_is_skipped_and_the_pass_returns(monkeypatch):
    with tempfile.TemporaryDirectory() as d:
        fake_docker(d, "bbb")
        monkeypatch.setenv("PATH", d + ":" + os.environ["PATH"])
        monkeypatch.setattr(M, "DOCKER_TIMEOUT_S", 2)
        monkeypatch.setattr(M, "DOCKER_ONE_S", 2)
        t = time.time()
        got = M.docker_inspect_all(["aaa", "bbb", "ccc"])
        assert time.time() - t < 15
        assert sorted(g["Id"] for g in got) == ["aaa", "ccc"]


def test_docker_cmd_times_out_with_124(monkeypatch):
    with tempfile.TemporaryDirectory() as d:
        fake_docker(d, "bbb")
        monkeypatch.setenv("PATH", d + ":" + os.environ["PATH"])
        t = time.time()
        rc, _ = M.docker_cmd("inspect", "bbb", t=1)
        assert rc == 124 and time.time() - t < 10
