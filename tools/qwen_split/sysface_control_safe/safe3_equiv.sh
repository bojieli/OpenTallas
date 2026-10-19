#!/bin/bash
# QW-SYSFACE3: two-state next-state equivalence of the SAFE3 leaves against the untouched originals
# (same register names; equiv_make/equiv_simple/equiv_induct, unconstrained inputs and present state),
# plus causal mutants that must FAIL.  Fleet only (ot-run).  Usage: safe3_equiv.sh OUTDIR
set -u
export PATH=$HOME/.local/opentallas-tools/yosys-0.68/bin:$PATH
O=${1:-safe3_equiv};mkdir -p "$O"
CTX=rtl/qwen_sys/context_transport_20261014/qkd_context_records.sv
CMT=rtl/qwen_sys/program_receiver_20261014/qkd_program_commit.sv
S3=rtl/qwen_split/qfd_sys_face_safe3.sv
prove(){ # name gold gate s3file
 cat > "$O/$1.ys" <<YS
read_verilog -sv $CTX $CMT $4
proc; opt_clean
async2sync
equiv_make $2 $3 eq_$1
hierarchy -top eq_$1
equiv_simple -seq 1
equiv_induct -seq 1
equiv_status -assert
YS
 yosys -Q -s "$O/$1.ys" > "$O/$1.log" 2>&1; echo $? > "$O/$1.rc"
}
prove ctx qfd_host_native_context_rx qfd_sys_face_context_rx_s3 $S3
prove commit qkd_program_commit qfd_sys_face_program_commit_s3 $S3
ok=1
for n in ctx commit; do
 if [ "$(cat $O/$n.rc)" = 0 ] && grep -q "Equivalence successfully proven" "$O/$n.log"; then echo "SAFE3_EQUIV_PASS $n $(grep -o "[0-9]* are proven and [0-9]* are unproven" $O/$n.log | head -1)"; else echo "SAFE3_EQUIV_FAIL $n"; ok=0; fi
done
# causal mutants (each must leave unproven equiv cells)
mut(){ # name gold gate sed-expr
 sed "$4" $S3 > "$O/mut_$1.sv"; cmp -s $S3 "$O/mut_$1.sv" && { echo "MUTANT_NOT_APPLIED $1"; ok=0; return; }
 prove "mut_$1" $2 $3 "$O/mut_$1.sv"
 if [ "$(cat $O/mut_$1.rc)" != 0 ] && grep -q "unproven" "$O/mut_$1.log"; then echo "SAFE3_MUTANT_FAIL_AS_EXPECTED $1 $(grep -o 'Found [0-9]* unproven [^.]*' $O/mut_$1.log | head -1)"; else echo "SAFE3_MUTANT_ESCAPED $1"; ok=0; fi
}
mut reserved qfd_host_native_context_rx qfd_sys_face_context_rx_s3 's/  |rx_record\[511:142\],/  1'"'"'b0,/'
mut late_image qfd_host_native_context_rx qfd_sys_face_context_rx_s3 's/wire hev_next=~changed_image&/wire hev_next=/'
mut sticky qfd_host_native_context_rx qfd_sys_face_context_rx_s3 's/(cause\[1\]|cause\[0\])/(cause[1])/'
mut dw_window qkd_program_commit qfd_sys_face_program_commit_s3 's/|(|count\[9:3\])//'
[ $ok = 1 ] && echo SAFE3_EQUIV_ALL_PASS || { echo SAFE3_EQUIV_SUITE_FAIL; exit 1; }
