#!/bin/bash
# MU-QWEN-HOST 10-19: every host-plane bench.  usage: run_all.sh NEW_ROOT HEAD_ROOT OUT [PAR]
#  ex_new/ex_head: the 13 existing host benches that reach a changed file, at default params (MU 0), on the MU tree and
#  on the pre-MU tree; their logs must be identical.  mu: the MU 1 PASS benches.  mut: mutants (must FAIL).
set -u
N=${1:?new}; H=${2:?head}; O=${3:?out}; PAR=${4:-12}
B=$(dirname "$(readlink -f "$0")"); mkdir -p "$O"
EX="tb_qkd_host_ctl tb_qkd_ctrl8_composed tb_qkd_host_control_capture tb_qkd_host_control_composed tb_qkd_host_control_prompt
 tb_qkd_host_control_role tb_qkd_host_control_service tb_qkd_host_control_token_service tb_qkd_host_fullcontrol_packet
 tb_qkd_host_fullcontrol tb_qkd_host_program_loader tb_qkd_host_prompt_packet tb_qkd_host_prompt_ue"
{ for t in $EX; do echo "$N $O/ex_new $t"; echo "$H $O/ex_head $t"; done
  for t in tb_qkd_host_ctl_mu tb_qkd_host_mu_out tb_qkd_kv_mu_rowoff; do echo "$N $O/mu $t"; done
  for m in cm1 cm2 cm3 cm4 cm5 hm1 hm2 hm3 hm4 rm1 rm2; do echo "$N $O/mut $m"; done
} | xargs -P "$PAR" -L 1 bash -c '"$0" "$1" "$2" "$3"' "$B/run_host_mu.sh" > "$O/summary.txt" 2>&1
sort "$O/summary.txt"
echo "IDENTITY (ex_new vs ex_head logs, Verilator run-statistics lines excluded):"
for t in $EX; do
  if [ -s "$O/ex_new/$t.log" ] && cmp -s <(grep -v "^- Verilator:" "$O/ex_new/$t.log") <(grep -v "^- Verilator:" "$O/ex_head/$t.log"); then echo "  $t identical"; else echo "  $t DIFFERS"; fi
done
