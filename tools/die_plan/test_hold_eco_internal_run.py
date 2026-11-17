"""hold_eco_internal_run.py: the one-command post-route internal-endpoint hold ECO (QC-TYPES-R3 11-17): its pure helpers and the
properties that removed the three hand-run restarts (libs from the receipt, Tcl read-only from the checkout, containers as the
calling user)."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import hold_eco_internal_run as H  # noqa: E402

SRC = (HERE / "hold_eco_internal_run.py").read_text()


def test_libs_come_from_the_signoff_receipt_and_std_cells_split_off(tmp_path):
    p = tmp_path / "libraries.json"
    p.write_text(json.dumps({"libraries": [
        {"path": "/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz", "sha256": "x"},
        {"path": "/work/macros/ot_phy_tt.lib", "sha256": "y"}]}))
    allp, std = H.libs_from_receipt(p)
    assert len(allp) == 2 and std == [allp[0]]


def test_session_patch_adds_the_dump_once_per_corner_and_refuses_a_foreign_session():
    s = "a\n" + H.MARK + "\nb\n"
    ff, tt = H.patch_session(s, "ff"), H.patch_session(s, "tt")
    assert "ep_ff.tsv" in ff and "ep_tt.tsv" not in ff and ff.count(H.MARK) == 1
    assert "ep_tt.tsv" in tt and "ep_ff.tsv" not in tt
    try:
        H.patch_session("no marker", "ff")
        raise AssertionError("must refuse")
    except SystemExit:
        pass


def test_cmd_is_retargeted_to_the_dump_copy_with_a_fresh_container_name():
    cmd = "docker run --rm --name so_1_ff_2 -v /o/ff:/out -v /k:/work:ro img run"
    out = H.retarget_cmd(cmd, "/o/ff", "/o/dump/ff", "hei_dump_ff_9")
    assert "-v /o/dump/ff:/out" in out and "--name hei_dump_ff_9" in out and "so_1_ff_2" not in out
    try:
        H.retarget_cmd("docker run -v /x:/out", "/o/ff", "/n", "t")
        raise AssertionError("must refuse")
    except SystemExit:
        pass


def test_endpoints_merge_ff_hold_with_tt_setup_in_ps(tmp_path):
    (tmp_path / "ff").mkdir()
    (tmp_path / "tt").mkdir()
    (tmp_path / "ff" / "ep_ff.tsv").write_text("endpoint\tstartpoint\tstart_kind\tend_kind\tff_hold_slack_ps\n"
                                               "u/rbs[0]/RESETN\tu/rrl/q\treg\treg\t-1.55e12\n")
    (tmp_path / "tt" / "ep_tt.tsv").write_text("endpoint\ttt_setup_slack_ps\nu/rbs[0]/RESETN\t120e12\n")
    out = tmp_path / "hold_endpoints.tsv"
    assert H.merge_endpoints(tmp_path, out) == 1
    row = out.read_text().splitlines()[1].split("\t")
    assert row[0] == "u/rbs[0]/RESETN" and abs(float(row[4]) - (-1.55)) < 1e-9 and abs(float(row[5]) - 120.0) < 1e-9


def test_no_hand_copied_inputs_and_containers_run_as_the_caller():
    assert "libraries.json" in SRC and 'ro = rt / "tools/die_plan/post_route_drv"' in SRC
    assert '"-v", "%s:/ro:ro" % ro' in SRC                       # Tcl mounted read-only, never copied (the chmod restarts)
    assert 'user = ["-u", "%d:%d" % (os.getuid(), os.getgid())]' in SRC   # no root-owned outputs
    assert "(a previous ECO)" not in SRC and "never overwrite a previous ECO" in SRC
