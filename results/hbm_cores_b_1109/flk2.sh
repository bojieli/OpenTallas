cd /srv/opentallas-scratch3/claude/rm56
grep -hE "landing_group_rects|landing_start_clear|test_landing" y/rc.txt | cut -c1-100
run(){ t=$1; f=$2; p=0; cd /dev/shm/rm56/$t; for i in 1 2 3 4 5; do timeout 300 python3 -m pytest -q -p no:cacheprovider --basetemp=/dev/shm/rm56/tmp/flk2_${t}_$$_$i "$f" >/dev/null 2>&1 && p=$((p+1)); done; echo "$t ${f##*::} pass=$p/5"; }
for f in "tools/qwen_kv_die/chain/test_case_status.py::RealConstantMapping::test_actual_pin_rail_contacts_and_connected_grid" "tools/qwen_kv_die/chain/test_case_status.py::RealConstantMapping::test_logical_pg_binding_cannot_replace_literal_supply_rails" "tools/ref_tile/tests/test_multiple_cts_roots.py::Physical::test_actual_liberty_constant_output_and_nonconstant_mutants"; do run x "$f" & done
run y "tools/die_plan/test_lec_async.py::test_physical_receipt_before_wait_and_later_scope_reuses_owner" &
run y "tools/fleet/test_ot_run_spill_floor.py::test_drop_keeps_a_copy_another_process_uses" &
wait
