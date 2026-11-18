"""FLEET-OPS-R 11-17: flow images are pinned and never pulled (epyc7: unpinned openroad/orfs:latest pulled an upstream image, 6 svc cores died)."""
import os, pathlib, subprocess, sys, types
H = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(H.parent / "autopilot"))
import derive_gen_hosts as G

PIN = "sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29"


def shim(tmp_path, *args, env=None):
    real = tmp_path / "realdocker"
    real.write_text("#!/bin/bash\nprintf '%s\\n' \"$@\"\n")
    real.chmod(0o755)
    e = dict(os.environ, OT_REAL_DOCKER=str(real), OT_DOCKER_PINS=str(H / "flow_images.txt"))
    e.update(env or {})
    r = subprocess.run(["bash", str(H / "ot-docker"), *args], capture_output=True, text=True, env=e, timeout=30)
    return r.returncode, r.stdout.split("\n")[:-1], r.stderr


def test_run_gets_pull_never_and_a_pinned_id_for_an_unpinned_tag(tmp_path):
    rc, out, _ = shim(tmp_path, "run", "--rm", "-v", "/a:/b", "openroad/orfs:latest", "bash", "-lc", "x")
    assert rc == 0 and out[:2] == ["run", "--pull=never"] and PIN in out and "openroad/orfs:latest" not in out
    assert out[out.index(PIN) + 1:] == ["bash", "-lc", "x"]


def test_bare_name_and_asap7lock_are_pinned_other_images_untouched(tmp_path):
    _, out, _ = shim(tmp_path, "run", "openroad/orfs", "true")
    assert PIN in out
    _, out, _ = shim(tmp_path, "run", "python:3", "true")
    assert "python:3" in out and "--pull=never" in out and PIN not in out


def test_an_explicit_pull_policy_is_respected_and_other_commands_pass_through(tmp_path):
    _, out, _ = shim(tmp_path, "run", "--pull=missing", "openroad/orfs:latest")
    assert "--pull=never" not in out and "--pull=missing" in out
    _, out, _ = shim(tmp_path, "images", "--no-trunc")
    assert out == ["images", "--no-trunc"]
    _, out, _ = shim(tmp_path, "ps", "-a")
    assert out == ["ps", "-a"]


def test_pulling_a_flow_image_is_refused_unless_deliberate(tmp_path):
    for img in ("openroad/orfs:latest", "opentallas/orfs:asap7lock-grtoff", "verilator/verilator:v5.032"):
        rc, out, err = shim(tmp_path, "pull", img)
        assert rc == 78 and "never pulled" in err and out == [], img
    assert shim(tmp_path, "pull", "alpine:3")[0] == 0
    assert shim(tmp_path, "pull", "openroad/orfs:latest", env={"OT_DOCKER_ALLOW_PULL": "1"})[0] == 0


def test_every_pin_is_a_gen_host_requirement_and_the_check_compares_ids():
    pins = G.pinned_images()
    assert ("openroad/orfs:latest", PIN) in pins
    for n, i in pins:
        assert "docker-id:%s=%s" % (n, i) in G.REQUIRES_DEFAULT
    seen = []
    run = lambda cmd, **k: (seen.append(cmd[-1]), types.SimpleNamespace(returncode=0, stdout="MISSING 'docker-id:openroad/orfs:latest=%s'\n" % PIN))[1]
    miss = G.host_requires("h", ("docker-id:openroad/orfs:latest=" + PIN,), run=run)
    assert miss == ["docker-id:openroad/orfs:latest=" + PIN] and "docker image inspect" in seen[0] and PIN in seen[0]


def test_no_launcher_pulls_a_flow_image():
    bad = []
    for p in (H.parent).rglob("*"):
        if p.suffix in (".py", ".sh") and p.is_file() and "test_" not in p.name and "evidence" not in p.parts:
            try:
                t = p.read_text(errors="ignore")
            except OSError:
                continue
            for ln in t.splitlines():
                if "docker pull" in ln and ("orfs" in ln or "verilator" in ln) and not ln.lstrip().startswith("#"):
                    bad.append("%s: %s" % (p.relative_to(H.parent), ln.strip()[:100]))
    assert not [b for b in bad if "ot-docker" not in b], bad
