cd /srv/opentallas-scratch3/claude/rm56
grep -h "test_compose_current_latency" u3/list.txt u3/rc.txt | cut -c1-120; grep -c compose_current_latency u3/fails.txt
run(){ t=$1; f=$2; p=0; cd /dev/shm/rm56/$t; for i in 1 2 3 4 5; do timeout 300 python3 -m pytest -q -p no:cacheprovider --basetemp=/dev/shm/rm56/tmp/flk_$t_$$_$i "$f" >/dev/null 2>&1 && p=$((p+1)); done; echo "$t ${f##*::} pass=$p/5"; }
for f in "tools/autopilot/test_watchdog.py::VerifyFakeDirTest::test_verify_cpu_sample_counts_busy_process" "tools/fleet/test_ot_heavy.py::OtHeavy::test_no_fixed_slots" "tools/fleet/test_ot_run_spill_floor.py::test_drop_keeps_a_copy_another_process_uses" "tools/fleet/test_ot_run_spill_floor.py::test_drop_only_without_signed_or_keep_at_any_depth" "tools/qwen_kv_die/chain/test_case_status.py::RealConstantMapping::test_actual_die_native_rail_ladder_reaches_core_M9" "tools/qwen_kv_die/chain/test_case_status.py::RealConstantMapping::test_direct_openroad_error_is_fatal_in_generated_contract"; do run w2 "$f" & done
run u3 "tools/die_plan/test_lec_async.py::test_physical_receipt_before_wait_and_later_scope_reuses_owner" &
wait
