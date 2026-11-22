"""T1 (FABLE-FLOW-0800), driver side: a running attempt whose bind of record does not fit its tools rt (BIND-GEN-TOOLSKEW) switches to the
rt snapshot on the gen host whose generators fit the bind stamp, instead of FAIL.  bind_rt_cmd is the remote finder."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kit_wave as KW  # noqa: E402

BTS = HERE.parent / "die_plan" / "bind_tool_stamp.py"


def snap(root, name, anchor):
    d = Path(root) / name
    (d / "tools/die_plan").mkdir(parents=True)
    shutil.copy(BTS, d / "tools/die_plan/bind_tool_stamp.py")
    (d / "tools/die_plan/reset_anchor.py").write_text(anchor)
    return d


def stamp_bind(tmp_path, rt, sha=""):
    sys.path.insert(0, str(BTS.parent))
    import bind_tool_stamp as B
    b = tmp_path / "bind"
    rec = B.stamp(b, rt)
    if sha is not None:
        rec["tools_sha"] = sha
        (b / B.STAMP).write_text(json.dumps(rec))
    return b


def find(bind, root):
    r = subprocess.run(["bash", "-c", KW.bind_rt_cmd(bind, root)], capture_output=True, text=True, timeout=60)
    return r.returncode, r.stdout


def test_finds_the_snapshot_that_fits_the_bind_stamp(tmp_path):
    root = tmp_path / "rt"
    a = snap(root, "a" * 12, "v1")
    snap(root, "b" * 12, "v2")
    rc, out = find(stamp_bind(tmp_path, a, sha=""), root)
    assert rc == 0 and f"KW_BIND_RT {a} {'a' * 12}" in out


def test_named_sha_wins_and_no_fit_is_rc3(tmp_path):
    root = tmp_path / "rt"
    a = snap(root, "a" * 12, "v1")
    c = snap(root, "c" * 12, "v1")                     # same generators as a
    rc, out = find(stamp_bind(tmp_path, a, sha="c" * 12 + "0" * 28), root)
    assert rc == 0 and f"KW_BIND_RT {c} " in out
    shutil.rmtree(a); shutil.rmtree(c)
    snap(root, "b" * 12, "v2")
    rc, out = find(tmp_path / "bind", root)
    assert rc == 3 and "KW_BIND_RT_NONE" in out and "KW_BIND_RT " not in out
