"""QC-PADLEG-1119: plan field placement_guides -> soft GPL region guides (u_stream spread, 4-5x its outline)."""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import region_guide as RG  # noqa: E402

PLAN = {"partition_types": {
    "sle_stm_v1__x": {"outline_um": [613.44, 1831.68], "placement_guides": [
        {"inst": "u_core.u_stream", "bbox_um": [180.0, 1180.0, 439.2, 1560.0], "kind": "soft_region"}]},
    "plain": {"outline_um": [100.0, 100.0]}}}


def test_spec_from_plan_field_and_none_without_it():
    s = RG.from_plan(PLAN, "sle_stm_v1__x")
    r = s["regions"][0]
    assert s["schema"] == RG.SCHEMA and r["name"].startswith("ot_rg_") and r["insts"] == []
    assert r["inst_glob"] == ["u_bound.u_core.u_stream.*"] and r["box_um"] == [180.0, 1180.0, 439.2, 1560.0]
    assert RG.from_plan(PLAN, "plain") is None


def test_rejects_outside_overlap_and_unknown_kind():
    p = json.loads(json.dumps(PLAN))
    g = p["partition_types"]["sle_stm_v1__x"]["placement_guides"]
    g[0]["bbox_um"] = [500.0, 1500.0, 700.0, 1700.0]
    for bad in (lambda: RG.from_plan(p, "sle_stm_v1__x"),):
        try:
            bad()
            raise AssertionError("outside box accepted")
        except SystemExit:
            pass
    g[0]["bbox_um"] = [0, 0, 100, 100]; g.append({"inst": "b", "bbox_um": [50, 50, 150, 150]})
    try:
        RG.from_plan(p, "sle_stm_v1__x"); raise AssertionError("overlap accepted")
    except SystemExit:
        pass
    g.pop(); g[0]["kind"] = "hard"
    try:
        RG.from_plan(p, "sle_stm_v1__x"); raise AssertionError("kind accepted")
    except SystemExit:
        pass


def test_install_writes_glob_rows_and_the_tcl_hook_reads_them(tmp_path):
    kd = tmp_path
    (kd / "face_flops.tcl").write_text("# hook\n"); (kd / "face_flops_release.tcl").write_text("# rel\n")
    rec = RG.install(kd, RG.from_plan(PLAN, "sle_stm_v1__x"), outline=(613.44, 1831.68))
    tsv = (kd / "region_guide.tsv").read_text().splitlines()
    assert rec["regions"] == 1 and rec["globs"] == 1
    assert tsv[0].split("\t")[0] == "R" and tsv[1].split("\t")[:2] == ["G", "ot_rg_pg_0"]
    tcl = (kd / "region_guide.tcl").read_text()
    assert '"G"' in tcl and "string match" in tcl and "dbRegion_create" in tcl and "INCLUSIVE" in tcl


def test_cli_from_plan(tmp_path):
    pf = tmp_path / "plan.json"; pf.write_text(json.dumps(PLAN))
    out = tmp_path / "rg.json"
    r = subprocess.run([sys.executable, "-I", str(Path(RG.__file__)), "from-plan", "--plan", str(pf), "--type", "sle_stm_v1__x", "--out", str(out)], capture_output=True, text=True)
    assert r.returncode == 0 and json.loads(out.read_text())["regions"][0]["inst_glob"]
    out2 = tmp_path / "rg2.json"
    r = subprocess.run([sys.executable, "-I", str(Path(RG.__file__)), "from-plan", "--plan", str(pf), "--type", "plain", "--out", str(out2)], capture_output=True, text=True)
    assert r.returncode == 0 and not out2.exists()


def test_kit_wave_cmd_uses_plan_guides(tmp_path):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "autopilot"))
    import kit_wave as K
    pf = tmp_path / "plan.json"; pf.write_text(json.dumps(PLAN))
    (tmp_path / "tools").symlink_to(Path(RG.__file__).resolve().parent.parent, target_is_directory=True)
    (tmp_path / "a1").mkdir()
    sp = dict(work=str(tmp_path / "a1"), item="sle_stm_v1__x", plan=str(pf))
    pre, suf = K.region_guide_cmd(sp, False)
    out = subprocess.run(["bash", "-c", pre + "echo ARGS" + suf], cwd=tmp_path, capture_output=True, text=True).stdout
    assert out.strip().endswith(f"ARGS --region-guide sle_stm_v1__x={tmp_path}/a1/region_guide.json")
    sp2 = dict(sp, item="plain")
    out = subprocess.run(["bash", "-c", "".join(K.region_guide_cmd(sp2, False)[:1]) + "echo ARGS"], cwd=tmp_path, capture_output=True, text=True).stdout
    assert "KW_REGION_GUIDE none" in out
