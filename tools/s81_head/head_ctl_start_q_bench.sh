#!/bin/bash
# HEAD-92/CTL 11-10: lockstep proof of the hd_ctl cycle form OT_S81HD_CTL_START_Q (ot_s81hd_ctl_hsf0_static).
# A = baseline hsf0_static (argument 2, e.g. the routed kit's file or `git show <base>:...`), B = this tree's file.
# Full controller incl. the real dsfd_mtp_seq_fan, kit parameters; bench tools/s81_head/head_ctl_start_q_tb.sv.
#   off        B without the define: every output identical every cycle (default circuit unchanged)
#   sq         B with the define: stream / mesh / ro / host / draft / mu_rc / ctl_f exactly +1, mu_c and the
#              x_o fault bit same-cycle, job_active rise same / fall +1, earliest legal reload, directed duplicate
#              token in the cycle after START, no fault in A or B
#   floor      reload one cycle before B's earliest legal cycle: only B faults (reload window moved by exactly 1)
#   mut_retire must FAIL: token_retire mask in the start_q cycle removed
#   mut_align  must FAIL: the stream counter left on the combinational START
# Usage: head_ctl_start_q_bench.sh OUTDIR BASELINE_HSF0 [variant ...]   (needs iverilog >= 11 / vvp)
set -u
OUT=$1; OLD=$2; shift 2
VARS=${*:-off sq floor mut_retire mut_align}
T=$(cd "$(dirname "$0")/../.." && pwd)
H=$T/rtl/dsrom_sys/s81_head; M=$T/rtl/dsrom_sys/mtp
DEPS="$T/rtl/lib/ot_rst_relay_tree3.sv $H/ot_s81hd_util.sv $H/ot_s81hd_static_issue.sv $M/ot_dsrom_mtp_link_pair.sv $M/ot_dsrom_mtp_seq.sv $M/dsfd_mtp_tops.sv $T/physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v"
mkdir -p "$OUT"; cd "$OUT"
sed -E 's/\b(ot_s81hd_ctl_hsf0_static|ot_s81hd_ctl_grx)\b/\1_sq/g' "$H/ot_s81hd_ctl_hsf0_static.sv" > new_sq.sv
{ echo '`undef OT_S81HD_CTL_START_Q'; echo '`undef OT_S81HD_CTL_START_Q_MUT'; cat "$OLD"; } > old_wrap.sv
rc=0
for v in $VARS; do
 newf=new_sq.sv; expect=PASS
 case $v in
  off) defs=""; mode=0; nj=4;;
  sq) defs="OT_S81HD_CTL_START_Q"; mode=1; nj=5;;
  floor) defs="OT_S81HD_CTL_START_Q"; mode=2; nj=2;;
  mut_retire) defs="OT_S81HD_CTL_START_Q OT_S81HD_CTL_START_Q_MUT"; mode=1; nj=5; expect=FAIL;;
  mut_align) defs="OT_S81HD_CTL_START_Q"; mode=1; nj=5; expect=FAIL; newf=new_sq_align.sv
    sed "s/else if (start_s) begin busy <= 1'b1;/else if (start) begin busy <= 1'b1;/" new_sq.sv > $newf
    cmp -s new_sq.sv $newf && { echo "MUTANT NOT APPLIED $v"; rc=1; continue; };;
  *) echo "unknown variant $v"; rc=1; continue;;
 esac
 { for d in $defs; do echo "\`define $d"; done; cat $newf; } > new_wrap_$v.sv
 tbd=""; [ -n "$defs" ] && tbd=-DTB_SQ
 if ! iverilog -g2012 -s tb -P tb.MODE=$mode -P tb.NJ=$nj $tbd -o sim_$v $DEPS old_wrap.sv new_wrap_$v.sv "$T/tools/s81_head/head_ctl_start_q_tb.sv" > build_$v.log 2>&1; then
  echo "BUILD FAIL $v"; rc=1; continue; fi
 vvp -n sim_$v > run_$v.log 2>&1
 if grep -q '^PASS hd_ctl start_q' run_$v.log; then got=PASS; else got=FAIL; fi
 if [ $got = $expect ]; then echo "CHECK $v $got (expected) $(grep -m1 -E '^(PASS|MISMATCH)' run_$v.log)"
 else echo "CHECK $v $got UNEXPECTED"; tail -n 5 run_$v.log; rc=1; fi
done
exit $rc
