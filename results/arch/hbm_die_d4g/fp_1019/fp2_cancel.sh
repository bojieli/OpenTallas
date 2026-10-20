#!/bin/bash
# L2H-GEN2D-FP2 10-19: cancel GEN2d floorplan variant $1 (fp | fp86 | fprsv) after another variant's real forest PASSED first
# (LEAD3-HBM decision 3).  Exact PIDs only: the variant's driver (pid file + cmdline check; never the caller), its post-forest
# chain (post_fp_<v>/chain.pid + kids), its forest wrappers (run_var_fp.sh real_* whose cwd is $A/<v>/forest) + their ot-run
# children, the remote forest python (pgrep on its own fp_<src>/real_ path) and a still-running GEN (gen_a ot-run pid).
# A variant that already has a forest VAR_DONE PASS is never cancelled.  Log: $A/fp2_cancel.log
V=$1; WHY=${2:-unspecified}; A=/home/ubuntu/artifacts/hdie-d4/d4g_gen2d; L=$A/$V; LOG=$A/fp2_cancel.log
echo "CANCEL $V start $(date -Is) reason: $WHY" >> $LOG
grep -qs '^VAR_DONE \S* PASS PASS' $L/forest/real_cplanR.otrun $L/forest/real_hhKR.otrun && { echo "$V has a PASS forest: not cancelled" >> $LOG; exit 0; }
touch $L/CANCELLED
k() { for p in "$@"; do [ "$p" = "$PPID" ] || [ "$p" = "$$" ] && continue; kids=$(pgrep -P $p); echo "  kill $p ($(tr '\0' ' ' < /proc/$p/cmdline 2>/dev/null | cut -c1-120)) kids $kids" >> $LOG; kill $p $kids 2>>$LOG; done; }
dp=$(cat $L/drive.pid 2>/dev/null || cat $L/fp_drive.pid 2>/dev/null)
[ -n "$dp" ] && tr '\0' ' ' < /proc/$dp/cmdline 2>/dev/null | grep -qE 'fp2?_drive\.sh' && k $dp
cp_=$(cat $A/post_fp_$V/chain.pid 2>/dev/null)
[ -n "$cp_" ] && tr '\0' ' ' < /proc/$cp_/cmdline 2>/dev/null | grep -q 'chain_d4g2d_post_fp' && k $cp_
for p in $(pgrep -f 'run_var_fp\.sh real_(cplanR|hhKR)'); do
  [ "$(readlink /proc/$p/cwd)" = "$L/forest" ] && k $p
done
for t in real_cplanR real_hhKR; do
  hs=$(sed -n 's/^VAR_START .* src=\([0-9a-f]*\) .*/\1/p' $L/forest/$t.otrun 2>/dev/null | head -1)
  host=$(sed -n 's/^VAR_START .* host=\(\S*\) .*/\1/p' $L/forest/$t.otrun 2>/dev/null | head -1)
  [ -n "$hs" ] && [ -n "$host" ] && ssh -o ControlPath=none $host "pids=\$(pgrep -f '[f]p_$hs/$t/'); echo remote $t \$pids; [ -n \"\$pids\" ] && kill \$pids" >> $LOG 2>&1
  [ -f $L/forest/$t.otrun ] && ! grep -q '^VAR_DONE' $L/forest/$t.otrun && echo "VAR_DONE $t CANCELLED by L2H-GEN2D-FP2 ($WHY) $(date -Is)" >> $L/forest/$t.otrun
done
gp=$(cat $L/gen_a.pid 2>/dev/null); [ -n "$gp" ] && tr '\0' ' ' < /proc/$gp/cmdline 2>/dev/null | grep -q 'ot-run' && k $gp
echo "CANCEL $V done $(date -Is)" >> $LOG
