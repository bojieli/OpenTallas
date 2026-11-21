"""FLOW-GRT-RESID 11-21: (1) the round limit with a small concentrated overflow finishes GRT with -allow_congestion (OT_GRT_RESID class line, one
continue per kit), (2) a flat DRT of such a kit stops on a short window, (3) a flat post-GRT repair resumes from the pre-repair design.  Local, no OpenROAD."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "physical/common_flow"))
import failfast_rules as R  # noqa: E402
from test_grt183_kit import calls, fake, kit, run  # noqa: E402

C = R.config_values({}, "")


def rpt(entries):
    """entries [(overflow, x, y)] -> congestion report text"""
    s = ""
    for ov, x, y in entries:
        s += ("violation type: Horizontal congestion\n\tsrcs: net:a\n\tcomment: capacity:20 usage:%d congestion:%d\n"
              "\tbbox = (%s, %s) - (%s, %s) on Layer M3\n" % (20 + ov, ov, x, y, x + 1, y + 1))
    return s


def test_resid_concentrated_small_overflow_applies():
    d = R.resid_decide(rpt([(300, 100.0, 100.0), (150, 110.0, 105.0)]), C)
    assert d and d["total"] == 450 and d["bins"] == 1 and "OT_GRT_RESID stage=grt class=GRT_RESID" in R.resid_line(d)


def test_resid_over_threshold_or_spread_or_off_is_not_applied():
    assert R.resid_decide(rpt([(600, 100.0, 100.0)]), C) is None                      # over 500
    spread = rpt([(50, 43.0 * i + 1, 43.0 * i + 1) for i in range(8)])                   # 400 over 8 bins, top-3 share 37 %
    assert R.resid_decide(spread, C) is None
    assert R.resid_decide(rpt([(300, 100.0, 100.0)]), dict(C, OT_GRT_RESID_MAX=0)) is None
    assert R.resid_decide("", C) is None


def test_drt_flat_resid_stops_early_only_for_resid_kits():
    series = [("%d" % i, v) for i, v in enumerate([40, 30, 25, 22, 20, 19, 18, 18, 17, 17, 17, 17, 17, 17, 17, 17])]
    assert R.drt_decide(series, C) is None                                           # general rule waits for iteration 40
    d = R.drt_decide(series, C, resid=True)
    assert d and d["rule"] == "DRT_STALL" and "FLOW-GRT-RESID" in R.drt_line(d, stamp=False)
    assert R.drt_decide(series[:9], C, resid=True) is None                           # still gaining / too early


STOP_LOG = "[ERROR GRT-0116] Global routing finished with congestion.\n"


def _setup_resid(tmp_path, total):
    k, r, l, s = kit(tmp_path)
    (k / "failfast_rules.py").write_text((HERE.parents[1] / "physical/common_flow/failfast_rules.py").read_text())
    rp = k / "run/reports/asap7/t/base"; rp.mkdir(parents=True)
    (rp / "congestion-10.rpt").write_text(rpt([(total, 100.0, 100.0)]))
    os.utime(rp / "congestion-10.rpt", (time.time() + 600, time.time() + 600))     # written "during" the run (the judge reads this run's reports only)
    return k, r, l, s


FAIL1 = ('if [ $N = 1 ]; then printf "%s" "' + STOP_LOG.strip() + '\\n" > $L/5_1_grt.log; exit 2; fi\n')
OK2 = 'echo "${OT_GRT_ALLOW_CONGESTION:-0}" > $K/ac$N.txt; echo ok > $L/5_1_grt.log; exit 0\n'


def test_stage_reruns_once_with_allow_congestion(tmp_path):
    k, r, l, s = _setup_resid(tmp_path, 120)
    p = run(k, s, fake(tmp_path, FAIL1 + OK2), "grt")
    assert p.returncode == 0, p.stdout + p.stderr
    assert len(calls(k)) == 2 and (k / "ac2.txt").read_text().strip() == "1"
    assert "OT_GRT_RESID stage=grt class=GRT_RESID" in p.stdout and "OT_GRT_RESID attempt 1 rc 2" in p.stdout
    assert json.loads((r / "5_1_grt.resid_allow.json").read_text())["schema"] == "opentallas.grt_resid.v1"
    assert "OT_GRT_ALLOW_CONG_HOOK" in (s / "global_route.tcl").read_text()           # the allow-congestion hook is in for the re-run


def test_big_overflow_keeps_the_stop_and_marker_gives_one_rerun(tmp_path):
    k, r, l, s = _setup_resid(tmp_path, 5000)
    p = run(k, s, fake(tmp_path, FAIL1 + OK2), "grt")
    assert p.returncode == 2 and len(calls(k)) == 1 and "OT_GRT_RESID" not in p.stdout
    k2, r2, l2, s2 = _setup_resid(tmp_path / "b", 120)
    (r2 / "5_1_grt.resid_allow.json").write_text("{}")
    p = run(k2, s2, fake(tmp_path / "b", FAIL1 + OK2), "grt")
    assert p.returncode == 2 and len(calls(k2)) == 1


def test_opt_out_and_allow_congestion_kits(tmp_path):
    k, r, l, s = _setup_resid(tmp_path, 120)
    p = run(k, s, fake(tmp_path, FAIL1 + OK2), "grt", env={"OT_GRT_RESID_MAX": "0"})
    assert p.returncode == 2 and len(calls(k)) == 1


# (3) the no-progress continue path resumes from the pre-repair design
IN_REPAIR = ('if [ $N = 1 ]; then echo prerepair > $R/5_1_grt.prerepair.odb; echo "[]" > $R/5_1_grt.prerepair.shapes; '
             'printf "OT_MAXWIRE repair_design -verbose -max_wire_length 100\\n     4000 |     +0.0%% |       0 |    1232 |          1116 |    142176\\n" > $L/5_1_grt.tmp.log; sleep 60; exit 0; fi\n')
FAST = {"OT_GRT_REPAIR_STALL_S": "3", "OT_GRT_REPAIR_LOG_S": "1", "OT_GRT_STALL_POLL": "1", "OT_GRT_STALL_KILL_WAIT": "1"}


def test_repair_stall_resumes_from_prerepair_design(tmp_path):
    k, r, l, s = kit(tmp_path)
    p = run(k, s, fake(tmp_path, IN_REPAIR + 'ls $R > $K/ls2.txt; cat $R/4_cts.odb > $K/in2.txt; ls $R/5_1_grt.stall_strip.shapes >> $K/ls2.txt; exit 0\n'), "grt", env=FAST)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "OT_GRT_REPAIR_RESUME from the pre-repair full-route design" in p.stdout
    assert (k / "in2.txt").read_text().strip() == "prerepair"                       # the re-run starts from the saved design
    assert "5_1_grt.repair_nostall.json" in (k / "ls2.txt").read_text()               # and skips only the stuck repair
    assert (r / "4_cts.odb").read_text() == "cts" and not (r / "4_cts.pre_grt183.odb").exists()   # CTS result restored
