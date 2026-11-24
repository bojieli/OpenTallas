"""RT-HOST-DATA-1124 (COORD: epyc10 rt follow took 509-641 s on its saturated scratch NVMe): OT_RT_HOST_DATA puts a host's new
version dirs on another disk; RT/<sha12> there is a symlink to the copy, RT/current and the manifests keep their path, and
prune removes a symlinked version together with its data dir."""
import importlib.machinery, importlib.util, json, os, pathlib, subprocess, tempfile

P = str(pathlib.Path(__file__).with_name("ot-tools-sync"))


def load(env=None):
    old = dict(os.environ)
    os.environ.update(env or {})
    try:
        loader = importlib.machinery.SourceFileLoader("ots_hd", P)
        m = importlib.util.module_from_spec(importlib.util.spec_from_loader("ots_hd", loader)); loader.exec_module(m)
    finally:
        os.environ.clear(); os.environ.update(old)
    return m


def test_host_data_copy_lands_on_the_data_disk_and_rt_name_is_a_symlink(tmp_path, monkeypatch):
    rt, data = tmp_path / "rt", tmp_path / "data"
    rt.mkdir()
    m = load({"OT_RT_ROOT": str(rt), "OT_RT_HOST_DATA": f"h1={data} other=/x", "OT_RT_HOST_PATHS": "tools"})
    assert m.HOST_DATA == {"h1": str(data), "other": "/x"}
    name, prev = "a" * 12, "b" * 12
    (rt / f"{name}.manifest.json").write_text(json.dumps({"sha": "a" * 40, "made": "t", "files": {"tools/x.py": "0"}}))
    cmds = []

    class R:
        def __init__(self, out=""): self.returncode, self.stdout, self.stderr = 0, out, ""

    def fake_run(cmd, timeout=900, input=None, **k):
        c = " ".join(map(str, cmd)); cmds.append(c)
        if "echo HAVE" in c:
            return R("500G\n")
        if "python3 -I -c" in c:
            return R("[]\n")
        if "readlink current" in c:
            return R(name + "\n")
        return R()
    monkeypatch.setattr(m, "run", fake_run)
    monkeypatch.setattr(m, "MANIFEST_PY", "")
    ok, note = m._host_sync_unlocked("h1", name, prev)
    assert ok and note == "ok", note
    rs = [c for c in cmds if c.startswith("rsync")][0]
    assert f"--link-dest {data}/{prev}/" in rs and rs.endswith(f"h1:{data}/.{name}.partial/")
    inst = [c for c in cmds if "chmod -R a-w" in c][0]
    assert f"mv -T {data}/.{name}.partial {data}/{name}" in inst
    assert f"ln -sfn {data}/{name} {rt}/.{name}.lnk && mv -T {rt}/.{name}.lnk {rt}/{name}" in inst
    assert f"{rt}/{name}.manifest.json" in inst                  # manifest stays under RT
    flip = [c for c in cmds if "readlink current" in c][0]
    assert f"cd {rt} && ln -sfn {name} " in flip                  # current -> <sha12> as before
    # a host without a data dir is unchanged
    cmds.clear()
    ok, _ = m._host_sync_unlocked("h2", name, prev)
    rs = [c for c in cmds if c.startswith("rsync")][0]
    assert ok and rs.endswith(f"h2:{rt}/.{name}.partial/") and not any("ln -sfn" in c and ".lnk" in c for c in cmds)


def test_prune_removes_a_symlinked_version_and_its_data_dir(tmp_path):
    m = load()
    rt, data = tmp_path / "rt", tmp_path / "data"
    rt.mkdir(); data.mkdir()
    import uuid; names = sorted(uuid.uuid4().hex[:12] for _ in range(14))
    for i, n in enumerate(names):
        if i % 2:                                    # odd: on the data disk, RT/<n> is a symlink
            (data / n / "tools").mkdir(parents=True)
            os.symlink(data / n, rt / n)
        else:
            (rt / n / "tools").mkdir(parents=True)
        os.utime(rt / n, (1000 + i, 1000 + i), follow_symlinks=True)
        (rt / f"{n}.manifest.json").write_text("{}")
    os.symlink(names[-1], rt / "current")
    gone = m.prune_snapshots(rt, keep=m.MIN_KEEP, text="")
    assert gone and len(gone) == len(names) - max(m.MIN_KEEP, 1)
    for n in gone:
        assert not os.path.lexists(rt / n) and not (data / n).exists() and not (rt / f"{n}.manifest.json").exists()
    assert (rt / names[-1]).is_dir() and (data / names[-1]).is_dir()          # current stays (symlinked)
    assert os.readlink(rt / "current") == names[-1]


def _fake(m, monkeypatch, name, probe):
    cmds = []

    class R:
        def __init__(self, out=""): self.returncode, self.stdout, self.stderr = 0, out, ""

    def fake_run(cmd, timeout=900, input=None, **k):
        c = " ".join(map(str, cmd)); cmds.append(c)
        if "echo HAVE" in c:
            return R(probe)
        if "python3 -I -c" in c:
            return R("[]\n")
        if "readlink current" in c:
            return R(name + "\n")
        return R()
    monkeypatch.setattr(m, "run", fake_run)
    monkeypatch.setattr(m, "MANIFEST_PY", "")
    return cmds


def test_host_data_manifest_is_written_on_the_data_disk_and_linked(tmp_path, monkeypatch):
    """RT-HOST-DATA-MAN-1124 (epyc10 07:54 'install: cat: -: No space left on device'): only small symlinks are written under RT"""
    rt, data = tmp_path / "rt", tmp_path / "data"
    rt.mkdir()
    m = load({"OT_RT_ROOT": str(rt), "OT_RT_HOST_DATA": f"h1={data}", "OT_RT_HOST_PATHS": "tools"})
    name = "a" * 12
    (rt / f"{name}.manifest.json").write_text(json.dumps({"sha": "a" * 40, "made": "t", "files": {"tools/x.py": "0"}}))
    cmds = _fake(m, monkeypatch, name, "500G\n")
    ok, note = m._host_sync_unlocked("h1", name, "b" * 12)
    inst = [c for c in cmds if "chmod -R a-w" in c][0]
    assert ok and f"cat > {data}/.{name}.m.tmp && mv {data}/.{name}.m.tmp {data}/{name}.manifest.json" in inst
    assert f"cat > {rt}/" not in inst
    assert f"ln -sfn {data}/{name}.manifest.json {rt}/.{name}.ml && mv -T {rt}/.{name}.ml {rt}/{name}.manifest.json" in inst
    probe = [c for c in cmds if "echo HAVE" in c][0]
    assert f"test -f {data}/{name}.manifest.json && test -d {data}/{name} && echo DATA" in probe


def test_a_version_on_the_data_disk_without_rt_links_is_only_relinked(tmp_path, monkeypatch):
    rt, data = tmp_path / "rt", tmp_path / "data"
    rt.mkdir()
    m = load({"OT_RT_ROOT": str(rt), "OT_RT_HOST_DATA": f"h1={data}", "OT_RT_HOST_PATHS": "tools"})
    name = "c" * 12
    cmds = _fake(m, monkeypatch, name, "DATA\n")
    ok, note = m._host_sync_unlocked("h1", name, "b" * 12)
    assert ok and note == "ok", note
    assert not any(c.startswith("rsync") or "chmod -R a-w" in c for c in cmds)
    assert any(c.endswith(m.host_links(str(data), name)) for c in cmds)


def test_host_links_shell_really_makes_both_links(tmp_path):
    rt, data = tmp_path / "rt", tmp_path / "data"
    m = load({"OT_RT_ROOT": str(rt)})
    rt.mkdir(); data.mkdir()
    name = "d" * 12
    (data / name / "tools").mkdir(parents=True)
    (data / f"{name}.manifest.json").write_text('{"sha": "x"}')
    for _ in range(2):                                            # idempotent: a rerun replaces the links
        subprocess.run(["bash", "-c", m.host_links(str(data), name, rt)], check=True)
    assert os.path.islink(rt / name) and (rt / name / "tools").is_dir()
    assert json.loads((rt / f"{name}.manifest.json").read_text()) == {"sha": "x"}
    assert not [p for p in os.listdir(rt) if p.startswith(".")]


def test_prune_also_drops_the_data_disk_manifest(tmp_path):
    m = load()
    rt, data = tmp_path / "rt", tmp_path / "data"
    rt.mkdir(); data.mkdir()
    import uuid; names = sorted(uuid.uuid4().hex[:12] for _ in range(m.MIN_KEEP + 3))
    for i, n in enumerate(names):
        (data / n / "tools").mkdir(parents=True)
        os.symlink(data / n, rt / n)
        (data / f"{n}.manifest.json").write_text("{}")
        os.symlink(data / f"{n}.manifest.json", rt / f"{n}.manifest.json")
        os.utime(rt / n, (1000 + i, 1000 + i), follow_symlinks=True)
    os.symlink(names[-1], rt / "current")
    gone = m.prune_snapshots(rt, keep=m.MIN_KEEP, text="")
    assert gone
    for n in gone:
        assert not (data / f"{n}.manifest.json").exists() and not os.path.lexists(rt / f"{n}.manifest.json")
    assert (data / f"{names[-1]}.manifest.json").exists()
