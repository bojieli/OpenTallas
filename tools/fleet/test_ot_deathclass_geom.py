"""FLOW-FLEET-R1 11-22 (COORD: 'private-spec geom stages die ~11 min rc 1 class=UNCLASSIFIED, cause = ot-run admits ... headroom 0').  All 9 such
DIED posts 00:10-01:25 were ADMITTED jobs whose AUTO-GEOM judged the placed kit FAIL; the admission status line was taken as the cause because the
post reads <stage>.live.log (stderr) and the verdict is in <stage>.log (stdout).  A real memory-admission refusal is ADMIT, not UNCLASSIFIED."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ot_deathclass as DC      # noqa: E402

LIVE = """ot-run: epyc7          admits   231 GB (avail 458, reserve 0, fresh 0, peak 182.5, headroom 0, waiters 0/0 GB, oldest 0.0 h) load 59/96 running 25 disk 1929 GB
ot-run: -> epyc7
ot-heavy: request 24G is charged 9G (SIMPLE_PEAK: MemAvailable 458 - 48 headroom)
ot-heavy: admitted on loved-redfish as oth-ubuntu-1153057-1795338871 after 0 s
ot-run: RAN on epyc7 (unit oth-ubuntu-1153057-1795338871): exit 1
"""
OUT = """AP_AUTO_GEOM_GRT TIMEOUT 600s after dump (1 it): grt NA, route GRT decides
AP_AUTO_GEOM_GRT rc 137 (M2-M8 adj 0.25, 50 it)
AP_AUTO_GEOM AUTO-GEOM FAIL dsdv_slice_c3x_C__t1 KIT-WAVE a9ed808a98d 3_place fill=FAIL(0.0812) empty=FAIL(0.6748) pin_reg_p90=FAIL(243.08)
AP_AUTO_GEOM_PNG /srv/x/geom/auto_geom.png
"""


def test_admission_status_line_is_never_the_cause():
    cls, cause = DC.classify(1, "", LIVE, 678)
    assert "admits" not in cause


def test_geom_stage_reads_its_stdout_verdict(tmp_path):
    (tmp_path / "geom.live.log").write_text(LIVE)
    (tmp_path / "geom.log").write_text(OUT + LIVE)
    lab = DC.label(1, "--mem 24 -- bash -c geom", str(tmp_path / "geom.live.log"), 678)
    assert "class=GEOM-FAIL" in lab and "AUTO-GEOM FAIL dsdv_slice_c3x_C__t1" in lab


def test_geom_pass_with_advisory_grt_kill_is_not_geom_fail():
    assert DC.classify(1, "", OUT.replace("AUTO-GEOM FAIL", "AUTO-GEOM PASS"), 600)[0] != "GEOM-FAIL"


def test_memory_admission_refusal_is_admit():
    assert DC.classify(78, "", "ot-run: NOT-RUN no host qualifies (mem: request 400 GB > admissible on every host)\n", 3)[0] == "ADMIT"
    assert DC.classify(1, "", "ot-run: epyc9 request 900 GB exceeds physical RAM after mandatory headroom\n", 1)[0] == "ADMIT"
    assert DC.classify(1, "", "ot-run: NOT-RUN no host qualifies (scratch disk under floor)\n", 1)[0] == "RAIL-KILL"


def test_plain_fail_word_is_a_design_fail():
    assert DC.classify(1, "", "check: r2r=FAIL(1851.98)\n", 50)[0] == "DESIGN-FAIL"
