"""FLOW-OPS-0900 (COORD ruling for S81-J6-ASSEMBLY-R4): delta-apply --link never hardlinks outside the base tree's parent dir; private-spec
--tree refuses a linked lane tree there."""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import src_manifest as SM      # noqa: E402
import kit_wave as KW          # noqa: E402


def _base(tmp):
    b = tmp / "trees" / "src_s81_d1"
    (b / "rtl").mkdir(parents=True)
    (b / "rtl" / "a.sv").write_text("module a; endmodule\n")
    return b


def test_link_scope_rule():
    assert SM.link_outside_base("/srv/x/trees/src_d1", "/srv/x/trees/src_d2") == ""
    assert "outside the base tree's parent dir" in SM.link_outside_base("/srv/x/trees/src_d1", "/srv/x/claude/LANE/src_d2")


def test_shared_inodes_and_private_tree_refusal(tmp_path):
    b = _base(tmp_path)
    lane = tmp_path / "claude" / "LANE" / "src_s81_d1_mine"
    SM.link_tree(str(b), str(lane))                                   # what delta-apply --link used to make outside the base dir
    assert SM.inodes_shared_with(str(lane), str(b)) == ["rtl/a.sv"]
    why = KW.private_tree_link_refusal(str(b), str(lane))
    assert "shares inodes with the source of record" in why
    with pytest.raises(ValueError):
        raise ValueError(why) if why else None
    real = tmp_path / "claude" / "LANE" / "src_copy"
    import shutil
    shutil.copytree(b, real)
    assert KW.private_tree_link_refusal(str(b), str(real)) == ""     # a real copy anywhere is fine
    sib = tmp_path / "trees" / "src_s81_d2"
    SM.link_tree(str(b), str(sib))
    assert KW.private_tree_link_refusal(str(b), str(sib)) == ""      # a linked sibling next to the base is the published-tree form
    assert KW.private_tree_link_refusal(str(b), "/nonexistent/tree") == ""


def test_delta_apply_link_outside_base_makes_real_copy(tmp_path, monkeypatch, capsys):
    calls = []
    def fake_link(s, d):
        calls.append(("link", s, d))
        raise SystemExit("stop after the link choice")
    monkeypatch.setattr(SM, "link_tree", fake_link)
    def fake_run(argv, check=False, **k):
        calls.append(("cp", argv))
        raise SystemExit("stop after the copy choice")
    monkeypatch.setattr(SM.subprocess, "run", fake_run)
    monkeypatch.setattr(SM, "load_manifest", lambda t: {"manifest_hash": "h"})
    pack = tmp_path / "pack"
    pack.mkdir()
    (pack / "delta.json").write_text('{"old_manifest_hash": "h"}')
    b = _base(tmp_path)
    with pytest.raises(SystemExit):
        SM.delta_apply(str(pack), str(b), str(tmp_path / "claude" / "LANE" / "new"), link=True)
    assert calls[0][0] == "cp" and "--reflink=auto" in calls[0][1] and "REAL copy" in capsys.readouterr().out
    calls.clear()
    with pytest.raises(SystemExit):
        SM.delta_apply(str(pack), str(b), str(tmp_path / "trees" / "src_s81_d2"), link=True)
    assert calls[0][0] == "link"
