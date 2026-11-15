"""FLOW-23 class D: kit_wave passes the previous AUTO-GEOM to region_guide.py on a relaunch (spec only on r2r FAIL)."""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as K  # noqa: E402

EV = "intel2:/w/items/x/attempt_7/geom/auto_geom.json"


def test_geom_dir_only_after_a_geom_fail_on_the_gen_host():
    prev = dict(status="FAIL", stage="geom", evidence=EV)
    assert K.region_guide_geom(prev, "intel2") == "/w/items/x/attempt_7/geom"
    assert K.region_guide_geom(prev, "epyc2") is None                   # geom.tsv is read in place only
    assert K.region_guide_geom(dict(prev, stage="place"), "intel2") is None
    assert K.region_guide_geom(dict(prev, status="PASS"), "intel2") is None
    assert K.region_guide_geom(dict(prev, evidence="intel2:/w/kit"), "intel2") is None
    assert K.region_guide_geom({}, "intel2") is None


def test_cmd_off_without_previous_geom():
    assert K.region_guide_cmd(dict(work="/w/a8", item="x"), True) == ("RG=; ", "")


def _sh(prefix, suffix, tmp_path):
    return subprocess.run(["bash", "-c", prefix + "echo ARGS" + suffix], cwd=tmp_path, capture_output=True, text=True).stdout


def test_cmd_flag_only_when_spec_written(tmp_path):
    gd = tmp_path / "geom"
    gd.mkdir()
    (gd / "geom.tsv").write_text("")
    tool = tmp_path / "tools" / "die_plan"
    tool.mkdir(parents=True)
    sp = dict(region_guide_geom=str(gd), work=str(tmp_path / "a8"), item="hnx_fused_lane")
    (tmp_path / "a8").mkdir()
    # stub planner: writes no spec (r2r passed) -> no flag
    (tool / "region_guide.py").write_text("import sys\n")
    pre, suf = K.region_guide_cmd(sp, True)
    out = _sh(pre, suf, tmp_path)
    assert "KW_REGION_GUIDE none" in out and out.strip().endswith("ARGS")
    # stub planner writes a spec (class D) -> core flag / type flag
    (tool / "region_guide.py").write_text("import sys\nopen(sys.argv[sys.argv.index('--out')+1],'w').write('{}')\n")
    out = _sh(*K.region_guide_cmd(sp, True), tmp_path)
    assert out.strip().endswith(f"ARGS --region-guide {tmp_path}/a8/region_guide.json")
    out = _sh(*K.region_guide_cmd(sp, False), tmp_path)
    assert out.strip().endswith(f"ARGS --region-guide hnx_fused_lane={tmp_path}/a8/region_guide.json")
    # a planner error or a source without the tool -> kit without guide
    (tool / "region_guide.py").write_text("import sys\nsys.exit(2)\n")
    out = _sh(*K.region_guide_cmd(sp, True), tmp_path)
    assert "KW_NOTE region_guide plan failed" in out and out.strip().endswith("ARGS")
    (tool / "region_guide.py").unlink()
    out = _sh(*K.region_guide_cmd(sp, True), tmp_path)
    assert "KW_NOTE no region_guide.py" in out and out.strip().endswith("ARGS")


def test_no_guide_after_infra_watchdog_or_a_passed_geom():
    """QC-FAIL-22 11-10: the INFRA path marks the record FAIL at stage geom before launch; only a real geom FAIL plans guides."""
    prev = dict(status="FAIL", stage="geom", evidence=EV, reason="AUTO-GEOM rule FAIL (geometry)", **{"class": "PLAN"})
    assert K.region_guide_geom(prev, "intel2") == "/w/items/x/attempt_7/geom"
    assert K.region_guide_geom(dict(prev, **{"class": "INFRA"}), "intel2") is None
    assert K.region_guide_geom(dict(prev, q_id="406ada361bad", q_status="FAIL"), "intel2") is None
    assert K.region_guide_geom(dict(prev, q_status="FAIL"), "intel2") is None
    assert K.region_guide_geom(dict(prev, reason="watchdog-stopped: exit 143: stopped by the hub WATCHDOG"), "intel2") is None
