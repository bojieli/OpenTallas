# Runnable native command reproducer; Python drivers created the actual dbWire design.
# Requires OpenROAD26Q3-1510-g6cb3f2b704, binarySHA21eda99e, image16470cea.
# No routing/repair. Hidden -box coordinates are INTEGER DBU, not microns.
read_db native/original.odb
set_thread_count 1
drt::check_drc -output_file replay_all_markers.rpt -marker_name STAGE_A_ORIGINAL
# Exact source/case ROIs are in coupon.json and executed by run_roi.py.
drt::check_drc -box {772 772 1172 1172} -output_file replay_case0.rpt -marker_name CASE_0
