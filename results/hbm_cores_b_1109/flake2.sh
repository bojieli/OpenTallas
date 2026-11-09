for t in o p; do cd /dev/shm/rm55/$t
 for f in "tools/die_plan/test_lec_async.py::test_physical_receipt_before_wait_and_later_scope_reuses_owner" "tools/fleet/test_ot_run_spill_floor.py::test_drop_keeps_a_copy_another_process_uses"; do
  p=0; for i in 1 2 3 4 5; do timeout 300 python3 -m pytest -q -p no:cacheprovider "$f" >/dev/null 2>&1 && p=$((p+1)); done; echo "$t ${f##*::} pass=$p/5"
 done
done
cd /home/ubuntu/OpenTallas; git diff --name-only ab64dba2a82 refs/rm55/P -- tools/die_plan/lec.py tools/die_plan/test_lec_async.py tools/fleet/ot-run tools/fleet/test_ot_run_spill_floor.py
