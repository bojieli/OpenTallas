"""FABLE-FLOW-0230 T1: kit_wave.json min_rt is enforced for NEW launches (private-spec, ot-build bind); a declared exemption is recorded."""
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rt_floor as RTF      # noqa: E402


@pytest.fixture
def rt(tmp_path):
    for sha, made in (("aaaaaaaaaaaa1111", "2026-11-21T20:00:00-08:00"), ("6d2e187f0d65aaaa", "2026-11-22T01:26:38-08:00"),
                      ("bbbbbbbbbbbb2222", "2026-11-22T02:40:00-08:00")):
        (tmp_path / f"{sha[:12]}.manifest.json").write_text(json.dumps({"sha": sha, "made": made}))
        (tmp_path / sha[:12]).mkdir()
    (tmp_path / "current").symlink_to(tmp_path / "bbbbbbbbbbbb")
    return tmp_path


def test_below_refused_with_repin(rt):
    r = RTF.check("aaaaaaaaaaaa1111", {"min_rt": "6d2e187f0d"}, rt_root=rt, what="private-spec s81/x")
    assert r["verdict"] == "BELOW" and "--rt bbbbbbbbbbbb" in r["why"] and "--rt-floor-exempt" in r["why"]


def test_at_or_above_ok_and_exempt_recorded(rt):
    assert RTF.check("6d2e187f0d65aaaa", {"min_rt": "6d2e187f0d"}, rt_root=rt)["verdict"] == "OK"
    assert RTF.check("bbbbbbbbbbbb2222", {"min_rt": "6d2e187f0d"}, rt_root=rt)["verdict"] == "OK"
    r = RTF.check("aaaaaaaaaaaa1111", {"min_rt": "6d2e187f0d"}, exempt="sealed J7 pin", rt_root=rt)
    assert r["verdict"] == "EXEMPT" and "sealed J7 pin" in r["why"]


def test_unknown_and_no_floor_never_refuse(rt, monkeypatch):
    monkeypatch.delenv("OT_MIN_RT", raising=False)
    assert RTF.check("cccccccccccc", {"min_rt": "6d2e187f0d"}, rt_root=rt)["verdict"] == "UNKNOWN"
    assert RTF.check("aaaaaaaaaaaa", {}, rt_root=rt)["verdict"] == "NO-FLOOR"
    (rt / "MIN_RT").write_text("6d2e187f0d65\n")
    assert RTF.check("aaaaaaaaaaaa", {}, rt_root=rt)["verdict"] == "BELOW"          # the rt root's MIN_RT file (gen hosts)


def test_ot_build_bind_refuses_below_floor(rt, tmp_path, monkeypatch):
    import ot_build as OB
    monkeypatch.setenv("OT_MIN_RT", "6d2e187f0d")
    monkeypatch.setattr(OB, "rt_resolve", lambda r: (rt / "aaaaaaaaaaaa", "aaaaaaaaaaaa"))
    tree = tmp_path / "tree"
    tree.mkdir()

    class A:
        tree = str(tmp_path / "tree"); plan = str(tmp_path / "p.json"); asbuilt = None; rt = "aaaaaaaaaaaa"; env = []; remap_base = None
        out_root = str(tmp_path / "o"); status = False; dry = False; rt_floor_exempt = ""
    with pytest.raises(OB.G.BuildError) as e:
        OB.BindStage(A)
    assert "RT-FLOOR refused" in str(e.value)
