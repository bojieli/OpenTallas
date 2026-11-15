"""WAVE-BALANCE-1: a kit-wave stage may run on any synced gen host, resumes from the synced checkpoint, pulls back home"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave_roam as R


class FakeOps:
    """each host is a directory under root; W is the same absolute-looking suffix on every host"""
    def __init__(self, root, fail=()):
        self.root, self.fail, self.calls = Path(root), set(fail), []

    def p(self, host, path):
        return self.root / host / path.lstrip("/")

    def size_mb(self, host, path):
        return sum(f.stat().st_size for f in self.p(host, path).rglob("*") if f.is_file()) // 2**20

    def copy(self, src, dst, path, delete=True):
        self.calls.append((src, dst, delete))
        if dst in self.fail or src in self.fail:
            return 255, "ssh: connect refused"
        s, d = self.p(src, path), self.p(dst, path)
        if delete and d.exists():
            shutil.rmtree(d)
        shutil.copytree(s, d, dirs_exist_ok=True)
        return 0, ""


def mk(tmp, **kw):
    ops = FakeOps(tmp, **kw)
    W = "/w/att"
    (ops.p("epyc9", W)).mkdir(parents=True)
    (ops.p("epyc9", W) / "stage1.out").write_text("kit_topology")
    return ops, W


def test_stage_moves_hosts_and_next_stage_resumes_from_synced_checkpoint(tmp_path):
    ops, W = mk(tmp_path)
    ro = R.Roamer(ops, W, "epyc9", ["epyc9", "epyc2", "epyc7", "localhost"], hub_names=("localhost", "intel2"))
    hs = ro.before("gen")
    assert hs == ["epyc9", "epyc2", "epyc7"]                      # home first, hub never, every other host synced
    for h in hs:
        assert (ops.p(h, W) / "stage1.out").read_text() == "kit_topology"
    # ot-run ran the gen stage on epyc2: it writes its output there
    (ops.p("epyc2", W) / "stage2.out").write_text("gen")
    ok, note = ro.after("gen", "ot-run: RAN on epyc2: x\n")
    assert ok and "copied back to epyc9" in note
    assert (ops.p("epyc9", W) / "stage2.out").read_text() == "gen"          # home holds the outputs
    # the next stage is offered every host again, all mirroring home (epyc7 never saw stage2 before this sync)
    hs = ro.before("gen_lint")
    assert (ops.p("epyc7", W) / "stage2.out").read_text() == "gen" and hs == ["epyc9", "epyc2", "epyc7"]
    (ops.p("epyc7", W) / "stage3.out").write_text("lint")
    assert ro.after("gen_lint", "ot-run: RAN on epyc7:\n")[0]
    assert (ops.p("epyc9", W) / "stage3.out").exists()


def test_stage_on_home_needs_no_pullback(tmp_path):
    ops, W = mk(tmp_path)
    ro = R.Roamer(ops, W, "epyc9", ["epyc2"])
    ro.before("gen")
    n = len(ops.calls)
    assert ro.after("gen", "ot-run: RAN on epyc9:\n") == (True, "") and len(ops.calls) == n


def test_failed_sync_drops_host_and_big_dir_or_no_others_pins_home(tmp_path):
    ops, W = mk(tmp_path, fail=["epyc2"])
    ro = R.Roamer(ops, W, "epyc9", ["epyc2", "epyc7"])
    assert ro.before("gen") == ["epyc9", "epyc7"] and any("epyc2 dropped" in x for x in ro.log)
    assert R.Roamer(ops, W, "epyc9", ["epyc9"]).before("gen") == ["epyc9"]
    assert R.Roamer(ops, W, "epyc9", ["epyc2"], enabled=False).before("gen") == ["epyc9"]
    (ops.p("epyc9", W) / "big").write_bytes(b"x" * 2**21)
    assert R.Roamer(ops, W, "epyc9", ["epyc7"], max_mb=1).before("gen") == ["epyc9"]


def test_pullback_failure_is_reported(tmp_path):
    ops, W = mk(tmp_path)
    ro = R.Roamer(ops, W, "epyc9", ["epyc2"])
    ro.before("gen")
    ops.fail.add("epyc9")
    ok, note = ro.after("gen", "ot-run: RAN on epyc2:\n")
    assert not ok and "KW_ROAM_PULLBACK_FAIL" in note


def test_roamargv_rewrites_hosts():
    a = R.RoamArgv(["ot-run", "--dir", "W", "--hosts", "epyc9", "--", "bash"])
    a.set_hosts(["epyc9", "epyc2"])
    assert a[a.index("--hosts") + 1] == "epyc9,epyc2" and isinstance(a, list)


def test_roam_note_is_never_the_decisive_line():
    # KITRTL-FAIL-1115: the copy-back note must not replace the stage error as the classified reason
    import kit_wave as K
    txt = ("usage: bind.py [-h]\nbind.py: error: unrecognized arguments: --src-tree /x/y\n"
           "ot-run: RAN on intel1 (unit u): exit 2\n\nKW_ROAM kit_rtl: ran on intel1, outputs copied back to epyc9\n")
    cls, why = K.classify("kit_rtl", txt)
    assert "unrecognized arguments" in why and "KW_ROAM" not in why
    assert K.classify("kit_rtl", txt)[1] == K.classify("kit_rtl", txt.replace("intel1", "epyc8"))[1]
