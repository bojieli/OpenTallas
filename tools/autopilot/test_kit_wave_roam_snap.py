"""COORD r241: a roam stage is offered only to hosts that hold the kit's verified snapshot (the 4 QC kit_rtl FileNotFoundError fails)"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave_roam as R


class FakeOps:
    """each host is a directory under root; snapshots are dirs with a .verified marker once verify passed"""
    def __init__(self, root, fail=(), verify_fail=()):
        self.root, self.fail, self.verify_fail, self.calls = Path(root), set(fail), set(verify_fail), []

    def p(self, host, path):
        return self.root / host / path.lstrip("/")

    def size_mb(self, host, path):
        return 1

    def copy(self, src, dst, path, delete=True):
        s, d = self.p(src, path), self.p(dst, path)
        shutil.copytree(s, d, dirs_exist_ok=True)
        return 0, ""

    def ensure_snap(self, src, dst, sd, verify_cmd):
        self.calls.append(("snap", src, dst, sd))
        d = self.p(dst, sd)
        if (d / ".verified").exists():
            return 0, ""
        if dst in self.fail:
            return 255, "ssh: connect refused"
        shutil.copytree(self.p(src, sd), d, dirs_exist_ok=True, ignore=shutil.ignore_patterns(".verified"))
        if dst in self.verify_fail:
            return 3, "KW_KIT_SNAP_VERIFY mismatch"
        (d / ".verified").write_text("ok")
        return 0, ""


SD = "/store/snaps/" + "a" * 40


def setup(tmp, **kw):
    ops = FakeOps(tmp, **kw)
    W = "/w/att"
    ops.p("epyc8", W).mkdir(parents=True)
    (ops.p("epyc8", SD) / "root/plan").mkdir(parents=True)
    (ops.p("epyc8", SD) / "root/plan/p.json").write_text("{}")
    (ops.p("epyc8", SD) / ".verified").write_text("ok")
    return ops, W


def test_race_reproduced_without_snapshots_then_fixed(tmp_path):
    """the old behaviour: the host list had intel1 although it lacked the snapshot -> kit_rtl read a missing plan json"""
    ops, W = setup(tmp_path)
    r = R.Roamer(ops, W, "epyc8", ["intel1"])
    assert r.before("kit_rtl") == ["epyc8", "intel1"]
    assert not (ops.p("intel1", SD) / "root/plan/p.json").exists()          # the race: dispatched to a host without the snapshot
    r.snaps, r.snap_verify = [SD], (lambda sd: "verify " + sd)
    assert r.before("kit_rtl") == ["epyc8", "intel1"]
    assert (ops.p("intel1", SD) / "root/plan/p.json").exists() and (ops.p("intel1", SD) / ".verified").exists()


def test_snapshot_already_present_is_not_copied_again(tmp_path):
    ops, W = setup(tmp_path)
    r = R.Roamer(ops, W, "epyc8", ["intel1"]); r.snaps, r.snap_verify = [SD], (lambda sd: "v")
    r.before("a"); r.before("b")
    assert [c for c in ops.calls if c[0] == "snap"] and (ops.p("intel1", SD) / ".verified").exists()


def test_host_without_a_verified_snapshot_is_dropped_not_pinned(tmp_path):
    for kw in ({"fail": ["intel1"]}, {"verify_fail": ["intel1"]}):
        ops, W = setup(tmp_path / ("x" + next(iter(kw))), **kw)
        r = R.Roamer(ops, W, "epyc8", ["intel1", "epyc10"]); r.snaps, r.snap_verify = [SD], (lambda sd: "v")
        assert r.before("kit_rtl") == ["epyc8", "epyc10"]                     # intel1 dropped, epyc10 kept: still roaming
        assert any("intel1 dropped" in x for x in r.log)
