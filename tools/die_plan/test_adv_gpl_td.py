"""ADV-GPL-TD-INFLATION (report only): log measurement, static predictor, calibration counts, plan region census."""
import adv_gpl_td as A

GPL_LOG = """\
global_placement -density 0.5 -pad_left 0 -pad_right 0 -routability_driven -timing_driven -force_center_initial_place
OT_GPL_SPARSE movable util 1.042 % < 5.000 %: routability-driven GPL off, timing-driven kept
OT_GPL_SPARSE global_placement -density 0.5 -pad_left 0 -pad_right 0 -timing_driven -force_center_initial_place
[INFO GPL-0032] ---- Initialize Region: Top-level
[INFO GPL-0006] Number of instances:            1000
[INFO GPL-0007] Movable instances:                  800
[INFO GPL-0010] Number of nets:                  900
[INFO GPL-0032] ---- Initialize Region: c1
[INFO GPL-0006] Number of instances:            20
[INFO GPL-0007] Movable instances:                  8
[INFO GPL-0032] ---- Initialize Region: c2
[INFO GPL-0006] Number of instances:            200
[INFO GPL-0007] Movable instances:                  150
Iteration | Overflow |     HPWL (um) |  HPWL(%) |   Penalty | Group
---------------------------------------------------------------
        0 |   0.7300 |  1.000000e+06 |   +0.00% |  1.21e-13 |      
        0 |   0.0200 |  1.000000e+06 |   +0.00% |  6.96e-12 |  (c1)
       10 |   0.6000 |  1.100000e+06 |  +10.00% |  1.94e-13 |      
[INFO GPL-0100] Timing-driven iteration 1/2, virtual: false.
[INFO GPL-0101]    Iter: 12, overflow: 0.185, keep resizer changes at: 1, HPWL: 1100000
[INFO RSZ-0038] Inserted 400 buffers in 300 nets.
[INFO GPL-0107] Timing-driven: repair_design delta area: 10.0 um^2 (+25.00%)
[INFO GPL-0108] Timing-driven: repair_design, gpl delta gcells: 400 (+50.00%)
      390 |   0.0973 |  1.900000e+06 |          |  5.65e-06 |      
[INFO GPL-1001] Global placement finished at iteration 391
[INFO GPL-1014] Final placement area: 50.0 (+25.00%)
"""
RSZ_LOG = """\
[INFO RSZ-0037] Found 90 long wires.
[INFO RSZ-0038] Inserted 100 buffers in 60 nets.
    final |     +0.5% |      10 |     100 |            60 | 0
"""


def _row(tmp_path, gpl=GPL_LOG, rsz=RSZ_LOG):
    (tmp_path / "3_3_place_gp.log").write_text(gpl)
    if rsz is not None:
        (tmp_path / "3_4_place_resized.log").write_text(rsz)
    return A.analyse(str(tmp_path / "3_3_place_gp.log"))


def test_log_measures_regions_trigger_gap_and_growth(tmp_path):
    r = _row(tmp_path)
    assert (r["regions"], r["tiny_regions"], r["region_cells_min"], r["region_cells_max"]) == (2, 1, 8, 150)
    assert (r["td_on"], r["td_passes"], r["first_fire_iter"], r["first_fire_overflow"]) == (1, 1, 12, 0.185)
    assert r["first_fire_top_overflow"] == 0.6 and A.region_mean_gap(r) is True and r["mean_top_gap_max"] == "0.415"
    assert (r["td_kept_buffers"], r["td_virtual_first"], r["movable_top"], r["nets_top"]) == (400, 0, 800, 900)
    assert (r["resize_buffers"], r["resize_nets"], r["resize_long_wires"]) == (100, 60, "90")
    assert r["td_delta_area_pct"] == "+25.00" and r["sparse_util_pct"] == "1.042"
    assert abs(A.growth_ratio(r) - 0.625) < 1e-9 and A.inflated(r) is True and A.risk(r) is True


def test_virtual_first_pass_buffers_are_not_kept(tmp_path):
    log = GPL_LOG.replace("virtual: false", "virtual: true")
    r = _row(tmp_path, log, None)
    assert r["td_virtual_first"] == 1 and r["td_kept_buffers"] == 0 and A.inflated(r) is False


def test_cell_cap_makes_a_low_ratio_inflated():
    assert A.inflated({"movable_top": 395000, "td_kept_buffers": 0, "resize_buffers": 10000}) is True
    assert A.inflated({"movable_top": 100000, "td_kept_buffers": 1000, "resize_buffers": 1000}) is False


def test_predictor_reads_only_pre_pass_facts():
    assert A.risk({"td_on": 1, "tiny_regions": 3, "sparse_util_pct": "9"}) is True
    assert A.risk({"td_on": 1, "tiny_regions": 0, "sparse_util_pct": "1.5"}) is True
    assert A.risk({"td_on": 1, "tiny_regions": 0, "sparse_util_pct": "2.5"}) is False
    assert A.risk({"td_on": 0, "tiny_regions": 3, "sparse_util_pct": "0.1"}) is False
    assert A.risk({"td_on": 1, "tiny_regions": "", "sparse_util_pct": ""}) is False


def test_calibration_counts():
    rows = [dict(td_on=1, tiny_regions=2, movable_top=100, td_kept_buffers=80, resize_buffers=0),    # TP
            dict(td_on=1, tiny_regions=2, movable_top=100, td_kept_buffers=1, resize_buffers=0),     # FP
            dict(td_on=1, tiny_regions=0, sparse_util_pct="9", movable_top=100, td_kept_buffers=80),  # FN
            dict(td_on=1, tiny_regions=0, sparse_util_pct="9", movable_top=100, td_kept_buffers=1)]  # TN
    assert A.calibrate(rows) == {"TP": 1, "FP": 1, "FN": 1, "TN": 1}


def test_plan_check_counts_regions_and_flag():
    plan = {"partition_types": {"a": {"logic_cluster_rects_um": [{}, {}]}, "b": {"place_regions": [[]]}, "c": {}}}
    rows = A.plan_check(plan)
    assert [(r["type"], r["logic_cluster_regions"], r["place_regions"], r["exposed"]) for r in rows] == [("a", 2, 0, "yes"), ("b", 0, 1, "yes")]
    plan["gpl_td"] = {"top_overflow_trigger": 1}
    assert A.plan_check(plan, "^a$")[0]["exposed"] == "no (top_overflow_trigger)"


def test_missing_log_is_an_empty_row(tmp_path):
    assert A.analyse(str(tmp_path / "nope.log"))["regions"] == ""
