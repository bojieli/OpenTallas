import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import autopilot as AP

GEN = (Path(__file__).resolve().parents[1] / "die_plan" / "gen_phys.py").read_text()


def test_run_kit_writes_fail_route_on_a_silent_make_exit():
    assert "FAIL_route" in GEN and "ls \"$K\"/FAIL_*" in GEN and "[ERROR DRT-" in GEN


def test_drt_0255_is_class_drt_nopath_with_the_net_name():
    line = "FAIL_route [ERROR DRT-0255] Maze Route cannot find path of net net93226 in worker of routeBox ( 405840 298110 )"
    cls, kind, why = AP.classify({"FAIL_route": line, "goal": "route"}, {"exit": 2})
    assert (cls, kind) == ("STRUCTURAL", "drt-nopath") and "DRT-NOPATH net net93226" in why
    cls2, kind2, _ = AP.classify({"FAIL_route": "FAIL_route make exit 2 (see run_route.log)", "goal": "route"}, {"exit": 2})
    assert (cls2, kind2) == ("CRASH", "route-make-fail")
