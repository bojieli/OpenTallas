#!/bin/bash
set -eu
trial_root=/srv/opentallas-scratch2/claude/codex-s81-2340/reach17
baseline_kit=/srv/opentallas-scratch2/claude/die-s81-18/go16/kit
printf 'START %s source 510ac51ec diagnostic go16 physical baseline\n' "$(date)" > "$trial_root/status"
for corner in TT FF; do
  trial_out="$trial_root/out_$corner"
  mkdir -p "$trial_out"
  CORNER="$corner" ADJ=0.75 python3 "$trial_root/mk_combo_dcm.py" "$baseline_kit" "$trial_root/clk" "$trial_out" > "$trial_out/mk.log" 2>&1
  python3 "$trial_root/patch_combo_inv.py" "$trial_root/clk/ctree.v" "$trial_out/combo.tcl" >> "$trial_out/mk.log" 2>&1
  python3 "$trial_root/splice_readout.py" "$trial_out/combo.tcl" "$trial_root/readout.tcl" >> "$trial_out/mk.log" 2>&1
  docker run --rm --name "codex-s81-reach17-$corner" --memory=56g --memory-swap=56g --cpus=8 -e CORNER="$corner" -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -v "$baseline_kit":/work:ro -v "$trial_out":/out openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 8 -exit /out/combo.tcl > /out/combo.log 2>&1; run_rc=$?; echo EXIT "$run_rc" >> /out/combo.log; exit "$run_rc"' > "$trial_out/docker.log" 2>&1 &
  if [ "$corner" = TT ]; then tt_pid=$!; else ff_pid=$!; fi
done
job_rc=0
wait "$tt_pid" || job_rc=$?
wait "$ff_pid" || job_rc=$?
for corner in TT FF; do
  grep -E '^(M[1-9]|Total) ' "$trial_root/out_$corner/combo.log" | tail -10 >> "$trial_root/status" || true
  tail -2 "$trial_root/out_$corner/combo.log" >> "$trial_root/status"
  python3 "$trial_root/duty_compat.py" "$trial_root/out_$corner/arr_$corner.txt" "$trial_root/out_$corner/arr_${corner}_duty.txt"
done
python3 "$trial_root/duty_eval.py" "$trial_root/out_TT/arr_TT_duty.txt" "$trial_root/out_FF/arr_FF_duty.txt" "$trial_root/duty17.json" > "$trial_root/duty.log" 2>&1
printf 'DONE %s RC %s\n' "$(date)" "$job_rc" >> "$trial_root/status"
exit "$job_rc"
