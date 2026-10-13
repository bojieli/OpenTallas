#!/usr/bin/env bash
# Run in a source-pinned scratch directory under ot-heavy; never a die simulation.
set -euo pipefail
out=$1
mkdir -p "$out"
if [[ -e "$out/source.sha256" ]]; then echo 'refuse overwriting evidence' >&2;exit 2;fi
sha256sum ot_hbm_b2_*.sv tb_hbm_b2_*.sv ot_vms_hub.sv ot_vms_bank.sv ot_sram_1r1w_1024x256_m2_r2c2.v > "$out/source.sha256"
for unit in packet_mux vm8_sm_sink xread_aperture xwrite_aperture xload_command;do
 for mut in 0 1;do
  case_id=${unit}_mut${mut}
  iverilog -g2012 -s tb_hbm_b2_$unit -Ptb_hbm_b2_$unit.MUT=$mut -o "$out/$case_id.out" ot_hbm_b2_$unit.sv tb_hbm_b2_$unit.sv > "$out/$case_id.build.log" 2>&1
  set +e
  /usr/bin/time -v vvp "$out/$case_id.out" > "$out/$case_id.run.log" 2>&1
  rc=$?
  set -e
  echo "$rc" > "$out/$case_id.rc"
  head -2 "$out/$case_id.run.log"
  if [[ $mut == 0 ]];then test "$rc" -eq 0;else test "$rc" -ne 0;grep -q 'FATAL:' "$out/$case_id.run.log";fi
 done
done
for mode in ready native;do
peer_flags=()
if [[ $mode == native ]];then peer_flags=(-DNATIVE_PEERS);fi
for mut in 0 1;do
 case_id=actual_memory_${mode}_mut${mut}
 iverilog -g2012 -DACTUAL_MEMORY "${peer_flags[@]}" -DOT_MEM_NO_INIT -s tb_hbm_b2_packet_mux -Ptb_hbm_b2_packet_mux.MUT=$mut -o "$out/$case_id.out" ot_hbm_b2_packet_mux.sv ot_hbm_b2_packet_share.sv tb_hbm_b2_packet_mux.sv ot_vms_hub.sv ot_vms_bank.sv ot_sram_1r1w_1024x256_m2_r2c2.v > "$out/$case_id.build.log" 2>&1
 set +e
 /usr/bin/time -v vvp "$out/$case_id.out" > "$out/$case_id.run.log" 2>&1
 rc=$?
 set -e
 echo "$rc" > "$out/$case_id.rc"
 head -2 "$out/$case_id.run.log"
 if [[ $mut == 0 ]];then test "$rc" -eq 0;else test "$rc" -ne 0;grep -q 'FATAL:' "$out/$case_id.run.log";fi
done
done
