"""COORD 11-17: no kit may carry a GRT stop (timecap / early stop); the current tree's own wrapper is clean, an old kit copy is refused."""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kit_preflight as KP

ROOT = HERE.parents[1]
OLD = """gstop=""
if [ "$POST_MAX" -gt 0 ]; then
    echo "OT_GRT_TIMECAP stage=grt post-route repair over 9 s"
    gstop=timecap
fi
"""


def test_old_kit_copy_and_config_are_refused(tmp_path):
    (tmp_path / "grt183_make.sh").write_text(OLD)
    err = KP.retired_grt_stop(tmp_path)
    assert len(err) == 1 and "retired GRT stop" in err[0] and "regenerate" in err[0]
    (tmp_path / "grt183_make.sh").write_text("# gstop=timecap was removed\necho ok\n")          # a comment is not a stop
    assert KP.retired_grt_stop(tmp_path) == []
    (tmp_path / "config.mk").write_text("export OT_GRT_POST_MAX_S = 600\nexport OT_GRT_STOP_X = 1\n")
    assert len(KP.retired_grt_stop(tmp_path)) == 2
    (tmp_path / "config.mk").write_text("export OT_GRT_POST_MAX_S = 0\n")                    # zero = the diagnostic is off
    assert KP.retired_grt_stop(tmp_path) == []


def test_the_current_wrapper_and_every_generator_are_clean():
    pat = KP.RETIRED_GRT_STOP
    bad = []
    for sub in ("tools", "physical"):
        for p in (ROOT / sub).rglob("*"):
            if not p.is_file() or p.suffix not in (".py", ".sh", ".tcl", ".mk") or p.name.startswith("test_") or p.name == "kit_preflight.py":
                continue
            for n, ln in enumerate(p.read_text(errors="replace").splitlines(), 1):
                if ln.strip() and not ln.lstrip().startswith("#") and re.search(r"gstop=timecap|echo \"OT_GRT_TIMECAP|export OT_GRT_STOP", ln):
                    bad.append(f"{p.relative_to(ROOT)}:{n}")
    assert not bad, bad
    assert KP.retired_grt_stop(ROOT / "physical" / "common_flow_tmp_none") == []          # no kit dir: nothing to refuse
    shim = ROOT / "physical" / "common_flow"
    assert not [e for e in KP.retired_grt_stop(shim) if "grt183_make.sh" in e]            # the real script passes the kit check
