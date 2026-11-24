"""STAGE-REFS-1124: a staged spill never runs against a tree that is missing / empty on the spill host (RELEC-R2 R7 / R11: m/lec.py)."""
import importlib.machinery, importlib.util, pathlib, types
import pytest
l = importlib.machinery.SourceFileLoader("ot_run_stage_refs", str(pathlib.Path(__file__).with_name("ot-run")))
m = importlib.util.module_from_spec(importlib.util.spec_from_loader(l.name, l)); l.exec_module(m)
L = "/srv/opentallas-scratch2/claude/RELEC-R2"
D = L + "/r/R7"
RUNSH = f"docker run -v {L}/k/refm:/work:ro -v {D}:/eco -v {L}/m:/m:ro img python3 -I /m/lec.py > {D}/lec.log"


def fake_ssh(states):
    """states: host -> {path: n}; the src grep returns the run.sh paths"""
    def ssh(host, cmd, timeout=120):
        if "xargs -0r grep" in cmd:
            return types.SimpleNamespace(stdout="\n".join(m.STAGE_REF_RE.findall(RUNSH)) + "\n", stderr="", returncode=0)
        if cmd.startswith("for p in") and "ls -A" in cmd:
            st = states[host]
            paths = [p for p in st] + [x for x in cmd.split("; do")[0].split()[2:] if x not in st]
            return types.SimpleNamespace(stdout="".join(f"{st.get(p, -1)} {p}\n" for p in paths), stderr="", returncode=0)
        return types.SimpleNamespace(stdout="", stderr="", returncode=0)
    return ssh


@pytest.fixture
def staged(monkeypatch):
    m.STAGE.clear(); m.STAGE.append(D)
    yield
    m.STAGE.clear(); m.AUTOSTAGED[0] = False


def test_refs_are_the_lane_paths_outside_the_stage(monkeypatch, staged):
    monkeypatch.setattr(m, "ssh_sh", fake_ssh({"epyc7": {L + "/k/refm": 1, L + "/m": 1}}))
    assert m.stage_outside_refs("epyc7", [D + "/run.sh"]) == {L + "/k/refm": 1, L + "/m": 1}


def plan(monkeypatch, states):
    monkeypatch.setattr(m, "ssh_sh", fake_ssh(states))
    monkeypatch.setattr(m, "spill_scan", lambda *a, **k: ([], 0.0, "", False, {L}))
    monkeypatch.setattr(m, "proof_away", lambda *a: False)
    monkeypatch.setattr(m, "spill_dest_rows", lambda h, r, b: [dict(ncpu=128, disk_gb=900)])
    for f in ("physically_capable",):
        monkeypatch.setattr(m, f, lambda *a: True)
    monkeypatch.setattr(m, "host_refusal", lambda *a: "")
    monkeypatch.setattr(m, "spill_dst_full", lambda *a: False)
    monkeypatch.setattr(m, "spill_room", lambda *a: (True, ""))
    monkeypatch.setattr(m, "drop_low_disk", lambda ok, *a, **k: ok)
    monkeypatch.setattr(m, "choose", lambda ok, *a: ("epyc2", False))
    monkeypatch.setattr(m, "log_signal", lambda s: None)
    monkeypatch.setattr(m, "HOSTS", ["epyc7", "epyc2"])
    return m._spill_plan("epyc7", D, [D + "/run.sh"], 64, 8, False, 20, set(), lambda s: None)


def test_autostage_with_outside_refs_is_refused(monkeypatch, staged):
    m.AUTOSTAGED[0] = True
    p, why, perm = plan(monkeypatch, {"epyc7": {L + "/k/refm": 1, L + "/m": 1}, "epyc2": {}})
    assert p is None and perm and "missing tree" in why


def test_explicit_stage_refused_when_dst_dir_is_empty_or_missing(monkeypatch, staged):
    p, why, perm = plan(monkeypatch, {"epyc7": {L + "/k/refm": 1, L + "/m": 1}, "epyc2": {L + "/m": 0}})
    assert p is None and "epyc2 lacks 2 path(s)" in why


def test_explicit_stage_spills_when_dst_has_the_refs(monkeypatch, staged):
    p, why, perm = plan(monkeypatch, {"epyc7": {L + "/k/refm": 1, L + "/m": 1}, "epyc2": {L + "/k/refm": 1, L + "/m": 1}})
    assert p and p[0] == "epyc2"
