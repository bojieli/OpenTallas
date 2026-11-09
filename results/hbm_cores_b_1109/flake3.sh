cd /home/ubuntu/OpenTallas; echo changed-in-R-S: $(git diff --name-only refs/rm55/Q refs/rm55/S -- tools/fleet tools/qwen_kv_die | head)
for t in q r s; do cd /dev/shm/rm55/$t
 for f in "tools/qwen_kv_die/chain/test_case_status.py::RealConstantMapping::test_actual_die_native_rail_ladder_reaches_core_M9" "tools/qwen_kv_die/chain/test_case_status.py::RealConstantMapping::test_direct_openroad_error_is_fatal_in_generated_contract" "tools/fleet/test_ot_run_spill_floor.py::test_drop_only_without_signed_or_keep_at_any_depth"; do
  p=0; for i in 1 2 3 4 5; do timeout 300 python3 -m pytest -q -p no:cacheprovider "$f" >/dev/null 2>&1 && p=$((p+1)); done; echo "$t ${f##*::} pass=$p/5"
 done
done
grep -h 'test_actual_die_native_rail\|test_direct_openroad_error' /srv/opentallas-scratch3/claude/rm55/{n,o,p,q}/fails.txt | sort | uniq -c | cut -c1-120
