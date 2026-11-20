"""GIT-MIRROR-1119: a rejected lane-ref update is a warning, any other fetch error still fails the unit."""
import importlib.machinery, importlib.util, pathlib
H = pathlib.Path(__file__).parent
ld = importlib.machinery.SourceFileLoader("gm", str(H / "ot-git-mirror"))
M = importlib.util.module_from_spec(importlib.util.spec_from_loader("gm", ld)); ld.exec_module(M)


def test_rejected_lane_ref_is_not_fatal_but_main_or_other_errors_are():
    ok = "From github.com:bojieli/OpenTallas\n ! [rejected]                claude/x-1117 -> claude/x-1117  (non-fast-forward)\n"
    assert M.only_rejected_updates(ok)
    assert not M.only_rejected_updates(ok + "fatal: unable to access 'x': Could not resolve host\n")
    assert not M.only_rejected_updates(" ! [rejected]                main -> main  (non-fast-forward)\n")
    assert not M.only_rejected_updates("")
