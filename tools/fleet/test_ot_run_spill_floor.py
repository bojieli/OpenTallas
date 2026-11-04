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
    assert m.spill_dst_full("epyc2", {"rootfs_free_gb": 291})
    assert not m.spill_dst_full("epyc2", {"rootfs_free_gb": 620})
    assert m.spill_dst_full("intel1", {"scratch_disk_gb": 92})
    assert m.spill_dst_full("localhost", {"scratch_disk_gb": 99})
    assert not m.spill_dst_full("epyc4", {"scratch_disk_gb": 40})      # no floor named
    assert not m.spill_dst_full("epyc2", {})                           # older probe: not refused


def test_off_root_lane_uses_scratch_floor():
    m = load()
    m.spill_lands_on_root = lambda host, roots: False
    assert not m.spill_dst_full("epyc2", {"rootfs_free_gb": 291, "scratch_disk_gb": 116}, ["/srv/opentallas-scratch2/claude/l/k"])
    assert m.spill_dst_full("epyc2", {"rootfs_free_gb": 291, "scratch_disk_gb": 60}, ["/srv/opentallas-scratch2/claude/l/k"])
    m.spill_lands_on_root = lambda host, roots: True
    assert m.spill_dst_full("epyc2", {"rootfs_free_gb": 291, "scratch_disk_gb": 116}, ["/srv/opentallas-scratch2/claude/l/k"])


def test_drop_stage_only_under_a_lane():
    m = load()
    calls = []
    m.ssh_sh = lambda h, c, timeout=0: calls.append(c) or type("R", (), {"stdout": "DROPPED"})()
    m.spill_drop_stage("epyc4", ["/srv/opentallas-scratch2/claude/l/k"])
    assert not calls                                   # not a --stage job
    m.STAGE.append("/srv/opentallas-scratch2/claude/l/k")
    m.spill_drop_stage("epyc4", ["/srv/opentallas-scratch2/claude/l", "/tmp/x", "/srv/opentallas-scratch2/claude/l/k"])
    assert len(calls) == 1 and "SIGNED" in calls[0] and ".ot-run-spill-copy" in calls[0]
