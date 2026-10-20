#!/bin/bash
# TOKSIM-S81/HEADMU (10-19): MTP-calendar multi-user run of the REAL dsdv_seq_host (+ ot_dsdv_fixed_issue) on the
# release source (claude/s81-bind-mu4-1019 19bf4121e; dsdv_seq_host.sv / ot_dsdv_fixed_issue.sv blobs = release).
# Same TB/checker as tools/s81_dv/layer_prog/run_mu.sh (MU-S81/TOK); the only change is the calendar:
# prog_L0_mu_mtp = prog_L0_mu with prog/mu_slots.json from calendar_mtp_q4.json (10 MTP + 1 filler, slot 124,524,
# period 1,303,400), via dv_layer_compile.mu_slot_tables. One period (11 starts; 2 periods exceed the TB #2000000 timeout).
# Also re-runs L0_all (AR q4 46 users) for a release-pinned record, and mutant m_shift4 (must FAIL, issuer code 9).
# run_mu_mtp.sh <tree R> <out O>
set -u
R=$(realpath $1); O=$2; mkdir -p $O; O=$(realpath $O)
L=$R/tools/s81_dv/layer_prog; D=$R/results/rtl/toksim_s81_headmu_1019
PB=$R/results/rtl/s81_layer_tput_1018/compiler/prog_L0_s0S; PA=$R/results/rtl/s81_mu_1018/prog_L0_mu; PM=$D/prog_L0_mu_mtp
CK="python3 $L/check_mu.py"
mkdir -p $O/base; CYC=3000 bash $L/run_seqhost_prog.sh $R $PB $O/base > $O/base/summary.txt 2>&1; cat $O/base/summary.txt
TB=$O/base/obj/tb; [ -x $TB ] || { echo "MU BUILD_FAIL"; exit 3; }
run() { local n=$1 p=$2 m=$3; shift 3; mkdir -p $O/$n
  local N=$(grep -c . $p/prog/host_boot.memh)
  /usr/bin/time -v -o $O/$n/run.time $TB +dir=$p +n=$N +cyc=3000 +mu=$m "$@" > $O/$n/run.log 2>&1; }
mkdir -p $O/mu
$CK --make $PM/prog/mu_slots.json --copy A --out $O/mu/p0.txt --pass 0 > /dev/null
$CK --make $PM/prog/mu_slots.json --copy A --out $O/mu/p1.txt --pass 1 > /dev/null
P=$(python3 -c "import json;print(json.load(open('$PM/prog/mu_slots.json'))['period'])")
cp $O/mu/p0.txt $O/mu/L0_mtp.txt   # one period (11 starts, 1.25M edges): the TB times out at #2000000
head -1 $O/mu/L0_mtp.txt > $O/mu/L0_single.txt
$CK --make $PA/prog/mu_slots.json --copy A --out $O/mu/L0_all.txt > /dev/null
head -1 $O/mu/L0_all.txt > $O/mu/L0_all_single.txt
U0=$(head -1 $O/mu/L0_mtp.txt); U1=$(sed -n 2p $O/mu/L0_mtp.txt | cut -d' ' -f2-)
printf '%s\n4 %s\n' "$U0" "$U1" > $O/mu/m_shift4.txt
run L0_single $PM $O/mu/L0_single.txt
run L0_mtp $PM $O/mu/L0_mtp.txt
run L0_all_single $PA $O/mu/L0_all_single.txt
run L0_all $PA $O/mu/L0_all.txt
run m_shift4 $PM $O/mu/m_shift4.txt
{
echo "L0_mtp: $($CK --dir $PM --single $O/L0_single/run.log --multi $O/L0_mtp/run.log --mu $O/mu/L0_mtp.txt)"
echo "L0_all: $($CK --dir $PA --single $O/L0_all_single/run.log --multi $O/L0_all/run.log --mu $O/mu/L0_all.txt)"
echo "m_shift4: $($CK --dir $PM --single $O/L0_single/run.log --multi $O/m_shift4/run.log --mu $O/mu/m_shift4.txt)"
echo "m_shift4 issuer: $(grep -m1 '^PROG FAULT' $O/m_shift4/run.log || echo 'no fault')"
} | tee $O/summary.txt
grep -q '^L0_mtp: SEQHOST_MU PASS' $O/summary.txt && grep -q '^L0_all: SEQHOST_MU PASS' $O/summary.txt && grep -q '^m_shift4: SEQHOST_MU FAIL' $O/summary.txt \
  && echo HEADMU_SEQHOST_MTP_GATE PASS || { echo HEADMU_SEQHOST_MTP_GATE FAIL; exit 1; }
