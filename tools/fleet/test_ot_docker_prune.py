import importlib.machinery, importlib.util, pathlib, sys, types
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "autopilot"))
import derive_gen_hosts as G
import block_raw_rm as B
p = pathlib.Path(__file__).with_name("ot-docker-prune")
m = importlib.machinery.SourceFileLoader("odp", str(p)).load_module()


def test_flow_images_are_never_removed():
    keep = m.keep_names()
    imgs = [("opentallas/orfs:asap7lock-grtoff", "A"), ("opentallas/orfs:asap7lock-grtT3", "A"), ("python:3", "B"), ("foo:1", "C"), ("used:1", "D")]
    rm, kept = m.plan(imgs, {"D"}, keep)
    assert rm == ["python:3", "foo:1"] and "opentallas/orfs:asap7lock-grtoff" in kept and "used:1" in kept


def test_a_second_tag_of_a_kept_id_is_kept():
    rm, kept = m.plan([("openroad/orfs:asap7lock", "X"), ("other:tag", "X")], set(), m.keep_names())
    assert rm == []


def test_prune_all_is_blocked():
    for c in ("docker image prune -af", "sudo docker image prune -a -f", "docker system prune --all -f"):
        assert B.blocked(c), c
    assert not B.blocked("docker image prune -f") and not B.blocked("docker image prune --filter until=24h")


def test_required_images_are_a_gen_host_requirement():
    assert "docker-image:opentallas/orfs:asap7lock-grtoff" in G.REQUIRES_DEFAULT and G.REQUIRES_DEFAULT[0].startswith("~/.local/opentallas-pdk")
    seen = []
    run = lambda cmd, **k: (seen.append(cmd[-1]), types.SimpleNamespace(returncode=0, stdout="MISSING 'docker-image:x:1'\n"))[1]
    assert G.host_requires("h", ("docker-image:x:1",), run=run) == ["docker-image:x:1"]
    assert "docker image inspect" in seen[0]
