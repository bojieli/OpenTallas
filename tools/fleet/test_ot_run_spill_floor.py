"""KW-FIX-5: a spill destination below its disk floor receives no spill (ot-run SPILL_DST_FLOOR)."""
import importlib.machinery, importlib.util, pathlib


def load():
    p = str(pathlib.Path(__file__).resolve().parent / "ot-run")
    ld = importlib.machinery.SourceFileLoader("ot_run_spillfloor", p)
    m = importlib.util.module_from_spec(importlib.util.spec_from_loader(ld.name, ld))
    ld.exec_module(m)
    return m


def test_floor():
    m = load()
    assert m.spill_dst_full("epyc2", {"rootfs_free_gb": 149})          # root floor 150 (OWNER 11-06 22:4x)
    assert not m.spill_dst_full("epyc2", {"rootfs_free_gb": 151})
    assert m.spill_dst_full("intel1", {"scratch_disk_gb": 45})           # intel1 floor 50 (KW-FIX-42 11-09 COORD 08:5x)
    assert not m.spill_dst_full("intel1", {"scratch_disk_gb": 92})
    assert m.spill_dst_full("localhost", {"scratch_disk_gb": 99})
    assert not m.spill_dst_full("epyc4", {"scratch_disk_gb": 40})      # no floor named
    assert not m.spill_dst_full("epyc2", {})                           # older probe: not refused


def test_off_root_lane_uses_scratch_floor():
    m = load()
    m.spill_lands_on_root = lambda host, roots: False
    assert not m.spill_dst_full("epyc2", {"rootfs_free_gb": 100, "scratch_disk_gb": 141}, ["/srv/opentallas-scratch2/claude/l/k"])
    assert m.spill_dst_full("epyc2", {"rootfs_free_gb": 100, "scratch_disk_gb": 139}, ["/srv/opentallas-scratch2/claude/l/k"])
    m.spill_lands_on_root = lambda host, roots: True
    assert m.spill_dst_full("epyc2", {"rootfs_free_gb": 100, "scratch_disk_gb": 141}, ["/srv/opentallas-scratch2/claude/l/k"])


def test_drop_stage_only_under_a_lane():
    m = load()
    calls = []
    m.ssh_sh = lambda h, c, timeout=0: calls.append(c) or type("R", (), {"stdout": "DROPPED"})()
    m.spill_stage_protected = lambda r: False
    m.spill_drop_stage("epyc4", ["/srv/opentallas-scratch2/claude/l/k"])
    assert not calls                                   # not a --stage job
    m.STAGE.append("/srv/opentallas-scratch2/claude/l/k")
    m.spill_drop_stage("epyc4", ["/srv/opentallas-scratch2/claude/l", "/tmp/x", "/srv/opentallas-scratch2/claude/l/k"])
    assert len(calls) == 1 and "SIGNED" in calls[0] and ".ot-run-spill-copy" in calls[0]
    assert "-maxdepth" not in calls[0] and ".keep" in calls[0]
    calls.clear()
    m.spill_stage_protected = lambda r: True
    m.spill_drop_stage("epyc4", ["/srv/opentallas-scratch2/claude/l/k"])
    assert not calls                                   # a PROTECTED-DBS entry is never dropped


def _drop(tmp_path, setup):
    import shlex, subprocess
    m = load()
    r = tmp_path / "stage"
    r.mkdir()
    (tmp_path / "mark").touch()
    setup(r)
    out = subprocess.run(["sh", "-c", m.spill_drop_cmd(str(r), shlex.quote(str(tmp_path / "mark")), shlex.quote(str(r / "nomark")))],
                         capture_output=True, text=True).stdout
    return "DROPPED" in out, r.exists()


def _put(r, rel, txt=""):
    p = r / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(txt)


def test_drop_only_without_signed_or_keep_at_any_depth(tmp_path):
    (tmp_path / "a").mkdir(); (tmp_path / "b").mkdir(); (tmp_path / "c").mkdir(); (tmp_path / "d").mkdir()
    assert _drop(tmp_path / "a", lambda r: _put(r, "x/signoff.json", "FAILED")) == (True, False)
    assert _drop(tmp_path / "b", lambda r: _put(r, "K/eco_1/i2/signoff/signoff.json", "SIGNED")) == (False, True)
    assert _drop(tmp_path / "c", lambda r: _put(r, "a/b/c/d/.keep")) == (False, True)
    assert _drop(tmp_path / "d", lambda r: (_put(r, "a/signoff.json", "FAILED"), _put(r, "b/signoff.json", "SIGNED"))) == (False, True)


def test_protected_list_names_entry_child_or_parent(tmp_path, monkeypatch):
    m = load()
    d = tmp_path / "coord"; d.mkdir()
    (d / "PROTECTED-DBS.txt").write_text("intel1\t/srv/x/claude/a/b\tnote\nepyc2:/srv/x/claude/c note\n")
    monkeypatch.setattr(m.os.path, "expanduser", lambda p: str(tmp_path / p[2:]))
    assert m.spill_stage_protected("/srv/x/claude/a/b")
    assert m.spill_stage_protected("/srv/x/claude/a")
    assert m.spill_stage_protected("/srv/x/claude/c/k")
    assert not m.spill_stage_protected("/srv/x/claude/z")
    (d / "PROTECTED-DBS.txt").unlink()
    assert m.spill_stage_protected("/srv/x/claude/z")                  # unreadable list keeps the copy


def test_stage_eco_uses_lower_epyc2_scratch_floor():
    m = load()
    m.spill_lands_on_root = lambda host, roots: False
    r, eco, kit = ["/srv/opentallas-scratch2/claude/l/k"], ["python3 /x/eco_loop.py run --kit /k"], ["bash /x/run_kit.sh"]
    r60, r40 = {"rootfs_free_gb": 361, "scratch_disk_gb": 60}, {"rootfs_free_gb": 361, "scratch_disk_gb": 40}
    assert m.spill_dst_full("epyc2", r60, r, eco)                      # not a --stage job
    m.STAGE.append(r[0])
    assert not m.spill_dst_full("epyc2", r60, r, eco)
    assert m.spill_dst_full("epyc2", r40, r, eco)
    assert m.spill_dst_full("epyc2", r60, r, kit)
    assert m.spill_dst_full("intel1", r40, r, eco)                     # intel1 floor 50: 40 GB is full, 60 is not
    assert not m.spill_dst_full("intel1", r60, r, eco)
    m.spill_lands_on_root = lambda host, roots: True
    assert not m.spill_dst_full("epyc2", r60, r, eco)                  # root above its floor
    assert m.spill_dst_full("epyc2", {"rootfs_free_gb": 149, "scratch_disk_gb": 60}, r, eco)  # the root floor stays


def test_drop_keeps_a_copy_another_process_uses(tmp_path):
    """DIE-KV-65 11-04: a stage dir another running job also staged stays; once that job ends the copy goes."""
    import shlex, subprocess, time
    m = load()
    r = tmp_path / "lane" / "k"
    r.mkdir(parents=True)
    mk = tmp_path / "lane" / "mark"
    mk.write_text("")
    cmd = m.spill_drop_cmd(str(r), shlex.quote(str(mk)), shlex.quote(str(mk)))
    other = subprocess.Popen(["sh", "-c", f": {r}; sleep 30"])
    time.sleep(0.2)
    try:
        out = subprocess.run(["sh", "-c", cmd], capture_output=True, text=True).stdout
        assert "DROPPED" not in out and r.is_dir()
    finally:
        other.kill()
        other.wait()
    out = subprocess.run(["sh", "-c", cmd], capture_output=True, text=True).stdout
    assert "DROPPED" in out and not r.exists()
