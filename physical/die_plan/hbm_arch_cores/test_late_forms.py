import subprocess

import late_forms as F


def _kit(tmp_path):
    (tmp_path / "config.mk").write_text(
        "export PRE_GLOBAL_ROUTE_TCL = /work/core_grt_pre.tcl\noverride export PRE_GLOBAL_PLACE_TCL = /work/face_flops.tcl\n")
    (tmp_path / "core_grt_pre.tcl").write_text("source /work/max_fanout.tcl\n")
    (tmp_path / "face_flops.tcl").write_text("set a 1\n")
    return tmp_path


def _tclsh(script, body):
    return subprocess.run(["tclsh"], input=f"{body}\n{script}\nputs [global_route -end_incremental]\nputs [global_route -start_incremental]\n"
                          "puts [global_placement -density 0.5 -routability_driven -timing_driven]\n",
                          text=True, capture_output=True, check=True).stdout.split("\n")


def test_hooks_idempotent(tmp_path):
    k = _kit(tmp_path)
    for _ in range(2):
        F.hook(k, "GLOBAL_ROUTE", "grt_near_miss.tcl", F.GRT)
        F.hook(k, "GLOBAL_PLACE", "gpl_no_routability.tcl", F.GPL)
    assert (k / "core_grt_pre.tcl").read_text() == "source /work/grt_near_miss.tcl\nsource /work/max_fanout.tcl\n"
    assert (k / "face_flops.tcl").read_text() == "source /work/gpl_no_routability.tcl\nset a 1\n"


def test_shims_change_only_the_named_flag():
    out = _tclsh(F.GRT + F.GPL, "proc global_route {args} {return $args}\nproc global_placement {args} {return $args}")
    assert out[0] == "-end_incremental -allow_congestion"
    assert out[1] == "-start_incremental"
    assert out[2] == "-density 0.5 -timing_driven"


def test_from_failed_keeps_prehold(tmp_path):
    b = tmp_path / "run/results/asap7/x/base"
    b.mkdir(parents=True)
    (b / "4_cts.odb").write_text("cts")
    (b / "5_1_grt-failed.odb").write_text("held")
    F.from_failed(tmp_path)
    assert (b / "4_cts.odb").read_text() == "held" and (b / "4_cts.prehold.odb").read_text() == "cts"
    assert not (b / "5_1_grt-failed.odb").exists()


def test_grt_form_skips_antenna_repair():
    assert "set ::env(SKIP_ANTENNA_REPAIR) 1" in F.GRT
