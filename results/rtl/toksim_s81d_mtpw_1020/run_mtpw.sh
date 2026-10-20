#!/bin/bash
# TOKSIM-S81D/MTPW (10-20): S029-class 6-position verify-wave occupancy vehicle on the REAL release issuer
# (dsdv_seq_host + ot_dsdv_fixed_issue, blobs = release GEN mu4c 19bf4121e). One user's 6 verify positions
# (pos P0..P0+5, one job each) are issued back to back on one die's issuer with the compiled stage programme.
# Same TB / checker as MU-S81/TOK (tb_dv_prog_seqhost.sv +mu=, check_mu.py): PASS = position 0 line-identical to the
# single-position run, positions 1..5 = position 0's event trace moved by k x S with their own {user,pos,tok}
# context, no issuer fault, 6 jobs accepted.  Measured: KS_k - KS_0 (issue handoff), min legal spacing (overlap).
# run_mtpw.sh <tree R> <out O> <prog dir> <W = per-position stage window, edges>
set -u
R=$(realpath $1); O=$2; P=$(realpath $3); W=$4; mkdir -p $O; O=$(realpath $O)
L=$R/tools/s81_dv/layer_prog; CK="python3 $L/check_mu.py"
mkdir -p $O/base; CYC=3000 bash $L/run_seqhost_prog.sh $R $P $O/base > $O/base/summary.txt 2>&1; cat $O/base/summary.txt
TB=$O/base/obj/tb; [ -x $TB ] || { echo "MTPW BUILD_FAIL"; exit 3; }
N=$(grep -c . $P/prog/host_boot.memh)
mk() { local f=$1 s=$2; : > $f; for k in 0 1 2 3 4 5; do echo "$((k*s)) 0 $((5000+k)) 1000" >> $f; done; }
run() { local n=$1 m=$2; mkdir -p $O/$n; /usr/bin/time -v -o $O/$n/run.time $TB +dir=$P +n=$N +cyc=3000 +mu=$m > $O/$n/run.log 2>&1; }
mkdir -p $O/mu; echo "0 0 5000 1000" > $O/mu/single.txt; run single $O/mu/single.txt
SPAN=$(python3 - "$O/single/run.log" <<'PY'
import re,sys
t=open(sys.argv[1]).read(); ks=int(re.search(r'^PROG KS (\d+)',t,re.M).group(1))
ev=[int(m.group(1)) for m in re.finditer(r'^PROG (?:VO [NS]|CW|SJ|KD) (\d+) ',t,re.M)]
print(max(e for e in ev if e>=ks)-ks+1)
PY
)
echo "programme span (KS -> last event, edges): $SPAN"
SW=$(( (W+3)/4*4 )); mk $O/mu/p6_w.txt $SW; run p6_w $O/mu/p6_w.txt
echo "p6_w S=$SW: $($CK --dir $P --single $O/single/run.log --multi $O/p6_w/run.log --mu $O/mu/p6_w.txt)"
for s in 4 8 16 32 $(( (SPAN+3)/4*4 )) $(( (SPAN+3)/4*4+4 )) $(( (SPAN/2+3)/4*4 )); do
  mk $O/mu/p6_s$s.txt $s; run p6_s$s $O/mu/p6_s$s.txt
  echo "p6_s$s: $($CK --dir $P --single $O/single/run.log --multi $O/p6_s$s/run.log --mu $O/mu/p6_s$s.txt) | $(grep -m1 '^PROG FAULT' $O/p6_s$s/run.log || echo no-fault)"
done
mk $O/mu/m_off4.txt $((SW+2)); run m_off4 $O/mu/m_off4.txt
echo "m_off4 S=$((SW+2)): $($CK --dir $P --single $O/single/run.log --multi $O/m_off4/run.log --mu $O/mu/m_off4.txt) | $(grep -m1 '^PROG FAULT' $O/m_off4/run.log || echo no-fault)"
verilator_v=$(cat $O/base/verilator.version); echo "verilator: $verilator_v"
